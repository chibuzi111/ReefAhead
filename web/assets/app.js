const $=id=>document.getElementById(id);
const t=(key,params)=>window.ReefI18n.t(key,params);
let spatialData=null,habitatData=null,catalogData=null;
let sites=[],current,lastEvaluation,lastError,lastEvaluationError,loading=false,requestId=0;
const num=x=>Number.isFinite(Number(x))?Number(x).toFixed(2):'—';
async function get(url){const r=await fetch(url);if(!r.ok){const v=await r.json().catch(()=>({}));throw new Error(typeof v.detail==='string'?v.detail:'数据暂不可用');}return r.json();}
document.querySelectorAll('.nav').forEach(b=>b.onclick=()=>{document.querySelectorAll('.view').forEach(v=>v.hidden=v.id!==b.dataset.view);document.querySelectorAll('.nav').forEach(n=>n.classList.toggle('active',n===b));if(b.dataset.view==='evidence')evidence();});
function svgEl(type,attrs,text){const el=document.createElementNS('http://www.w3.org/2000/svg',type);Object.entries(attrs).forEach(([k,v])=>el.setAttribute(k,v));if(text!==undefined)el.textContent=text;return el;}
function chart(d){const svg=$('chart');svg.replaceChildren();const hist=d.history||[],fs=d.forecasts||[];if(!hist.length)return;
const x0=new Date(hist[0].date).getTime(),x1=new Date(d.issue_date).getTime()+17*864e5;
const ymax=Math.max(9,...hist.map(p=>p.dhw),...fs.map(p=>p.upper))*1.12;
const x=date=>48+(new Date(date).getTime()-x0)/(x1-x0)*686,y=v=>240-v/ymax*205;
for(let val=0;val<=ymax;val+=2){svg.append(svgEl('line',{x1:48,x2:735,y1:y(val),y2:y(val),stroke:val===4||val===8?'#56755a':'#29434b','stroke-dasharray':val===4||val===8?'5 5':'0'}));svg.append(svgEl('text',{x:36,y:y(val)+4,fill:'#8ca9ae','font-size':10,'text-anchor':'end'},String(val)));}
svg.append(svgEl('polyline',{points:hist.map(p=>x(p.date)+','+y(p.dhw)).join(' '),fill:'none',stroke:'#6db7b4','stroke-width':2.5}));
const last=hist[hist.length-1];const pts=fs.map(p=>({...p,valid:new Date(new Date(d.issue_date).getTime()+p.horizon*864e5).toISOString().slice(0,10)}));
const poly=[x(last.date)+','+y(last.dhw),...pts.map(p=>x(p.valid)+','+y(p.upper)),...pts.slice().reverse().map(p=>x(p.valid)+','+y(p.lower))].join(' ');
svg.append(svgEl('polygon',{points:poly,fill:'#b9e48d',opacity:.13}));
svg.append(svgEl('polyline',{points:[x(last.date)+','+y(last.dhw),...pts.map(p=>x(p.valid)+','+y(p.mean))].join(' '),fill:'none',stroke:'#c0e799','stroke-width':2.5,'stroke-dasharray':'6 4'}));
pts.forEach(p=>{svg.append(svgEl('circle',{cx:x(p.valid),cy:y(p.mean),r:4,fill:'#c0e799'}));svg.append(svgEl('text',{x:x(p.valid),y:260,fill:'#b5d89a','font-size':10,'text-anchor':'middle'},'+'+p.horizon+'d'));});
[hist[0],hist[Math.floor(hist.length/2)],last].forEach(p=>svg.append(svgEl('text',{x:x(p.date),y:278,fill:'#8ca9ae','font-size':10,'text-anchor':'middle'},p.date.slice(5))));
svg.append(svgEl('text',{x:50,y:15,fill:'#8ca9ae','font-size':10},'DHW / °C-weeks'));
}
function map(d){const c=$('pixel-map');c.replaceChildren();const s=svgEl('svg',{viewBox:'0 0 190 170',role:'img','aria-label':t('示范像素经纬度示意图')});
for(let i=20;i<190;i+=30)s.append(svgEl('line',{x1:i,x2:i,y1:15,y2:155,stroke:'#28454c'}));
for(let i=20;i<170;i+=30)s.append(svgEl('line',{x1:10,x2:180,y1:i,y2:i,stroke:'#28454c'}));
const xs=sites.map(v=>v.longitude),ys=sites.map(v=>v.latitude),xmin=Math.min(...xs)-.05,xmax=Math.max(...xs)+.05,ymin=Math.min(...ys)-.05,ymax=Math.max(...ys)+.05;
sites.forEach((v,i)=>{const x=25+(v.longitude-xmin)/(xmax-xmin)*140,y=140-(v.latitude-ymin)/(ymax-ymin)*110;const active=v.site_id===d.site_id;s.append(svgEl('rect',{x:x-6,y:y-6,width:12,height:12,rx:2,fill:active?'#b9e48d':'#4c8c8b'}));s.append(svgEl('text',{x:x+10,y:y+3,'font-size':9,fill:'#a9c7c2'},'P'+(i+1)));});
s.append(svgEl('text',{x:160,y:18,fill:'#8ca9ae','font-size':9},'N ↑'));c.append(s);}
function action(d){
  const f=d.forecasts.find(v=>v.horizon===14)||d.forecasts[0],dhw=d.current.dhw;
  let title='维持常规观察',reason='未来热压力预测仍需结合官方信息和现场观察。',steps=['核验数据日期与官方 NOAA 产品。','按既定方案记录水温和珊瑚状态。','保持对未来更新和异常现场报告的关注。'];
  if(dhw>=4||f.upper>=4){
    title='优先准备现场复核';reason='当前指标或预测区间触及 4 °C-weeks 参考阈值；这提示复核需求，并不证明已发生白化。';
    steps=['由巡护负责人核对区间、阈值与数据延迟。','在符合海况和安全规程时安排定点观察。','记录深度、抽样方法与白化比例，避免扩大解释。'];
  }
  if(d.diagnostics&&d.diagnostics.overall.review_required){
    title='模型证据需要复核';reason='模型分歧、参考范围或阈值包络触发复核；请结合官方数据与现场证据判断。';
    steps=['比较AI与物理基线，检查误差和参考范围。','比较包络未经校准，不能解释为覆盖概率。','由负责人核验信息后决定是否安排观察。'];
  }
  if(d.stale_input){
    title='先更新数据，再做判断';reason='数据距今 {{days}} 天，本页仅供历史回放。请更新并经人工复核后安排巡护。';
    steps=['先检查 NOAA 官方最新产品及其观测日期。','更新数据后重新生成简报，并由负责人复核。','保留本页用于历史分析，不将其当作当期巡护建议。'];
  }
  $('action-title').textContent=t(title);$('action-reason').textContent=t(reason,{days:d.age_days});
  $('action-steps').replaceChildren(...steps.map(text=>{const li=document.createElement('li');li.textContent=t(text);return li;}));
}
function renderCurrent(d){
  $('sst').textContent=num(d.current.sst);$('dhw').textContent=num(d.current.dhw);
  [7,14].forEach(h=>{const f=d.forecasts.find(v=>v.horizon===h);if(f){$('pred'+h).textContent=num(f.mean);$('range'+h).textContent=t('90% 校准区间 {{lower}}–{{upper}}',{lower:num(f.lower),upper:num(f.upper)});}});
  if(!loading)$('status').textContent=t('观测基准日 {{date}}',{date:d.issue_date});
  const freshness=d.stale_input?t('数据已延迟 {{days}} 天，须更新后复核',{days:d.age_days}):t('仍需核对官方最新数据');
  $('freshness').textContent=t('数据截至 {{date}} · 模型输出为研究性预测 · {{freshness}}',{date:d.issue_date,freshness});
  $('coords').textContent=d.coordinates.latitude.toFixed(3)+'° N / '+d.coordinates.longitude.toFixed(3)+'° E';
  chart(d);map(d);action(d);renderDiagnostics(d);renderSpatial(d);
}
function showError(message){
  $('error').textContent=t('无法读取数据：{{detail}}',{detail:t(message)});$('error').hidden=false;
  $('status').textContent=t('无法生成预测');
}
async function load(latest=false){
  const id=++requestId;loading=true;lastError=null;$('error').hidden=true;
  $('status').textContent=t('计算中…');$('refresh').disabled=true;
  try{
    const asof=latest?'':$('asof').value,site=$('site').value;
    const d=await get('/api/forecast?site_id='+encodeURIComponent(site)+(asof?'&as_of='+asof:''));
    if(id!==requestId)return;
    current=d;loading=false;$('asof').value=d.issue_date;$('asof').min='2022-01-01';$('asof').max=d.latest_available_date;
    $('content').hidden=false;renderCurrent(d);
  }catch(e){
    if(id!==requestId)return;
    lastError=e.message;current=null;$('content').hidden=true;showError(lastError);
  }finally{if(id===requestId){loading=false;$('refresh').disabled=false;}}
}
function renderEvaluation(e){
  $('evaluation-json').textContent=JSON.stringify(e,null,2);
  const box=$('evaluation-summary');box.replaceChildren();const table=document.createElement('table');
  const rows=[['预测期','采用方法','测试 MAE','物理基线 MAE','区间覆盖'].map(k=>t(k))];
  const methodNames={dhw_persistence:'DHW 持续',physical_persistence:'持续 HotSpot 物理外推',seasonal_climatology:'季节气候态',hist_gradient_boosting_residual:'梯度提升残差模型',random_forest_residual:'随机森林残差模型'};
  for(const h of ['7','14']){
    const r=e.horizons[h],m=r.partitions.test;
    rows.push([t('{{days}} 天',{days:h}),t(methodNames[r.selected_model]||r.selected_model),num(m.selected.mae),num(m.physical_persistence.mae),(m.selected.interval_coverage*100).toFixed(1)+'%']);
  }
  rows.forEach((row,i)=>{const tr=document.createElement('tr');row.forEach(v=>{const td=document.createElement(i?'td':'th');td.textContent=v;tr.append(td);});table.append(tr);});box.append(table);
  const note=document.createElement('p');note.className='caption';
  note.textContent=t('MAE单位 °C-weeks；测试期2022–2025。90%为校准目标，表中为实际覆盖率。结果是历史卫星指标预测，非生态成效。');box.append(note);
  const limits=document.createElement('p');limits.className='caption';
  const a=e.horizons['14'].partitions.test,g=a.selected_gain_vs_physics,o7=e.horizons['7'].partitions.test.onsets,o14=a.onsets;
  limits.textContent=t('关键局限：7天选用物理基线。14天AI的MAE改善95%描述性区间为 {{lo}} 至 {{hi}}，跨零。首次达到DHW≥4的固定提前量命中为7天 {{h7}}/{{n7}}、14天 {{h14}}/{{n14}}；这些是相关像素样本，不能证明提前预警有效。',{lo:g.ci95_lower.toFixed(4),hi:g.ci95_upper.toFixed(4),h7:o7.exact_lead_hits,n7:o7.n,h14:o14.exact_lead_hits,n14:o14.n});box.append(limits);

}
async function evidence(){
  try{lastEvaluation=await get('/api/evaluation');lastEvaluationError=null;renderEvaluation(lastEvaluation);}
  catch(e){lastEvaluationError=e.message;$('evaluation-summary').textContent=t('无法读取数据：{{detail}}',{detail:t(lastEvaluationError)});}
}
window.ReefI18n.onchange=()=>{
  if(current)renderCurrent(current);
  if(lastEvaluation)renderEvaluation(lastEvaluation);
  if(catalogData)renderCatalog(catalogData);
  if(lastEvaluationError)$('evaluation-summary').textContent=t('无法读取数据：{{detail}}',{detail:t(lastEvaluationError)});
  if(lastError)showError(lastError);
  if(loading)$('status').textContent=t('计算中…');
};
$('refresh').onclick=()=>load();$('latest').onclick=()=>load(true);$('site').onchange=()=>load(true);
$('export').onclick=()=>{if(current)window.location.href='/api/export?site_id='+encodeURIComponent(current.site_id)+'&as_of='+current.issue_date;};
(async()=>{
  try{
    sites=await get('/api/sites');if(!sites.length)throw new Error('暂无可用固定像素数据');
    sites.forEach((s,i)=>{const o=document.createElement('option');o.value=s.site_id;o.textContent='P'+(i+1)+' · '+s.site_id;$('site').append(o);});
    await Promise.allSettled([loadSpatial(),loadCatalog()]);
    await load(true);
  }catch(e){lastError=e.message;showError(lastError);}
})();

