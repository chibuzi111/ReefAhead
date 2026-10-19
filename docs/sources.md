# 原始资料与数据来源索引

核验日期：2026-10-16。所有运行时数据请求的完整 URL、下载 UTC 时间、SHA-256、字节数、空间支持与错误状态保存在 data/manifest.json；原始响应及逐文件 .meta.json 放在同目录 raw/。本文件说明证据用途，不能替代运行清单。

| ID | 原始来源 | 用途与限制 |
|---|---|---|
| S01 | [AI4Climate 官方主页](https://ai4climate.world/en) | 六个推荐方向与评审主题；报名清单以提交前官网与表单再次核验为准。 |
| S02 | [NOAA CRW v3.1 产品](https://coralreefwatch.noaa.gov/product/5km/index.php) | 日尺度约 5 km 海表热压力数据官方入口。 |
| S03 | [NOAA CRW 方法](https://coralreefwatch.noaa.gov/product/5km/methodology.php) | SST、HotSpot、84 天 DHW 和阈值定义；生态风险不能等同观测到白化。 |
| S04 | [NOAA ERDDAP NOAA_DHW 元数据](https://coastwatch.pfeg.noaa.gov/erddap/info/NOAA_DHW/index.html) | 变量、维度、单位和许可说明；保留 1985–2002 OSTIA 上游限制文字。 |
| S05 | [NOAA ERDDAP 数据入口](https://coastwatch.pfeg.noaa.gov/erddap/griddap/NOAA_DHW.html) | 脚本以 CSV hyperslab 请求固定网格；不下载全球数据。 |
| S06 | [Sabah 区域日序列 TXT](https://coralreefwatch.noaa.gov/product/vs/data/sabah.txt) | 1985 年起的区域背景数据；非 Semporna 单点数据。 |
| S07 | [NOAA 区域站说明](https://coralreefwatch.noaa.gov/product/vs/description.php) | 区域 HotSpot 90 百分位、移动像素与 7 日最大预警定义。 |
| S08 | [NOAA CRW 引用规范](https://coralreefwatch.noaa.gov/satellite/docs/recommendations_crw_citation.php) | 数据归属与正式引用；项目不能声称 NOAA 认可或背书。 |
| S09 | [Reef Check Malaysia：Sabah 2024 年 4–6 月记录](https://reefcheck.org.my/sabah-updates-april-june-2024/) | 仙本那社区监测与巡护的原始证据，亦说明地方响应差异；不是已建立合作关系。 |
| S10 | [Reef Check Malaysia. 2025. Status of Coral Reefs in Malaysia, 2024](https://reefcheck.org.my/wp-content/uploads/2025/07/2024AnnualSurveyReport.pdf) | 全国调查报告。报告页 1 允许注明来源的教育/非营利复制；本项目只引用必要事实，未将报告当训练集。 |
| S11 | [NASA POWER 日 API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) | 茶园等方向可获取气象；空间分辨率不等于逐园微气候。 |
| S12 | [NASA COOLR](https://gpm.nasa.gov/applications/landslides/coolr) | 山地灾害方向的公开滑坡事件来源，须审核采样偏差和时间精度。 |
| S13 | [NOAA IBTrACS](https://www.ncei.noaa.gov/products/international-best-track-archive) | 台风历史路径与强度，不等于城市内涝真值或实时预报。 |
| S14 | [Sen1Floods11 原作者代码和数据说明](https://github.com/cloudtostreet/Sen1Floods11) | 多事件水体/洪水遥感分割，不自动提供中国街道水深标签。 |
| S15 | [NASA MODIS VI v6.1 用户指南](https://modis-land.gsfc.nasa.gov/pdf/MOD13_User_Guide_V61.pdf) | 荒漠化植被监测候选资料；NDVI 变化不是干预因果效果。 |
| S16 | [CEGIS 孟加拉环境与地理信息服务](https://www.cegisbd.com/) | 盐度、农业、水管理的机构数据与模型背景；未假设其全部资料可匿名直接下载。 |

## NOAA 固定像素查询格式

请求由 scripts/fetch_data.py 生成，使用真实变量 CRW_SST、CRW_HOTSPOT、CRW_DHW、CRW_SSTANOMALY，日期限定在既有观测范围内。例如实测可达的短请求：

https://coastwatch.pfeg.noaa.gov/erddap/griddap/NOAA_DHW.csv?CRW_SST[(2024-01-01T12:00:00Z):1:(2024-01-03T12:00:00Z)][(4.275)][(118.625)],CRW_HOTSPOT[(2024-01-01T12:00:00Z):1:(2024-01-03T12:00:00Z)][(4.275)][(118.625)],CRW_DHW[(2024-01-01T12:00:00Z):1:(2024-01-03T12:00:00Z)][(4.275)][(118.625)]

2024-01-01 该网格真实响应示例：SST 29.01°C，HotSpot -0.21°C，DHW 2.67°C-weeks。负 HotSpot 是合法原始值，不应当作缺失或擅自改成正值。

## 数据声明必须保持的区分

公开原始卫星/再分析产品、研究派生标签、模型预测、模拟用户场景、未来验证计划分别标识。禁止用模拟图像训练后宣称真实生态识别有效，禁止把阈值计算或生成文本当成预测模型的实测性能，禁止省略缺测、失败请求和许可说明。

## 补充直接地方证据与实践依据

- S17：[Szereday 等（2025）2024 年马来西亚白化影响报告](https://reefcheck.org.my/wp-content/uploads/2025/07/2024CoralBleachingImpactReportMalaysia.pdf)，DOI: 10.5281/zenodo.15290515。第 13 页表 1、第 16 页 Eastern Sabah 是 Mabul/Larapan 的具体观测，作为问题证据，不拼接成训练标签。
- S18：[Malaysia Bleaching Response Plan 2026–2030](https://reefcheck.org.my/wp-content/uploads/2026/04/20260420-Malaysia-Bleaching-Response-Plan-2026-2030.pdf)。用作工作流与沟通参考。岛屿方案需当地相关人员参与，本原型没有替代主管机构决策的权限。

## 数据分发与证据归档

实际下载时 NOAA CoastWatch 请求重定向至 PacIOOS ERDDAP 的 dhw_5km 数据集。运行清单同时保留请求 URL 和最终响应 URL。致谢 NOAA Coral Reef Watch 原始产品以及 PacIOOS 再分发服务；不暗示任一机构赞助或认可本项目。

三份证据 PDF 已直接保存在 data/raw/evidence/，其独立的 evidence_manifest.json 记录文件 SHA-256、URL、检索时间与许可说明。第三方 PDF 不并入项目代码许可。

## 第二官方分发镜像与同版本合并

PacIOOS 请求阶段出现连接超时后，补缺数据改从 NOAA OceanWatch PIFSC ERDDAP 获取：CRW_sst_v3_1（analysed_sst）、CRW_hs_v1_0（hotspot）、CRW_dhw_v1_0（degree_heating_week）、CRW_sst_anom_v1_0（sea_surface_temperature_anomaly）。四份元数据的 product_version 均为 3.1；部分 dataset ID 中的 v1_0 不能误认为产品版本1.0。每份变量/季度响应单独保存，通过 time、latitude、longitude 严格匹配连接。先裁剪至请求日期，再检验四像素的完整日历；镜像缺日只用同产品 PacIOOS 的真实记录补齐，不插值。已有完整年度 PacIOOS 文件按哈希复用。已发现的跨镜像冲突按下述独立来源核验处理，不能笼统声称两个分发镜像的所有记录完全相同。

- [PIFSC SST 元数据](https://oceanwatch.pifsc.noaa.gov/erddap/info/CRW_sst_v3_1/index.html)
- [PIFSC HotSpot 元数据](https://oceanwatch.pifsc.noaa.gov/erddap/info/CRW_hs_v1_0/index.html)
- [PIFSC DHW 元数据](https://oceanwatch.pifsc.noaa.gov/erddap/info/CRW_dhw_v1_0/index.html)
- [PIFSC SSTA 元数据](https://oceanwatch.pifsc.noaa.gov/erddap/info/CRW_sst_anom_v1_0/index.html)

年度合并文件明确标记 derived:quarterly-concatenation；经语义修复的2019年度标记 derived:audited-multi-source-join。source_requests 保存每个实际下载 URL、时间、许可和哈希，不能把合并文件冒充单次网络响应。最终 check_data.py 递归校验源文件与派生文件。

跨源重叠抽查：2022Q1主像素90天与2004Q1主像素91天，四变量最大绝对差均不超过1.11e-16（浮点舍入），见 raw/probes/crosssource_validation.json 和 pifsc_pacioos_overlap_2004q1.json。这是两个时期的单像素抽查，不是全部记录的双源校验。


## 最终数据冻结与镜像异常核验（2026-10-16）

正式固定像素数据位于 data/processed/daily.csv，包含2003-01-01至2026-10-12的8,686个日历日、4个固定像素，共34,744行；每行SST、HotSpot、DHW、SSTA均为真实公开产品值。SHA-256为 b795ba20b11420ed42d29c8525af1ce63c2c4cd606d3a80074030998b42c1062。该冻结版本未改变训练、验证、校准或最终测试时间分段。

- **日期边界与缺日：** PIFSC部分时间轴缺日，ERDDAP最近时刻选择还会返回请求结束日期之外的次年1月1日。脚本排除64条越界原始响应记录；用13个PacIOOS短窗口请求补齐168个缺失变量值，136个可交叠数值同时比对，最大绝对差2.22e-16。越界响应及其原始哈希仍保留，未伪造日期或插值。
- **2019年4月的镜像语义冲突：** SST−HotSpot应与固定像素的MMM气候基准一致。审计发现PIFSC的2019-04-02至04-16期间HotSpot/SSTA共118个值与PacIOOS不同，SST和DHW相同。修复采用PacIOOS实际响应中的对应值，原PIFSC响应、逐值差异、修复前2019年度文件全部留存。没有以公式生成替代观测，也没有将问题隐藏为缺失值。
- **生产方第三源佐证：** 直接下载NOAA STAR的2019-04-02原始HS、SSTA、DHW NetCDF，对4像素×3变量共12个值与PacIOOS比对，完全一致。该检查覆盖一个代表日，并非对15天或完整23.8年记录全部做第三源下载。原始文件明确使用scale_factor=0.01；不能由这一存储精度直接推出所有上游处理过程的误差保证。
- **最终语义验收：** 全时期4像素SST−HotSpot分别保持29.22、29.21、29.21、29.23°C（仅有浮点表示误差）；每像素8,603个完整84日窗口的公开HotSpot重建DHW与官方DHW最大绝对差不超过0.004286°C-weeks。该一致性是产品内部检查，不是独立生态真值验证。

第三源公开文件：

- [NOAA STAR HS原始文件](https://www.star.nesdis.noaa.gov/pub/socd/mecb/crw/data/5km/v3.1_op/nc/v1.0/daily/hs/2019/ct5km_hs_v3.1_20190402.nc)
- [NOAA STAR SSTA原始文件](https://www.star.nesdis.noaa.gov/pub/socd/mecb/crw/data/5km/v3.1_op/nc/v1.0/daily/ssta/2019/ct5km_ssta_v3.1_20190402.nc)
- [NOAA STAR DHW原始文件](https://www.star.nesdis.noaa.gov/pub/socd/mecb/crw/data/5km/v3.1_op/nc/v1.0/daily/dhw/2019/ct5km_dhw_v3.1_20190402.nc)

可复核证据：

| 证据 | 远程位置与内容 |
|---|---|
| 完整下载清单 | data/manifest.json：complete=true、failures=[]；24年度来源及嵌套请求 |
| 质量验收 | data/processed/data_quality.json：241个源/派生文件SHA校验；所有34,744行逐值、坐标、日历、MMM与原始来源核对 |
| 镜像缺日请求 | data/raw/noaa_crw_transect/gap_fill/：原始CSV与下载元数据 |
| 跨源冲突原始差异 | data/raw/probes/pifsc_pacioos_2019_mmm_audit.json：118个字段级差异 |
| 生产方原文件与提取 | data/raw/probes/ct5km_*_v3.1_20190402.nc及对应meta；noaa_producer_*_20190402_extraction.json |
| 可重复第三源验收 | ./scripts/verify_noaa_producer.py；报告位于 data/processed/noaa_producer_sample_verification.json |
| 修复前派生快照 | data/raw/noaa_crw_transect/archived/：保留旧文件，正式数据不使用这些快照 |

在项目虚拟环境运行 scripts/fetch_data.py --workers 2 可复用原始缓存并重现相同数据；运行 scripts/check_data.py 同时核验完整日历、逐值溯源、固定MMM和生产方样本。daily.partial.csv与daily.incomplete.csv仅是历史下载诊断文件，不进入正式训练、演示或提交包。


## 产品方法文献

Skirving et al. (2020). CoralTemp and the Coral Reef Watch Coral Bleaching Heat Stress Product Suite Version 3.1. Remote Sensing, 12, 3856. [DOI:10.3390/rs12233856](https://doi.org/10.3390/rs12233856)。该条为NOAA引用指南推荐的产品方法文献，不是本项目处理数据快照的DOI；下载日期、具体端点与SHA仍由数据manifest记录。指南原文归档于数据目录raw/metadata/noaa_crw_citation.html。
