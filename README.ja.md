<h1 align="center">
  <img src="assets/logo.svg" width="72" alt=""><br>
  Cleartake
</h1>

<p align="center">
  <strong>ノイズの多い録音をきれいなテイクにして、誰の言葉も変わっていないことを確かめます。</strong>
</p>

<p align="center">
  <a href="https://github.com/Arthur031221/Cleartake/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/Arthur031221/Cleartake/ci.yml?style=flat-square&color=ffb02e&label=CI" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-ffb02e?style=flat-square" alt="MIT license"></a>
  <img src="https://img.shields.io/badge/python-3.10%20to%203.12-ffb02e?style=flat-square" alt="Python 3.10 to 3.12">
  <a href="https://arthur031221.github.io/Cleartake/"><img src="https://img.shields.io/badge/live%20demo-open-ffb02e?style=flat-square" alt="Live demo"></a>
</p>

<p align="center">
  <a href="README.md">English</a> | <a href="README.zh-TW.md">繁體中文</a> | <a href="README.zh-CN.md">简体中文</a> | 日本語 | <a href="README.ko.md">한국어</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.de.md">Deutsch</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="assets/demo.gif" alt="Cleartake の Web 画面：ファイルを置き、前後を聴き比べ、単語チェックを見る" width="860">
</p>

内容は良いのに、ヒスノイズやファンの音や部屋の響きが残る録音のために Cleartake を作りました。音声強調モデルをお使いのマシン上で動かし、ラウドネスを放送向けの目標に合わせ、動画の映像はバイト単位でそのまま保ち、元の音声と結果を文字起こしして、変わった単語を示します。何もアップロードしません。

```bash
uv tool install git+https://github.com/Arthur031221/Cleartake
cleartake serve --open
```

VoiceBank-DEMAND のテスト音声 103 本で、DNSMOS の背景スコアは **2.98 から 4.08**、総合スコアは **2.59 から 3.14** に上がりました。studio エンジン、強調処理だけで RTX 5090 1 枚あたりリアルタイムの 13.8 倍です。<br>
<sub>方法：テスト用の 824 発話から 8 本ごとに 1 本を選び、強度 1.0、ラウドネス調整なし、DNSMOS P.835 を `speechmos` で計算、GPU はウォームアップ済みです。この程度の軽いノイズでは単語誤り率は改善しませんでした。完全な表と注意点は [benchmarks/README.md](benchmarks/README.md)（英語）にあります。</sub>

## 処理の前と後

デモ用データの 1 本（VoiceBank-DEMAND の話者 p232、28.4 秒、81 語）を既定の設定で処理し、[docs/demo](docs/demo) のファイルで測定しました。

|  | 元の音声 | Cleartake | 意味 |
| --- | --- | --- | --- |
| DNSMOS 総合 | 2.63 | 3.33 | 予測品質、1 から 5 |
| DNSMOS 音声 | 3.46 | 3.54 | 声そのものはほとんど変わらない |
| DNSMOS 背景 | 2.86 | 4.14 | 消えるのはノイズ |
| 統合ラウドネス | -22.2 LUFS | -16.2 LUFS | podcast プリセット |
| トゥルーピーク | -4.3 dBTP | -1.6 dBTP | 上限は -1.5 |
| 変わった単語 | | 0 / 81 | Whisper `base.en`、単語ごとに対応付け |

