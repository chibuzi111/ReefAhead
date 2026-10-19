#!/usr/bin/env python3
"""Download authentic NOAA CRW observations; never synthesize missing observations.

Default model data start in 2003 to avoid the legacy OSTIA licensing ambiguity.
Use --start-year 1985 explicitly for research-only historical archive.
"""
from __future__ import annotations
import argparse, csv, hashlib, io, json, os, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
import requests

BASE = "https://coastwatch.pfeg.noaa.gov/erddap"
VARIABLES = ["CRW_SST", "CRW_HOTSPOT", "CRW_DHW", "CRW_SSTANOMALY"]
# Ocean sampling cells selected in the Semporna offshore area, NOT surveyed reef
# boundaries, dive sites, or in situ sensors. Return coordinates are checked.
SITES = [
    {"site_id":"semporna_south_central", "latitude":4.275, "longitude":118.625},
    {"site_id":"semporna_offshore_1", "latitude":4.275, "longitude":118.725},
    {"site_id":"semporna_offshore_2", "latitude":4.275, "longitude":118.825},
    {"site_id":"semporna_offshore_3", "latitude":4.275, "longitude":118.925},
]
FIELDS = ["date","site_id","latitude","longitude","sst","hotspot","dhw","ssta","spatial_support","source"]
LICENSE_NOTE = ("NOAA CRW requests credit and citation and states CRW-produced products are available without restriction. "
    "Redistributor NOAA_DHW metadata also retains a legacy OSTIA 1985-2002 academic-only/5-year/reproduction-license statement. "
    "These statements are not resolved by this project. Default analysis starts 2003; earlier source records are archived "
    "for provenance only unless --start-year 1985 is explicitly requested. No exclusive ownership claimed. "
    "See metadata snapshot and https://coralreefwatch.noaa.gov/satellite/docs/recommendations_crw_citation.php .")
HEADERS = {"User-Agent":"AI4Climate-SempornaResearch/0.1 (public research prototype; NOAA CRW attribution retained)"}

_local = threading.local()

def session():
    if not hasattr(_local, "session"):
        _local.session = requests.Session()
    return _local.session

def stamp():
    return datetime.now(timezone.utc).isoformat()

def download(url, path, timeout=120, retries=3):
    path.parent.mkdir(parents=True,exist_ok=True)
    meta_path = path.with_suffix(path.suffix+".meta.json")
    if path.exists() and meta_path.exists():
        m=json.loads(meta_path.read_text())
        if hashlib.sha256(path.read_bytes()).hexdigest()==m["sha256"] and m["url"]==url:
            return m
    err=None
    for attempt in range(retries):
        try:
            r=session().get(url,timeout=(45,timeout),headers=HEADERS)
            r.raise_for_status()
            if not r.content: raise ValueError("empty response")
            data=r.content
            tmp=path.with_suffix(path.suffix+".part")
            tmp.write_bytes(data); tmp.replace(path)
            m={"url":url,"resolved_url":r.url,"retrieved_at_utc":stamp(),"sha256":hashlib.sha256(data).hexdigest(),
               "bytes":len(data),"path":str(path),"content_type":r.headers.get("Content-Type"),"license_note":LICENSE_NOTE}
            meta_path.write_text(json.dumps(m,indent=2,ensure_ascii=False)+"\n")
            return m
        except Exception as e:
            err=e
            if attempt+1<retries: time.sleep(2**attempt)
    raise RuntimeError(f"{url}: {err}")

def erddap_url(site,start,end):
    sl=f"[({start}T12:00:00Z):1:({end}T12:00:00Z)][({site['latitude']})][({site['longitude']})]"
    return BASE+"/griddap/NOAA_DHW.csv?"+",".join(v+sl for v in VARIABLES)

def expected_grid_keys(start, end):
    lo,hi=date.fromisoformat(start),date.fromisoformat(end)
    return {(f"{lo+timedelta(days=i)}T12:00:00Z",f"{s['latitude']:.3f}",f"{s['longitude']:.3f}")
            for i in range((hi-lo).days+1) for s in SITES}

