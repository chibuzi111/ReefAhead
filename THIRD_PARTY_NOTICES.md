# Third-party notices / 第三方来源与许可

`LICENSE` 中 MIT 仅覆盖原创项目代码，不重新许可第三方数据、字体或依赖。各 Python 依赖保留其分发包中的原有许可；锁定版本见 `requirements.lock.txt`。

## NOAA Coral Reef Watch

本包含 2003-01-01 至 2026-10-12、四个固定像素的 CRW v3.1 派生处理快照（SST、HotSpot、DHW、SSTA），非全球完整产品。生产方 NOAA Coral Reef Watch，分发来源 NOAA OceanWatch 和 PacIOOS；具体 URL、下载时间、原始/派生哈希和处理说明保留在 `data/manifest.json` 与 `docs/sources.md`。引用 Skirving et al. (2020), *CoralTemp and the Coral Reef Watch Coral Bleaching Heat Stress Product Suite Version 3.1*, Remote Sensing 12, 3856, https://doi.org/10.3390/rs12233856 。

NOAA 引用说明：https://coralreefwatch.noaa.gov/satellite/docs/recommendations_crw_citation.php 。本包不包含 1985–2002 上游 OSTIA 序列，不据此宣称所有历史数据或商业用途均无条件许可。保留原始服务元数据的许可/免责声明文字；不表示 NOAA、PacIOOS 对本项目背书。

## Allen Coral Atlas

Allen Coral Atlas maps, bathymetry and map statistics © 2018–2023 Allen Coral Atlas Partnership and Arizona State University. Map data: **CC BY 4.0**, https://creativecommons.org/licenses/by/4.0/ 。来源 https://allencoralatlas.org/resources/ ，使用条款 https://allencoralatlas.org/tou/ 。

仅分发仙本那局部 AOI 的生境几何派生导出及像素叠加统计，做了裁剪、等面积投影下的面积计算、按类别融合及仅供显示的简化；不包含 Planet 影像或全球数据。归属和处理细节亦见 `data/atlas_20261018/manifest.json` 及各 GeoJSON。原始细节几何未全部包含在便携版中；面积来自完整几何，不用显示简化几何重新估计。

## Noto Sans SC

`web/assets/NotoSansSC-Regular.ttf`：SIL Open Font License 1.1，完整许可见 `web/assets/OFL.txt`。字体不受项目 MIT 重新许可。

## Reef Check Malaysia 与第三方研究

仅在说明和界面中引用公开报告的必要事实与链接。没有将 RCM 原始地图、报告 PDF、调查点数据或受限制的现场资料纳入本包，也不把公开报告中的区域比例转换成逐日训练标签。未声称与任何机构已有合作或试点。
