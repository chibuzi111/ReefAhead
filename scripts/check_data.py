#!/usr/bin/env python3
"""Audit downloaded NOAA records without filling missing dates."""
import argparse,csv,hashlib,json,math,statistics
from collections import defaultdict
from datetime import date,timedelta,datetime,timezone
from pathlib import Path
from verify_noaa_producer import verify as verify_producer_sample

p=argparse.ArgumentParser()
p.add_argument("--data-dir",default="data")
a=p.parse_args();root=Path(a.data_dir)
manifest=json.loads((root/"manifest.json").read_text())
assert manifest.get("complete") is True,"Download is not marked complete"
assert not manifest.get("failures"),"Source downloads failed"
verified=0
def check_source(m):
    global verified
    path=Path(m["path"])
    assert hashlib.sha256(path.read_bytes()).hexdigest()==m["sha256"],f"Checksum mismatch {path}"
    verified+=1
    for child in m.get("source_requests",[]): check_source(child)
for m in manifest["sources"]: check_source(m)
processed_path=root/"processed"/"daily.csv"
rows=list(csv.DictReader(processed_path.open()))
assert len(rows)==manifest["fixed_pixel_rows"],"Manifest row count differs from processed file"
expected_coords={s["site_id"]:(s["latitude"],s["longitude"]) for s in manifest["sites"]}
raw_values={}
annual_sources=[m for m in manifest["sources"] if Path(m["path"]).parent==root/"raw"/"noaa_crw_transect" and Path(m["path"]).suffix==".csv"]
assert len(annual_sources)==int(manifest["cutoff"][:4])-manifest["analysis_start_year"]+1,"Missing annual source files"
for m in annual_sources:
    for r in csv.DictReader(Path(m["path"]).read_text().splitlines()):
        if r["time"]=="UTC": continue
        key=(r["time"][:10],float(r["latitude"]),float(r["longitude"]))
        assert key not in raw_values,("Duplicate raw key across years",key)
        raw_values[key]=tuple(float(r[v]) for v in ["CRW_SST","CRW_HOTSPOT","CRW_DHW","CRW_SSTANOMALY"])
assert len(raw_values)==len(rows),"Raw and processed record counts differ"
groups=defaultdict(list)
for r in rows:
    d=date.fromisoformat(r["date"])
    assert r["site_id"] in expected_coords,"Unknown processed site"
    coords=(float(r["latitude"]),float(r["longitude"]))
    assert coords==expected_coords[r["site_id"]],"Coordinate/site mapping changed"
    key=(r["date"],*coords)
    assert key in raw_values,"Processed row absent from original annual data"
    assert tuple(float(r[v]) for v in ["sst","hotspot","dhw","ssta"])==raw_values[key],"Processed value differs from source"
    assert r["spatial_support"]=="fixed_5km_satellite_pixel" and r["source"]=="NOAA_CRW_v3.1"
    assert date(manifest["analysis_start_year"],1,1)<=d<=date.fromisoformat(manifest["cutoff"])
    for col,lo,hi in [("sst",-2,50),("hotspot",-15,15),("dhw",0,100),("ssta",-15,15)]:
        val=float(r[col]);assert math.isfinite(val) and lo<=val<=hi,(r["site_id"],r["date"],col,val)
    groups[r["site_id"]].append(r)
assert set(groups)=={s["site_id"] for s in manifest["sites"]}
report={"checked_at_utc":datetime.now(timezone.utc).isoformat(),"source_sha256_verified":verified,
        "raw_requests_complete":True,"rows":len(rows),
        "processed_sha256":hashlib.sha256(processed_path.read_bytes()).hexdigest(),
        "source_value_rows_verified":len(raw_values),"annual_sources_verified":len(annual_sources),"synthetic_observations":0,"interpolation_applied":False,"sites":{}}
for site,rs in groups.items():
    dates=[date.fromisoformat(r["date"]) for r in rs]
    assert len(set(dates))==len(dates),"Duplicate site/date"
    start=date(manifest["analysis_start_year"],1,1);end=date.fromisoformat(manifest["cutoff"])
    expected={start+timedelta(days=i) for i in range((end-start).days+1)}
    missing=sorted(expected-set(dates))
    records={date.fromisoformat(r["date"]):r for r in rs}
    diff=[]
    for d in dates:
        window=[d-timedelta(days=i) for i in range(84)]
        if all(t in records for t in window):
            reconstructed=sum(float(records[t]["hotspot"]) for t in window if float(records[t]["hotspot"])>=1)/7
            diff.append(abs(reconstructed-float(records[d]["dhw"])))
    mmm=[float(r["sst"])-float(r["hotspot"]) for r in rs]
    assert max(mmm)-min(mmm)<=0.011,f"SST minus HotSpot climatology inconsistency: {site}"
    report["sites"][site]={"rows":len(rs),"date_min":str(min(dates)),"date_max":str(max(dates)),
        "missing_calendar_dates":[str(d) for d in missing],"duplicates":0,
        "inferred_mmm_min":min(mmm),"inferred_mmm_max":max(mmm),
        "dhw_84day_reconstruction":{"valid_windows":len(diff),"mean_abs_difference":statistics.mean(diff) if diff else None,
                                   "max_abs_difference":max(diff) if diff else None,
                                   "note":"Uses rounded public HS; small differences from rounded official DHW are expected."}}
report["calendar_complete"]=all(not x["missing_calendar_dates"] for x in report["sites"].values())
assert report["calendar_complete"],"Missing calendar dates remain; complete dataset is required for the frozen experiment"
report["gap_fill_summary"]={"requests":sum("filled_values" in c for m in annual_sources for c in m.get("source_requests",[])),
    "genuine_values_filled":sum(c.get("filled_values",0) for m in annual_sources for c in m.get("source_requests",[])),
    "overlap_values_compared":sum(c.get("overlap_values_compared",0) for m in annual_sources for c in m.get("source_requests",[])),
    "maximum_overlap_difference":max([c.get("overlap_max_absolute_difference",0) for m in annual_sources for c in m.get("source_requests",[])]+[0]),
    "out_of_window_rows_excluded":sum(c.get("out_of_window_rows_excluded",0) for m in annual_sources for c in m.get("source_requests",[]))}
report["semantic_source_reconciliation"]=[m["semantic_correction"] for m in annual_sources if "semantic_correction" in m]
report["sst_hotspot_mmm_consistency_passed"]=True
report["producer_sample_verification"]=verify_producer_sample(root)
report["model_policy"]="Use calendar reindexing; never silently bridge gaps. Drop incomplete feature/label windows."
out=root/"processed"/"data_quality.json";out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(report,ensure_ascii=False,indent=2))