def csv_key(item):
    return (item["time"],f"{float(item['latitude']):.3f}",f"{float(item['longitude']):.3f}")

def gap_spans(keys):
    dates=sorted({date.fromisoformat(k[0][:10]) for k in keys})
    spans=[]
    for d in dates:
        if spans and d==spans[-1][1]+timedelta(days=1): spans[-1][1]=d
        else: spans.append([d,d])
    return spans

def fill_mirror_gaps(root, year, quarter, merged, expected, parts):
    missing={key for key in expected if set(merged.get(key,{}))!=set(VARIABLES)}
    if not missing: return
    for lo,hi in gap_spans(missing):
        sl=f"[({lo}T12:00:00Z):1:({hi}T12:00:00Z)][(4.275)][(118.625):2:(118.925)]"
        url="https://pae-paha.pacioos.hawaii.edu/erddap/griddap/dhw_5km.csv?"+",".join(v+sl for v in VARIABLES)
        path=root/"raw"/"noaa_crw_transect"/"gap_fill"/f"{lo}_{hi}_pacioos.csv"
        meta=download(url,path,timeout=120,retries=3)
        overlap=0;max_diff=0.0;filled=0
        for row in csv.DictReader(path.read_text().splitlines()):
            if row["time"]=="UTC": continue
            key=csv_key(row)
            if key not in expected: raise ValueError(f"Unexpected gap-fill key: {key}")
            dest=merged.setdefault(key,{})
            for v in VARIABLES:
                if v in dest:
                    diff=abs(float(dest[v])-float(row[v]));overlap+=1;max_diff=max(max_diff,diff)
                    if diff>1e-8: raise ValueError(f"Mirror disagreement {key} {v}: {dest[v]} != {row[v]}")
                else: dest[v]=row[v];filled+=1
        meta.update({"purpose":"Fill only missing PIFSC mirror dates/variables with genuine same-product PacIOOS observations; no interpolation",
                     "filled_values":filled,"overlap_values_compared":overlap,"overlap_max_absolute_difference":max_diff})
        parts.append(meta)
        print(f"Gap fill {lo}..{hi}: {filled} values; {overlap} overlapping values agree (max diff {max_diff})",flush=True)
    if any(set(merged.get(k,{}))!=set(VARIABLES) for k in expected):
        raise ValueError(f"Unresolved gaps for {year} Q{quarter}; refusing partial year")

