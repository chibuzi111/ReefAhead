#!/usr/bin/env python3
"""Exploratory audit of v1 forecasts plus post-v1 review diagnostics.

Never train, tune, recalibrate or overwrite a v1 artifact. Existing 2022-2026
results have already been inspected and cannot become a fresh holdout.
"""
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.features import DEFAULT_DATA,load_data
from src.diagnostics import build_diagnostics,VERSION
ART=ROOT/'artifacts'
OUT=ART/'diagnostics_v2'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def finite(v):
    if isinstance(v,dict):return {str(k):finite(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [finite(x) for x in v]
    if isinstance(v,(np.integer,)):return int(v)
    if isinstance(v,(np.floating,float)):return float(v) if np.isfinite(v) else None
    if isinstance(v,(np.bool_,)):return bool(v)
    if isinstance(v,pd.Timestamp):return v.strftime('%Y-%m-%d')
    return v

def group_onsets(onsets,max_gap_days=84):
    """Same declared region, onset gaps <=84 days: a descriptive proxy only.

    Single-linkage can join a long sequence; this is deliberately not a claim
    that groups are biologically independent or that 84 days defines a season.
    """
    groups=[]
    for (partition,region),part in onsets.groupby(['partition','region'],sort=True):
        current=[];last=None
        for row in part.sort_values(['target_date','site_id']).to_dict('records'):
            if last is not None and (row['target_date']-last).days>max_gap_days:
                groups.append(current);current=[]
            current.append(row);last=row['target_date']
        if current:groups.append(current)
    return groups

def metrics(g):
    y=g.observed.to_numpy();pred=g.selected_prediction.to_numpy();events=y>=4;alert=pred>=4
    tp=int((events&alert).sum());fp=int((~events&alert).sum());fn=int((events&~alert).sum())
    review=g.review_required.to_numpy().astype(bool)
    return {'n_pixel_days':len(g),'selected_mae':float(np.abs(pred-y).mean()),
      'physical_mae':float(np.abs(g.physical_persistence-y).mean()),
      'event_days_ge4':int(events.sum()),'selected_false_positive_days':fp,'selected_false_negative_days':fn,
      'selected_event_precision':tp/(tp+fp) if tp+fp else None,'selected_event_recall':tp/(tp+fn) if tp+fn else None,
      'v1_nominal90_empirical_coverage':float(((y>=g.lower90)&(y<=g.upper90)).mean()),
      'v1_mean_interval_width':float((g.upper90-g.lower90).mean()),
      'uncalibrated_envelope_empirical_containment':float(((y>=g.envelope_lower)&(y<=g.envelope_upper)).mean()),
      'uncalibrated_envelope_mean_width':float((g.envelope_upper-g.envelope_lower).mean()),
      'review_days':int(review.sum()),'review_fraction':float(review.mean()),
      'observed_event_days_with_review_flag':int((events&review).sum()),
      'selected_false_negative_days_with_review_flag':int((events&~alert&review).sum()),
      'review_on_non_event_days':int((~events&review).sum()),
      'outside_training_range_days':int(g.outside_training_range.sum()),
      'model_threshold_disagreement_days':int(g.threshold_disagreement.sum())}

def main():
    OUT.mkdir(exist_ok=True)
    v1=json.loads((ART/'evaluation.json').read_text())
    protocol=json.loads((ROOT/'evidence/training_protocol.json').read_text())
    frozen=[ROOT/k for k in protocol['source_sha256']]+[ROOT/'evidence/training_protocol.json']
    frozen += [ART/n for n in ['evaluation.json','model_7d.joblib','model_14d.joblib','all_predictions.csv','test_predictions.csv','replay_2026_predictions.csv','validation_predictions.csv']]
    before={str(p.relative_to(ROOT)):sha(p) for p in frozen}
    for k,h in protocol['source_sha256'].items():assert before[k]==h,f'V1 source drift: {k}'
    assert sha(DEFAULT_DATA)==v1['data_sha256'],'V1 data changed; this audit must use its original complete input'
    rules={'created_at_utc':datetime.now(timezone.utc).isoformat(),'version':VERSION,
      'designed_after_v1_test_and_replay_observed':True,'evidence_status':'exploratory retrospective diagnostics; not a new holdout or a new forecast model',
      'reference':'Raw same-pixel input ranges from 2003-01-01 through 2019-12-31; no test/replay labels in rules.',
      'point_forecasts_and_v1_intervals':'Unchanged.',
      'review_rules':['stale input in live API','current input outside fitting-era marginal min/max','AI/physical point estimates disagree at satellite DHW>=4','uncalibrated comparison envelope spans DHW=4','reference/forecast unavailable'],
      'envelope':'[min(v1 lower, AI point, physical point, selected point), max(v1 upper, AI point, physical point, selected point)]; no nominal coverage level.',
      'freshness_replay':'Historical release timestamps unavailable. Staleness is NOT reconstructed in offline rule rates; diagnostics assume observation-day input for this descriptive replay only.',
      'regional_episode_proxy':'All four existing nearby demonstration pixels are one declared Semporna demo region. Merge consecutive pixel upcrossing dates separated by <=84 days within the same partition. This is a retrospective proxy, not ecological independence or a defined climate season.',
      'no_test_tuning':'No threshold, hyperparameter, candidate selection or recalibration optimized against these diagnostics.',
      'frozen_v1_hashes':before,'new_source_sha256':{'src/diagnostics.py':sha(ROOT/'src/diagnostics.py'),'scripts/evaluate_v2.py':sha(__file__)}}
    (ROOT/'evidence/diagnostics_v2_protocol.json').write_text(json.dumps(rules,indent=2)+'\n')
    raw=load_data(DEFAULT_DATA)
    look=raw.set_index(['site_id','date'])[['sst','hotspot','dhw','ssta']].to_dict('index')
    p=pd.read_csv(ART/'all_predictions.csv',parse_dates=['date','target_date'],float_precision='round_trip')
    p=p.loc[p.partition.isin(['test','replay_2026'])].copy()
    diagnostics=[];reason_counts=Counter()
    for row in p.itertuples():
        payload={'site_id':row.site_id,'issue_date':str(row.date.date()),'stale_input':False,
          'current':look[(row.site_id,row.date)],'forecasts':[{'horizon':row.horizon,'target_date':str(row.target_date.date()),
          'mean':row.selected_prediction,'ai_prediction':row.ai_prediction,'baseline':row.physical_persistence,
          'lower':row.lower90,'upper':row.upper90,'interval_nominal_coverage':.9,'model_name':row.selected_model}]}
        d=build_diagnostics(payload,data_path=DEFAULT_DATA);h=d['per_horizon'][0]
        reason_counts.update(d['overall']['reasons'])
        diagnostics.append({'review_required':d['overall']['review_required'],'review_reasons':'|'.join(d['overall']['reasons']),
          'outside_training_range':bool(d['training_range']['outside_variables']),
          'outside_variables':'|'.join(d['training_range']['outside_variables']),
          'threshold_disagreement':h['threshold_disagreement'],'envelope_spans_threshold':h['envelope_spans_threshold'],
          'absolute_model_disagreement':h['absolute_model_disagreement'],
          'envelope_lower':h['comparison_envelope']['lower'],'envelope_upper':h['comparison_envelope']['upper']})
    d=pd.concat([p.reset_index(drop=True),pd.DataFrame(diagnostics)],axis=1)
    d.to_csv(OUT/'row_diagnostics.csv',index=False,float_format='%.17g')
    pooled=[];strata=[]
    for (partition,h),g in d.groupby(['partition','horizon']):
        pooled.append({'partition':partition,'horizon':int(h),**metrics(g)})
        dimensions={'site':g.site_id,'issue_year':g.date.dt.year.astype(str),
          'calendar_quarter':g.date.dt.quarter.map(lambda q:f'Q{q}'),
          'current_stress':pd.cut(g.current_dhw,[-np.inf,4,8,np.inf],right=False,labels=['below_4','4_to_below_8','8_or_more']).astype(str)}
        for dimension,keys in dimensions.items():
            for level,sub in g.groupby(keys):
                strata.append({'partition':partition,'horizon':int(h),'stratification':dimension,'stratum':str(level),**metrics(sub)})
    pd.DataFrame(strata).to_csv(OUT/'stratified_metrics.csv',index=False,float_format='%.17g')
    onset_rows=[]
    for site,g in raw.groupby('site_id'):
        g=g.sort_values('date');cross=g.dhw.ge(4)&g.dhw.shift().lt(4)&g.date.diff().dt.days.eq(1)
        for row in g.loc[cross].itertuples():
            partition='test' if pd.Timestamp('2022-01-01')<=row.date<=pd.Timestamp('2025-12-31') else 'replay_2026' if row.date>=pd.Timestamp('2026-01-01') else None
            if partition:onset_rows.append({'site_id':site,'region':'semporna_demo','partition':partition,'target_date':row.date,'observed_dhw':row.dhw})
    onset_frame=pd.DataFrame(onset_rows,columns=['site_id','region','partition','target_date','observed_dhw'])
    onset_scores=[];episode_scores=[]
    for row in onset_rows:
        for h in (7,14):
            match=d.loc[d.site_id.eq(row['site_id'])&d.target_date.eq(row['target_date'])&d.horizon.eq(h)&d.partition.eq(row['partition'])]
            if len(match):
                r=match.iloc[0];onset_scores.append({**row,'horizon':h,'assessable':True,'issue_date':r.date,
                  'selected_point':r.selected_prediction,'ai_point':r.ai_prediction,'physical_point':r.physical_persistence,
                  'selected_exact_lead_hit':bool(r.selected_prediction>=4),'physical_exact_lead_hit':bool(r.physical_persistence>=4),
                  'review_flag_at_exact_lead':bool(r.review_required)})
            else:onset_scores.append({**row,'horizon':h,'assessable':False})
    for i,group in enumerate(group_onsets(onset_frame),1):
        first=min(x['target_date'] for x in group);partition=group[0]['partition']
        for h in (7,14):
            at=d.loc[d.partition.eq(partition)&d.horizon.eq(h)&d.target_date.eq(first)]
            episode_scores.append({'proxy_id':f'{partition}-semporna-{i}','partition':partition,'region':'semporna_demo',
              'horizon':h,'first_onset':first,'last_onset':max(x['target_date'] for x in group),
              'pixel_upcrossings':len(group),'participating_pixels':sorted({x['site_id'] for x in group}),
              'assessable':bool(len(at)),'available_pixel_forecasts':len(at),
              'selected_region_signal_at_first_onset':bool(at.selected_prediction.ge(4).any()) if len(at) else None,
              'physical_region_signal_at_first_onset':bool(at.physical_persistence.ge(4).any()) if len(at) else None,
              'any_review_flag_at_first_onset':bool(at.review_required.any()) if len(at) else None})
    pd.DataFrame(onset_scores).to_csv(OUT/'pixel_upcrossings.csv',index=False,float_format='%.17g')
    pd.DataFrame(episode_scores).to_csv(OUT/'regional_episode_proxies.csv',index=False)
    after={str(p.relative_to(ROOT)):sha(p) for p in frozen}
    assert before==after,'Audit altered a frozen v1 artifact'
    result={'project':'ReefAhead','version':VERSION,'generated_at_utc':datetime.now(timezone.utc).isoformat(),
      'evidence_status':'exploratory_after_v1_test_and_replay_observed','independent_holdout':False,'model_retrained':False,
      'point_forecasts_unchanged':True,'v1_hashes_unchanged':before==after,'v1_hashes':before,
      'input_data_sha256':v1['data_sha256'],'rules':{k:v for k,v in rules.items() if k!='frozen_v1_hashes'},
      'pooled':pooled,'stratified':strata,'review_reason_counts':dict(reason_counts),
      'pixel_upcrossings':onset_scores,'regional_episode_proxies':episode_scores,
      'spatial_validation':{'status':'not_established','reason':'All four nearby pixels were used during fitting. Per-pixel scores and Atlas habitat context do not create a held-out region or confirm reef-scale skill.'},
      'prospective_validation_plan':['Freeze any new model and diagnostic protocol before acquiring its prospective forecast outcomes. Existing 2022-2026 labels are development evidence, not a new holdout.',
        'Record source publication timestamps and immutable issue-time input snapshots; evaluate each h-day target only when it becomes observable.',
        'Collect independent reef regions and separate whole regions for outer spatial evaluation, with rolling-origin inner time splits and label-date embargoes.',
        'Record human-reviewed field observations with location/time/method and access consent; Reef Check reports and Atlas habitat geometry are context, not substitute pixel-day bleaching labels.'],
      'limitations':['The comparison envelope is uncalibrated and its empirical containment on reused data is not a coverage guarantee.',
        'Review flags are designed after seeing v1 results; observed flag counts are not independently validated early-warning skill.',
        'The 84-day regional grouping is a descriptive correlation proxy, not a biologically validated event definition or proof of independence.',
        'Offline review rates exclude unverified historic publication-time freshness; the live API separately reports stale inputs.',
        'No point forecast, risk threshold, model selection or calibration was changed; v1 missed first onsets and 2026 degradation remain.']}
    (ART/'evaluation_v2.json').write_text(json.dumps(finite(result),ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    lines=['# v2：分歧、漂移与事件单位审计','','这是看过v1测试和2026回放后设计的探索性诊断；不是新模型，也不是新的独立测试。v1点预测、区间、训练源和模型文件哈希全部保持不变。',
      '', '## 展示与人工复核规则','','并列显示AI与物理持续性估计，以及包含两者和原v1区间的比较包络。比较包络没有名义覆盖率，不得称为90%预测区间。当前输入超出2003–2019同像素边际范围、模型在DHW≥4判断上分歧、包络跨4、数据过期或参考缺失时提示人工复核；未触发也不表示安全。',
      '', '## 复用历史数据的描述性结果','',
      '| 数据段 | 时距 | 原选择模型MAE | 原物理MAE | 原90%区间实测覆盖 | 未校准包络实测包含 | 人工复核比例 |',
      '|---|---:|---:|---:|---:|---:|---:|']
    for r in pooled:lines.append(f"| {r['partition']} | {r['horizon']}天 | {r['selected_mae']:.6f} | {r['physical_mae']:.6f} | {r['v1_nominal90_empirical_coverage']:.2%} | {r['uncalibrated_envelope_empirical_containment']:.2%} | {r['review_fraction']:.2%} |")
    lines+=['','包络变宽可以提高对这些已见标签的包含比例，但不证明未来覆盖有效；复核比例和包络包含均不可包装成新预测技能。历史发布时间不可核验，因此这张表不重建数据过期规则；实时API仍单独提示过期。',
      '', '## 从像素上穿到区域相关性代理','',
      '原始像素首次上穿保留。将同一示范海域中相邻上穿日期间隔不超过84天的样本合并，仅用于说明相关性与证据量；84天来自DHW记忆窗口，并不等于生物学事件或气候季节。每个代理在最早上穿日检验恰好7/14天前的区域信号。',
      '', '| 数据段 | 时距 | 区域代理首日 | 包含像素上穿数 | 原选择模型有区域信号 | 物理模型有区域信号 | 任一复核标志 |',
      '|---|---:|---|---:|---|---|---|']
    for r in episode_scores:lines.append(f"| {r['partition']} | {r['horizon']}天 | {str(r['first_onset'].date())} | {r['pixel_upcrossings']} | {r['selected_region_signal_at_first_onset']} | {r['physical_region_signal_at_first_onset']} | {r['any_review_flag_at_first_onset']} |")
    lines+=['','这些代理仍然不能作为独立生态事件计数。复核标志是人工检查理由，不应重新命名为成功预警。',
      '', '## 空间与下一次验证','','逐站、年份、日历季度和签发日热应激分层结果见 `artifacts/diagnostics_v2/stratified_metrics.csv`。四个像素都参与过拟合，逐站统计不能证明空间泛化。Allen Coral Atlas的局部栖息地几何只能增加地理背景，不能直接给历史每日白化标签。',
      '', '未来提升需要先冻结方案，再记录真正前瞻的输入发布时间、签发与到期标签；空间验证应留出完整独立海域，并在内层使用滚动时间划分与标签日期隔离。已见的2022–2026数据都只能用于开发与失败分析。',
      '', '## 复现','','运行 `.venv/bin/python scripts/evaluate_v2.py`。该命令读取v1产物，输出v2报告与诊断表，不训练或修改v1。协议与前后哈希核验见 `evidence/diagnostics_v2_protocol.json` 和 `artifacts/evaluation_v2.json`。','']
    (ROOT/'docs/evaluation_v2.md').write_text('\n'.join(lines))
    print(json.dumps(finite({'v1_hashes_unchanged':True,'row_count':len(d),'pooled':pooled,'regional_episode_proxies':episode_scores}),indent=2))

if __name__=='__main__':main()
