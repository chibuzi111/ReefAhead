"""Post-v1 decision diagnostics: no model fitting or alteration of point forecasts.

Designed after inspection of v1 test/replay results. Diagnostic rule performance on
those periods is exploratory; the comparison envelope has no coverage guarantee.
"""
from functools import lru_cache
from pathlib import Path
import math
import pandas as pd
from src.features import DEFAULT_DATA

VERSION='reefahead-diagnostics-1.1.0'
VARIABLES=('sst','hotspot','dhw','ssta')
REFERENCE_START='2003-01-01'
REFERENCE_END='2019-12-31'
THRESHOLD=4.0

@lru_cache(maxsize=8)
def _ranges(path,mtime_ns,size,cutoff):
    # Cache invalidates on file change; only predeclared fitting-era rows enter.
    raw=pd.read_csv(path,usecols=['date','site_id',*VARIABLES])
    raw['date']=pd.to_datetime(raw['date'],errors='coerce',utc=True).dt.tz_localize(None).dt.normalize()
    ref=raw.loc[raw.date.between(REFERENCE_START,cutoff)].copy()
    for variable in VARIABLES:
        ref[variable]=pd.to_numeric(ref[variable],errors='raise')
        if not ref[variable].dropna().map(math.isfinite).all():
            raise ValueError('Non-finite fitting-era reference')
    if ref.duplicated(['site_id','date']).any():raise ValueError('Duplicate fitting-era reference rows')
    result={}
    for site,g in ref.groupby('site_id'):
        result[str(site)]={'observations':len(g),'first_date':g.date.min().strftime('%Y-%m-%d'),
          'last_date':g.date.max().strftime('%Y-%m-%d'),
          'variables':{v:{'min':float(g[v].min()),'max':float(g[v].max())} for v in VARIABLES if g[v].notna().any()}}
    return result

def _number(value):
    try:
        result=float(value)
        return result if math.isfinite(result) else None
    except (TypeError,ValueError):return None

def build_diagnostics(forecast_result,data_path=DEFAULT_DATA):
    """Return JSON-safe diagnostics without modifying ``forecast_result``.

    ``data_path`` is explicit so custom API data directories cannot silently use
    the default training reference. A missing reference triggers review, never an
    assumed in-distribution/safe label. No target labels are read for a rule.
    """
    reasons=[];site=str(forecast_result.get('site_id',''))
    issue=forecast_result.get('issue_date',forecast_result.get('date'))
    try:
        cutoff=min(pd.Timestamp(issue).date().isoformat(),REFERENCE_END)
        p=Path(data_path);stat=p.stat()
        reference=_ranges(str(p.resolve()),stat.st_mtime_ns,stat.st_size,cutoff).get(site)
    except (OSError,ValueError,TypeError,KeyError):reference=None;cutoff=REFERENCE_END
    training={'status':'available' if reference else 'unavailable',
      'reference_start':REFERENCE_START,'reference_end':cutoff,
      'observations':reference['observations'] if reference else 0,
      'variables':{},'outside_variables':[],
      'interpretation':'Marginal fitting-era ranges only; being inside them does not establish spatial validity, calibrated risk or safety.'}
    current=forecast_result.get('current',{})
    if reference:
        training['actual_first_date']=reference['first_date'];training['actual_last_date']=reference['last_date']
        for variable in VARIABLES:
            bounds=reference['variables'].get(variable);value=_number(current.get(variable))
            if bounds is None or value is None:
                training['variables'][variable]={'status':'unavailable','current':value}
                if 'training_reference_unavailable' not in reasons:reasons.append('training_reference_unavailable')
                continue
            outside=value<bounds['min']-1e-8 or value>bounds['max']+1e-8
            training['variables'][variable]={**bounds,'current':value,'outside':bool(outside),'status':'available'}
            if outside:training['outside_variables'].append(variable)
        if training['outside_variables']:reasons.append('outside_training_range')
    else:reasons.append('training_reference_unavailable')
    if forecast_result.get('stale_input') is True:reasons.append('stale_input')
    horizons=[]
    for f in forecast_result.get('forecasts',[]):
        values={k:_number(f.get(k)) for k in ['mean','ai_prediction','baseline','lower','upper']}
        unavailable=any(v is None for v in values.values())
        hr=[]
        if unavailable:
            hr.append('forecast_values_unavailable');lower=upper=gap=None;disagree=spans=None
        else:
            selected,ai,physical,lo,hi=[values[k] for k in ['mean','ai_prediction','baseline','lower','upper']]
            if lo>hi or lo>selected or hi<selected:
                hr.append('forecast_interval_invalid')
            lower=min(lo,ai,physical,selected);upper=max(hi,ai,physical,selected)
            gap=abs(ai-physical);disagree=(ai>=THRESHOLD)!=(physical>=THRESHOLD)
            spans=lower<THRESHOLD<=upper
            if disagree:hr.append('model_threshold_disagreement')
            if spans:hr.append('comparison_envelope_spans_threshold')
        horizons.append({'horizon':int(f['horizon']),'target_date':f.get('target_date'),
          'selected_model':f.get('model_name'),'selected_point':values['mean'],
          'ai_point':values['ai_prediction'],'physical_point':values['baseline'],
          'absolute_model_disagreement':gap,
          'v1_interval':{'lower':values['lower'],'upper':values['upper'],'nominal_coverage':f.get('interval_nominal_coverage',.9)},
          'comparison_envelope':{'lower':lower,'upper':upper,'calibrated':False,'coverage_level':None,
            'kind':'model-comparison envelope, not a prediction interval',
            'interpretation':'Contains the unchanged v1 interval and both point estimates; no probability or guaranteed coverage is attached.'},
          'threshold':THRESHOLD,'threshold_disagreement':disagree,'envelope_spans_threshold':spans,
          'review_required':bool(hr or reasons),'reasons':list(dict.fromkeys(reasons+hr))})
    all_reasons=list(dict.fromkeys(reasons+[r for h in horizons for r in h['reasons']]))
    if not horizons:all_reasons.append('forecast_values_unavailable')
    return {'version':VERSION,'evidence_status':'post_v1_exploratory',
      'scope':'Human-review diagnostics; no new predictive-skill, independent-validation or safety claim.',
      'point_forecasts_unchanged':True,'threshold':THRESHOLD,
      'overall':{'review_required':bool(all_reasons),'reasons':all_reasons,
        'interpretation':'A review flag is a reason to inspect the inputs and competing estimates. No flag does not mean safe or reliable.'},
      'training_range':training,'per_horizon':horizons,
      'field_outcome_status':'No observed coral bleaching labels or ecological-event validation.'}
