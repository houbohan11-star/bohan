# 架构与数据契约 v1

## 处理链路

CLI → pipeline → media → transcription → vision → prompts。
批量调度复用单任务编排；每个任务有独立目录与状态。v0.1 顺序执行，避免 CPU/GPU 同时装载多个大模型。基础包不依赖模型库。

## 输入和产物

- `media.extract(Path, Path, interval)` 仅接受本地文件；返回 duration、frames、audio。frames 每项为 `{timestamp: 秒, path: 相对路径}`。这是请求采样时间，不承诺原始帧的精确 PTS；VFR 与镜头边界精确定位留待下一版。
- `Transcriber.transcribe(audio, language) -> Transcript`。段落包含 start/end/text；language 不为空；时间必须位于素材范围内。`timing=asr_estimate` 不等于强制对齐。原文与后续纠错、翻译应分文件保存。
- `VisionAnalyzer.analyze(frames, job_dir) -> VisionAnalysis`。每项 observation 包含 start/end/observation/evidence；证据路径只能引用本任务 frames 清单。模型文本属于待核实观察，不能自动认定商品功能、心理或材质。
- 单任务 Python API 可注入以上两个适配器；CLI 暂无模型选择参数。未配置时保留 pending 状态，不调用替代服务。
- 商品输入必须有 name、image_ref 和非空 facts；每条 fact 有 claim 与 evidence 字符串。evidence 是用户提供的证据定位描述，不代表系统已核实。每个 SKU 独立输入，不继承其他任务商品事实。
- `prompts.render` 只整理商品事实与制作检查项，不将未核实模型输出转成最终脚本，也不调用 Seedance。

## 状态

manifest 顶层：running / needs_review / failed。
阶段状态：completed、pending、skipped、needs_review、reviewed、draft_needs_review、blocked_missing_product、failed。
`needs_review` 是当前骨架的正常结束状态，不能解释为全流程完成。`reviewed` 只能由将来的复核流程明确赋值，模型不应自行宣称复核。

目录已存在时拒绝启动。失败后 manifest 保留错误阶段，可能存在中间文件；改用新目录重跑。不承诺原子写入或进程被强制终止后的恢复。后续恢复需验证来源 SHA256、参数与模型版本，不能仅凭文件存在跳过阶段。

## 暂缓边界

下载只处理明确给出的单链接，不抓取全账号。强制对齐、OCR、切镜与翻译分别扩展，不塞进 vision。生成阶段应有独立 provider 接口、成本限制和人工确认；发布不属于本仓库第一版。远端模型需要显式配置并说明数据去向，不隐式上传素材。
