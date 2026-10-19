from fastapi.testclient import TestClient
from app import app
client=TestClient(app)
def test_catalog_preserves_task_and_label_distinctions():
 d=client.get('/api/data-catalog').json()
 assert not d['resource_index']['fixed_benchmark']
 assert d['table']['rows']==34744 and d['table']['key']==['site_id','date']
 assert {x['name'] for x in d['table']['fields']}=={'date','site_id','latitude','longitude','sst','hotspot','dhw','ssta','spatial_support','source'}
 rcm=next(x for x in d['datasets'] if x['id']=='reef_check_malaysia')
 assert not rcm['daily_training_labels_available']
def test_diagnostic_envelope_does_not_claim_calibrated_coverage():
 d=client.get('/api/forecast',params={'site_id':'semporna_offshore_1','as_of':'2024-05-15'}).json()
 assert d['model_version']=='reefahead-1.0.0' and d['interface_version']=='2.0.0'
 assert d['diagnostics']['overall']['review_required']
 for f,x in zip(d['forecasts'],d['diagnostics']['per_horizon']):
  assert x['selected_point']==f['mean']
  assert x['comparison_envelope']['calibrated'] is False
  assert x['comparison_envelope']['coverage_level'] is None
  assert x['comparison_envelope']['lower']<=min(f['baseline'],f['ai_prediction'],f['lower'])
  assert x['comparison_envelope']['upper']>=max(f['baseline'],f['ai_prediction'],f['upper'])
def test_real_spatial_context_is_local_and_semantically_limited():
 r=client.get('/api/spatial-context');assert r.status_code==200
 d=r.json();assert d['complete'];assert len(d['sites'])==4
 for site in d['sites']:
  b=site['layers']['benthic']
  assert 0<b['mapped_fraction_of_pixel']<1
  assert b['mapped_area_km2']<=site['pixel_area_km2']
 r=client.get('/api/habitat');assert r.status_code==200
 assert r.json()['type']=='FeatureCollection' and len(r.json()['features'])>0
 assert client.get('/api/spatial-context',params={'site_id':'unknown'}).status_code==404
def test_updated_offline_template_and_export():
 template=client.get('/observation-template.csv').text
 assert 'sampling_unit' in template and 'total_count' in template and 'survey_id' in template
 data=client.get('/api/export',params={'site_id':'semporna_offshore_1','as_of':'2024-05-15'}).text
 assert 'comparison_envelope_calibrated' in data and 'uncalibrated' in data
