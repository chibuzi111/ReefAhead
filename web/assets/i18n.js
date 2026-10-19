/* Local reviewed English text. No translation service or user-data upload. */
(() => {
  const en = {
    '关键局限：7天选用物理基线。14天AI的MAE改善95%描述性区间为 {{lo}} 至 {{hi}}，跨零。首次达到DHW≥4的固定提前量命中为7天 {{h7}}/{{n7}}、14天 {{h14}}/{{n14}}；这些是相关像素样本，不能证明提前预警有效。':'Key limits: the 7-day output uses the physical baseline. The 14-day AI MAE gain has a 95% descriptive interval of {{lo}} to {{hi}}, crossing zero. Exact-lead first-crossing hits at DHW ≥ 4 are {{h7}}/{{n7}} for 7 days and {{h14}}/{{n14}} for 14 days. These are correlated pixel samples; early-warning effectiveness is unproven.',

    '礁先知 ReefAhead · 仙本那热压力准备工具':'ReefAhead · Semporna heat-stress preparedness',
    '礁先知 / SEMPORNA':'SEMPORNA / CORAL REEFS',
    '决策工作台':'Decision workspace', '验证与边界':'Evidence & limits', '90 天试点':'90-day pilot',
    '研究原型':'Research prototype',
    '看见热压力的变化，':'Track changing heat stress.',
    '提前准备下一次巡护。':'Prepare the next observation patrol.',
    '面向仙本那附近海域的 7 / 14 天卫星热压力预测。':'7- and 14-day satellite heat-stress forecasts for waters near Semporna.',
    '将数据、预测区间和复核行动放在同一张工作台上。':'Observations, forecast intervals and human review in one workspace.',
    '一个地方':'One place', '一个气候问题':'One climate problem', '一个可检验的 AI 任务':'One testable AI task',
    '卫星示范像素':'Demonstration satellite pixel', '历史回放日期':'Historical replay date',
    '查看预测 ↗':'View forecast ↗', '最新数据':'Latest data', '正在读取数据…':'Loading observations…',
    '海表温度 / SST':'Sea-surface temperature / SST', '卫星夜间海表温度 · °C':'Satellite night-time SST · °C',
    '当前热压力 / DHW':'Current heat stress / DHW', '过去 12 周累积 · °C-weeks':'Accumulated over 12 weeks · °C-weeks',
    '未来第 7 天 / DHW':'DHW at day +7', '未来第 14 天 / DHW':'DHW at day +14',
    '热压力轨迹':'Heat-stress trajectory', '历史观测':'Observed', '预测':'Forecast',
    '单位 °C-weeks。色带仅连接第7/14天历史校准区间，不代表中间各日的区间预测；虚线 4 / 8 为 NOAA 热压力参考阈值。预测点不代表整段期间的最大风险。':'Units: °C-weeks. Shading joins historically calibrated intervals. Dashed lines at 4 and 8 are NOAA heat-stress reference thresholds. Forecast points are not the maximum risk over the intervening period.',
    '准备观察与复核':'Prepare observations and review', '导出本次简报 ↓':'Export this briefing ↓',
    '辅助制定巡护准备；实际出海、潜水、封闭或修复决策由有资质人员和主管机构负责。':'Supports patrol preparation. Qualified personnel and relevant authorities remain responsible for boat trips, diving, closures and restoration decisions.',
    '从像素到现场，保留尺度边界':'From satellite pixels to field observations',
    '示意图仅展示抽样像素之间的经纬度位置，不表示海岸线、珊瑚礁边界或真实巡护点。':'The diagram shows relative latitude and longitude of sampled pixels. It does not depict coastlines, reef boundaries or actual patrol locations.',
    '数据来源：NOAA Coral Reef Watch / CoralTemp v3.1。海表温度无法直接反映不同深度、珊瑚物种或局部水流。':'Source: NOAA Coral Reef Watch / CoralTemp v3.1. Sea-surface temperature does not directly resolve depth, coral species or local currents.',
    '热压力 ≠ 已发生白化':'Heat stress is not observed bleaching',
    '系统没有把卫星指标当作水下实测白化标签，也没有声称已验证珊瑚保护效果。用现场记录连接下一阶段验证。':'Satellite indicators are not underwater bleaching observations. No coral conservation benefit has been demonstrated. Field observations are needed for the next validation stage.',
    '下载现场观测记录模板 ↗':'Download field observation template ↗',
    '工作台不上传现场记录；模板含观察点经纬度及匿名观察者代码。敏感生态点位由试点伙伴决定是否公开。':'This workspace does not upload field records. The template includes observation coordinates and an anonymous observer code. Pilot partners must decide whether sensitive ecological locations may be shared.',
    '让结果经得起复核。':'Make the evidence inspectable.',
    '严格分开训练、模型选择、区间校准与最终测试。仅使用观测日期不晚于基准日的数据；尚未核验历史产品的实际发布时间。':'Training, model selection, interval calibration and final testing are separated in time. Inputs have observation dates no later than the forecast reference date; historical product release times have not been verified.',
    '训练':'Training', '模型选择':'Model selection', '区间校准':'Interval calibration', '保留测试':'Held-out test', '回放 / 漂移观察':'Replay / drift review',
    'AI 必须与强基线比较':'AI must be tested against strong baselines',
    '对比当前 DHW 持续、季节气候态与持续 HotSpot 的物理外推。报告误差、阈值事件、区间覆盖率与年度表现；未胜出的模型不会被描述成有效提升。':'Compare DHW persistence, seasonal climatology and physical extrapolation with persistent HotSpot. Report errors, threshold events, interval coverage and yearly results. Models that do not outperform baselines are not presented as improvements.',
    '相邻日期和空间像素存在相关性，日样本数不等于独立事件数。离线回测不等于前瞻运营验证。':'Nearby dates and pixels are correlated; daily rows are not independent events. Retrospective testing is not prospective operational validation.',
    '查看完整机器可读评估 ↗':'Read the full evaluation JSON ↗', '适用范围与风险':'Scope and risks',
    '约 5 km 卫星像素是热压力筛查尺度，不是潜点深度的温度测量。DHW 的参考阈值来自群体关系，无法保证某处珊瑚发生白化。':'A roughly 5 km satellite pixel screens heat stress; it does not measure temperature at dive-site depth. DHW thresholds reflect population-level associations and cannot confirm bleaching at an individual reef.',
    '90% 是校准目标，不是每次预测的正确概率；气候非平稳、云影响、卫星算法变化和数据延迟会影响可靠性。':'90% is the calibration target, not the probability that an individual forecast is correct. Climate shifts, cloud effects, satellite algorithm changes and delayed data can reduce reliability.',
    '查看数据来源与校验记录 ↗':'Read data provenance and checks ↗', '实际实验摘要':'Measured experiment results', '等待实验结果…':'Waiting for experiment results…', '展开完整评估 JSON':'Expand full evaluation JSON',
    '90 天，把原型带到现场。':'A proposed 90-day field pilot.',
    '拟面向当地保护组织、潜店巡护人员与海洋管理者开展小规模可用性试点。尚未与任何机构建立或宣称合作关系。':'A small usability pilot is proposed with local conservation organizations, dive operators and marine managers. No institutional partnership has been established or claimed.',
    '01 / 第 1–15 天':'01 / DAYS 1–15', '共定问题':'Define the problem together',
    '获得伙伴同意，访谈 5–8 名目标用户，确认巡护准备时间、可接受漏报与误报、语言和数据使用规则。':'With partner consent, interview 5–8 intended users about patrol preparation time, acceptable missed and false alerts, language and data-use rules.',
    '02 / 第 16–35 天':'02 / DAYS 16–35', '影子运行':'Shadow operation',
    '定时生成简报并由专家复核。与常规 NOAA 信息并行查看，不自动发出封闭、出海或潜水指令。':'Generate scheduled briefings for expert review alongside standard NOAA information. Do not automatically issue closure, boating or diving instructions.',
    '03 / 第 36–65 天':'03 / DAYS 36–65', '测试理解与行动':'Test understanding and decisions',
    '用交叉任务测试比较查找风险时间、阈值理解、区间理解和计划质量。实地记录与卫星代理指标分开保存。':'Use crossover tasks to compare risk-assessment time, threshold and interval understanding, and planning quality. Store field observations separately from satellite proxies.',
    '04 / 第 66–90 天':'04 / DAYS 66–90', '复盘与去留':'Review and decide',
    '分析误报、漏报、数据新鲜度、成本与采用意愿。不满足技术或可用性目标则缩减适用范围并重新校准。':'Assess false and missed alerts, data freshness, costs and willingness to adopt. If technical or usability targets are missed, narrow the scope and recalibrate in a future version.',
    '预设成功与停止条件':'Predefined success and stopping criteria',
    '目标：主要预测误差优于强基线、参考区间覆盖率在可接受范围、用户任务完成率 ≥80%、查找与理解风险的中位耗时降低 ≥30%。这些是待验证目标。':'Targets: outperform strong baselines on prediction error; achieve acceptable interval coverage; user task completion ≥80%; and ≥30% less median time to locate and understand risk. These targets have not yet been validated.',
    '停止：关键数据缺失或连续过期、误导性输出、未经允许的敏感点位使用；持续偏移则仅显示观测与官方数据链接。90 天内不承诺证明减少珊瑚死亡。':'Stop current-use recommendations when key data are missing or persistently stale, outputs are misleading, or sensitive locations lack permission. Persistent drift restricts the tool to observations and official links. The pilot does not promise evidence of reduced coral mortality within 90 days.',
    '下载现场观测模板 ↓':'Download field template ↓', 'ReefAhead · 礁先知':'ReefAhead · Semporna',
    '公开数据 · 可复核模型 · 人工决策':'Public data · Inspectable models · Human decisions', 'NOAA 数据方法 ↗':'NOAA data methods ↗',
    'ReefAhead 首页':'ReefAhead home', '主导航':'Main navigation', '选择卫星像素':'Select a satellite pixel',
    '过去120天DHW与7天和14天预测及区间':'DHW over the past 120 days, with forecasts and intervals at 7 and 14 days', '示范像素经纬度示意图':'Relative latitude and longitude of demonstration pixels',
    '数据暂不可用':'Data are temporarily unavailable', '暂无可用固定像素数据':'No fixed-pixel observations are available',
    '计算中…':'Calculating…', '无法生成预测':'Forecast unavailable',
    '90% 校准区间 {{lower}}–{{upper}}':'90% calibration interval {{lower}}–{{upper}}',
    '观测基准日 {{date}}':'Observation reference date {{date}}',
    '数据截至 {{date}} · 模型输出为研究性预测 · {{freshness}}':'Observations through {{date}} · Research forecast · {{freshness}}',
    '数据已延迟 {{days}} 天，须更新后复核':'Data are {{days}} days old; update before review',
    '仍需核对官方最新数据':'Check the latest official data before use',
    '维持常规观察':'Continue routine observations',
    '未来热压力预测仍需结合官方信息和现场观察。':'Interpret future heat stress alongside official information and field observations.',
    '核验数据日期与官方 NOAA 产品。':'Verify the observation date and official NOAA products.',
    '按既定方案记录水温和珊瑚状态。':'Record water temperature and coral condition using the agreed protocol.',
    '保持对未来更新和异常现场报告的关注。':'Watch for updated data and unusual field reports.',
    '优先准备现场复核':'Prioritize preparations for field review',
    '当前指标或预测区间触及 4 °C-weeks 参考阈值；这提示复核需求，并不证明已发生白化。':'Current DHW or a forecast interval reaches the 4 °C-weeks reference threshold. This calls for review; it does not confirm bleaching.',
    '由巡护负责人核对区间、阈值与数据延迟。':'Ask the patrol coordinator to check intervals, thresholds and data delays.',
    '在符合海况和安全规程时安排定点观察。':'Arrange fixed-location observations only when sea conditions and safety procedures allow.',
    '记录深度、抽样方法与白化比例，避免扩大解释。':'Record depth, sampling method and observed bleaching; avoid overgeneralization.',
    '先更新数据，再做判断':'Update data before making a decision',
    '数据距今 {{days}} 天，本页仅供历史回放。请更新并经人工复核后安排巡护。':'These observations are {{days}} days old. This page is historical replay only. Update the data and obtain human review before planning patrols.',
    '先检查 NOAA 官方最新产品及其观测日期。':'First check the latest official NOAA product and its observation date.',
    '更新数据后重新生成简报，并由负责人复核。':'Update the observations, regenerate the briefing and request coordinator review.',
    '保留本页用于历史分析，不将其当作当期巡护建议。':'Keep this page for historical analysis; do not treat it as current patrol advice.',
    '预测期':'Horizon', '采用方法':'Selected method', '测试 MAE':'Test MAE', '物理基线 MAE':'Physical baseline MAE', '区间覆盖':'Interval coverage', '{{days}} 天':'{{days}} days',
    'DHW 持续':'DHW persistence', '持续 HotSpot 物理外推':'Physical HotSpot persistence', '季节气候态':'Seasonal climatology', '梯度提升残差模型':'Gradient-boosted residual model', '随机森林残差模型':'Random-forest residual model',
    'MAE单位 °C-weeks；测试期2022–2025。90%为校准目标，表中为实际覆盖率。结果是历史卫星指标预测，非生态成效。':'MAE units: °C-weeks; test period: 2022–2025. 90% is the calibration target; the table shows measured coverage. These are retrospective satellite-indicator forecasts, not ecological outcomes.',
    '无法读取数据：{{detail}}':'Unable to read data: {{detail}}'
  };
  Object.assign(en,{"模型分歧与人工复核": "Model disagreement & human review", "把热压力像素与已制图生境对应": "Relate heat-stress pixels to mapped habitat", "Allen Coral Atlas局部生境与NOAA像素叠加图": "Local Allen Coral Atlas habitat and NOAA pixel overlay", "图中为地图集真实分类多边形的显示简化版；网格为NOAA热压力像素，不是巡护路线。": "Simplified display of actual Atlas classification polygons. Grid cells represent NOAA heat-stress pixels, not patrol routes.", "Coral/Algae 是珊瑚与藻类合并类；已制图面积不等于活珊瑚覆盖率。未制图不等于没有珊瑚礁，历史生境图也不能证明当前白化状态。": "Coral/Algae combines coral and algae. Mapped area is not live-coral cover. Unmapped does not mean reef-free, and historical habitat maps cannot establish current bleaching.", "地图数据 © Allen Coral Atlas Partnership / Arizona State University，CC BY 4.0；仅展示局部区域。": "Map data © Allen Coral Atlas Partnership / Arizona State University, CC BY 4.0; local area only.", "官方推荐数据源与接入状态": "Recommended sources & integration status", "正在读取空间数据…": "Loading spatial data…", "正在读取数据目录…": "Loading data catalog…", "查看字段、单位与关联规则 ↗": "Inspect fields, units and join rules ↗", "新增诊断为看过原测试集后的探索性分析；没有重新训练，也不将其当作新的独立准确率提升。": "The new diagnostics are exploratory after seeing the original test set. No retraining or newly independent skill improvement is claimed.", "查看事件去重与分层诊断 ↗": "Inspect episode grouping & stratified diagnostics ↗", "模型证据需要复核": "Model evidence requires review", "模型分歧、参考范围或阈值包络触发复核；请结合官方数据与现场证据判断。": "Model disagreement, reference ranges or a threshold envelope trigger review. Consult official data and field evidence.", "比较AI与物理基线，检查误差和参考范围。": "Compare AI and the physical baseline; inspect errors and reference ranges.", "比较包络未经校准，不能解释为覆盖概率。": "The comparison envelope is uncalibrated and has no coverage probability.", "由负责人核验信息后决定是否安排观察。": "The coordinator verifies evidence before deciding on observations.", "输入数据已过期": "Input observations are stale", "当前变量超出训练参考范围": "Current variables exceed the training reference range", "训练参考范围不可用": "Training reference range unavailable", "模型对热压力阈值判断不一致": "Models disagree at the heat-stress threshold", "比较包络跨过热压力阈值": "Comparison envelope spans the heat-stress threshold", "采用预测": "Selected forecast", "AI候选": "AI candidate", "物理基线": "Physical baseline", "未经校准的比较包络": "Uncalibrated comparison envelope", "比较包络包含历史校准区间及模型分歧，没有覆盖率保证，也不是新的90%区间。未触发复核不代表安全。": "The envelope contains the historical interval and model disagreement. It has no coverage guarantee and is not a new 90% interval. No review trigger does not mean safe.", "请继续核验官方数据与现场情况": "Continue checking official information and field conditions", "空间数据暂不可用；不推断礁区是否存在。": "Spatial data unavailable; no inference about reef presence.", "真实生境分类 / 北 ↑": "Actual habitat classes / North ↑", "已制图底栖生境与当前像素": "Mapped benthic habitat in this pixel", "像素面积 {{pixel}} km²；已制图 {{mapped}} km²（{{fraction}}%）。": "Pixel area {{pixel}} km²; mapped habitat {{mapped}} km² ({{fraction}}%).", "分类": "Class", "面积 km²": "Area km²", "未制图部分状态未知，不能当作无礁区。静态生境仅作空间背景，不加入历史预测特征。": "Unmapped areas have unknown status. Static habitat is spatial context only and is excluded from historical forecasting features.", "数据目录暂不可用": "Data catalog unavailable", "已接入逐日时序": "Daily time series integrated", "报告证据，非逐日标签": "Report evidence, not daily labels", "已接入局部空间数据": "Local spatial data integrated", "空间数据待获取": "Spatial data pending", "资源帖是数据源目录，没有统一评分脚本。生境制图精度、热压力预测误差与现场白化验证属于不同任务。": "The resource post is a source directory without a unified scoring script. Habitat mapping accuracy, heat-stress forecast error and field bleaching validation are different tasks."});
  Object.assign(en,{"当前四个网格未与RCM该公开地图的仙本那41个调查站重合，仍缺少同点现场验证。": "None of the four current cells overlaps the 41 Semporna survey stations in the reviewed RCM public map. Same-site field validation is still missing."});
  let lang='zh';
  try { if(localStorage.getItem('reefahead-language')==='en') lang='en'; } catch (_) {}
  function t(key,params={}) { return (lang==='en'?(en[key]||key):key).replace(/\{\{(\w+)\}\}/g,(_,k)=>String(params[k]===undefined?'':params[k])); }
  const walker=document.createTreeWalker(document.documentElement,NodeFilter.SHOW_TEXT);
  const textNodes=[];
  while(walker.nextNode()) {
    const n=walker.currentNode;
    if(!['SCRIPT','STYLE'].includes((n.parentElement&&n.parentElement.tagName))&&en[n.nodeValue.trim()])
      textNodes.push([n,n.nodeValue,n.nodeValue.trim()]);
  }
  const attrs=[];
  document.querySelectorAll('[aria-label]').forEach(n=>{const v=n.getAttribute('aria-label');if(en[v])attrs.push([n,v]);});
  function apply(){
    document.documentElement.lang=lang==='en'?'en':'zh-CN';
    for(const [n,original,key] of textNodes)n.nodeValue=lang==='en'?original.replace(key,en[key]):original;
    for(const [n,key] of attrs)n.setAttribute('aria-label',t(key));
    const button=document.getElementById('language');
    button.textContent=lang==='en'?'中文':'English';button.lang=lang==='en'?'zh-CN':'en';
    button.setAttribute('aria-label',lang==='en'?'切换到中文':'Switch to English');
  }
  window.ReefI18n={t,get language(){return lang;},onchange:null};
  document.getElementById('language').onclick=()=>{
    lang=lang==='en'?'zh':'en';try{localStorage.setItem('reefahead-language',lang);}catch(_){}
    apply();if(window.ReefI18n.onchange)window.ReefI18n.onchange();
  };
  apply();
})();
