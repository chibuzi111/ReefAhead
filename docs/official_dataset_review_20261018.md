# 公开数据目录、字段和评估协议核验（2026-10-18）

本报告针对用户指定的[参赛数据源汇总帖](https://deepseek.club/topic/5152)及其中珊瑚方向原始资料。所有取证和衍生核验文件位于 `data/research_20261018/`。本轮保留原模型、训练分区及冻结预测，已新增空间数据接入、字段目录、模型诊断、现场导入适配和界面代码；没有注册、发帖或联系数据提供方。

## 1. 先明确“官方要求”与“可用数据”

2026-10-18通过公开GET接口重新取得帖子全文。标题为“AI4Climate.world 全球青年气候解决方案挑战赛 参赛数据源汇总”，作者显示“辛酉”；API的 `isAnnouncement=false`、`attachments=null`。正文包含36个链接：15个通用入口、六方向共21个条目。它是资源导航，没有提供统一训练集、测试标签、评分脚本、排行榜或数据字典，也没有声明必须使用全部资源。不能把它写成“赛事官方benchmark”，更不能虚构官方 train/test split。原文的 Allen Coral Atlas URL 为 `allencorallatlas.com`，拼写多一个l；本次以原机构的 [allencoralatlas.org](https://allencoralatlas.org/) 核验。

赛事正式要求以[AI4Climate官网](https://ai4climate.world/)和[报名页](https://ai4climate.world/apply)为准：项目需说明真实气候问题、具体用户和AI任务，提供项目说明、≤3分钟演示视频、可运行Demo或代码库、数据与AI说明、验证计划。官网六维评分是解决方案评分，不是预测竞赛的固定误差函数。完整条款已有 `docs/competition_research.md` 与 `docs/official_requirements.json`；本报告不新增报名义务。

|层次|确证内容|在本项目中的作用|
|---|---|---|
|赛事要求|数据与AI说明、验证计划；气候价值、AI能力、可行性、市场持续性、传播采用、扩展伦理开放性等维度|必须交付可核验材料；不能用“有数据”替代验证|
|导航帖|推荐数据入口与具体产品链接|寻找资料，不构成授权、标准标签或评分协议|
|数据生产方文档|产品单位、空间/时间粒度、方法、标签和使用条件|必须遵循该产品自身语义|
|项目自行制定|7/14日DHW目标、时间隔离、基线、误差与区间评估|明确标记为ReefAhead评估协议，不称官方指定|

## 2. 珊瑚方向的四个条目实际对应三类证据

|帖子条目|原始结构与标签|可承担的任务|不能据此声称|
|---|---|---|---|
|NOAA Coral Reef Watch|每日全球0.05°网格；SST、SSTA、HotSpot、DHW等卫星分析产品|热压力时序建模、DHW预测与产品值回测|现场已白化、某个珊瑚群落死亡、生态恢复效果|
|NOAA_DHW ERDDAP|同一产品的机器读取入口；PacIOOS聚合镜像和NOAA PIFSC镜像字段名不同|可追溯下载、固定像素一致性核验|这是第二套独立观测或新增独立真值|
|Reef Check Malaysia|现场调查年度报告、年度地图；另有2024事件研究报告|场景证据、调查设计、经授权的外部生态验证候选|把年度覆盖率或年度桶复制成每日白化标签|
|Allen Coral Atlas|5m栖息地分类、礁区范围及另行生产的监测层|空间背景、礁区/海水像素对应核查|静态coral/algae标签等于活珊瑚率；空间覆盖等于预测已验证|

## 3. NOAA：可复现的主数据结构与严格标签语义

依据[NOAA v3.1方法页](https://coralreefwatch.noaa.gov/product/5km/methodology.php)、[产品页](https://coralreefwatch.noaa.gov/product/5km/index.php)及本次保存的四个PIFSC ERDDAP `info/*.json`。全产品标称0.05°，通常简称5km；它是规则经纬网格，不能说每格恒等于5km²。每日产品时间轴为12:00Z标记，产品日期不等同于历史可下载时刻。

|标准化字段|帖子所指PacIOOS聚合变量|NOAA PIFSC数据集 / 变量|单位/维度|
|---|---|---|---|
|date / observed_at|time|time|UTC；原始数值为Unix秒；日粒度|
|latitude|latitude|latitude|degrees_north|
|longitude|longitude|longitude|degrees_east；PIFSC为0.025–359.975，须统一经度约定|
|sst|CRW_SST|CRW_sst_v3_1 / analysed_sst|°C；time×latitude×longitude|
|ssta|CRW_SSTANOMALY|CRW_sst_anom_v1_0 / sea_surface_temperature_anomaly|°C；同上|
|hotspot|CRW_HOTSPOT|CRW_hs_v1_0 / hotspot|°C；同上|
|dhw|CRW_DHW|CRW_dhw_v1_0 / degree_heating_week|°C·week；同上|

四个metadata均为 `product_version=3.1`；数据集名中的 `v1_0` 不能当成不同科学产品版本。SST/SSTA/HotSpot起于1985-01-01，DHW该镜像起于1985-03-25；本次metadata末日均为2026-10-15。镜像后续会更新，因此必须记录每次下载截止日期。CSV第二行为单位行，不能当观测。ERDDAP输出已转换为物理值，不能再重复应用NetCDF缩放。`_FillValue=NaN`应视缺失，不能视0；海陆掩膜/不可用像素不生成预测。

[HotSpot元数据](https://oceanwatch.pifsc.noaa.gov/erddap/info/CRW_hs_v1_0/index.json)对应 `SST-MMM`，原始数据可为负值；仅地图显示正值并不意味着要把下载值全部裁成0。SSTA比较相应日的气候态，HotSpot比较最暖月气候态，二者不能互换。DHW在包含当前日的84天窗口中累加 `HS>=1°C` 的全部HS，再除7；不是累加 `HS-1`。本项目监督目标应继续采用原始官方DHW值，重建公式可用于基线和一致性诊断，不能悄悄替换标签。

目标定义建议固定为 `y_h(t,p)=DHW(t+h,p)`，h∈{7,14}；它是未来第h天值，不是未来窗口最大值。`DHW>=4` 是项目使用的热压力事件指标。NOAA正式Bleaching Alert Area还联合HotSpot，并有7日最大版本；不能仅用DHW把输出改称官方警报等级。当前官方方法已扩展Alert1–5，对应HS≥1时DHW的4/8/12/16/20分界。

来源许可：SST metadata保留1985–2002 OSTIA的研究用途、期限及再复制条款，同时列出后期GHRSST开放说明；其他CRW产品要求恰当署名和引用。保留原始许可文本和[NOAA引用指引](https://coralreefwatch.noaa.gov/satellite/docs/recommendations_crw_citation.php)，不把代码开源许可延伸到第三方数据。项目从2003年开始的选择不能被写成法律层面的全部商业授权证明。

**已做的跨镜像实证**：同一主像素4.275°N、118.625°E，2004Q1的91天和2022Q1的90天四变量逐日对齐；最大差为0或1.11×10^-16浮点误差。证据仍在 `data/raw/probes/`。这是两个季度单像素的兼容性证据，不是全历史全空间一致性的证明。

## 4. Reef Check：真实调查资料、字段与使用边界

[年度报告目录](https://reefcheck.org.my/annualsurveyreports/)目前提供2007–2025年度调查报告；本次保存[2025年度调查报告](https://reefcheck.org.my/wp-content/uploads/2026/01/2025-Annual-Survey-Report.pdf)，其书内第4–5页说明100m样带沿线设置4段20m重复。底质采用0.5m点截法；鱼类、无脊椎和干扰分别记录。活珊瑚覆盖是硬珊瑚HC与软珊瑚SC之和，与白化发生比例含义不同。报告附录列站名、岛名和度分坐标，转换时需保留原始坐标文本并做范围检查。

另保存[2024白化专项报告](https://reefcheck.org.my/wp-content/uploads/2025/07/2024CoralBleachingImpactReportMalaysia.pdf)。其表1记录地点、深度、DHW、死亡/白化比例、群体数量和分类单元数量，涉及24个调查站和不同现场采样方法。东沙巴包括Mabul和Larapan，但该事件研究不提供当前项目所需的逐日全量监督表；跨方法、深度、时间与群落组成差异需保留，不能从汇总表推造逐日数据或作因果归因。报告说明教育/非营利用途可在署名后再复制，商业再利用需书面许可。

### 4.1 当前公开互动地图的实际字段（私有研究核验）

2026-10-18读取[官方互动地图](https://reefcheck.org.my/interactive-map/)直接引用的GeoJSON，原始为328个Point。以下是原属性含义，不是本项目新定义的训练标签：

|字段|实际结构|注意事项|
|---|---|---|
|geometry.coordinates|[longitude,latitude]|按GeoJSON经纬顺序；源未单列CRS|
|title / siteId|站名/字符串站点ID|保留原名，不假定同名即同一站|
|locationName / locationId / geoRegion|岛/地区、地区ID、生态区|与站点层次区分|
|surveyData[]|按year组织；含substrate/fish/invertebrate/other|局部样本含2020–2026；没有实际调查日、深度或重复编号|
|surveyData[].substrate|hard_coral、soft_coral、recently_killed_coral、nutrient_indicator_algae、sponge、rock、rubble、sand、silt、substrate_other|字符串数值；对应底质百分比；缺值和0区别保留|
|fish / invertebrate|各指示类群计数/丰度字段|报告按不同调查体积/面积呈现；GeoJSON未声明单位，不自动跨字段统一单位|
|other|包括coral_damage_*、trash_*、bleaching_num_of_population、bleaching_num_of_colony、疾病与动物记录|白化字段虽存在，但GeoJSON没有分母、单位、调查日字典，不能自动解释成百分比或每日真值|
|live_coral_cover|顶层数值|静态最新快照；不要默认其年份等于trend首年|
|trend[]|year、date、live_coral_cover等六项年度构成|date为Jan1年度桶；同地区各站重复，页面明确称Location Trend Analysis，不是独立站点逐日序列|
|fields|每个指标的label、shortcode、type|只是标签字典，缺完整单位和采样协议|

按bbox `[118.5,4.0,119.2,4.7]` 筛选得到41站：Mabul6、Kapalai6、Sipadan11、Tun Sakaran Marine Park6、Mataking6、Larapan6。原属性完整保留在私有研究目录的 `semporna_survey_sites.geojson`；来源哈希、筛选范围、逐站像素关系和许可状态保存在 `semporna_survey_sites.metadata.json` 与 `metadata.json`。

**空间核验结论：41站中0站落在当前4个演示像素内。** 当前像素中心纬度4.275，经度118.625/118.725/118.825/118.925，每格边界为中心±0.025°。此处按左闭右开的网格边界检验；没有边界歧义样本。不能将原4像素重新命名为Mabul等真实调查站，也不能用最近邻关联冒称已经完成现场验证。真实落地需要明确目标站、匹配其实际所在的独立海水网格并重新获取数据；新像素验证应预先冻结协议，避免看测试结果后选点。

### 4.2 地图许可与报告许可不相同

本次原GeoJSON未提供开放数据许可证。[RCM网站使用条款](https://reefcheck.org.my/terms-of-service/)第2节对复制/利用网站服务要求书面许可，第12节列有爬取限制；这不是CC开放数据授权。报告的教育/非营利复制条件不能自动覆盖互动地图。已取得数据仅保留为本地于远程服务器的私有研究证据，不进入产品、模型训练、公开代码包或公开交付附件；不继续自动抓取地图。项目可引用官方地图/报告、说明局部站点数量和匹配差距。需要实际整合时，应先取得相应授权及数据字典。此许可记录不影响已授权的NOAA原型工作继续开展。

## 5. Allen Coral Atlas：作为空间背景，不冒充现场验证

[Earth Engine官方目录](https://developers.google.com/earth-engine/datasets/catalog/ACA_reef_habitat_v2_0)给出 `ACA/reef_habitat/v2_0` 的5m栅格波段：

|波段|编码/含义|项目用法|
|---|---|---|
|geomorphic|地貌区类别，0为未制图|记录礁坪/礁坡等背景；不推导现场白化率|
|benthic|0未制图，11砂、12碎屑、13岩石、14海草、15珊瑚/藻类、18微藻席|15是合并类，不能统计为“活珊瑚覆盖率”|
|reef_mask|0非礁、1礁区|可核查NOAA格内的静态礁区空间背景；非训练白化标签|

底层影像为2018–2020时段合成，目录可用时段标签与实际影像日期需区分。它不是2003–2026逐日地图。[Atlas方法](https://allencoralatlas.org/methods/)采用参考点和分类误差矩阵评估栖息地地图，报告总体准确率及类别用户/生产者准确率；这属于Atlas自己的产品制图验证，不是本项目DHW预测的评估协议。空间抽样还需防止邻近点相关性，不能照搬随机像素切分到时序预测。

Atlas另有白化监测产品：NOAA热压力告警触发处理，Sentinel-2双周亮度变化与持续性用于判断疑似白化，并受水深、云、浑浊和底质类别限制。因为启动条件本身依赖NOAA，不能称为完全独立的NOAA效果验证。若未来取得数据，最多先作为不同观测方式的辅助外部证据，仍需现场验证。

[资源与许可页](https://allencoralatlas.org/resources/)区分地图/测深/统计的CC BY4.0和Planet影像的非商业相同方式共享条件，并对整套全球地图再发布另作限制；其他图层还可能使用各自提供方条款。网页下载包与公开WFS属于不同获取方式；本次未注册账户，通过公开WFS实际下载局部两层共11,108个要素，已进行裁剪、等面积相交和显示简化并接入产品。当前准确说法为“已接入真实局部空间背景”，不能写“已完成Atlas现场验证”。完整几何、导出、来源和哈希位于atlas_20261018，细节见升级章节。

## 6. 建议的项目数据契约与评估协议（项目建议，非赛事强制）

### 6.1 三张表分离，杜绝跨尺度伪标签

1. 卫星日表：`pixel_id, observed_at_utc, product_date, latitude, longitude, sst_c, ssta_c, hotspot_c, dhw_c_weeks, source_dataset, product_version, fetched_at_utc, source_sha256, quality_flags`。主键为pixel_id+product_date；先核验重复、坐标精确性、逐日连续性和缺失，不做未来插值。
2. 礁区/站点背景表：`site_id, geometry, source, geometry_version, source_date, license_status, pixel_id, point_inside_pixel, distance_to_pixel_center`。明确实际包含关系和最近邻关系不同；没有授权/没有几何时不填造值。
3. 现场验证表：`survey_id, site_id, survey_datetime, depth_m, method, replicate_id, taxon, total_colonies, bleached_colonies, bleaching_definition, live_cover_pct, observer_qc, location_accuracy_m, release_permission`。这是将来需要的采集规范，并非声称RCM当前公开接口已经含这些字段。

### 6.2 时间、空间和标签隔离

继续冻结训练2003–2016、验证2017–2019、最终拟合2003–2019、校准2020–2021、测试2022–2025、2026回放；issue_date和target_date均不得跨分区边界。所有预处理、气候态、特征选择和超参数只使用相应训练/验证范围。2026回放不能当一次新的独立盲测。若优化过程中查看过2022–2025指标后再选方案，应将其明确降级为已查看的回顾验证，并新增前瞻性冻结验证；不能维持“从未接触的测试集”宣传。

近邻4像素高度相关，行数不等于独立样本量。新的空间推广结论需要在不同礁区/海域上保留整块留出，且不能按数据表现选择空间测试区。真实现场外部验证应按调查活动/站点/年份分组，先核对采样方法、深度、实际时间和定位误差；不把年度趋势扩展到365个日样本。

### 6.3 必须并列的基线、误差和实用性检查

- 点预测：与当前DHW持续、持续HotSpot物理启发基线、训练期季节气候态比较；列MAE、RMSE、偏差、年度/像素/高热压力分层。残差回归仅为物理基线残差模型，不叫严格热守恒模型。
- 热压力事件：明确阈值和目标日，报告TP/FP/FN/TN、precision/recall、事件数；阈值首次穿越命中与每天命中分开，避免长事件的日数放大效果。若输出概率，要说明其估计方式，并报告Brier与可靠性，不能将经验残差分布叫已验证风险概率。
- 不确定性：校准只用2020–2021；展示测试覆盖率、区间宽度及极端年份表现。时序相关和分布变化下不承诺名义90%未来覆盖。用同一日期区块汇总多像素误差，保留序列相关性。
- 实际可用性：把产品观测日、可用时刻、下载日、模型发布时刻分开；当前归档只证明日期无未来泄漏，不证明当天上线已可得到数据。增加真实更新前后的影子运行日志；过期/缺失输入返回明确不可用，不能以模型数值掩盖资料落后。
- 原型效用：提前准备调查的时间、误报带来的额外复核次数、用户任务完成率和安全边界是90天试点指标；不以离线DHW误差直接换算“减少白化面积”或“挽救珊瑚数量”。

## 7. 其他方向与通用入口的核验范围

本次完整保留帖子36项链接，附后。门户型入口不等于可下载的特定训练表；气象/行政/全球遥感门户的产品、字段和许可必须选定具体产品后再核验。没有为珊瑚项目下载与目标无关的大型数据。

具体元数据补查：CLCD原链接确认为中国30m年度土地覆盖的版本1.0.2，含1985及1990–2022的栅格文件/分类说明，数据页面提示已有更新版本；API许可为CC BY4.0，应固定版本并保留分类字典。茶园和放牧强度的Figshare API请求返回403；尼泊尔两个DOI重定向到ICIMOD metadataId36002/36003但连接超时；MODIS原链接重定向到NASA Earthdata对应MOD13A3-061/MOD17A3HGF-061目录后本次远程403。失败已保留，不能据此宣称数据不存在或字段已全面验证；这些不影响当前NOAA珊瑚方向的可复现数据链。

### 其他五方向的代表产品与任务评估建议

以下仅说明合理的研究设计；均不是赛事指定的任务、标准字段或官方评分。具体产品未成功读取的部分明确标出，门户本身没有可统一概括的schema。

|方向|已辨认的代表产品/入口|字段或标签的核验程度|适合的评价建议|
|---|---|---|---|
|茶园|帖子列全国10m茶园分布数据集，Figshare 25047308|本轮API403，仅确认目录名称和DOI；不能声称已有其栅格编码/精度标签|若做茶园制图，按独立地块/区域留出并报IoU、precision/recall；若做霜冻预警，还需真实霜冻/受损日期，不能用茶园分布替代受损标签|
|尼泊尔山地|ICIMOD气候情景降水36002、气温36003|DOI确实重定向相应metadataId，但本轮连接超时；情景模式、变量单位和时段未核实|情景产品可支持长期适应分析，不能当未来7日真实天气。洪水/滑坡预警需历史事件清单，按流域和时间隔离；报漏报、误报及提前量|
|孟加拉农业|FFWC预报/预警及公开API、HDX|本帖未指定唯一数据产品或字段字典；本轮未抓取其动态观测|水位预测需站点/日期/水位基准，报MAE、洪水阈值事件识别与提前量；农业损失预测还需作物/田块/受损真值|
|台风内涝|CMA、NMC及浙江气象/水利门户|多个来源门户，不是统一训练表；未指定台风best-track版本、雨量或积水产品|按完整台风事件及地理区域留出；水深MAE/关键点召回/空间IoU视任务选用，不能将台风轨迹准确率等同内涝预报准确率|
|西北荒漠化|CLCD 30m土地覆盖；MOD13A3.061 NDVI、MOD17A3HGF.061 NPP入口|CLCD原始元数据与CC BY4.0已读；MODIS原入口重定向后403；土壤与放牧条目尚无本轮详细字段核验|土地覆盖分类标签不等于荒漠化程度。变化检测按年份/空间块留出并报变化类F1、面积偏差；趋势归因还需气候/管理信息，不用相关性冒称放牧导致退化|

## 8. 交付和缺口清单

- 已完成：Atlas局部两层实际导入与校验、模型分歧诊断和字段目录；当前帖子正文、全部链接清单、NOAA四变量机器元数据与方法、Atlas原始结构/许可文档、RCM年度/事件报告、公开地图字段私有核验、41站空间匹配结果、源文件哈希。
- 可立即用于项目：NOAA字段映射和质量契约、来源/时间状态展示、明确无官方benchmark、校准与分层评估规范、现场场景证据引用。
- 明确没有完成且不应声称完成：RCM数据再发布授权、精确逐日现场白化标签、已匹配当前四像素的真实调查站、独立空间泛化验证、前瞻性用户/生态效果试验。
- 建议下一步：冻结优化实验和评估记录；补取得授权且采样方法一致的实际调查数据；为目标礁点独立选择合适海水网格并做空间留出。当前Atlas已作为实际局部空间背景接入，当前现场材料仍只支持真实问题、结构核验与验证设计。

## 附录：帖子当前全部数据入口

以下由当前公开正文自动提取，原链接保留以便复查；存在失效或拼写问题不代表本项目采用该链接。

|分组|名称|原链接|
|---|---|---|
|通用入口|国家气象科学数据中心|[https://data.cma.cn](https://data.cma.cn)|
|通用入口|国家地球系统科学数据中心|[http://www.geodata.cn](http://www.geodata.cn)|
|通用入口|国家青藏高原科学数据中心|[https://data.tpdc.ac.cn](https://data.tpdc.ac.cn)|
|通用入口|资源环境科学数据中心|[https://www.resdc.cn](https://www.resdc.cn)|
|通用入口|地理空间数据云|[https://www.gscloud.cn](https://www.gscloud.cn)|
|通用入口|风云卫星遥感数据服务网|[https://satellite.nsmc.org.cn](https://satellite.nsmc.org.cn)|
|通用入口|国家冰川冻土沙漠科学数据中心|[http://www.ncdc.ac.cn](http://www.ncdc.ac.cn)|
|通用入口|浙江省数据开放平台|[https://data.zjzwfw.gov.cn](https://data.zjzwfw.gov.cn)|
|通用入口|NASA Earthdata|[https://earthdata.nasa.gov](https://earthdata.nasa.gov)|
|通用入口|USGS EarthExplorer|[https://earthexplorer.usgs.gov](https://earthexplorer.usgs.gov)|
|通用入口|Copernicus Data Space|[https://browser.dataspace.copernicus.eu](https://browser.dataspace.copernicus.eu)|
|通用入口|Google Earth Engine|[https://earthengine.google.com](https://earthengine.google.com)|
|通用入口|CHIRPS 全球降水数据|[https://data.chc.ucsb.edu/products/CHIRPS/v3.0/](https://data.chc.ucsb.edu/products/CHIRPS/v3.0/)|
|通用入口|FAOSTAT|[https://www.fao.org/faostat](https://www.fao.org/faostat)|
|通用入口|World Bank Open Data|[https://datacatalog.worldbank.org](https://datacatalog.worldbank.org)|
|【01 茶园】|全国首套10m茶园分布数据集|[https://doi.org/10.6084/m9.figshare.25047308](https://doi.org/10.6084/m9.figshare.25047308)|
|【02 尼泊尔山地】|ICIMOD 区域数据库|[https://rds.icimod.org](https://rds.icimod.org)|
|【02 尼泊尔山地】|尼泊尔气候情景·降水|[https://doi.org/10.26066/RDS.36002](https://doi.org/10.26066/RDS.36002)|
|【02 尼泊尔山地】|尼泊尔气候情景·气温|[https://doi.org/10.26066/RDS.36003](https://doi.org/10.26066/RDS.36003)|
|【03 孟加拉农业】|孟加拉洪水预报预警中心|[http://old.ffwc.gov.bd](http://old.ffwc.gov.bd)|
|【03 孟加拉农业】|FFWC 官方API|[https://api.ffwc.gov.bd/data_load/](https://api.ffwc.gov.bd/data_load/)|
|【03 孟加拉农业】|人道主义数据交换 HDX|[https://data.humdata.org](https://data.humdata.org)|
|【03 孟加拉农业】|孟加拉开放数据平台|[http://www.data.gov.bd](http://www.data.gov.bd)|
|【04 仙本那珊瑚礁】|NOAA Coral Reef Watch|[https://coralreefwatch.noaa.gov](https://coralreefwatch.noaa.gov)|
|【04 仙本那珊瑚礁】|NOAA 机器可读端点 ERDDAP|[https://coastwatch.pfeg.noaa.gov/erddap/griddap/NOAA_DHW.html](https://coastwatch.pfeg.noaa.gov/erddap/griddap/NOAA_DHW.html)|
|【04 仙本那珊瑚礁】|Reef Check Malaysia|[https://reefcheck.org.my](https://reefcheck.org.my)|
|【04 仙本那珊瑚礁】|Allen Coral Atlas|[https://allencorallatlas.com](https://allencorallatlas.com)|
|【05 浙江台风内涝】|中国气象数据网·台风产品|[https://data.cma.cn](https://data.cma.cn)|
|【05 浙江台风内涝】|中央气象台台风网|[http://typhoon.nmc.cn](http://typhoon.nmc.cn)|
|【05 浙江台风内涝】|浙江省气象局|[http://zj.cma.gov.cn](http://zj.cma.gov.cn)|
|【05 浙江台风内涝】|浙江省水利厅|[https://slt.zj.gov.cn](https://slt.zj.gov.cn)|
|【06 西北荒漠化】|中国土地覆被数据集 CLCD|[https://zenodo.org/records/8176941](https://zenodo.org/records/8176941)|
|【06 西北荒漠化】|MODIS NDVI|[https://lpdaac.usgs.gov/products/mod13a3v061/](https://lpdaac.usgs.gov/products/mod13a3v061/)|
|【06 西北荒漠化】|MODIS NPP|[https://lpdaac.usgs.gov/products/mod17a3hgfv061/](https://lpdaac.usgs.gov/products/mod17a3hgfv061/)|
|【06 西北荒漠化】|中国土壤信息网格|[http://soil.geodata.cn](http://soil.geodata.cn)|
|【06 西北荒漠化】|全球放牧强度数据集|[https://doi.org/10.6084/m9.figshare.26195684](https://doi.org/10.6084/m9.figshare.26195684)|

空间匹配数按公开站点坐标与0.05°网格边界严格计算，未建模站点定位误差；0个直接落格点不代表附近无调查、无珊瑚礁或不可能存在可验证的邻近场景。