def reconcile_documented_2019_mirror_discrepancy(root,path,meta,year):
    """Use genuine same-product observations for a verified PIFSC HS/SSTA conflict.
    Source choice was independently checked against NOAA STAR producer NetCDF
    for 2019-04-02. The original PIFSC responses are never edited.
    """
    if year!=2019: return meta
    table=[r for r in csv.DictReader(path.read_text().splitlines()) if r["time"]!="UTC"]
    lookup={csv_key(r):r for r in table}
    sl="[(2019-04-01T12:00:00Z):1:(2019-04-17T12:00:00Z)][(4.275)][(118.625):2:(118.925)]"
    url="https://pae-paha.pacioos.hawaii.edu/erddap/griddap/dhw_5km.csv?"+",".join(v+sl for v in VARIABLES)
    source=root/"raw"/"probes"/"pacioos_2019_mmm_audit.csv"
    source_meta=download(url,source,timeout=120,retries=3)
    differences=[]
    replacements=0
    for r in csv.DictReader(source.read_text().splitlines()):
        if r["time"]=="UTC": continue
        key=csv_key(r)
        if key not in lookup: raise ValueError(f"Correction key absent from year: {key}")
        old=lookup[key]
        for v in VARIABLES:
            if abs(float(old[v])-float(r[v]))>1e-8:
                if not ("2019-04-02"<=key[0][:10]<="2019-04-16") or v not in ["CRW_HOTSPOT","CRW_SSTANOMALY"]:
                    raise ValueError(f"Unexpected cross-source discrepancy requires independent review: {key} {v}")
                differences.append({"key":list(key),"variable":v,"pifsc_value":old[v],"pacioos_value":r[v]})
                old[v]=r[v];replacements+=1
    if not differences: return meta
    archive=root/"raw"/"noaa_crw_transect"/"archived";archive.mkdir(parents=True,exist_ok=True)
    name=f"{year}_{meta['sha256'][:12]}_before_semantic_repair"
    (archive/(name+".csv")).write_bytes(path.read_bytes())
    archived_meta=dict(meta);archived_meta["original_path"]=meta["path"];archived_meta["path"]=str(archive/(name+".csv"))
    (archive/(name+".csv.meta.json")).write_text(json.dumps(archived_meta,ensure_ascii=False,indent=2)+"\n")
    producer_sources=[]
    for prod in ["hs","ssta","dhw"]:
        source_name=f"ct5km_{prod}_v3.1_20190402.nc"
        producer_path=root/"raw"/"probes"/source_name
        producer_url=f"https://www.star.nesdis.noaa.gov/pub/socd/mecb/crw/data/5km/v3.1_op/nc/v1.0/daily/{prod}/2019/"+source_name
        producer_sources.append(download(producer_url,producer_path,timeout=120,retries=3))
    source_meta.update({"purpose":"Verified correction of PIFSC HotSpot/SSTA mirror inconsistency, 2019-04-02 through 2019-04-16; PacIOOS agrees with NOAA STAR producer sample 2019-04-02",
        "corrected_values":replacements,"differences":differences,"source_requests":producer_sources,
        "scope_of_third_source_verification":"One representative day, four fixed pixels, HS/SSTA/DHW; not a second download of all 15 days"})
    out=io.StringIO();writer=csv.DictWriter(out,fieldnames=["time","latitude","longitude",*VARIABLES],lineterminator="\n")
    writer.writeheader();writer.writerow(dict(zip(["time","latitude","longitude",*VARIABLES],["UTC","degrees_north","degrees_east","Celsius","Celsius","Celsius weeks","Celsius"])))
    writer.writerows(table);data=out.getvalue().encode()
    tmp=path.with_suffix(".csv.part");tmp.write_bytes(data);tmp.replace(path)
    meta=dict(meta);meta.update({"url":"derived:audited-multi-source-join","resolved_url":None,"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data),"assembled_at_utc":stamp(),
        "semantic_correction":{"changed_values":replacements,"date_start":"2019-04-02","date_end":"2019-04-16","variables":["CRW_HOTSPOT","CRW_SSTANOMALY"],"previous_annual_sha256":archived_meta["sha256"]}})
    meta["source_requests"]=[*meta.get("source_requests",[]),source_meta]
    meta["derivation"]+=" Documented 2019 HS/SSTA mirror discrepancy replaced by independent genuine PacIOOS values, with NOAA producer sample verification; original mirror responses and pre-repair annual file retained."
    path.with_suffix(".csv.meta.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n")
    print(f"Semantic source reconciliation {year}: {replacements} values, original observations retained",flush=True)
    return meta