function simpleTable(headers,rows){const table=document.createElement('table');[headers,...rows].forEach((row,i)=>{const tr=document.createElement('tr');row.forEach(value=>{const td=document.createElement(i?'td':'th');td.textContent=value;tr.append(td);});table.append(tr);});return table;}
const reasonNames={stale_input:'输入数据已过期',outside_training_range:'当前变量超出训练参考范围',training_reference_unavailable:'训练参考范围不可用',model_threshold_disagreement:'模型对热压力阈值判断不一致',comparison_envelope_spans_threshold:'比较包络跨过热压力阈值'};
function renderDiagnostics(d){const box=$('diagnostics-summary');box.replaceChildren();if(!d.diagnostics)return;
 const rows=d.diagnostics.per_horizon.map(v=>[t('{{days}} 天',{days:v.horizon}),num(v.selected_point),num(v.ai_point),num(v.physical_point),num(v.comparison_envelope.lower)+'–'+num(v.comparison_envelope.upper)]);
 box.append(simpleTable(['预测期','采用预测','AI候选','物理基线','未经校准的比较包络'].map(k=>t(k)),rows));
 const note=document.createElement('p');note.className='caption';note.textContent=t('比较包络包含历史校准区间及模型分歧，没有覆盖率保证，也不是新的90%区间。未触发复核不代表安全。');box.append(note);
 const reasons=document.createElement('p');reasons.className='review-reasons';const codes=d.diagnostics.overall.reasons;
 reasons.textContent=codes.length?codes.map(k=>t(reasonNames[k]||k)).join(' · '):t('请继续核验官方数据与现场情况');box.append(reasons);
}
async function loadSpatial(){try{[spatialData,habitatData]=await Promise.all([get('/api/spatial-context'),get('/api/habitat')]);if(current)renderSpatial(current);}catch(e){$('habitat-summary').textContent=t('空间数据暂不可用；不推断礁区是否存在。');}}
function renderSpatial(d){if(!spatialData||!habitatData)return;const site=spatialData.sites.find(v=>v.site_id===d.site_id);if(!site)return;
 const svg=$('habitat-map');svg.replaceChildren();const bounds=spatialData.bbox,[west,south,east,north]=bounds,cos=Math.cos((south+north)/2*Math.PI/180),scale=Math.min(660/((east-west)*cos),170/(north-south));
 const x=lon=>360+(lon-(east+west)/2)*cos*scale,y=lat=>125-(lat-(north+south)/2)*scale;
 const colors={'Coral/Algae':'#ef9d83','Seagrass':'#92c28a','Sand':'#d7cb91','Rubble':'#aeb295','Rock':'#88989d','Microalgal Mats':'#9dbb79'};
 for(const f of habitatData.features){if(!String(f.properties.layer_id).includes('benthic'))continue;const g=f.geometry;const polygons=g.type==='Polygon'?[g.coordinates]:g.type==='MultiPolygon'?g.coordinates:[];
  const path=polygons.map(poly=>poly.map(ring=>ring.map((p,i)=>(i?'L':'M')+x(p[0]).toFixed(2)+','+y(p[1]).toFixed(2)).join(' ')+'Z').join(' ')).join(' ');if(path)svg.append(svgEl('path',{d:path,fill:colors[f.properties.class_name]||'#8caeb5',opacity:.82,'fill-rule':'evenodd'}));}
 sites.forEach((option,i)=>{const v=spatialData.sites.find(z=>z.site_id===option.site_id);if(!v)return;const b=v.pixel_bbox,active=v.site_id===d.site_id;svg.append(svgEl('rect',{x:x(b[0]),y:y(b[3]),width:x(b[2])-x(b[0]),height:y(b[1])-y(b[3]),fill:'none',stroke:active?'#c6e99f':'#688b95','stroke-width':active?2.5:1}));svg.append(svgEl('text',{x:x(v.longitude),y:y(b[1])+17,fill:active?'#d3edac':'#8eafb2','font-size':11,'text-anchor':'middle'},'P'+(i+1)));});
 svg.append(svgEl('text',{x:18,y:22,fill:'#abc8c0','font-size':11},t('真实生境分类 / 北 ↑')));svg.append(svgEl('text',{x:18,y:238,fill:'#8eafb2','font-size':10},west.toFixed(3)+'°E — '+east.toFixed(3)+'°E / '+south.toFixed(3)+'°N — '+north.toFixed(3)+'°N'));
 const box=$('habitat-summary');box.replaceChildren();const b=site.layers.benthic;const h=document.createElement('h3');h.textContent=t('已制图底栖生境与当前像素');box.append(h);
 const summary=document.createElement('p');summary.textContent=t('像素面积 {{pixel}} km²；已制图 {{mapped}} km²（{{fraction}}%）。',{pixel:num(site.pixel_area_km2),mapped:Number(b.mapped_area_km2).toFixed(4),fraction:num(100*b.mapped_fraction_of_pixel)});box.append(summary);
 if(b.classes.length)box.append(simpleTable([t('分类'),t('面积 km²')],b.classes.map(v=>[v.class_name,Number(v.area_km2).toFixed(4)])));
 const note=document.createElement('p');note.className='caption';note.textContent=t('未制图部分状态未知，不能当作无礁区。静态生境仅作空间背景，不加入历史预测特征。');box.append(note);
}
async function loadCatalog(){try{catalogData=await get('/api/data-catalog');renderCatalog(catalogData);}catch(e){$('catalog-summary').textContent=t('数据目录暂不可用');}}
function renderCatalog(d){const box=$('catalog-summary');box.replaceChildren();const names={integrated_time_series:'已接入逐日时序',public_reports_context_only:'报告证据，非逐日标签',downloaded_spatial_context:'已接入局部空间数据',spatial_context_pending:'空间数据待获取'};
 for(const ds of d.datasets){const item=document.createElement('div');item.className='catalog-item';const a=document.createElement('a');a.href=ds.url;a.target='_blank';a.rel='noopener';a.textContent=ds.name;item.append(a,document.createTextNode(' · '+t(names[ds.state]||ds.state)));box.append(item);}
 const note=document.createElement('p');note.className='caption';note.textContent=t('资源帖是数据源目录，没有统一评分脚本。生境制图精度、热压力预测误差与现场白化验证属于不同任务。');box.append(note);
}
