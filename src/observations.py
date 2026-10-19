"""Offline observation import preserves denominators and never manufactures daily labels."""
import numpy as np
import pandas as pd
REQUIRED=['survey_id','date_utc','site_id','latitude','longitude','depth_m','observer_code','method','sampling_unit','total_count','bleached_count','consent']
def validate_observations(frame,sites):
 missing=set(REQUIRED)-set(frame.columns)
 if missing:raise ValueError('Missing observation columns: '+', '.join(sorted(missing)))
 d=frame.copy()
 if d.empty:return d.assign(bleached_fraction=pd.Series(dtype=float))
 for c in ['survey_id','site_id','observer_code','method']:
  if d[c].isna().any() or d[c].astype(str).str.strip().eq('').any():raise ValueError('Empty '+c)
 if d.survey_id.duplicated().any():raise ValueError('Duplicate survey_id; preserve separate sampling units explicitly.')
 d['date_utc']=pd.to_datetime(d.date_utc,utc=True,errors='raise')
 if d.date_utc.isna().any():raise ValueError('Missing observation date')
 for c in ['latitude','longitude','depth_m','total_count','bleached_count']:
  d[c]=pd.to_numeric(d[c],errors='raise')
  if not np.isfinite(d[c].to_numpy()).all():raise ValueError('Nonfinite '+c)
 if not d.depth_m.between(0,100).all():raise ValueError('Depth outside supported 0..100 m range')
 for c in ['total_count','bleached_count']:
  if not d[c].eq(np.floor(d[c])).all():raise ValueError('Counts must be integers')
 if not (d.total_count.gt(0)&d.bleached_count.ge(0)&d.bleached_count.le(d.total_count)).all():raise ValueError('Invalid count denominator or bleaching count')
 if not d.sampling_unit.isin(['colonies','points']).all():raise ValueError('sampling_unit must be colonies or points; do not mix denominators')
 if not d.consent.astype(str).str.lower().isin(['yes','true','1']).all():raise ValueError('Only explicitly authorized observations can be imported')
 lookup={s['site_id']:s for s in sites}
 for x in d.itertuples():
  if x.site_id not in lookup:raise ValueError('Unknown satellite site_id')
  s=lookup[x.site_id]
  if not (-.025<=x.latitude-s['latitude']<.025 and -.025<=x.longitude-s['longitude']<.025):raise ValueError('Observation outside selected 0.05-degree cell')
 d['bleached_fraction']=d.bleached_count/d.total_count
 d['label_scope']='observed sampling unit; not a daily satellite training label'
 return d
