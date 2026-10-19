#!/usr/bin/env python3
"""Independent post-training checks of serialized forecasts, metrics and API data routing.

This audit never trains, recalibrates, selects or modifies model artifacts.
"""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import joblib
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from src.features import DEFAULT_DATA,HORIZONS,SPLITS,load_data,build_features,split_mask,retained_heat_floor
from src.predict import predict_forecast,_bundle

ART=ROOT/'artifacts'
checks=[]
def require(condition,label):
    if not condition: raise AssertionError(label)
    checks.append(label)

def checksum(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def close(actual,expected,label,atol=3e-6):
    if expected is None:
        require(actual is None or pd.isna(actual),label)
    else:
        require(np.isclose(float(actual),float(expected),atol=atol,rtol=1e-7),label)

def independent_metrics(g,pred_col,interval=False,probability=False):
    y=g.observed.to_numpy();p=g[pred_col].to_numpy()
    event=y>=4;alert=p>=4
    tp=int((event&alert).sum());fp=int((~event&alert).sum())
    fn=int((event&~alert).sum());tn=int((~event&~alert).sum())
    m={'n':len(g),'mae':float(np.abs(p-y).mean()),'rmse':float(np.sqrt(np.square(p-y).mean())),
       'bias':float((p-y).mean()),'event_days_ge4':int(event.sum()),'event_prevalence':float(event.mean()),
       'event_precision':tp/(tp+fp) if tp+fp else None,'event_recall':tp/(tp+fn) if tp+fn else None,
       'event_f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
       'true_positive':tp,'false_positive':fp,'false_negative':fn,'true_negative':tn,
       'heat_stress_mae':float(np.abs(p[event]-y[event]).mean()) if event.any() else None}
    if interval:
        m['interval_coverage']=float(((y>=g.lower90)&(y<=g.upper90)).mean())
        m['mean_interval_width']=float((g.upper90-g.lower90).mean())
    if probability:m['brier_score_ge4']=float(np.square(g.probability_dhw_ge4-event.astype(float)).mean())
    return m

def compare_metrics(actual,expected,label):
    for key,value in actual.items():close(expected[key],value,f'{label}: {key}')

def main():
    manifest=json.loads((DEFAULT_DATA.parents[1]/'manifest.json').read_text())
    require(manifest.get('complete') is True,'Input manifest is complete')
    require(not manifest.get('failures'),'Input manifest has no failed requests')
    quality=json.loads((DEFAULT_DATA.parent/'data_quality.json').read_text())
    require(quality['raw_requests_complete'],'Source checksums were checked by check_data.py')
    e=json.loads((ART/'evaluation.json').read_text())
    frozen=json.loads((ROOT/'evidence/training_protocol.json').read_text())
    for name,expected in frozen['source_sha256'].items():
        require(checksum(ROOT/name)==expected,f'Frozen source SHA: {name}')
    for name,expected in e['pipeline_source_sha256'].items():
        require(checksum(ROOT/name)==expected,f'Training source SHA: {name}')
    require(checksum(DEFAULT_DATA)==e['data_sha256'],'Evaluated data SHA matches current complete input')
    raw=load_data(DEFAULT_DATA);f,names=build_features(raw)
    require(len(raw)==e['data_rows'],'Evaluation data-row count matches input')
    require(not any(n.startswith('target') for n in names),'Model feature names exclude targets')
    require(e['splits']=={k:list(v) for k,v in SPLITS.items()},'Evaluation partitions match frozen code')
    p=pd.read_csv(ART/'all_predictions.csv',parse_dates=['date','target_date'],float_precision='round_trip')
    v=pd.read_csv(ART/'validation_predictions.csv',parse_dates=['date','target_date'],float_precision='round_trip')
    yearly=pd.read_csv(ART/'year_metrics.csv');sitewise=pd.read_csv(ART/'site_metrics.csv')
    split_audit={};selection={};coverage={}
    for h in HORIZONS:
        r=e['horizons'][str(h)];split_audit[str(h)]={}
        require(checksum(ART/f'model_{h}d.joblib')==e['model_artifacts'][str(h)]['sha256'],f'{h}d model SHA')
        b=joblib.load(ART/f'model_{h}d.joblib')
        require(b['training_last_label']=='2019-12-31' and b['calibration_last_label']=='2021-12-31',f'{h}d fixed artifact cutoffs')
        require(b['feature_names']==names,f'{h}d serialized feature list')
        for split,(start,end) in SPLITS.items():
            part=f.loc[split_mask(f,split,h)]
            require(len(part)==r['split_counts'][split],f'{h}d {split} count')
            require(part.date.between(start,end).all() and part[f'target_date_{h}'].between(start,end).all(),f'{h}d {split} issue and target boundaries')
            split_audit[str(h)][split]={'n':len(part),'first_issue':str(part.date.min().date()),'last_issue':str(part.date.max().date()),'first_target':str(part[f'target_date_{h}'].min().date()),'last_target':str(part[f'target_date_{h}'].max().date())}
        chosen=min(r['validation'],key=lambda k:r['validation'][k]['mae'])
        require(chosen==r['selected_model']==b['selected_name'],f'{h}d selection uses minimum validation MAE')
        best=min(frozen['candidates'],key=lambda k:r['validation'][k]['mae'])
        require(best==r['best_ai']==b['ai_name'],f'{h}d best residual learner uses validation only')
        require(b['model'].get_params()==frozen['candidates'][best],f'{h}d serialized hyperparameters match pre-evaluation protocol')
        selection[str(h)]={'selected_model':chosen,'best_ai':best,'validation_mae':r['validation'][chosen]['mae']}
        val=v.loc[v.horizon.eq(h)]
        for method,m in r['validation'].items():compare_metrics(independent_metrics(val,method),m,f'{h}d validation {method}')
        for split in ['calibration','test','replay_2026']:
            part=f.loc[split_mask(f,split,h)].copy()
            out=p.loc[p.horizon.eq(h)&p.partition.eq(split)].copy()
            require(len(out)==len(part),f'{h}d {split} serialized rows')
            require(not out.duplicated(['site_id','date']).any(),f'{h}d {split} unique forecasts')
            part=part.sort_values(['site_id','date']).reset_index(drop=True)
            out=out.sort_values(['site_id','date']).reset_index(drop=True)
            require(out.site_id.equals(part.site_id) and out.date.equals(part.date),f'{h}d {split} forecast keys')
            require((out.target_date==out.date+pd.Timedelta(days=h)).all(),f'{h}d {split} calendar target lead')
            require(np.allclose(out.observed,part[f'target_{h}'],atol=5.01e-7,rtol=0),f'{h}d {split} targets match source labels')
            reconstructed_ai=np.maximum(retained_heat_floor(part,h),part[f'physics_{h}']+b['model'].predict(part[names]))
            require((out.ai_prediction.to_numpy()+5.01e-7>=retained_heat_floor(part,h)).all(),f'{h}d {split} every AI point prediction respects retained-heat floor')
            require(np.allclose(out.ai_prediction,reconstructed_ai,atol=5.01e-7,rtol=0),f'{h}d {split} stored model reproduces every AI forecast')
            require(np.allclose(out.physical_persistence,part[f'physics_{h}'],atol=5.01e-7,rtol=0),f'{h}d {split} physical baseline accounting')
            require(np.allclose(out.selected_prediction,out[chosen],atol=1e-12,rtol=0),f'{h}d {split} selected forecast column')
            require((out.lower90>=0).all() and (out.lower90<=out.selected_prediction).all() and (out.upper90>=out.selected_prediction).all(),f'{h}d {split} valid interval endpoints')
            require(out.probability_dhw_ge4.between(0,1).all(),f'{h}d {split} residual frequency bounds')
            for method,m in r['partitions'][split].items():
                if method in ['selected_gain_vs_physics','onsets']:continue
                compare_metrics(independent_metrics(out,'selected_prediction' if method=='selected' else method,method=='selected',method=='selected'),m,f'{h}d {split} {method}')
            if split=='calibration':
                for site,g in part.groupby('site_id',sort=True):
                    cal=b['calibration'][site];idx=g.index
                    predicted={'physical_persistence':g[f'physics_{h}'].to_numpy(),'dhw_persistence':g.dhw.to_numpy(),
                               'seasonal_climatology':np.array([b['climatology'][site][d.dayofyear-1] for d in g[f'target_date_{h}']])}.get(chosen,np.asarray(reconstructed_ai)[idx])
                    errors=g[f'target_{h}'].to_numpy()-predicted
                    require(np.allclose(errors,cal['signed_errors'],atol=1e-12,rtol=0),f'{h}d {site} calibration residuals only from held-out 2020-2021')
                    rank=min(len(errors),math.ceil((len(errors)+1)*.9))
                    close(cal['radius90'],np.sort(np.abs(errors))[rank-1],f'{h}d {site} finite-sample nominal 90% radius',1e-12)
            if split=='test':coverage[str(h)]=r['partitions'][split]['selected']['interval_coverage']
    for table,name in [(yearly,'year'),(sitewise,'site')]:
        for _,row in table.iterrows():
            g=p.loc[p.partition.eq(row.partition)&p.horizon.eq(row.horizon)&p.site_id.eq(row.site_id)]
            if name=='year':g=g.loc[g.date.dt.year.eq(row.year)]
            compare_metrics(independent_metrics(g,row.method,row.method=='selected_prediction'),row,f'{name} {row.partition} {row.horizon} {row.site_id} {row.method}')
    for partition,filename in [('test','test_predictions.csv'),('replay_2026','replay_2026_predictions.csv')]:
        separate=pd.read_csv(ART/filename,float_precision='round_trip')
        pd.testing.assert_frame_equal(separate,p.loc[p.partition.eq(partition)].assign(date=lambda x:x.date.dt.strftime('%Y-%m-%d'),target_date=lambda x:x.target_date.dt.strftime('%Y-%m-%d')).reset_index(drop=True),check_dtype=False)
        checks.append(f'{filename} matches all_predictions subset exactly')
    latest=json.loads((ART/'latest_forecast.json').read_text())
    for site,stored in latest['sites'].items():
        current=predict_forecast(site,data_path=DEFAULT_DATA)
        require(stored['issue_date']==current['issue_date'],f'{site} latest forecast issue date')
        for a,b in zip(stored['forecasts'],current['forecasts']):
            for key in ['mean','lower','upper','baseline','ai_prediction','probability_dhw_ge4']:close(a[key],b[key],f'{site} latest {a["horizon"]}d {key}',1e-12)
    import app as api
    client=TestClient(api.app)
    response=client.get('/api/forecast',params={'site_id':raw.site_id.iloc[0],'as_of':'2024-05-15'})
    require(response.status_code==200,'API actual-model historic forecast succeeds')
    original=api.DATA
    with tempfile.TemporaryDirectory(prefix='model-route-audit-',dir=str(DEFAULT_DATA.parents[1])) as tmp:
        custom=Path(tmp);(custom/'processed').mkdir()
        site=raw.site_id.iloc[0]
        subset=raw.loc[raw.site_id.eq(site)&raw.date.le('2024-05-15')].tail(100)
        subset.to_csv(custom/'processed/daily.csv',index=False)
        api.DATA=custom
        try:
            routed=client.get('/api/forecast',params={'site_id':site})
            require(routed.status_code==200,'API accepts custom validated data directory')
            require(routed.json()['issue_date']=='2024-05-15','API predict honors explicit data_path rather than default latest input')
            for a,b in zip(response.json()['forecasts'],routed.json()['forecasts']):
                close(a['mean'],b['mean'],f'{a["horizon"]}d custom data_path forecast matches fixed historic result',1e-12)
        finally:api.DATA=original
    report={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'success':True,'training_runs_in_this_audit':0,
            'checks_passed':len(checks),'checks':checks,'partition_boundaries':split_audit,'selection':selection,
            'observed_test_interval_coverage':coverage,'coverage_note':'Nominal 90% calibration does not guarantee future coverage; all observed coverage is reported without test-set recalibration.',
            'data_sha256':e['data_sha256'],'model_artifacts':e['model_artifacts'],'prediction_rows':len(p),
            'input_data_quality_calendar_complete':quality.get('calendar_complete')}
    out=ROOT/'evidence/model_audit.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['checks','partition_boundaries','model_artifacts']},indent=2))

if __name__=='__main__': main()
