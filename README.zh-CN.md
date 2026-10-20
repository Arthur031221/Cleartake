<h1 align="center">
  <img src="assets/logo.svg" width="72" alt=""><br>
  Cleartake
</h1>

<p align="center">
  <strong>把嘈杂的录音变成干净的一take，并检查没有人的话被改掉。</strong>
</p>

<p align="center">
  <a href="https://github.com/Arthur031221/Cleartake/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/Arthur031221/Cleartake/ci.yml?style=flat-square&color=ffb02e&label=CI" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-ffb02e?style=flat-square" alt="MIT license"></a>
  <img src="https://img.shields.io/badge/python-3.10%20to%203.12-ffb02e?style=flat-square" alt="Python 3.10 to 3.12">
  <a href="https://arthur031221.github.io/Cleartake/"><img src="https://img.shields.io/badge/live%20demo-open-ffb02e?style=flat-square" alt="Live demo"></a>
</p>

<p align="center">
  <a href="README.md">English</a> | <a href="README.zh-TW.md">繁體中文</a> | 简体中文 | <a href="README.ja.md">日本語</a> | <a href="README.ko.md">한국어</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.de.md">Deutsch</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="assets/demo.gif" alt="Cleartake 网页界面：拖入文件，试听前后差异，查看词语检查" width="860">
</p>

我做 Cleartake，是为了那种内容很好、只是有嘶声、风扇声和房间回声的录音。它在你的电脑上运行语音增强模型，把响度调到广播目标，视频画面逐字节保持不变，最后转写原文件和处理结果，告诉你哪些词变了。不会上传任何东西。

```bash
uv tool install git+https://github.com/Arthur031221/Cleartake
cleartake serve --open
```

在 103 段 VoiceBank-DEMAND 测试音频上，DNSMOS 背景分数从 **2.98 提升到 4.08**，整体分数从 **2.59 提升到 3.14**。使用 studio 引擎，只看增强阶段，在一张 RTX 5090 上为 13.8 倍实时速度。<br>
<sub>方法：从 824 句测试语料中每 8 句取 1 句，强度 1.0，不做响度调整，DNSMOS P.835 通过 `speechmos` 计算，GPU 已预热。在这种轻度噪声下，词错误率没有改善。完整表格和限制见 [benchmarks/README.md](benchmarks/README.md)（英文）。</sub>

## 处理前后

演示数据中的一段音频（VoiceBank-DEMAND 说话人 p232，28.4 秒，81 个词），使用默认设置，在 [docs/demo](docs/demo) 的文件上测量。

|  | 原始 | Cleartake | 含义 |
| --- | --- | --- | --- |
| DNSMOS 整体 | 2.63 | 3.33 | 预测质量，1 到 5 |
| DNSMOS 语音 | 3.46 | 3.54 | 人声本身几乎没变 |
| DNSMOS 背景 | 2.86 | 4.14 | 消失的是噪声 |
| 整合响度 | -22.2 LUFS | -16.2 LUFS | podcast 预设 |
| 真峰值 | -4.3 dBTP | -1.6 dBTP | 上限为 -1.5 |
| 改变的词 | | 0 / 81 | Whisper `base.en`，逐词对齐 |

