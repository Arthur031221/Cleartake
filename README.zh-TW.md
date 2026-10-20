<h1 align="center">
  <img src="assets/logo.svg" width="72" alt=""><br>
  Cleartake
</h1>

<p align="center">
  <strong>把吵雜的錄音變成乾淨的一take，並檢查沒有人的話被改掉。</strong>
</p>

<p align="center">
  <a href="https://github.com/Arthur031221/Cleartake/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/Arthur031221/Cleartake/ci.yml?style=flat-square&color=ffb02e&label=CI" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-ffb02e?style=flat-square" alt="MIT license"></a>
  <img src="https://img.shields.io/badge/python-3.10%20to%203.12-ffb02e?style=flat-square" alt="Python 3.10 to 3.12">
  <a href="https://arthur031221.github.io/Cleartake/"><img src="https://img.shields.io/badge/live%20demo-open-ffb02e?style=flat-square" alt="Live demo"></a>
</p>

<p align="center">
  <a href="README.md">English</a> | 繁體中文 | <a href="README.zh-CN.md">简体中文</a> | <a href="README.ja.md">日本語</a> | <a href="README.ko.md">한국어</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.de.md">Deutsch</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

在 103 段 VoiceBank-DEMAND 測試音檔上，DNSMOS 背景分數從 **2.98 提升到 4.08**，整體分數從 **2.59 提升到 3.14**。使用 studio 引擎，單看增強階段，在一張 RTX 5090 上為 13.8 倍即時速度。<br>
<sub>方法：從 824 句測試語料中每 8 句取 1 句，強度 1.0，不做響度調整，DNSMOS P.835 透過 `speechmos` 計算，GPU 已暖機。在這種輕度噪音下，字詞錯誤率沒有改善。完整表格與限制請看 [benchmarks/README.md](benchmarks/README.md)（英文）。</sub>

<p align="center">
  <img src="assets/demo.gif" alt="Cleartake 網頁介面：拖入檔案，聆聽前後差異，查看字詞檢查" width="860">
</p>

我做 Cleartake，是為了那種內容很好、只是有嘶聲、風扇聲和房間回音的錄音。它在你的電腦上執行語音增強模型，把響度調到廣播目標，影片畫面逐位元組保持不變，最後轉寫原始檔和處理結果，告訴你哪些字變了。不會上傳任何東西。

## 處理前後

示範資料中的一段音檔（VoiceBank-DEMAND 說話者 p232，28.4 秒，81 個字），使用預設設定，在 [docs/demo](docs/demo) 的檔案上量測。

|  | 原始 | Cleartake | 意義 |
| --- | --- | --- | --- |
| DNSMOS 整體 | 2.63 | 3.33 | 預測品質，1 到 5 |
| DNSMOS 語音 | 3.46 | 3.54 | 人聲本身幾乎沒變 |
| DNSMOS 背景 | 2.86 | 4.14 | 消失的是噪音 |
| 整合響度 | -22.2 LUFS | -16.2 LUFS | podcast 預設 |
| 真峰值 | -4.3 dBTP | -1.6 dBTP | 上限為 -1.5 |
| 改變的字 | | 0 / 81 | Whisper `base.en`，逐字對齊 |

