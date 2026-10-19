"""Independently recompute frozen aggregate, site/year and event evidence.

No imports from src or the training/evaluation implementation. Reads exact CSV
round-trips and locally hash-verified model bundles. Does not refit models.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,math,os
import numpy as np
import pandas as pd
import joblib
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts'
DATA=Path(os.environ.get('CLIMATE_DATA_DIR','data'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(name):return pd.read_csv(ART/name,float_precision='round_trip')
def measures(y,p,lo=None,hi=None,prob=None):
    y=np.asarray(y);p=np.asarray(p);truth=y>=4;alert=p>=4;e=p-y
    tp=int((truth&alert).sum());fp=int((~truth&alert).sum());fn=int((truth&~alert).sum());tn=int((~truth&~alert).sum())
    r={'n':len(y),'mae':float(np.abs(e).mean()),'rmse':float(np.sqrt(np.square(e).mean())),
       'bias':float(e.mean()),'event_days_ge4':int(truth.sum()),'event_prevalence':float(truth.mean()),
       'event_precision':tp/(tp+fp) if tp+fp else None,'event_recall':tp/(tp+fn) if tp+fn else None,
       'event_f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,'true_positive':tp,'false_positive':fp,
       'false_negative':fn,'true_negative':tn,'heat_stress_mae':float(np.abs(e[truth]).mean()) if truth.any() else None}
    if lo is not None:r.update(interval_coverage=float(((y>=lo)&(y<=hi)).mean()),mean_interval_width=float(np.mean(np.asarray(hi)-lo)))
    if prob is not None:r['brier_score_ge4']=float(np.square(np.asarray(prob)-truth).mean())
    return r
checks=0
max_metric_delta=0.
def compare(actual,expected,context):
    global checks,max_metric_delta
    for k,a in actual.items():
        assert k in expected,(context,'missing',k)
        b=expected[k]
        if a is None:assert b is None or pd.isna(b),(context,k,a,b)
        elif isinstance(a,(int,np.integer)):assert a==b,(context,k,a,b)
        else:
            delta=abs(float(a)-float(b));max_metric_delta=max(max_metric_delta,delta)
            assert np.isfinite(b) and delta<1e-10,(context,k,a,b)
        checks+=1

def main():
    ev=json.loads((ART/'evaluation.json').read_text());assert sha(DATA/'processed/daily.csv')==ev['data_sha256']
    raw=pd.read_csv(DATA/'processed/daily.csv',float_precision='round_trip');raw['date']=pd.to_datetime(raw.date)
    assert len(raw)==ev['data_rows'];assert str(raw.date.min())[:10]==str(ev['data_start'])[:10];assert str(raw.date.max())[:10]==str(ev['data_end'])[:10]
    for name,expected in ev['pipeline_source_sha256'].items():assert sha(ROOT/name)==expected,('Pipeline changed after experiment',name)
    p=read('all_predictions.csv');p['date']=pd.to_datetime(p.date);p['target_date']=pd.to_datetime(p.target_date)
    v=read('validation_predictions.csv');v['date']=pd.to_datetime(v.date);v['target_date']=pd.to_datetime(v.target_date)
    assert not p.duplicated(['partition','horizon','site_id','date']).any()
    raw_index=raw.set_index(['site_id','date']);raw_sites={s:g.sort_values('date').set_index('date') for s,g in raw.groupby('site_id')}
    final_summaries={};event_rows=[];formula_rows=0
    for htext,report in ev['horizons'].items():
        h=int(htext);model=ART/f'model_{h}d.joblib';assert sha(model)==ev['model_artifacts'][htext]['sha256']
        bundle=joblib.load(model)
        assert bundle['selected_name']==report['selected_model'] and bundle['ai_name']==report['best_ai']
        assert bundle['training_last_label']=='2019-12-31' and bundle['calibration_last_label']=='2021-12-31'
        vh=v.loc[v.horizon.eq(h)]
        for method,metrics in report['validation'].items():compare(measures(vh.observed,vh[method]),metrics,('validation',h,method))
        assert report['selected_model']==min(report['validation'],key=lambda k:report['validation'][k]['mae'])
        # Derive available partitions from raw calendar continuity and target availability.
        for split,(start,end) in ev['splits'].items():
            count=0
            for site,g in raw_sites.items():
                assert g.index.equals(pd.date_range(g.index.min(),g.index.max(),name='date'))
                assert np.isfinite(g[['sst','hotspot','dhw','ssta']].to_numpy()).all()
                first=max(g.index.min()+pd.Timedelta(days=83),pd.Timestamp(start))
                last=min(g.index.max(),pd.Timestamp(end))-pd.Timedelta(days=h)
                count+=max(0,(last-first).days+1)
            assert count==report['split_counts'][split],('partition count',h,split,count,report['split_counts'][split])
        hp=p.loc[p.horizon.eq(h)]
        assert hp.selected_model.eq(report['selected_model']).all()
        assert np.array_equal(hp.selected_prediction.to_numpy(),hp[report['selected_model']].to_numpy())
        for split,part in report['partitions'].items():
            g=hp.loc[hp.partition.eq(split)]
            start,end=map(pd.Timestamp,ev['splits'][split])
            assert g.date.between(start,end).all() and g.target_date.between(start,end).all()
            for method,metrics in part.items():
                if method in ['onsets','selected_gain_vs_physics']:continue
                if method=='selected':actual=measures(g.observed,g.selected_prediction,g.lower90.to_numpy(),g.upper90.to_numpy(),g.probability_dhw_ge4)
                else:actual=measures(g.observed,g[method])
                compare(actual,metrics,(split,h,method))
        for r in pd.concat([hp,vh],ignore_index=True).itertuples():
            assert (r.target_date-r.date).days==h
            row=raw_index.loc[(r.site_id,r.date)];target=raw_index.loc[(r.site_id,r.target_date)]
            assert abs(r.observed-target.dhw)<1e-12
            if hasattr(r,'current_dhw') and not pd.isna(r.current_dhw):assert abs(r.current_dhw-row.dhw)<1e-12
            outgoing=raw_sites[r.site_id].loc[r.date-pd.Timedelta(days=83):r.date-pd.Timedelta(days=84-h),'hotspot']
            assert len(outgoing)==h
            removed=float(outgoing.where(outgoing>=1,0).sum())/7
            physics=max(0,float(row.dhw)-removed+h*(float(row.hotspot) if row.hotspot>=1 else 0)/7)
            assert abs(physics-r.physical_persistence)<1e-10,('physics',r.site_id,r.date,h)
            floor=max(0,float(row.dhw)-removed-(.01+h*.005/7))
            if hasattr(r,'ai_prediction') and not pd.isna(r.ai_prediction):assert r.ai_prediction>=floor-1e-10
            for name in ['hist_gradient_boosting_residual','random_forest_residual']:
                value=getattr(r,name,float('nan'))
                if not pd.isna(value):assert value>=floor-1e-10
            formula_rows+=1
        for site,cal in bundle['calibration'].items():
            g=hp.loc[hp.partition.eq('calibration')&hp.site_id.eq(site)]
            errors=(g.observed-g.selected_prediction).to_numpy()
            assert np.allclose(errors,np.asarray(cal['signed_errors']),atol=1e-12,rtol=0)
            index=min(len(errors)-1,math.ceil((len(errors)+1)*.9)-1);radius=float(np.sort(np.abs(errors))[index])
            assert abs(radius-cal['radius90'])<1e-12 and len(errors)==cal['n']
            compare({'n':len(errors),'radius90':radius},report['calibration'][site],('calibration',h,site))
            for r in hp.loc[hp.site_id.eq(site)].itertuples():
                assert abs(r.lower90-max(0,r.selected_prediction-radius))<1e-12
                assert abs(r.upper90-r.selected_prediction-radius)<1e-12
                expected=float(np.mean(errors+r.selected_prediction>=4))
                assert abs(r.probability_dhw_ge4-expected)<1e-12,('residual_frequency',h,site,r.date)
        test=hp.loc[hp.partition.eq('test')].copy()
        for site,g in test.groupby('site_id'):
            previous=None
            for r in g.sort_values('target_date').itertuples():
                if previous is not None and (r.target_date-previous.target_date).days==1 and previous.observed<4<=r.observed:
                    event_rows.append((h,site,r.target_date.strftime('%Y-%m-%d'),r.date.strftime('%Y-%m-%d'),r.selected_prediction>=4))
                previous=r
        actual_onsets=[r for r in event_rows if r[0]==h]
        assert len(actual_onsets)==report['partitions']['test']['onsets']['n']
        assert sum(int(r[-1]) for r in actual_onsets)==report['partitions']['test']['onsets']['exact_lead_hits']
        test['gain']=np.abs(test.physical_persistence-test.observed)-np.abs(test.selected_prediction-test.observed)
        blocks=((test.date-test.date.min()).dt.days//90)
        grouped=test.groupby(blocks)['gain'].agg(['sum','count']);rng=np.random.default_rng(42)
        indices=rng.integers(0,len(grouped),size=(1000,len(grouped)))
        sample=grouped['sum'].to_numpy()[indices].sum(1)/grouped['count'].to_numpy()[indices].sum(1)
        gain={'mae_gain':float(test.gain.mean()),'ci95_lower':float(np.quantile(sample,.025)),'ci95_upper':float(np.quantile(sample,.975)),'blocks':len(grouped)}
        compare(gain,report['partitions']['test']['selected_gain_vs_physics'],('gain',h))
        sel=report['partitions']['test']['selected']
        final_summaries[htext]={'selected_model':report['selected_model'],'test':sel,'gain_vs_physical':gain,
          'claim_support':{'lower_mae_than_physical_baseline':gain['mae_gain']>0,'descriptive_gain_interval_entirely_positive':gain['ci95_lower']>0,
          'empirical_coverage_at_least_nominal_90_percent':sel['interval_coverage']>=.9},'onsets':report['partitions']['test']['onsets']}
    for filename,keys in [('site_metrics.csv',['partition','horizon','site_id']),('year_metrics.csv',['partition','horizon','site_id','year'])]:
        by=read(filename)
        for r in by.to_dict('records'):
            g=p.loc[p.partition.eq(r['partition'])&p.horizon.eq(r['horizon'])&p.site_id.eq(r['site_id'])]
            if 'year' in keys:g=g.loc[g.date.dt.year.eq(r['year'])]
            actual=measures(g.observed,g[r['method']],g.lower90.to_numpy() if r['method']=='selected_prediction' else None,g.upper90.to_numpy() if r['method']=='selected_prediction' else None)
            compare(actual,r,(filename,*(r[k] for k in keys),r['method']))
    onsets=read('threshold_crossing_events.csv')
    observed_events=sorted((int(r.horizon),r.site_id,str(r.target_date)[:10],str(r.issue_date)[:10],bool(r.alert_at_exact_lead)) for r in onsets.itertuples())
    assert observed_events==sorted(event_rows)
    for name,partition in [('test_predictions.csv','test'),('replay_2026_predictions.csv','replay_2026')]:
        actual=read(name);expected=p.loc[p.partition.eq(partition)].copy();expected['date']=expected.date.dt.strftime('%Y-%m-%d');expected['target_date']=expected.target_date.dt.strftime('%Y-%m-%d')
        pd.testing.assert_frame_equal(actual.reset_index(drop=True),expected.reset_index(drop=True))
    report={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'data_sha256':ev['data_sha256'],'evaluation_sha256':sha(ART/'evaluation.json'),
      'all_predictions_sha256':sha(ART/'all_predictions.csv'),'metric_values_recomputed':checks,'maximum_metric_difference':max_metric_delta,
      'prediction_and_validation_rows_physically_recomputed':formula_rows,'observed_labels_match_input':True,'split_counts_independently_derived':True,
      'calibration_radius_bounds_and_residual_frequencies_recomputed':True,'selected_model_is_validation_winner':True,'source_and_model_hashes_valid':True,
      'all_site_and_year_metrics_recomputed':True,'first_crossing_records_recomputed':True,'bootstrap_resampled_independently':True,'horizons':final_summaries,
      'scope':'Independent arithmetic and provenance audit, without importing src metrics or fitting/tuning. Does not establish ecological benefit, prospective availability or independent spatial generalization.'}
    (ART/'independent_result_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
if __name__=='__main__':main()
