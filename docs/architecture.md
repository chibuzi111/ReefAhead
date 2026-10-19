# 架构与维护

数据目录由 CLIMATE_DATA_DIR 指定，默认 data；项目 .。raw 保留下载响应和证据；processed 保存标准化日数据；logs 保存执行日志。项目 artifacts 保存训练模型、评估和可共享图表，submission 保存报告、视频与材料包。

scripts/fetch_data.py 负责公开源下载、检查和清单；src/ 中特征、训练、预测互相分离；app.py 使用 FastAPI 提供只读数据与预测 API；web/ 为原生 HTML/CSS/JavaScript，无第三方埋点或在线地图依赖。
API：GET /health、/api/sites、/api/forecast?site_id=…&as_of=…、/api/evaluation、/api/data-manifest、/api/export；/observation-template.csv 提供空白现场模板。模型未生成或数据无效应明确报错，不回填模拟成功结果。

默认服务只监听 127.0.0.1:8765，通过 SSH 转发查看。不要把内网 URL 冒充评委可达的公网地址；如对外部署，应使用 TLS、只读容器、限流与版本固定。服务不采集账户、现场位置上传或个人信息。
训练/评估和服务均限制 CPU 线程。生产推理只加载本项目生成且校验过的本地模型，不加载用户上传 pickle。运行记录、测试报告、依赖锁文件和源码包支持复现。模型首次加载前核对 evaluation.json 中的 SHA-256；校验失败时拒绝推理。

维护流程：先下载到临时文件并检验，再切换版本；保留原始测试集和冻结指标；输入延迟、缺失与预测错误均呈现给用户；新增模型与旧模型并行比较，经人工审核后切换。