ノイズ除去で音声が直るとは言いません。Cleartake はノイズを取り、その結果を監査します。単語が変わっても、放送後に気づくのではなく、レポートの 1 行として分かります。[ブラウザで試す](https://arthur031221.github.io/Cleartake/)こともできます。公開ページはこのデモを再生するだけで、処理は行いません。

## パイプライン

```
 decode            enhance            finish             check              write
+----------+      +----------+      +----------+      +----------+      +----------+
| any file |  ->  | speech   |  ->  | loudness |  ->  | word     |  ->  | audio or |
| to 48 kHz|      | model    |      | and peak |      | drift    |      | video    |
| mono     |      | on-device|      | target   |      | report   |      | + JSON   |
+----------+      +----------+      +----------+      +----------+      +----------+
 cleartake in.mp4  --engine studio   --preset podcast  --whisper small   -o out/ --json
```

| やりたいこと | コマンド | 原則 |
| --- | --- | --- |
| 1 ファイルを処理 | `cleartake interview.mp4` | 結果は入力の隣に置き、入力には触れません |
| フォルダを処理 | `cleartake episodes/ -o cleaned/` | 壊れたファイルがあってもバッチは止まらず、`.cleartake` と名前が付いたファイルは飛ばします |
| 部屋の響きを少し残す | `cleartake talk.wav --strength 0.7` | 全部か無かではなく、元の音を混ぜ戻します |
| 配信先の目標に合わせる | `cleartake talk.wav --preset youtube` | 先にゲイン、次にリミッター。レポートには実測値が出ます |
| 単語チェックを省く | `cleartake talk.wav --no-check` | チェックには Whisper の実行が 1 回必要なので、切れます |
| 他の言語で監査する | `cleartake talk.wav --language de --whisper small` | その言語を読めるモデルを使います |
| ブラウザで使う | `cleartake serve --open` | 複数ファイルをまとめてドロップでき、どれでもキャンセルできるローカル Web アプリ。A/B プレーヤー、スペクトログラム、単語リスト付き |
| スクリプトから使う | `cleartake in.wav --json` | レポートは stdout、進捗は stderr に出ます |
| 環境を確認する | `cleartake doctor` | ダウンロードを待つ前に ffmpeg、デバイス、取得済みモデルを表示します |

## インストール

Python 3.10 から 3.12 と ffmpeg が必要です。Cleartake はまだ PyPI にありません。

```bash
uv tool install git+https://github.com/Arthur031221/Cleartake
cleartake doctor
cleartake your-recording.wav
```

初回の実行で、選んだモデル（studio は約 210 MB、classic は約 161 MB）と Whisper `base.en`（約 141 MB）をダウンロードします。その後はオフラインで動きます。PyTorch が CUDA ライブラリを同梱するため、私の環境ではツール環境が 6.2 GB になり、wheel のインストールには 75 秒かかりました。

## 段階ごとの内容

* **デコード.** ffmpeg が読めるコンテナなら入力でき、内部の信号は 48 kHz モノラルの浮動小数点です。動画は `-c:v copy` で映像を保ち、処理の前後で映像パケットのハッシュを比べ、一致したときだけレポートに `picture_kept: true` と書きます。残るのは最初の映像ストリームと新しい音声だけで、追加の音声トラックと字幕は落ちます。
* **強調.** `studio`（既定）は MossFormer2_SE_48K で、48 kHz の全帯域です。`classic` は FRCRN_SE_16K で、8 kHz までの音声だけを残します。速度のための選択肢ではなく、CPU 3 コアでは classic が 0.7 倍、studio が 3.2 倍のリアルタイムでした。どちらも Apache-2.0 の ClearerVoice-Studio 由来です。
* **仕上げ.** ffmpeg の `ebur128` で EBU R128 の統合ラウドネスを測り、ゲインをかけ、`alimiter` で上限を守ります。プリセットは podcast -16 LUFS、youtube -14、broadcast -23（トゥルーピーク上限 -1.0 dBTP）、または `none` です。
* **チェック.** faster-whisper が両方を CPU で文字起こしし、`difflib` で対応付けます。差分には時刻が付くので、聴いて確かめられます。Web アプリは文字起こしの上に印を付けます。
* **書き出し.** 音声は wav、flac、m4a、mp3 で出力します。`<output>.json` には前後のラウドネス、エンジン、デバイス、速度、単語の差分が入ります。 動画は入力に合わせて mp4、mov、mkv で出力し、webm、m4v、avi は mkv になります。

## 測定結果

VoiceBank-DEMAND 103 本、DNSMOS P.835、RTX 5090。方法と再現手順は [benchmarks/README.md](benchmarks/README.md) にあります。

| 種類 | OVRL | SIG | BAK | クリーン書き起こしに対する WER | 速度 |
| --- | --- | --- | --- | --- | --- |
| noisy | 2.59 | 3.22 | 2.98 | 5.4% | n/a |
| classic | 3.17 | 3.44 | 4.06 | 5.1% | 12.7x |
| studio | 3.14 | 3.40 | 4.08 | 6.6% | 13.8x |

その他の数値：76 秒の動画は単語チェックなしで最初から最後まで 6.6 秒（11.5 倍）でした。25 秒の音声は CPU 3 コアで studio が 8.0 秒、classic が 35.7 秒でした。

## 分かっている制限

* **単語誤り率は改善していません。** この程度のノイズでは Whisper は元の音声をすでによく読めます。studio はノイズありの入力より 1.2 ポイント高く、classic は 0.3 ポイント低く、103 本では両者の差は判断できません。同じコマンドを 2 回走らせると約 0.5 ポイント動きました。
* **単語チェックは判決ではなく、聴くべき場所の目印です。** ベンチマークでは約 7% の単語が違うと報告され、そこには綴りの揺れや、ノイズありの元音声が聞き間違えた単語も含まれます。Whisper に聞き取れない変化は検出できません。
* **ラウドネスの目標を約 0.5 LU 外すことがあります。** トゥルーピーク上限が先にゲインを止めた場合です。
* **品質スコアは予測値です。** DNSMOS は学習済みモデルで、聴取試験ではありません。試したのは英語の音声と DEMAND のノイズだけで、音楽、残響、他の言語は測っていません。
* **テストしたのは Linux だけです**（RTX 5090 と CPU 3 コア、Python 3.10 と 3.12）。macOS と Windows も動くはずですが、実行していません。Docker イメージはまだありません。
* **Web アプリの単語チェックは、英語以外では未検証です。** 英語は Whisper `base.en` を使います。設定カードで選んだほかの言語や自動検出では Whisper `small`（約 460 MB、ダウンロードは一度だけ）を使います。言語ごとの精度は測っていません。
* **バッチ処理にはファイル名の重複がないことが必要です。** `-o` はフォルダ構成を保ち、2 つの入力が同じファイルに書き込む場合や、結果が入力を置き換える場合は、Cleartake は開始を拒否します。
* **PyTorch のため数 GB のダウンロードが必要で、** 初回はモデル取得にネットワークが要ります。

## ドキュメント

詳細なドキュメントは英語です： [Install](docs/install.md) | [Usage](docs/usage.md) | [Config](docs/config.md) | [Architecture](docs/architecture.md) | [Benchmark](benchmarks/README.md) | [Contributing](CONTRIBUTING.md) | [Changelog](CHANGELOG.md)

## クレジット

* [ClearerVoice-Studio](https://github.com/modelscope/ClearerVoice-Studio)、強調モデル（Apache-2.0）。
* [faster-whisper](https://github.com/SYSTRAN/faster-whisper) と Whisper、単語チェック用。
* [VoiceBank-DEMAND](https://doi.org/10.7488/ds/2117)（CC BY 4.0）、デモ音声とベンチマーク用。
* Microsoft の DNSMOS P.835、`speechmos` 経由。

MIT ライセンスです。[LICENSE](LICENSE) を見てください。

Assisted by Claude/Codex.