def fetch_year(root, year, end_date):
    start=f"{year}-01-01" if year!=1985 else "1985-04-01"
    end=min(f"{year}-12-31",end_date)
    sl=f"[({start}T12:00:00Z):1:({end}T12:00:00Z)][(4.275)][(118.625):2:(118.925)]"
    url=BASE+"/griddap/NOAA_DHW.csv?"+",".join(v+sl for v in VARIABLES)
    path=root/"raw"/"noaa_crw_transect"/f"{year}.csv"
    meta_path=path.with_suffix(".csv.meta.json")
    cached=False
    if path.exists() and meta_path.exists():
        meta=json.loads(meta_path.read_text())
        cached=hashlib.sha256(path.read_bytes()).hexdigest()==meta["sha256"]
        if cached:
            table=[r for r in csv.DictReader(path.read_text().splitlines()) if r["time"]!="UTC"]
            keys=[csv_key(r) for r in table]
            cached=len(keys)==len(set(keys)) and set(keys)==expected_grid_keys(start,end)
            if not cached:
                # Preserve the previous derived file and metadata; original requests remain untouched.
                archive=root/"raw"/"noaa_crw_transect"/"archived"
                archive.mkdir(parents=True,exist_ok=True)
                name=f"{year}_{meta['sha256'][:12]}"
                (archive/(name+".csv")).write_bytes(path.read_bytes())
                (archive/(name+".csv.meta.json")).write_bytes(meta_path.read_bytes())
    if not cached:
        parts=[]
        output=[]
        for q,(lo,hi) in enumerate([("01-01","03-31"),("04-01","06-30"),("07-01","09-30"),("10-01","12-31")],1):
            qstart=max(start,f"{year}-{lo}");qend=min(end,f"{year}-{hi}")
            if qstart>qend: continue
            qsl=f"[({qstart}T12:00:00Z):1:({qend}T12:00:00Z)][(4.275)][(118.625):2:(118.925)]"
            # Independent NOAA OceanWatch PIFSC mirror of the same CRW v3.1 products.
            # Separate variable datasets; preserve every unmodified response and metadata.
            providers=[
                ("CRW_SST","CRW_sst_v3_1","analysed_sst"),
                ("CRW_HOTSPOT","CRW_hs_v1_0","hotspot"),
                ("CRW_DHW","CRW_dhw_v1_0","degree_heating_week"),
                ("CRW_SSTANOMALY","CRW_sst_anom_v1_0","sea_surface_temperature_anomaly")]
            merged={}
            expected_keys=expected_grid_keys(qstart,qend)
            excluded_outside_requested_window=[]
            for target,dataset,variable in providers:
                qurl="https://oceanwatch.pifsc.noaa.gov/erddap/griddap/"+dataset+".csv?"+variable+qsl
                qp=root/"raw"/"noaa_crw_transect"/"quarterly"/f"{year}_Q{q}_{dataset}.csv"
                qm=download(qurl,qp,timeout=120,retries=3)
                table=list(csv.DictReader(qp.read_text().splitlines()))
                keys=set()
                for item in table:
                    if item["time"]=="UTC": continue
                    key=csv_key(item)
                    if key in keys: raise ValueError("Duplicate key from PIFSC")
                    keys.add(key)
                    if key[0][:10]<qstart or key[0][:10]>qend:
                        excluded_outside_requested_window.append({"variable":target,"key":list(key)})
                        continue
                    if key not in expected_keys: raise ValueError(f"Unexpected PIFSC grid/time key: {key}")
                    merged.setdefault(key,{})[target]=item[variable]
                qm.update({"selected_date_start":qstart,"selected_date_end":qend,
                           "out_of_window_rows_excluded":sum(k[0][:10]<qstart or k[0][:10]>qend for k in keys)})
                parts.append(qm)
            fill_mirror_gaps(root,year,q,merged,expected_keys,parts)
            if set(merged)!=expected_keys: raise ValueError(f"Unexpected quarterly grid coverage {year} Q{q}")
            lines=[]
            if not output:
                lines=["time,latitude,longitude,"+",".join(VARIABLES),
                       "UTC,degrees_north,degrees_east,Celsius,Celsius,Celsius weeks,Celsius"]
            for key,values in sorted(merged.items()):
                lines.append(",".join([*key,*[values[v] for v in VARIABLES]]))
            output.extend(lines)
            print(f"Quarter {year} Q{q}: {len(merged)} rows, all four variables downloaded",flush=True)
        data=("\n".join(output)+"\n").encode()
        path.parent.mkdir(parents=True,exist_ok=True)
        tmp=path.with_suffix(".csv.part");tmp.write_bytes(data);tmp.replace(path)
        meta={"url":"derived:quarterly-concatenation","resolved_url":None,"path":str(path),
            "sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data),"assembled_at_utc":stamp(),
            "retrieved_at_utc":stamp(),"content_type":"text/csv","license_note":LICENSE_NOTE,
            "source_requests":parts,"derivation":"Strict requested-date/calendar/key join of NOAA PIFSC CRW v3.1 variable CSVs; missing mirror values filled only from genuine same-product PacIOOS observations, with overlapping values compared; out-of-window ERDDAP nearest-boundary rows excluded; original responses retained; no interpolation or numeric value changes."}
        meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n")
    meta=reconcile_documented_2019_mirror_discrepancy(root,path,meta,year)
    meta.update({"spatial_support":"four fixed 0.05 degree satellite ocean cells; not validated reef sites",
                 "requested_latitude":4.275,"requested_longitudes":[s["longitude"] for s in SITES],
                 "requested_start":start,"requested_end":end})
    rows=[]
    for r in csv.DictReader(path.read_text().splitlines()):
        if r["time"]=="UTC": continue
        vals={k:float(r[v]) for k,v in zip(["sst","hotspot","dhw","ssta"],VARIABLES)}
        if any(not (-10 < vals[k] < 100) for k in vals): continue
        lat,lon=float(r["latitude"]),float(r["longitude"])
        site=next((s for s in SITES if abs(s["latitude"]-lat)<0.0001 and abs(s["longitude"]-lon)<0.0001),None)
        if site is None: raise ValueError("unexpected grid coordinates")
        rows.append({"date":r["time"][:10],"site_id":site["site_id"],"latitude":lat,"longitude":lon,**vals,
                     "spatial_support":"fixed_5km_satellite_pixel","source":"NOAA_CRW_v3.1"})
    expected_rows=len(expected_grid_keys(start,end))
    if len(rows)!=expected_rows: raise ValueError(f"Incomplete valid observations in {year}: {len(rows)} != {expected_rows}")
    if len({(r['date'],r['site_id']) for r in rows})!=expected_rows: raise ValueError(f"Duplicate site/date in {year}")
    if set(r["site_id"] for r in rows)!={s["site_id"] for s in SITES}:
        raise ValueError(f"Not all four pixels contain valid ocean data in {year}")
    for site in SITES:
        mmm=[r["sst"]-r["hotspot"] for r in rows if r["site_id"]==site["site_id"]]
        if max(mmm)-min(mmm)>0.011:
            raise ValueError(f"SST/HotSpot MMM inconsistency in {year}, {site['site_id']}; source review required")
    meta.update({"valid_rows":len(rows),"date_min":min(r["date"] for r in rows),"date_max":max(r["date"] for r in rows)})
    return rows,meta