我不声称降噪能修好语音。Cleartake 先去除噪声，再审计结果，所以被改掉的词会是报告里的一行，而不是播出后的意外。[在浏览器中试用](https://arthur031221.github.io/Cleartake/)，托管页面只播放这段演示，不会运行任何处理。

## 处理流程

```
 decode            enhance            finish             check              write
+----------+      +----------+      +----------+      +----------+      +----------+
| any file |  ->  | speech   |  ->  | loudness |  ->  | word     |  ->  | audio or |
| to 48 kHz|      | model    |      | and peak |      | drift    |      | video    |
| mono     |      | on-device|      | target   |      | report   |      | + JSON   |
+----------+      +----------+      +----------+      +----------+      +----------+
 cleartake in.mp4  --engine studio   --preset podcast  --whisper small   -o out/ --json
```

| 你要做什么 | 命令 | 关键原则 |
| --- | --- | --- |
| 处理单个文件 | `cleartake interview.mp4` | 结果放在输入文件旁边，输入文件不会被改动 |
| 处理整个文件夹 | `cleartake episodes/ -o cleaned/` | 坏掉的文件不会中断批处理，已命名为 `.cleartake` 的文件会被跳过 |
| 保留一些房间感 | `cleartake talk.wav --strength 0.7` | 把原始声音混回去，而不是全有或全无 |
| 符合平台目标 | `cleartake talk.wav --preset youtube` | 先增益再限幅，报告显示实际测量值 |
| 跳过词语检查 | `cleartake talk.wav --no-check` | 检查需要跑一次 Whisper，所以可以关掉 |
| 用其他语言审计 | `cleartake talk.wav --language de --whisper small` | 使用读得懂该语言的模型 |
| 在浏览器中操作 | `cleartake serve --open` | 本机网页界面：可一次拖入多个文件，随时取消任何一个，并用 A/B 播放器、频谱图和词语列表对比 |
| 写成脚本 | `cleartake in.wav --json` | 报告输出到 stdout，进度输出到 stderr |
| 检查环境 | `cleartake doctor` | 在你等下载之前，先打印 ffmpeg、设备和已下载的模型 |

## 安装

需要 Python 3.10 到 3.12 和 ffmpeg。Cleartake 还没有发布到 PyPI。

```bash
uv tool install git+https://github.com/Arthur031221/Cleartake
cleartake doctor
cleartake your-recording.wav
```

第一次运行会下载你选的模型（studio 约 210 MB，classic 约 161 MB）和 Whisper `base.en`（约 141 MB），之后可离线使用。因为 PyTorch 自带 CUDA 库，我的机器上工具环境为 6.2 GB，安装 wheel 用了 75 秒。

## 各阶段

* **解码.** 任何 ffmpeg 能读的容器都可以输入，内部信号是 48 kHz 单声道浮点数。视频用 `-c:v copy` 保留画面，并比对处理前后的视频包哈希，只有一致时报告才会写 `picture_kept: true`。只保留第一条视频流和新的音频，额外的音轨和字幕会被丢掉。
* **增强.** `studio`（默认）是 MossFormer2_SE_48K，全频段 48 kHz。`classic` 是 FRCRN_SE_16K，只保留 8 kHz 以下的语音。它不是提速选项，在 3 个 CPU 核心上它是 0.7 倍实时，studio 是 3.2 倍。两者都来自 Apache-2.0 许可的 ClearerVoice-Studio。
* **收尾.** 用 ffmpeg `ebur128` 测量 EBU R128 整合响度，然后增益，再用 `alimiter` 限幅。预设：podcast -16 LUFS，youtube -14，broadcast -23（真峰值上限 -1.0 dBTP），或 `none`。
* **检查.** faster-whisper 在 CPU 上转写两个版本，再用 `difflib` 对齐。每个差异都带时间戳，方便你去听。网页界面会在逐字稿上标出来。
* **写出.** 音频输出 wav、flac、m4a 或 mp3。`<output>.json` 记录处理前后响度、引擎、设备、速度和词语差异。 视频按输入输出为 mp4、mov 或 mkv，webm、m4v、avi 会输出为 mkv。

## 实测

103 段 VoiceBank-DEMAND 音频，DNSMOS P.835，RTX 5090。方法和复现步骤见 [benchmarks/README.md](benchmarks/README.md)。

| 版本 | OVRL | SIG | BAK | 对干净转写的 WER | 速度 |
| --- | --- | --- | --- | --- | --- |
| noisy | 2.59 | 3.22 | 2.98 | 5.4% | n/a |
| classic | 3.17 | 3.44 | 4.06 | 5.1% | 12.7x |
| studio | 3.14 | 3.40 | 4.08 | 6.6% | 13.8x |

其他数字：一段 76 秒的视频在不做词语检查时端到端用了 6.6 秒（11.5 倍）。一段 25 秒的音频在 3 个 CPU 核心上，studio 用了 8.0 秒，classic 用了 35.7 秒。

## 我知道的限制

* **词错误率没有改善。** 在这种轻度噪声下 Whisper 本来就读得很好。studio 比带噪输入高 1.2 个百分点，classic 低 0.3 个百分点，103 段音频分不出两者的差别。同一条命令跑两次，结果会差约半个百分点。
* **词语检查是提示你去听的地方，不是判决。** 在基准测试中它把约 7% 的词标为不同，其中包含拼写差异和原始带噪版本本来就听错的词。Whisper 听不出来的改动它也抓不到。
* **响度目标可能差约 0.5 LU**，当真峰值上限先挡住增益时就会发生。
* **质量分数是预测值。** DNSMOS 是学习模型，不是听感测试，而且我只跑了英文语音和 DEMAND 的噪声类型。音乐、混响和其他语言没有测量。
* **只在 Linux 上测过**（RTX 5090 和 3 个 CPU 核心，Python 3.10 与 3.12）。macOS 和 Windows 理论上可以，但我没跑过。还没有 Docker 镜像。
* **网页界面在其他语言下的词语检查未经测试。** 英文使用 Whisper `base.en`。在设置卡片里选的其他语言，或自动检测，使用 Whisper `small`（约 460 MB，只下载一次）。我没有测量过各语言的准确率。
* **批处理需要不重复的文件名。** `-o` 会保留文件夹结构，如果两个输入会写到同一个文件，或结果会覆盖输入文件，Cleartake 会拒绝开始。
* **因为 PyTorch，需要下载数 GB**，而且第一次运行需要网络来获取模型。

## 文档

完整文档为英文： [Install](docs/install.md) | [Usage](docs/usage.md) | [Config](docs/config.md) | [Architecture](docs/architecture.md) | [Benchmark](benchmarks/README.md) | [Contributing](CONTRIBUTING.md) | [Changelog](CHANGELOG.md)

## 致谢

* [ClearerVoice-Studio](https://github.com/modelscope/ClearerVoice-Studio)，增强模型（Apache-2.0）。
* [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 和 Whisper，用于词语检查。
* [VoiceBank-DEMAND](https://doi.org/10.7488/ds/2117)（CC BY 4.0），演示音频和基准测试。
* Microsoft 的 DNSMOS P.835，通过 `speechmos` 运行。

MIT 许可，见 [LICENSE](LICENSE)。

Assisted by Claude/Codex.
