"""Independent reconstruction of frozen inputs from original response bytes.

Does not import the ingestion pipeline or edit data; writes one audit artifact.
Run from any working directory with the project environment.
"""
from pathlib import Path
from datetime import date,timedelta,datetime,timezone
from collections import Counter
import csv,json,hashlib,math,os
ROOT=Path(__file__).resolve().parents[1]
DATA=Path(os.environ.get('CLIMATE_DATA_DIR','data'))
FIELDS={'CRW_SST':'sst','CRW_HOTSPOT':'hotspot','CRW_DHW':'dhw','CRW_SSTANOMALY':'ssta'}
ALIASES={'analysed_sst':'CRW_SST','hotspot':'CRW_HOTSPOT','degree_heating_week':'CRW_DHW','sea_surface_temperature_anomaly':'CRW_SSTANOMALY',**{k:k for k in FIELDS}}
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(p):
    for row in csv.DictReader(Path(p).read_text().splitlines()):
        if row.get('time')!='UTC':yield row
def key(r):return (r['time'][:10],float(r['latitude']),float(r['longitude']))
def main():
    manifest=json.loads((DATA/'manifest.json').read_text())
    assert manifest['complete'] and not manifest['failures']
    count=0
    def verify(m):
        nonlocal count
        assert digest(m['path'])==m['sha256'],m['path']
        assert Path(m['path']).stat().st_size==m['bytes'],m['path']
        count+=1
        for c in m.get('source_requests',[]):verify(c)
    for m in manifest['sources']:verify(m)
    annual=[m for m in manifest['sources'] if Path(m['path']).parent==DATA/'raw/noaa_crw_transect' and Path(m['path']).suffix=='.csv']
    source={};reconstructed_years=[];request_counts=Counter();overlap_count=0;explicit_corrections=0
    for m in annual:
        observed={key(r):{v:float(r[v]) for v in FIELDS} for r in rows(m['path'])}
        assert not set(source).intersection(observed)
        children=m.get('source_requests',[])
        if children:
            restored={}
            for c in children:
                request_counts['pifsc' if 'oceanwatch.pifsc.noaa.gov' in c['url'] else 'pacioos' if 'pacioos' in c['url'] else 'other']+=1
                lower=c.get('selected_date_start',m['requested_start']);upper=c.get('selected_date_end',m['requested_end'])
                corrections={((d['key'][0][:10],float(d['key'][1]),float(d['key'][2])),d['variable']):d for d in c.get('differences',[])}
                changed_here=0
                for r in rows(c['path']):
                    k=key(r)
                    if not lower<=k[0]<=upper:continue
                    dest=restored.setdefault(k,{})
                    for header,target in ALIASES.items():
                        if header in r:
                            value=float(r[header]);assert math.isfinite(value)
                            if target in dest:
                                if abs(dest[target]-value)>=1e-8:
                                    change=corrections.get((k,target));assert change is not None,('Undocumented disagreement',k,target)
                                    assert abs(dest[target]-float(change['pifsc_value']))<1e-8
                                    assert abs(value-float(change['pacioos_value']))<1e-8
                                    assert m.get('semantic_correction'),('Unmarked annual correction',m['path'])
                                    changed_here+=1;explicit_corrections+=1
                                else:overlap_count+=1
                            dest[target]=value
                if corrections:assert changed_here==c['corrected_values']==len(corrections)
            assert set(restored)==set(observed),m['path']
            for k,vs in observed.items():
                assert set(restored[k])==set(FIELDS)
                for v,x in vs.items():assert abs(x-restored[k][v])<1e-8,(k,v,x,restored[k][v])
            reconstructed_years.append(Path(m['path']).stem)
        source.update(observed)
    daily_path=DATA/'processed/daily.csv';daily=list(csv.DictReader(daily_path.open()))
    assert len(daily)==manifest['fixed_pixel_rows']==len(source)
    coordinates={s['site_id']:(s['latitude'],s['longitude']) for s in manifest['sites']}
    start=date(manifest['analysis_start_year'],1,1);end=date.fromisoformat(manifest['cutoff'])
    expected={(str(start+timedelta(days=i)),s) for i in range((end-start).days+1) for s in coordinates}
    actual=set();ranges={v:[float('inf'),-float('inf')] for v in FIELDS.values()}
    for r in daily:
        pair=(r['date'],r['site_id']);assert pair not in actual;actual.add(pair)
        lat,lon=float(r['latitude']),float(r['longitude']);assert (lat,lon)==coordinates[r['site_id']]
        k=(r['date'],lat,lon);assert k in source
        for original,processed in FIELDS.items():
            value=float(r[processed]);assert math.isfinite(value)
            assert value==source[k][original],(k,processed)
            ranges[processed][0]=min(ranges[processed][0],value);ranges[processed][1]=max(ranges[processed][1],value)
    assert actual==expected
    report={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'manifest_sha256':digest(DATA/'manifest.json'),
      'processed_sha256':digest(daily_path),'source_records':len(source),'processed_rows':len(daily),
      'variable_values_compared':len(daily)*len(FIELDS),'recursive_source_hashes_verified':count,
      'annual_file_count':len(annual),'years_reconstructed_from_original_child_responses':sorted(reconstructed_years),
      'source_request_counts_for_reconstructed_years':dict(request_counts),'overlap_variable_values_independently_compared':overlap_count,'documented_mirror_corrections_reproduced':explicit_corrections,
      'all_dates_and_sites_complete':True,'date_min':str(start),'date_max':str(end),'sites':coordinates,
      'ranges':ranges,'duplicate_site_dates':0,'derived_values_equal_original_responses':True,
      'scope':'Validates preserved source bytes and exact published input values. It does not independently validate satellite retrieval accuracy, reef geometry or historical publication timing.'}
    out=ROOT/'artifacts/independent_data_audit.json';out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
if __name__=='__main__':main()