def fetch_regional(root, end_date):
    path=root/"raw"/"noaa_crw_regional"/"sabah.txt"
    meta=download("https://coralreefwatch.noaa.gov/product/vs/data/sabah.txt",path)
    lines=path.read_text().splitlines()
    header=next(i for i,s in enumerate(lines) if s.startswith("YYYY"))
    rows=[]
    for line in lines[header+1:]:
        p=line.split()
        if len(p)<10: continue
        d=f"{int(p[0]):04d}-{int(p[1]):02d}-{int(p[2]):02d}"
        if d>end_date or d<"1985-03-25": continue
        vals=dict(sst=float(p[5]),ssta=float(p[6]),hotspot=float(p[7]),dhw=float(p[8]))
        if any(not (-10 < v < 100) for v in vals.values()) or vals["dhw"]<0: continue
        rows.append({"date":d,"site_id":"sabah_regional","latitude":5.8,"longitude":117.2,**vals,
            "spatial_support":"regional_90th_percentile_hotspot_moving_pixel","source":"NOAA_CRW_RVS_v3.1"})
    meta.update({"valid_rows":len(rows),"date_min":rows[0]["date"],"date_max":rows[-1]["date"],
        "spatial_support":"Sabah regional 90th percentile HotSpot; SST is a moving pixel, not Semporna local observations",
        "marker_latitude":5.8,"marker_longitude":117.2})
    return rows,meta

