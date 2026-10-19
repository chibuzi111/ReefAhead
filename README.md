# 礁先知 ReefAhead

**珊瑚海域热压力预测与巡护准备软件。** 将 NOAA Coral Reef Watch 历史海温序列、本地机器学习推理与 Allen Coral Atlas 生境地图放在同一个中英双语界面中，支持查询、模型比较、人工复核提示和 CSV 简报导出。

这是可运行研究原型。预测对象是四个固定卫星像素在目标日期的 DHW，不是实测珊瑚白化或官方预警。界面与空间证据版本 2.0.0，冻结模型版本 1.0.0。

## 快速运行

需要 Python **3.14**。在项目根目录执行：

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
bash scripts/serve.sh
```

浏览器打开 **http://127.0.0.1:8765**。默认使用项目内 `data/`；包内已包含训练好的模型和数据快照，查看演示不需要重训练、GPU、付费模型 API 或外部账号。首次安装依赖需要互联网；软件核心推理使用本地文件。地图底图、外部来源链接等联网内容可能受网络状态影响。

Windows 可在 PowerShell 中执行：

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
$env:CLIMATE_DATA_DIR = "$PWD/data"
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8765
```

如需使用其他数据目录，设置 `CLIMATE_DATA_DIR`；`REEFAHEAD_HOST`、`REEFAHEAD_PORT` 可调整启动监听地址和端口。公网部署应自行配置 HTTPS、合理资源限制及常驻进程。Dockerfile 是备用配方，当前公开候选尚未完成 Docker 容器运行验证。

## 建议演示顺序

1. 打开首页，选择 P2（offshore 2）或其他固定像素，查看输入日期和当前热压力。
2. 选择历史日期 **2024-05-15**，查看目标日期的 7 天 / 14 天预测、参考区间与物理基线比较。
3. 查看 Atlas 生境叠加、像素内已制图面积及类别说明；未制图不代表没有珊瑚礁。
4. 查看证据页与真实评估表；切换英语或窄屏界面，导出 CSV 简报。

## AI 在运行中承担什么任务

14 天预测使用随机森林学习物理外推残差，以历史 SST、HotSpot、DHW、海温异常、季节性和过去窗口特征修正物理结果；模型在 CPU 上本地执行 `predict()`。7 天正式输出采用验证阶段优选的物理基线，同时保留 AI 候选供比较。地图、导出与复核提示由软件和明确规则实现。

## 数据、评估与结果边界

- **34,744 行真实卫星日记录**：2003-01-01 至 2026-10-12，四个 0.05° 固定像素。时间快照冻结，不自动变成实时数据。
- 训练 2003–2016、选择 2017–2019、重拟合至 2019、校准 2020–2021、测试 2022–2025、2026 离线回放；目标日期必须留在对应分区。
- 14 天测试平均绝对误差为 0.1422 °C-weeks，物理基线为 0.1620；相对平均误差降低约 12.2%，但配对区块 bootstrap 差异区间跨零，不能据此断言稳定或显著优于基线。2026 回放未优于物理基线。
- DHW 是卫星热压力指标，不是白化率。近邻像素与日期相关，不构成同等数量的独立事件；尚无同地点生态真值和现场试点验证。
- Atlas 用于静态空间背景，不把 NOAA 热压力下推到 5 米；Coral/Algae 合并类别不等于活珊瑚覆盖率。

完整细节见 [模型卡](docs/model_card.md)、[评估](docs/evaluation.md)、[结果解释](docs/evaluation_analysis.md)、[数据来源](docs/sources.md)、[数据对照升级](docs/official_dataset_review_20261018.md)及 [第三方许可](THIRD_PARTY_NOTICES.md)。

## 验证与重训练

```bash
.venv/bin/python -m pytest tests -q
.venv/bin/python scripts/verify_atlas_context.py --data-root data
```

包内快照足以推理及重训练：

```bash
OMP_NUM_THREADS=4 .venv/bin/python -m src.train --data data/processed/daily.csv
```

重训练会写入新的模型和评估文件；需要比较冻结原结果时请先复制整个项目。仅从可信项目来源加载 joblib 模型。`scripts/check_data.py`、原始来源审计脚本需要完整上游下载归档，不能只对便携快照执行。原始全球数据、第三方报告 PDF、RCM 原始地图和任何现场个人资料均不在此公开包。

## 目录

- `app.py`、`src/`、`web/`：服务、特征与模型、界面。
- `data/`：便携处理数据、空间快照与来源清单。
- `artifacts/`：冻结模型、逐日预测、真实指标及图表。
- `docs/`、`evidence/`：科学说明、原始冻结协议哈希、公开版本审计。
- `tests/`：科学逻辑、模型完整性、接口与空间数据测试。

## 版本与许可

[MIT](LICENSE) 只覆盖原创代码。NOAA、Atlas、字体等保留各自权利和归属，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。本公开快照只调整部署路径、公开文档和目录范围；**未重新训练，未修改模型、CSV 或科学评估数值**。原冻结管线哈希保持不变，另行列出公开源文件哈希与差异，见 [公开版本说明](docs/PUBLIC_RELEASE.md)及 `evidence/public_release_manifest.json`。不能将原科学版本的管线哈希当成路径调整后文件的现行哈希。开发由 OpenAI Codex 辅助，科学结论应由参赛团队复核。
