import pandas as pd
import pytest
from src.observations import validate_observations
SITES=[{'site_id':'pixel','latitude':4.275,'longitude':118.625}]
def sample():
 return pd.DataFrame([{'survey_id':'survey-a','date_utc':'2024-05-01T12:00:00Z','site_id':'pixel','latitude':4.27,'longitude':118.62,'depth_m':5,'observer_code':'anon','method':'photoquadrat','sampling_unit':'points','total_count':20,'bleached_count':3,'consent':'yes'}])
def test_preserves_observed_denominator():
 d=validate_observations(sample(),SITES);assert d.bleached_fraction.iloc[0]==.15;assert len(d)==1
@pytest.mark.parametrize('key,value',[('total_count',0),('bleached_count',21),('total_count',20.5),('consent','no'),('latitude',4.5),('site_id','unknown'),('sampling_unit','percent')])
def test_rejects_invalid_ecological_labels(key,value):
 d=sample();d[key]=value
 with pytest.raises(ValueError):validate_observations(d,SITES)
def test_duplicate_survey_is_not_silently_averaged():
 with pytest.raises(ValueError):validate_observations(pd.concat([sample(),sample()]),SITES)