def write_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(".tmp")
    with tmp.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(sorted(rows,key=lambda r:(r["site_id"],r["date"])))
    tmp.replace(path)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data-dir",default=os.environ.get("CLIMATE_DATA_DIR","data"))
    p.add_argument("--start-year",type=int,default=2003)
    p.add_argument("--end-date",default="2026-10-12",help="Frozen research cutoff; never use dates after retrieval")
    p.add_argument("--workers",type=int,default=2)
    p.add_argument("--regional-only",action="store_true")
    p.add_argument("--skip-regional",action="store_true")
    args=p.parse_args()
    if date.fromisoformat(args.end_date)>datetime.now(timezone.utc).date(): raise ValueError("Future cutoff forbidden")
    root=Path(args.data_dir); root.mkdir(parents=True,exist_ok=True)
    manifest={"created_at_utc":stamp(),"analysis_start_year":args.start_year,"cutoff":args.end_date,"sources":[],"failures":[],"complete":False,
       "sites":SITES,"spatial_warning":"Cells are ocean sampling pixels, not validated reef locations; use only for thermal exposure screening.",
       "license_note":LICENSE_NOTE}
    if not args.skip_regional:
        rows,m=fetch_regional(root,args.end_date); manifest["sources"].append(m)
        write_csv(root/"processed"/"sabah_regional.csv",rows)
        print(f"Sabah regional saved: {len(rows)} authentic daily records",flush=True)
    all_rows=[]
    if not args.regional_only:
        for name,url in [
            ("noaa_dhw_metadata.html",BASE+"/info/NOAA_DHW/index.html"),
            ("noaa_methodology.html","https://coralreefwatch.noaa.gov/product/5km/methodology.php"),
            ("noaa_crw_citation.html","https://coralreefwatch.noaa.gov/satellite/docs/recommendations_crw_citation.php"),
            ("pifsc_sst_metadata.json","https://oceanwatch.pifsc.noaa.gov/erddap/info/CRW_sst_v3_1/index.json"),
            ("pifsc_hs_metadata.json","https://oceanwatch.pifsc.noaa.gov/erddap/info/CRW_hs_v1_0/index.json"),
            ("pifsc_dhw_metadata.json","https://oceanwatch.pifsc.noaa.gov/erddap/info/CRW_dhw_v1_0/index.json"),
            ("pifsc_ssta_metadata.json","https://oceanwatch.pifsc.noaa.gov/erddap/info/CRW_sst_anom_v1_0/index.json")]:
            try: manifest["sources"].append(download(url,root/"raw"/"metadata"/name))
            except Exception as e: manifest["failures"].append({"metadata":name,"error":str(e)})
        jobs=list(range(args.start_year,int(args.end_date[:4])+1))
        priority=[2022,2023,2024,2025,2020,2021,2017,2018,2019]
        jobs=sorted(jobs,key=lambda y:(priority.index(y) if y in priority else len(priority)+y))
        # Two requests maximum; bounded network concurrency and cached chunks.
        with ThreadPoolExecutor(max_workers=max(1,min(args.workers,2))) as ex:
            futures={ex.submit(fetch_year,root,y,args.end_date):y for y in jobs}
            for fut in as_completed(futures):
                y=futures[fut]
                try:
                    rows,m=fut.result(); all_rows.extend(rows); manifest["sources"].append(m)
                    print(f"Semporna transect {y}: {len(rows)} rows",flush=True)
                    write_csv(root/"processed"/"daily.partial.csv",all_rows)
                except Exception as e:
                    manifest["failures"].append({"year":y,"error":str(e)})
                    print(f"FAILED {y}: {e}",flush=True)
                (root/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
        if all_rows:
            write_csv(root/"processed"/("daily.csv" if not manifest["failures"] else "daily.incomplete.csv"),all_rows)
            print(f"Semporna fixed-pixel saved: {len(all_rows)} authentic daily records",flush=True)
    manifest["complete"]=not manifest["failures"]
    manifest["fixed_pixel_rows"]=len(all_rows)
    manifest["completed_at_utc"]=stamp()
    (root/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    if manifest["failures"]: raise SystemExit("Some requests failed; inspect manifest.json and rerun (cached files are reused).")

if __name__=="__main__": main()
