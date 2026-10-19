"""Diagnostics preserve frozen outputs and isolate their historical reference."""
import copy
import json
import pandas as pd
import pytest
from src.diagnostics import build_diagnostics,_ranges

@pytest.fixture
def source(tmp_path):
    p=tmp_path/'daily.csv'
    pd.DataFrame({'date':['2010-01-01','2018-01-01','2024-01-01'],'site_id':['a']*3,
      'sst':[27.,30.,29.],'hotspot':[-.5,1.5,.5],'dhw':[0.,5.,2.],'ssta':[-1.,2.,1.]}).to_csv(p,index=False)
    _ranges.cache_clear()
    return p

@pytest.fixture
def forecast():
    return {'site_id':'a','issue_date':'2024-01-01','stale_input':False,
      'current':{'sst':29.,'hotspot':.5,'dhw':2.,'ssta':1.},
      'forecasts':[{'horizon':14,'target_date':'2024-01-15','mean':3.5,'ai_prediction':3.5,
        'baseline':4.5,'lower':3.,'upper':3.9,'interval_nominal_coverage':.9,'model_name':'fixed_v1'}]}

def test_preserves_forecast_and_marks_envelope_uncalibrated(source,forecast):
    before=copy.deepcopy(forecast);d=build_diagnostics(forecast,source)
    assert forecast==before
    h=d['per_horizon'][0];assert h['selected_point']==3.5
    assert h['comparison_envelope']['lower']==3. and h['comparison_envelope']['upper']==4.5
    assert h['comparison_envelope']['calibrated'] is False
    assert h['comparison_envelope']['coverage_level'] is None
    assert d['point_forecasts_unchanged'] is True
    assert h['threshold_disagreement'] and h['envelope_spans_threshold']

def test_future_values_never_change_reference(source,forecast):
    a=build_diagnostics(forecast,source)['training_range']
    df=pd.read_csv(source);df.loc[df.date.gt('2019-12-31'),['sst','hotspot','dhw','ssta']]=99999
    df.to_csv(source,index=False)
    b=build_diagnostics(forecast,source)['training_range']
    assert a==b
    assert a['actual_last_date']=='2018-01-01'

def test_earlier_issue_does_not_use_later_fitting_years(source,forecast):
    forecast['issue_date']='2012-01-01'
    d=build_diagnostics(forecast,source)
    assert d['training_range']['actual_last_date']=='2010-01-01'
    assert d['training_range']['variables']['sst']['max']==27.

def test_custom_data_path_without_fit_history_requires_review(tmp_path,source,forecast):
    df=pd.read_csv(source);df=df.loc[df.date.ge('2024-01-01')];p=tmp_path/'custom.csv';df.to_csv(p,index=False)
    d=build_diagnostics(forecast,p)
    assert d['training_range']['status']=='unavailable'
    assert 'training_reference_unavailable' in d['overall']['reasons']

def test_stale_and_outside_range_are_explicit(source,forecast):
    forecast['stale_input']=True;forecast['current']['sst']=32.
    d=build_diagnostics(forecast,source)
    assert d['overall']['review_required']
    assert {'stale_input','outside_training_range'}<=set(d['overall']['reasons'])
    assert d['training_range']['outside_variables']==['sst']

def test_threshold_at_four_counts_as_disagreement(source,forecast):
    f=forecast['forecasts'][0];f.update(mean=4.,ai_prediction=4.,baseline=3.9,lower=3.8,upper=4.2)
    assert build_diagnostics(forecast,source)['per_horizon'][0]['threshold_disagreement']

def test_invalid_float_is_json_safe_and_requires_review(source,forecast):
    forecast['forecasts'][0]['ai_prediction']=float('nan')
    d=build_diagnostics(forecast,source)
    json.dumps(d,allow_nan=False)
    assert 'forecast_values_unavailable' in d['overall']['reasons']

def test_no_rule_is_not_a_safe_label(source,forecast):
    forecast['forecasts'][0].update(mean=2.,ai_prediction=2.,baseline=2.1,lower=1.9,upper=2.2)
    d=build_diagnostics(forecast,source)
    assert d['overall']['review_required'] is False
    assert 'No flag does not mean safe' in d['overall']['interpretation']
