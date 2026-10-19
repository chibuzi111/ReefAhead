#!/usr/bin/env python3
"""Generate candid post-evaluation interpretation without modifying trained sources."""
from pathlib import Path
import json
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts'
MARKER='\n## Post-evaluation interpretation\n'

def fmt(value,digits=3):return 'NA' if value is None else f'{value:.{digits}f}'
def pct(value):return 'NA' if value is None else f'{100*value:.2f}%'

def main():
 e=json.loads((ART/'evaluation.json').read_text())
 p=pd.read_csv(ART/'all_predictions.csv',parse_dates=['date','target_date'],float_precision='round_trip')
 crossings=pd.read_csv(ART/'threshold_crossing_events.csv',parse_dates=['target_date','issue_date'],float_precision='round_trip')
 lines=['# 模型结果的完整解读','','本报告从固定模型实际产物自动生成；不训练、不重新校准，也不根据测试结果重新选择模型。预测对象是签发日恰好7或14天后的卫星像素DHW（°C-weeks），不是区间内是否发生事件，也不是现场白化诊断。',
  '', '## 验证集决定部署模型','',
  '| 提前量 | 验证集选择 | 验证MAE | 测试样本（像素日） |', '|---|---|---:|---:|']
 for h,r in e['horizons'].items():
  lines.append(f"| {h}天 | {r['selected_model']} | {r['validation'][r['selected_model']]['mae']:.6f} | {r['partitions']['test']['selected']['n']} |")
 lines+=['','7天验证结果选择物理持续性基线，不能把该时距的结果归功于AI；14天选择随机森林残差模型。模型选择只看2017–2019验证集。四个像素彼此邻近，按日重叠窗口的样本量不代表同样数量的独立证据。',
 '', '## 测试集平均误差与关键取舍（2022–2025）','',
 '| 提前量 / 方法 | MAE | RMSE | DHW≥4日精确率 | DHW≥4日召回率 | 误报像素日 | 漏报像素日 | DHW≥4日MAE |',
 '|---|---:|---:|---:|---:|---:|---:|---:|']
 for h,r in e['horizons'].items():
  t=r['partitions']['test']
  for name,key in [('部署选择','selected'),('物理持续性','physical_persistence'),('最佳验证AI','random_forest_residual'),('DHW持续性','dhw_persistence')]:
   m=t[key];lines.append(f"| {h}天 / {name} | {m['mae']:.6f} | {m['rmse']:.6f} | {pct(m['event_precision'])} | {pct(m['event_recall'])} | {m['false_positive']} | {m['false_negative']} | {fmt(m['heat_stress_mae'],6)} |")
 r=e['horizons']['14'];t=r['partitions']['test'];ai=t['selected'];base=t['physical_persistence'];gain=t['selected_gain_vs_physics']
 rel=(base['mae']-ai['mae'])/base['mae']
 lines+=['',f"14天AI的平均MAE较物理基线减少{100*rel:.2f}%，但热应激日MAE由{base['heat_stress_mae']:.6f}升至{ai['heat_stress_mae']:.6f}；误报从{base['false_positive']}降到{ai['false_positive']}个像素日，漏报却从{base['false_negative']}升到{ai['false_negative']}个像素日。它体现的是本样本内平均误差与误报/漏报的取舍，不能表述成在全部风险条件下更好。",
 '',f"与物理基线配对的90天日历块bootstrap，MAE改善估计为{gain['mae_gain']:.6f}，描述性95%区间[{gain['ci95_lower']:.6f}, {gain['ci95_upper']:.6f}]，包含0。仅{gain['blocks']}个时间块，所有近邻像素作为同一时间块重采样，不能据此声称稳定或显著的普遍优胜。", 
 '', '## 首次越阈检验必须与事件日指标一起阅读','',
 '| 提前量 | 可评估首次越过DHW=4的像素级上穿样本 | 恰好该提前量命中 |', '|---|---:|---:|']
 for h,r in e['horizons'].items():
  o=r['partitions']['test']['onsets'];lines.append(f"| {h}天 | {o['n']} | {o['exact_lead_hits']}/{o['n']} |")
 months=sorted(crossings.target_date.dt.strftime('%Y-%m').unique())
 lines+=['',f"这些上穿全部发生在{'、'.join(months)}，来自相关的近邻像素，并非独立生态白化事件。14天模型在这{t['onsets']['n']}个像素级上穿样本上的恰好14天提前命中为{t['onsets']['exact_lead_hits']}，因此尚未证明能提前识别新热应激事件。较高的事件日召回率也包含事件已经持续期间的预测，不能替代首次发生预警能力。",
 '', '| 时距 | 像素 | 目标日期 | 签发日期 | 真实DHW | 预测DHW | 越阈命中 |', '|---|---|---|---|---:|---:|---|']
 for _,x in crossings.sort_values(['horizon','site_id','target_date']).iterrows():
  lines.append(f"| {int(x.horizon)}天 | {x.site_id} | {x.target_date.date()} | {x.issue_date.date()} | {x.observed:.2f} | {x.prediction:.4f} | {'是' if bool(x.alert_at_exact_lead) else '否'} |")
 lines+=['','## 区间是名义90%，不是90%覆盖保证','',
 '| 时距 | 校准期实测覆盖 | 测试期实测覆盖 | 2026回放实测覆盖 | 测试期平均区间宽度 |','|---|---:|---:|---:|---:|']
 for h,r in e['horizons'].items():
  ps=r['partitions'];lines.append(f"| {h}天 | {pct(ps['calibration']['selected']['interval_coverage'])} | {pct(ps['test']['selected']['interval_coverage'])} | {pct(ps['replay_2026']['selected']['interval_coverage'])} | {ps['test']['selected']['mean_interval_width']:.6f} |")
 lines+=['','校准仅使用2020–2021；时序相关、气候分布变化和空间相关破坏通常的可交换性前提。低于90%的实测覆盖如实保留，没有使用测试集扩大区间。概率字段只是固定校准残差对DHW≥4的经验频率，不是经现场验证的白化概率。',
 '', '## 每年表现（所有四像素合并）','',
 '| 数据段 / 签发年份 | 时距 | 像素日数 | 选择模型MAE | 物理基线MAE | 选择模型覆盖 | DHW≥4像素日数 |',
 '|---|---|---:|---:|---:|---:|---:|']
 for (partition,h,year),g in p.loc[p.partition.isin(['test','replay_2026'])].groupby(['partition','horizon',p.date.dt.year]):
  selected=float(np.abs(g.selected_prediction-g.observed).mean());physical=float(np.abs(g.physical_persistence-g.observed).mean());coverage=float(((g.observed>=g.lower90)&(g.observed<=g.upper90)).mean())
  lines.append(f"| {partition} / {year} | {h}天 | {len(g)} | {selected:.6f} | {physical:.6f} | {pct(coverage)} | {int(g.observed.ge(4).sum())} |")
 lines+=['',f"2026年14天选择模型MAE为{e['horizons']['14']['partitions']['replay_2026']['selected']['mae']:.6f}，高于物理持续性基线的{e['horizons']['14']['partitions']['replay_2026']['physical_persistence']['mae']:.6f}。这一结果进一步限制了把2022–2025平均改善外推到未来的结论。",
 '', '2026部分是事后取得档案数据的前推回放，不能称为已上线的实时预测试验；尚未核验历史每个签发时点的数据发布时间。不同提前量由于标签截止规则，末端可评估签发日期不同。没有独立地点外推验证或现场白化标签，且四个像素不是经现场确认的珊瑚礁边界。',
 '', '## 产物和复现','',
 '`artifacts/evaluation.json`是未四舍五入的主指标；`all_predictions.csv`以17位有效数字保存，审计读取时使用`float_precision="round_trip"`。逐站和逐年表、阈值上穿样本、模型文件、数据及源码哈希均在项目中。',
 '', '训练后的解释文档重建命令：`./.venv/bin/python scripts/write_evaluation_analysis.py`。该命令不更改任何模型产物、原始评测指标或冻结训练源代码。','']
 (ROOT/'docs/evaluation_analysis.md').write_text('\n'.join(lines))
 summary=['','## Post-evaluation interpretation','',
  'The 7-day validation winner is physical persistence; its reported selected-model performance is not an AI gain. The 14-day winner is the random-forest residual model.',
  '',f"On the 2022–2025 test set, exact-lead first crossings of satellite DHW=4 were detected in {e['horizons']['7']['partitions']['test']['onsets']['exact_lead_hits']}/3 cases at 7 days and {e['horizons']['14']['partitions']['test']['onsets']['exact_lead_hits']}/3 at 14 days. These are three correlated pixel-level upcrossings, all in {', '.join(months)}, not three independent ecological events. Event-day recall includes already-ongoing stress and must not be presented as evidence of new-event early-warning skill.",
  '',f"For the 14-day forecast, MAE is {ai['mae']:.6f} versus {base['mae']:.6f} for physical persistence ({100*rel:.2f}% lower), but its descriptive block-bootstrap improvement interval [{gain['ci95_lower']:.6f}, {gain['ci95_upper']:.6f}] includes zero. False-positive pixel-days fall from {base['false_positive']} to {ai['false_positive']}, while false negatives rise from {base['false_negative']} to {ai['false_negative']}; heat-stress-day MAE increases from {base['heat_stress_mae']:.6f} to {ai['heat_stress_mae']:.6f}. There is no established universal superiority.",
  '',f"Nominal 90% intervals cover {pct(e['horizons']['7']['partitions']['test']['selected']['interval_coverage'])} and {pct(ai['interval_coverage'])} of 7-/14-day test labels; 14-day coverage is {pct(e['horizons']['14']['partitions']['replay_2026']['selected']['interval_coverage'])} in the 2026 retrospective replay. These are empirical findings, not coverage guarantees.",
  '', f"In the 2026 replay, 14-day selected-model MAE is {e['horizons']['14']['partitions']['replay_2026']['selected']['mae']:.6f}, worse than the physical baseline ({e['horizons']['14']['partitions']['replay_2026']['physical_persistence']['mae']:.6f}); the 2022–2025 average improvement does not establish future superiority.",
  '', 'See [complete interpretation, onset cases and annual results](evaluation_analysis.md). Rebuild this section after training with `.venv/bin/python scripts/write_evaluation_analysis.py`; this postprocessor leaves the frozen training source and model artifacts unchanged.','']
 for filename in ['evaluation.md','model_card.md']:
  path=ROOT/'docs'/filename;text=path.read_text().split(MARKER)[0].rstrip();path.write_text(text+'\n'+'\n'.join(summary))
 print(json.dumps({'created':'docs/evaluation_analysis.md','updated':['docs/evaluation.md','docs/model_card.md'],'first_crossings':{h:v['partitions']['test']['onsets'] for h,v in e['horizons'].items()}},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
