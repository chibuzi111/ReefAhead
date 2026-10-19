"""Machine-readable contracts for the recommended sources; no invented labels."""
from pathlib import Path
import json,hashlib
import pandas as pd
FIELDS=[
 ('date','date','UTC observation date; original daily CRW time is 12:00Z','day'),
 ('site_id','string','Stable fixed-grid identifier; not a surveyed reef ID',None),
 ('latitude','float','WGS84 pixel centre','degrees_north'),
 ('longitude','float','WGS84 pixel centre','degrees_east'),
 ('sst','float','CoralTemp nighttime surface-temperature estimate','degree_C'),
 ('hotspot','float','SST minus maximum-monthly-mean climatology; only >=1 contributes to DHW','degree_C'),
 ('dhw','float','Trailing 84-day accumulation of HotSpot>=1 divided by 7; not field bleaching','degree_C_weeks'),
 ('ssta','float','SST anomaly against the daily climatology','degree_C'),
 ('spatial_support','string','Fixed satellite-cell support, distinct from field geometry',None),
 ('source','string','Upstream product identity, not the original-download URL',None)]
def build_catalog(data_root):
 data_root=Path(data_root);p=data_root/'processed/daily.csv';df=pd.read_csv(p)
 ap=data_root/'atlas_20261018/context.json'
 from src.spatial import load_context
 atlas=load_context(data_root) if ap.exists() else None
 return {'version':'2.0','review_date':'2026-10-18',
 'resource_index':{'url':'https://deepseek.club/topic/5152','type':'community_source_directory','fixed_benchmark':False,'mandatory_test_split':None,'mandatory_metric':None,'note':'The post links providers. Product mapping accuracy is not forecast accuracy.'},
 'table':{'path':'processed/daily.csv','rows':len(df),'sites':int(df.site_id.nunique()),'start':str(df.date.min()),'end':str(df.date.max()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'key':['site_id','date'],'fields':[dict(name=n,dtype=t,description=d,unit=u) for n,t,d,u in FIELDS]},
 'datasets':[
 {'id':'noaa_crw','name':'NOAA Coral Reef Watch','state':'integrated_time_series','url':'https://coralreefwatch.noaa.gov/','structure':'time x latitude x longitude grid, extracted to fixed-pixel/day rows','native_resolution':'0.05 degree; daily','use':'forecast satellite DHW exactly at t+7/t+14; no biological bleaching labels','evaluation':'MAE/RMSE, event days, first crossing, calibration and time blocks; project-defined'},
 {'id':'reef_check_malaysia','name':'Reef Check Malaysia','state':'public_reports_context_only','url':'https://reefcheck.org.my/','structure':'site/date/depth/method-dependent surveys and aggregate reports','use':'local evidence; offline field-import adapter validates separate observations','daily_training_labels_available':False,'map_schema_review':{'review_date':'2026-10-18','semporna_station_count':41,'stations_inside_current_pixels':0,'overlap_definition':'Published coordinates inside 0.05-degree cell bounds; location uncertainty not modelled','annual_buckets_are_not_survey_dates':True,'map_reuse_license':'not_confirmed; raw map not redistributed'},'evaluation':'Independent field comparisons require same-site/date/depth/method observations; no expanding regional percentages to daily labels'},
 {'id':'allen_coral_atlas','name':'Allen Coral Atlas','state':'downloaded_spatial_context' if atlas and atlas.get('complete') else 'spatial_context_pending','url':'https://allencoralatlas.org/','structure':'5m geomorphic/benthic/reef_mask raster; WFS polygons retain source attributes','use':'spatial context and cell overlap, never DHW or bleaching labels','license':'Map data CC BY 4.0; separate Planet imagery terms; local AOI only','context_available':bool(atlas),'context_complete':bool(atlas and atlas.get('complete'))}],
 'join_contract':{'time_series':'Exact observation date + fixed centre; no interpolation','habitat':'Polygon intersection with 0.05-degree cells; equal-area CRS, not square degrees','field_observations':'Preserve method/depth/denominator/time; coordinates within selected cell; satellite association is not ecological truth'},
 'evaluation_contract':{'v1_frozen':True,'new_v2_analysis':'Exploratory after viewing v1 test/replay, not a new untouched holdout','future_validation':'Freeze a protocol before genuinely unseen future data and independent sites'}}