我不宣稱降噪能修好語音。Cleartake 先去除噪音，再稽核結果，所以被改掉的字會是報告裡的一行，而不是播出後的意外。[在瀏覽器試用](https://arthur031221.github.io/Cleartake/)，託管頁面只播放這段示範，不會執行任何處理。

## 處理流程

```
 decode            enhance            finish             check              write
+----------+      +----------+      +----------+      +----------+      +----------+
| any file |  ->  | speech   |  ->  | loudness |  ->  | word     |  ->  | audio or |
| to 48 kHz|      | model    |      | and peak |      | drift    |      | video    |
| mono     |      | on-device|      | target   |      | report   |      | + JSON   |
+----------+      +----------+      +----------+      +----------+      +----------+
 cleartake in.mp4  --engine studio   --preset podcast  --whisper small   -o out/ --json
```

| 你要做什麼 | 指令 | 關鍵原則 |
| --- | --- | --- |
| 處理單一檔案 | `cleartake interview.mp4` | 結果放在輸入檔旁邊，輸入檔不會被動到 |
| 處理整個資料夾 | `cleartake episodes/ -o cleaned/` | 壞掉的檔案不會中斷批次，已命名為 `.cleartake` 的檔案會被跳過 |
| 保留一些房間感 | `cleartake talk.wav --strength 0.7` | 把原始聲音混回去，而不是全有或全無 |
| 符合平台目標 | `cleartake talk.wav --preset youtube` | 先增益再限幅，報告顯示實際量測值 |
| 略過字詞檢查 | `cleartake talk.wav --no-check` | 檢查需要跑一次 Whisper，所以可以關掉 |
| 用其他語言稽核 | `cleartake talk.wav --language de --whisper small` | 使用讀得懂該語言的模型 |
| 在瀏覽器中操作 | `cleartake serve --open` | 本機網頁介面，有 A/B 播放器、頻譜圖和字詞清單 |
| 寫成腳本 | `cleartake in.wav --json` | 報告輸出到 stdout，進度輸出到 stderr |
| 檢查環境 | `cleartake doctor` | 在你等下載之前，先印出 ffmpeg、裝置和已下載的模型 |

## 安裝

需要 Python 3.10 到 3.12 和 ffmpeg。Cleartake 還沒有上架 PyPI。

```bash
uv tool install git+https://github.com/Arthur031221/Cleartake
cleartake doctor
cleartake your-recording.wav
```

第一次執行會下載你選的模型（studio 約 210 MB，classic 約 161 MB）和 Whisper `base.en`（約 141 MB），之後可離線使用。因為 PyTorch 內含 CUDA 函式庫，我的機器上工具環境為 6.2 GB，安裝 wheel 花了 75 秒。

## 各階段

* **解碼.** 任何 ffmpeg 能讀的容器都可以輸入，內部訊號是 48 kHz 單聲道浮點數。影片用 `-c:v copy` 保留畫面，並比對處理前後的影片封包雜湊，只有相符時報告才會寫 `picture_kept: true`。只保留第一條影像串流和新的音訊，額外的音軌和字幕會被丟掉。
* **增強.** `studio`（預設）是 MossFormer2_SE_48K，全頻段 48 kHz。`classic` 是 FRCRN_SE_16K，只保留 8 kHz 以下的語音。它不是加速選項，在 3 顆 CPU 核心上它是 0.7 倍即時，studio 是 3.2 倍。兩者都來自 Apache-2.0 授權的 ClearerVoice-Studio。
* **收尾.** 用 ffmpeg `ebur128` 量測 EBU R128 整合響度，然後增益，再用 `alimiter` 限幅。預設值：podcast -16 LUFS，youtube -14，broadcast -23（真峰值上限 -1.0 dBTP），或 `none`。
* **檢查.** faster-whisper 在 CPU 上轉寫兩個版本，再用 `difflib` 對齊。每個差異都附時間戳記，讓你去聽。網頁介面會在逐字稿上標出來。
* **寫出.** 音訊輸出 wav、flac、m4a 或 mp3。`<output>.json` 記錄處理前後響度、引擎、裝置、速度和字詞差異。 影片依輸入輸出為 mp4、mov 或 mkv，webm、m4v、avi 會輸出成 mkv。

## 實測

103 段 VoiceBank-DEMAND 音檔，DNSMOS P.835，RTX 5090。方法與重現步驟請看 [benchmarks/README.md](benchmarks/README.md)。

| 版本 | OVRL | SIG | BAK | 對乾淨逐字稿的 WER | 速度 |
| --- | --- | --- | --- | --- | --- |
| noisy | 2.59 | 3.22 | 2.98 | 5.4% | n/a |
| classic | 3.17 | 3.44 | 4.06 | 5.1% | 12.7x |
| studio | 3.14 | 3.40 | 4.08 | 6.6% | 13.8x |

其他數字：一段 76 秒的影片在不做字詞檢查時端到端花 6.6 秒（11.5 倍）。一段 25 秒的音檔在 3 顆 CPU 核心上，studio 花 8.0 秒，classic 花 35.7 秒。

## 我知道的限制

* **字詞錯誤率沒有改善。** 在這種輕度噪音下 Whisper 本來就讀得很好。studio 比有噪音的輸入高 1.2 個百分點，classic 低 0.3 個百分點，103 段音檔分不出兩者的差別。同一個指令跑兩次，結果會差約半個百分點。
* **字詞檢查是提示你去聽的地方，不是判決。** 在基準測試中它把約 7% 的字標為不同，其中包含拼法差異和原始噪音版本本來就聽錯的字。Whisper 聽不出來的改動它也抓不到。
* **響度目標可能差約 0.5 LU**，當真峰值上限先擋住增益時就會發生。
* **品質分數是預測值。** DNSMOS 是學習模型，不是聽感測試，而且我只跑了英文語音和 DEMAND 的噪音類型。音樂、迴響和其他語言沒有量測。
* **只在 Linux 上測過**（RTX 5090 和 3 顆 CPU 核心，Python 3.10 與 3.12）。macOS 和 Windows 理論上可以，但我沒跑過。還沒有 Docker 映像。
* **網頁介面的字詞檢查只支援英文。** 它固定使用 Whisper `base.en`。其他語言請用 CLI 並加上 `--whisper small --language de`。
* **批次模式需要不重複的檔名。** `-o` 會保留資料夾結構，若兩個輸入會寫到同一個檔案，或結果會覆蓋輸入檔，Cleartake 會拒絕開始。
* **因為 PyTorch，需要下載數 GB**，而且第一次執行需要網路來取得模型。

## 文件

完整文件為英文： [Install](docs/install.md) | [Usage](docs/usage.md) | [Config](docs/config.md) | [Architecture](docs/architecture.md) | [Benchmark](benchmarks/README.md) | [Contributing](CONTRIBUTING.md) | [Changelog](CHANGELOG.md)

## 致謝

* [ClearerVoice-Studio](https://github.com/modelscope/ClearerVoice-Studio)，增強模型（Apache-2.0）。
* [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 與 Whisper，用於字詞檢查。
* [VoiceBank-DEMAND](https://doi.org/10.7488/ds/2117)（CC BY 4.0），示範音檔與基準測試。
* Microsoft 的 DNSMOS P.835，透過 `speechmos` 執行。

MIT 授權，見 [LICENSE](LICENSE)。

Assisted by Claude/Codex.
