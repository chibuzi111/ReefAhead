"""Regional grouping is explicit, descriptive and never silently loses onsets."""
import pandas as pd
from scripts.evaluate_v2 import group_onsets

def test_related_pixel_upcrossings_merge_without_becoming_three_independent_events():
    rows=pd.DataFrame({'partition':['test']*3,'region':['semporna_demo']*3,
      'site_id':['a','b','c'],'target_date':pd.to_datetime(['2024-05-16','2024-05-22','2024-05-31'])})
    groups=group_onsets(rows)
    assert len(groups)==1 and len(groups[0])==3

def test_gap_region_and_partition_boundaries_remain_explicit():
    rows=pd.DataFrame({'partition':['test','test','test','replay_2026'],
      'region':['a','a','b','a'],'site_id':['p','p','q','p'],
      'target_date':pd.to_datetime(['2024-01-01','2024-03-26','2024-01-02','2026-01-01'])})
    groups=group_onsets(rows)
    assert len(groups)==4 and sum(map(len,groups))==len(rows)

def test_exactly_84_day_gap_is_included_by_declared_rule():
    rows=pd.DataFrame({'partition':['test']*2,'region':['a']*2,'site_id':['p','q'],
      'target_date':pd.to_datetime(['2024-01-01','2024-03-25'])})
    assert len(group_onsets(rows))==1
