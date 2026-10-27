# bohan · 视频分析与 AI 导演工作流

第一版工程骨架（Python 3.11+）。目标是把视频提取、语音转写、画面证据、商品事实与 Seedance 2.0 导演制作分开，便于逐步接入真实模型。

**当前可运行：** 本地视频参数检查、按时间抽帧、16 kHz 单声道 WAV 提取、任务状态记录、商品白名单草稿、顺序批量处理与错误隔离。

**尚未实现：** URL 下载、Whisper 模型推理、Qwen3-VL 推理、切镜/OCR/强制对齐、自动翻译、故事板图片生成、Seedance API 调用。未接入阶段会输出 `pending`；无商品时提示词为 `blocked_missing_product`。命令成功只代表已实现阶段执行完成，任务仍为 `needs_review`。

## 快速开始与安装顺序

1. 安装 Python 3.11+，创建隔离环境。
2. 从操作系统可信渠道安装 FFmpeg（必须同时包含 `ffmpeg` 与 `ffprobe`，并加入 PATH）。
3. 安装本仓库基础包；运行依赖为 Python 标准库，无模型下载。
4. 运行 doctor、测试及本地视频任务。
5. 后续按 [安装规划](docs/installation.md) 单独验证 Whisper 与 Qwen3-VL 环境，不一次安装全部重型组件。

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell 使用：.venv\Scripts\Activate.ps1
python -m pip install -e .
bohan doctor
python -m unittest discover -s tests -v
bohan run /absolute/path/video.mp4 --out runs/demo --language de --interval 2
# 有本次商品证据时：复制并修改 examples/product.json 后添加 --product 参数
bohan run /absolute/path/video.mp4 --out runs/product-demo --product examples/product.json
bohan batch examples/batch.json --out runs/batch-demo
```

`examples/product.json` 为明确标记的占位示例，不能直接当成真实商品事实。批量清单的相对路径以清单所在目录为基准；单任务路径以当前工作目录为基准。每次使用新的输出目录；已有目录直接拒绝，不覆盖素材。不支持断点续跑。

可复现的合成视频验收（FFmpeg）：

```bash
ffmpeg -f lavfi -i testsrc=size=160x120:rate=10 -f lavfi -i sine=frequency=440:sample_rate=16000 -t 2 -c:v mpeg4 -c:a aac /tmp/bohan-smoke.mp4
bohan run /tmp/bohan-smoke.mp4 --out runs/smoke --interval 1
```

## 目录与职责

| 路径 | 职责 |
| --- | --- |
| `src/bohan/media.py` | 本地视频输入、ffprobe、音频与证据帧提取；未来下载器另设适配器 |
| `src/bohan/transcription.py` | ASR 调用边界、无音轨与未配置状态 |
| `src/bohan/vision.py` | 画面模型调用边界、证据帧引用检查 |
| `src/bohan/contracts.py` | 转写/观察数据结构、适配器 Protocol、时间范围校验 |
| `src/bohan/prompts.py` | 本次商品白名单与待复核 Seedance 制作草稿 |
| `src/bohan/pipeline.py` | 单任务编排、状态与错误落盘 |
| `src/bohan/batch.py` | 顺序执行、任务目录隔离、失败继续及汇总 |
| `src/bohan/cli.py` | doctor / run / batch 命令 |
| `docs/` | 模块契约、依赖规划、后续验收顺序 |
| `examples/` | 商品事实与批量任务配置示例 |
| `tests/` | 标准库 unittest，含真实 FFmpeg 集成测试 |

## 单任务输出

| 文件 | 内容 |
| --- | --- |
| `manifest.json` | schema 版本、输入绝对路径、参数、阶段状态、失败原因 |
| `metadata.json` | ffprobe 原始参数 |
| `frames.json` + `frames/*.jpg` | 请求采样时间（非精确 PTS）与原分辨率证据帧 |
| `audio.wav` | 有音轨时提取第一条音轨；无音轨不生成 |
| `transcript.json` | ASR 结果或 `pending`/`skipped` 状态 |
| `vision.json` | 帧引用观察或 `pending` 状态 |
| `prompt.md` | 缺商品阻断说明，或待复核商品制作草稿 |

`batch.json` 是批量汇总。进程退出码 0 表示本版可执行阶段成功，1 表示失败；成功不等于模型分析完成。抽帧为稀疏时间采样，不是逐帧分析或切镜检测。单任务最多 1000 帧，单次外部命令超时 300 秒。当前为短视频、顺序任务设计，不是生产任务队列。

## 后续开发顺序

1. 来源与缓存：用户提供 URL 的单链接下载、来源哈希、版本化 manifest、可靠恢复。
2. Whisper：真实德语样本、时间戳与听辨校正，保留 ASR 原稿；词级强制对齐单独建模块。
3. Qwen3-VL：硬件评估、帧预算、逐条证据引用、人/商品/动作/场景观察；区分事实与推测。
4. 导演：参考视频报告 → 商品白名单 → 三钩子 → 中德脚本确认 → 真实试配音计时。
5. 故事板：人物/场景状态母表 → 首段九宫格逐格审核 → 实际尾帧 → 独立第二段故事板。
6. 批量增强：阶段恢复、模型常驻工作进程、资源限额；最后再接生成 API 与界面。

详见 [架构与契约](docs/architecture.md)、[安装规划](docs/installation.md)、[开发验收](docs/roadmap.md)。

本仓库不包含私人视频、密钥或模型权重。安装了骨架不代表已安装模型；没有执行模型推理不能报告模型分析成功。仓库尚未指定开源许可证。
