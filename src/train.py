"""Frozen temporal training and evaluation with complete auditable predictions."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import time
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor,RandomForestRegressor
from src.features import DEFAULT_DATA,HORIZONS,SPLITS,load_data,build_features,split_mask,retained_heat_floor
ROOT=Path(__file__).resolve().parents[1]
ARTIFACTS=ROOT/'artifacts'
VERSION='reefahead-1.0.0'
SEED=42

def jsonable(v):
    if isinstance(v,dict):return {str(k):jsonable(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [jsonable(x) for x in v]
    if isinstance(v,np.integer):return int(v)
    if isinstance(v,np.floating):return float(v) if np.isfinite(v) else None
    if isinstance(v,np.ndarray):return jsonable(v.tolist())
    if isinstance(v,pd.Timestamp):return v.strftime('%Y-%m-%d')
    if isinstance(v,float) and not math.isfinite(v):return None
    return v

def dump_json(path,data):
    path.write_text(json.dumps(jsonable(data),ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def make_model(name):
    if name=='hist_gradient_boosting_residual':
        return HistGradientBoostingRegressor(max_iter=180,max_leaf_nodes=15,min_samples_leaf=40,
            learning_rate=.05,l2_regularization=10,early_stopping=False,random_state=SEED)
    if name=='random_forest_residual':
        return RandomForestRegressor(n_estimators=200,max_depth=14,min_samples_leaf=20,
            max_features=.8,n_jobs=4,random_state=SEED)
    raise ValueError(name)

def metrics(y,pred,lower=None,upper=None,probability=None):
    y,pred=np.asarray(y),np.asarray(pred); event=y>=4; alert=pred>=4
    tp=int(np.sum(event&alert));fp=int(np.sum(~event&alert));fn=int(np.sum(event&~alert));tn=int(np.sum(~event&~alert))
    out={'n':len(y),'mae':np.mean(np.abs(pred-y)),'rmse':np.sqrt(np.mean((pred-y)**2)),
        'bias':np.mean(pred-y),'event_days_ge4':int(event.sum()),'event_prevalence':np.mean(event),
        'event_precision':tp/(tp+fp) if tp+fp else None,'event_recall':tp/(tp+fn) if tp+fn else None,
        'event_f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
        'true_positive':tp,'false_positive':fp,'false_negative':fn,'true_negative':tn,
        'heat_stress_mae':np.mean(np.abs(pred[event]-y[event])) if event.any() else None}
    if lower is not None:
        out.update(interval_coverage=np.mean((y>=lower)&(y<=upper)),mean_interval_width=np.mean(upper-lower))
    if probability is not None:out['brier_score_ge4']=np.mean((np.asarray(probability)-event.astype(float))**2)
    return jsonable(out)

def conformal_radius(errors,alpha=.1):
    errors=np.sort(np.abs(np.asarray(errors)))
    if not len(errors):raise ValueError('Empty calibration residuals.')
    index=min(len(errors)-1,math.ceil((len(errors)+1)*(1-alpha))-1)
    return float(errors[index])

def climatology_fit(f):
    lookup={}
    for site,g in f.groupby('site_id'):
        doy=g.date.dt.dayofyear.to_numpy();vals=g.dhw.to_numpy();means=[]
        for day in range(1,367):
            dist=np.abs(doy-day);dist=np.minimum(dist,366-dist)
            means.append(float(np.mean(vals[dist<=15])))
        lookup[site]=means
    return lookup

def climate_prediction(f,h,lookup):
    return np.array([lookup[s][d.dayofyear-1] for s,d in zip(f.site_id,f[f'target_date_{h}'])])

def model_prediction(model,f,names,h):
    return np.maximum(retained_heat_floor(f,h),f[f'physics_{h}'].to_numpy()+model.predict(f[names]))

def block_bootstrap_gain(f,reference='physical_persistence',n_boot=1000):
    d=f.copy();d['block']=(d.date-d.date.min()).dt.days//90
    d['gain']=np.abs(d[reference]-d.observed)-np.abs(d.selected_prediction-d.observed)
    grouped=d.groupby('block')['gain'].agg(['sum','count']);rng=np.random.default_rng(SEED)
    ix=rng.integers(0,len(grouped),size=(n_boot,len(grouped)))
    samples=grouped['sum'].to_numpy()[ix].sum(axis=1)/grouped['count'].to_numpy()[ix].sum(axis=1)
    return {'method':'Paired non-overlapping 90-day calendar blocks, sites grouped, 1000 bootstrap resamples; descriptive.',
        'mae_gain':float(d.gain.mean()),'ci95_lower':float(np.quantile(samples,.025)),
        'ci95_upper':float(np.quantile(samples,.975)),'blocks':len(grouped)}

def first_crossing_metrics(f):
    records=[]
    for site,g in f.groupby('site_id'):
        g=g.sort_values('target_date');adjacent=g.target_date.diff().dt.days.eq(1)
        onset=(g.observed>=4)&g.observed.shift().lt(4)&adjacent
        for _,r in g.loc[onset].iterrows():
            records.append({'site_id':site,'target_date':r.target_date,'issue_date':r.date,
                'horizon':int(r.horizon),'observed':r.observed,'prediction':r.selected_prediction,
                'alert_at_exact_lead':bool(r.selected_prediction>=4)})
    return records

def train(data_path=DEFAULT_DATA):
    ARTIFACTS.mkdir(exist_ok=True);started=time.time();raw=load_data(data_path);frame,names=build_features(raw)
    train_rows=frame.loc[frame.feature_valid & frame.date.le(pd.Timestamp('2016-12-31'))]
    fit_rows=frame.loc[frame.feature_valid & frame.date.le(pd.Timestamp('2019-12-31'))]
    climate_train=climatology_fit(train_rows);climate_final=climatology_fit(fit_rows)
    candidates=['hist_gradient_boosting_residual','random_forest_residual']
    report={};all_predictions=[];breakdown=[];onsets=[];importances=[];validation_predictions=[]
    for h in HORIZONS:
        print(f'Horizon {h}: frozen temporal partitions',flush=True)
        trainf=frame.loc[split_mask(frame,'train',h)];val=frame.loc[split_mask(frame,'validation',h)]
        fit=frame.loc[split_mask(frame,'fit',h)];cal=frame.loc[split_mask(frame,'calibration',h)]
        if min(map(len,[trainf,val,fit,cal]))==0:raise ValueError('Empty mandatory partition.')
        val_y=val[f'target_{h}'].to_numpy()
        validation={'dhw_persistence':metrics(val_y,val.dhw),
            'physical_persistence':metrics(val_y,val[f'physics_{h}']),
            'seasonal_climatology':metrics(val_y,climate_prediction(val,h,climate_train))}
        validation_out=val[['date','site_id',f'target_date_{h}']].rename(columns={f'target_date_{h}':'target_date'}).copy()
        validation_out['horizon']=h;validation_out['observed']=val_y
        validation_out['dhw_persistence']=val.dhw.to_numpy()
        validation_out['physical_persistence']=val[f'physics_{h}'].to_numpy()
        validation_out['seasonal_climatology']=climate_prediction(val,h,climate_train)
        for name in candidates:
            print(f'  validation fit {name}',flush=True);model=make_model(name)
            model.fit(trainf[names],trainf[f'target_{h}']-trainf[f'physics_{h}'])
            validation_out[name]=model_prediction(model,val,names,h)
            validation[name]=metrics(val_y,validation_out[name])
        validation_predictions.append(validation_out)
        best_ai=min(candidates,key=lambda k:validation[k]['mae'])
        selected=min(validation,key=lambda k:validation[k]['mae'])
        print(f'  selected {selected}; refit best AI {best_ai}',flush=True)
        model=make_model(best_ai);model.fit(fit[names],fit[f'target_{h}']-fit[f'physics_{h}'])
        if hasattr(model,'feature_importances_'):
            importances.extend({'horizon':h,'feature':n,'importance':v} for n,v in zip(names,model.feature_importances_))
        cal_ai=model_prediction(model,cal,names,h)
        cal_selected={'dhw_persistence':cal.dhw.to_numpy(),'physical_persistence':cal[f'physics_{h}'].to_numpy(),
            'seasonal_climatology':climate_prediction(cal,h,climate_final)}.get(selected,cal_ai)
        errors=cal[f'target_{h}'].to_numpy()-cal_selected;calibration={}
        for site in sorted(raw.site_id.unique()):
            e=errors[cal.site_id.to_numpy()==site]
            calibration[site]={'n':len(e),'radius90':conformal_radius(e),'signed_errors':e.tolist()}
        bundle={'model':model,'ai_name':best_ai,'selected_name':selected,'feature_names':names,
            'calibration':calibration,'climatology':climate_final,'horizon':h,'version':VERSION,
            'training_last_label':'2019-12-31','calibration_last_label':'2021-12-31','data_path':str(data_path)}
        joblib.dump(bundle,ARTIFACTS/f'model_{h}d.joblib',compress=3)
        partitions={}
        for split in ['calibration','test','replay_2026']:
            f=frame.loc[split_mask(frame,split,h)].copy()
            if not len(f):continue
            ai=model_prediction(model,f,names,h)
            preds={'dhw_persistence':f.dhw.to_numpy(),'physical_persistence':f[f'physics_{h}'].to_numpy(),
                'seasonal_climatology':climate_prediction(f,h,climate_final),best_ai:ai}
            chosen=preds[selected];radii=np.array([calibration[s]['radius90'] for s in f.site_id])
            lower=np.maximum(0,chosen-radii);upper=chosen+radii
            prob=np.array([np.mean(np.asarray(calibration[s]['signed_errors'])+p>=4) for s,p in zip(f.site_id,chosen)])
            out=f[['date','site_id',f'target_date_{h}']].rename(columns={f'target_date_{h}':'target_date'}).copy()
            out['partition']=split;out['horizon']=h;out['observed']=f[f'target_{h}'].to_numpy()
            out['current_dhw']=f.dhw.to_numpy();out['ai_prediction']=ai
            for k,p in preds.items():out[k]=p
            out['selected_prediction']=chosen;out['selected_model']=selected
            out['lower90']=lower;out['upper90']=upper;out['probability_dhw_ge4']=prob
            partitions[split]={k:metrics(out.observed,p) for k,p in preds.items()}
            partitions[split]['selected']=metrics(out.observed,chosen,lower,upper,prob)
            if split=='test':
                partitions[split]['selected_gain_vs_physics']=block_bootstrap_gain(out)
                onset=first_crossing_metrics(out);onsets.extend(onset)
                partitions[split]['onsets']={'n':len(onset),'exact_lead_hits':sum(r['alert_at_exact_lead'] for r in onset),
                    'note':'Nearby site episodes remain correlated; no field bleaching labels.'}
            for (site,year),g in out.groupby(['site_id',out.date.dt.year]):
                for k in ['selected_prediction','ai_prediction','physical_persistence','dhw_persistence','seasonal_climatology']:
                    breakdown.append({'partition':split,'horizon':h,'site_id':site,'year':int(year),'method':k,
                        **metrics(g.observed,g[k],g.lower90 if k=='selected_prediction' else None,g.upper90 if k=='selected_prediction' else None)})
            all_predictions.append(out)
        report[str(h)]={'horizon_days':h,'target':'DHW at issue date + horizon, degree C-weeks','validation':validation,
            'selection_rule':'Lowest pooled daily validation MAE; test never used for selection.',
            'best_ai':best_ai,'selected_model':selected,'split_counts':{s:int(split_mask(frame,s,h).sum()) for s in SPLITS},
            'calibration':{s:{k:v for k,v in c.items() if k!='signed_errors'} for s,c in calibration.items()},'partitions':partitions}
    pd.concat(validation_predictions,ignore_index=True).to_csv(ARTIFACTS/'validation_predictions.csv',index=False,float_format='%.17g')
    predictions=pd.concat(all_predictions,ignore_index=True)
    predictions.to_csv(ARTIFACTS/'all_predictions.csv',index=False,float_format='%.17g')
    predictions.loc[predictions.partition.eq('test')].to_csv(ARTIFACTS/'test_predictions.csv',index=False,float_format='%.17g')
    predictions.loc[predictions.partition.eq('replay_2026')].to_csv(ARTIFACTS/'replay_2026_predictions.csv',index=False,float_format='%.17g')
    pd.DataFrame(breakdown).to_csv(ARTIFACTS/'year_metrics.csv',index=False)
    site_metrics=[]
    for (partition,horizon,site),g in predictions.groupby(['partition','horizon','site_id']):
        for method in ['selected_prediction','ai_prediction','physical_persistence','dhw_persistence','seasonal_climatology']:
            site_metrics.append({'partition':partition,'horizon':horizon,'site_id':site,'method':method,
                **metrics(g.observed,g[method],g.lower90 if method=='selected_prediction' else None,
                    g.upper90 if method=='selected_prediction' else None)})
    pd.DataFrame(site_metrics).to_csv(ARTIFACTS/'site_metrics.csv',index=False)
    pd.DataFrame(onsets).to_csv(ARTIFACTS/'threshold_crossing_events.csv',index=False)
    if importances:pd.DataFrame(importances).to_csv(ARTIFACTS/'feature_importances.csv',index=False)
    result={'project':'ReefAhead / 礁先知','version':VERSION,'seed':SEED,
        'data_sha256':hashlib.sha256(Path(data_path).read_bytes()).hexdigest(),'data_path':str(data_path),
        'data_rows':len(raw),'data_start':raw.date.min(),'data_end':raw.date.max(),
        'sites':raw[['site_id','latitude','longitude']].drop_duplicates().to_dict('records'),
        'splits':SPLITS,'horizons':report,'python':platform.python_version(),'sklearn':sklearn.__version__,
        'runtime_seconds':round(time.time()-started,2),
        'model_artifacts':{str(h):{'path':str(ARTIFACTS/f'model_{h}d.joblib'),
            'sha256':hashlib.sha256((ARTIFACTS/f'model_{h}d.joblib').read_bytes()).hexdigest()} for h in HORIZONS},
        'pipeline_source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [ROOT/'src'/n for n in ['__init__.py','features.py','train.py','predict.py','reporting.py']]},
        'retained_heat_floor':{'formula':'max(0, current_DHW - expiring_HS_sum/7 - (0.01 + h*0.005/7))',
            'tolerances_degree_C_weeks':{'7':0.015,'14':0.02},
            'scope':'All residual-AI candidate and final point predictions; baselines and symmetric calibration interval formula are unchanged.',
            'assumption':'Nearest-0.01 DHW and HotSpot quantization. ERDDAP metadata do not establish the original rounding rule; this is a plausibility constraint, not a complete physical guarantee.',
            'fixed_before_evaluation':True},
        'scientific_scope':'Retrospective forecasts of NOAA CRW fixed-pixel satellite DHW, not observed bleaching or ecological recovery.',
        'limitations':['Four nearby demonstration water pixels; no verified reef geometry, field bleaching labels or independent spatial validation.',
            'Archives were downloaded retrospectively; issue dates assume same-day inputs, not verified operational availability.',
            'Autocorrelated temporal calibration does not guarantee 90% future coverage; observed test coverage is reported.',
            'DHW>=4 is a thermal-stress indicator, not an official Bleaching Alert Area category or proof of bleaching.',
            'Forecasts require 84 uninterrupted input days; no interpolation or future climate covariates.',
            'Four sites and daily horizons are correlated; row count is not independent sample size.',
            'Extreme warming beyond training conditions can invalidate residual corrections and intervals; physical-baseline residual trees do not guarantee extrapolation to unprecedented events.']}
    dump_json(ARTIFACTS/'evaluation.json',result)
    from src.reporting import generate_plots,write_reports
    generate_plots(predictions,result);write_reports(result)
    from src.predict import predict_forecast
    latest={s:predict_forecast(s,data_path=data_path) for s in sorted(raw.site_id.unique())}
    dump_json(ARTIFACTS/'latest_forecast.json',{'version':VERSION,'sites':latest})
    print(json.dumps({'done':True,'runtime_seconds':result['runtime_seconds'],'selected':{h:r['selected_model'] for h,r in report.items()}}),flush=True)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--data',type=Path,default=DEFAULT_DATA)
    args=parser.parse_args();train(args.data)
