<h1 align="center">
  <img src="assets/logo.svg" width="72" alt=""><br>
  Cleartake
</h1>

<p align="center">
  <strong>잡음이 많은 녹음을 깨끗한 테이크로 만들고, 누구의 말도 바뀌지 않았는지 확인합니다.</strong>
</p>

<p align="center">
  <a href="https://github.com/Arthur031221/Cleartake/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/Arthur031221/Cleartake/ci.yml?style=flat-square&color=ffb02e&label=CI" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-ffb02e?style=flat-square" alt="MIT license"></a>
  <img src="https://img.shields.io/badge/python-3.10%20to%203.12-ffb02e?style=flat-square" alt="Python 3.10 to 3.12">
  <a href="https://arthur031221.github.io/Cleartake/"><img src="https://img.shields.io/badge/live%20demo-open-ffb02e?style=flat-square" alt="Live demo"></a>
</p>

<p align="center">
  <a href="README.md">English</a> | <a href="README.zh-TW.md">繁體中文</a> | <a href="README.zh-CN.md">简体中文</a> | <a href="README.ja.md">日本語</a> | 한국어 | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.de.md">Deutsch</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="assets/demo.gif" alt="Cleartake 웹 화면: 파일을 놓고, 전후를 비교해 듣고, 단어 검사를 확인합니다" width="860">
</p>

내용은 좋은데 히스 소리, 팬 소리, 방 울림이 남은 녹음을 위해 Cleartake를 만들었습니다. 음성 향상 모델을 내 컴퓨터에서 실행하고, 음량을 방송 기준에 맞추고, 영상 화면은 바이트 단위로 그대로 두고, 원본과 결과를 모두 받아쓰기해서 바뀐 단어를 보여 줍니다. 아무것도 업로드하지 않습니다.

```bash
uv tool install git+https://github.com/Arthur031221/Cleartake
cleartake serve --open
```

VoiceBank-DEMAND 테스트 음성 103개에서 DNSMOS 배경 점수는 **2.98에서 4.08**로, 종합 점수는 **2.59에서 3.14**로 올랐습니다. studio 엔진, 향상 단계만 RTX 5090 한 장에서 실시간의 13.8배입니다.<br>
<sub>방법: 테스트 발화 824개 중 8개마다 1개를 골랐고, 강도 1.0, 음량 조정 없음, DNSMOS P.835는 `speechmos`로 계산했으며 GPU는 예열한 상태입니다. 이 정도의 가벼운 잡음에서는 단어 오류율이 좋아지지 않았습니다. 전체 표와 한계는 [benchmarks/README.md](benchmarks/README.md)(영어)에 있습니다.</sub>

## 처리 전과 후

데모 데이터의 클립 하나(VoiceBank-DEMAND 화자 p232, 28.4초, 81단어)를 기본 설정으로 처리했고, [docs/demo](docs/demo)의 파일로 측정했습니다.

|  | 원본 | Cleartake | 의미 |
| --- | --- | --- | --- |
| DNSMOS 종합 | 2.63 | 3.33 | 예측 품질, 1에서 5 |
| DNSMOS 음성 | 3.46 | 3.54 | 목소리 자체는 거의 변하지 않음 |
| DNSMOS 배경 | 2.86 | 4.14 | 사라지는 것은 잡음 |
| 통합 음량 | -22.2 LUFS | -16.2 LUFS | podcast 프리셋 |
| 트루 피크 | -4.3 dBTP | -1.6 dBTP | 상한은 -1.5 |
| 바뀐 단어 | | 0 / 81 | Whisper `base.en`, 단어 단위로 정렬 |

잡음 제거가 음성을 고쳐 준다고 말하지 않습니다. Cleartake는 잡음을 없앤 뒤 결과를 감사합니다. 그래서 바뀐 단어는 방송 후의 사고가 아니라 보고서의 한 줄이 됩니다. [브라우저에서 사용해 보세요](https://arthur031221.github.io/Cleartake/). 호스팅된 페이지는 이 데모를 재생만 하고 처리는 하지 않습니다.

## 파이프라인

```
 decode            enhance            finish             check              write
+----------+      +----------+      +----------+      +----------+      +----------+
| any file |  ->  | speech   |  ->  | loudness |  ->  | word     |  ->  | audio or |
| to 48 kHz|      | model    |      | and peak |      | drift    |      | video    |
| mono     |      | on-device|      | target   |      | report   |      | + JSON   |
+----------+      +----------+      +----------+      +----------+      +----------+
 cleartake in.mp4  --engine studio   --preset podcast  --whisper small   -o out/ --json
```

| 하려는 일 | 명령 | 핵심 원칙 |
| --- | --- | --- |
| 파일 하나 처리 | `cleartake interview.mp4` | 결과는 입력 옆에 두고, 입력은 건드리지 않습니다 |
| 폴더 처리 | `cleartake episodes/ -o cleaned/` | 깨진 파일이 있어도 일괄 처리는 멈추지 않고, 이름이 `.cleartake`인 파일은 건너뜁니다 |
| 방의 느낌을 조금 남기기 | `cleartake talk.wav --strength 0.7` | 전부 아니면 전무가 아니라 원본을 다시 섞습니다 |
| 플랫폼 기준에 맞추기 | `cleartake talk.wav --preset youtube` | 먼저 게인, 다음에 리미터. 보고서에는 실측값이 나옵니다 |
| 단어 검사 생략 | `cleartake talk.wav --no-check` | 검사에는 Whisper를 한 번 돌려야 하므로 끌 수 있습니다 |
| 다른 언어로 감사 | `cleartake talk.wav --language de --whisper small` | 그 언어를 읽을 수 있는 모델을 사용합니다 |
| 브라우저에서 작업 | `cleartake serve --open` | 파일 여러 개를 한 번에 놓고 하나씩 취소할 수 있는 로컬 웹 앱. A/B 플레이어, 스펙트로그램, 단어 목록이 있습니다 |
| 스크립트로 사용 | `cleartake in.wav --json` | 보고서는 stdout, 진행 상황은 stderr로 나옵니다 |
| 환경 점검 | `cleartake doctor` | 다운로드를 기다리기 전에 ffmpeg, 장치, 받아 둔 모델을 출력합니다 |

## 설치

Python 3.10에서 3.12와 ffmpeg가 필요합니다. Cleartake는 아직 PyPI에 없습니다.

```bash
uv tool install git+https://github.com/Arthur031221/Cleartake
cleartake doctor
cleartake your-recording.wav
```

처음 실행하면 고른 모델(studio 약 210 MB, classic 약 161 MB)과 Whisper `base.en`(약 141 MB)을 내려받습니다. 그 뒤에는 오프라인으로 동작합니다. PyTorch가 CUDA 라이브러리를 함께 담고 있어 제 환경에서 도구 환경은 6.2 GB였고, wheel 설치에는 75초가 걸렸습니다.

## 단계별 구성

* **디코드.** ffmpeg가 읽는 컨테이너라면 입력할 수 있고, 내부 신호는 48 kHz 모노 부동소수점입니다. 영상은 `-c:v copy`로 화면을 유지하고, 처리 전후의 비디오 패킷 해시를 비교해서 일치할 때만 보고서에 `picture_kept: true`를 적습니다.첫 번째 영상 스트림과 새 오디오만 남고, 추가 오디오 트랙과 자막은 버려집니다.
* **향상.** `studio`(기본값)는 MossFormer2_SE_48K이며 48 kHz 전 대역입니다. `classic`은 FRCRN_SE_16K이며 8 kHz까지의 음성만 남깁니다. 속도를 위한 선택지가 아니며, CPU 3코어에서 classic은 실시간의 0.7배, studio는 3.2배였습니다. 둘 다 Apache-2.0인 ClearerVoice-Studio에서 왔습니다.
* **마무리.** ffmpeg `ebur128`로 EBU R128 통합 음량을 측정하고, 게인을 적용한 다음 `alimiter`로 상한을 지킵니다. 프리셋은 podcast -16 LUFS, youtube -14, broadcast -23(트루 피크 상한 -1.0 dBTP), 또는 `none`입니다.
* **검사.** faster-whisper가 두 버전을 CPU에서 받아쓰고 `difflib`로 정렬합니다. 모든 차이에 시각이 붙어 있어 직접 들어 볼 수 있습니다. 웹 앱은 받아쓴 글에 표시를 합니다.
* **저장.** 오디오는 wav, flac, m4a, mp3로 내보냅니다. `<output>.json`에는 전후 음량, 엔진, 장치, 속도, 단어 차이가 기록됩니다. 영상은 입력에 맞춰 mp4, mov, mkv로 나가고 webm, m4v, avi는 mkv가 됩니다.

## 측정 결과

VoiceBank-DEMAND 103개, DNSMOS P.835, RTX 5090. 방법과 재현 절차는 [benchmarks/README.md](benchmarks/README.md)에 있습니다.

| 종류 | OVRL | SIG | BAK | 깨끗한 받아쓰기 대비 WER | 속도 |
| --- | --- | --- | --- | --- | --- |
| noisy | 2.59 | 3.22 | 2.98 | 5.4% | n/a |
| classic | 3.17 | 3.44 | 4.06 | 5.1% | 12.7x |
| studio | 3.14 | 3.40 | 4.08 | 6.6% | 13.8x |

그 밖의 수치: 76초 영상은 단어 검사 없이 처음부터 끝까지 6.6초(11.5배)가 걸렸습니다. 25초 음성은 CPU 3코어에서 studio 8.0초, classic 35.7초가 걸렸습니다.

## 알고 있는 한계

* **단어 오류율은 좋아지지 않았습니다.** 이 정도 잡음에서는 Whisper가 원본을 이미 잘 읽습니다. studio는 잡음이 있는 입력보다 1.2포인트 높고 classic은 0.3포인트 낮은데, 103개로는 둘의 차이를 구분할 수 없습니다. 같은 명령을 두 번 돌리면 약 0.5포인트 흔들렸습니다.
* **단어 검사는 판결이 아니라 들어 봐야 할 곳을 알려 주는 표시입니다.** 벤치마크에서 약 7%의 단어가 다르다고 나오는데, 철자 차이와 잡음 있는 원본이 잘못 들은 단어도 포함됩니다. Whisper가 듣지 못하는 변화는 잡아내지 못합니다.
* **음량 목표를 약 0.5 LU 놓칠 수 있습니다.** 트루 피크 상한이 먼저 게인을 막을 때 생깁니다.
* **품질 점수는 예측값입니다.** DNSMOS는 학습된 모델이지 청취 시험이 아니며, 저는 영어 음성과 DEMAND 잡음 종류만 돌렸습니다. 음악, 잔향, 다른 언어는 측정하지 않았습니다.
* **실제 모델은 Linux에서만 돌려 봤습니다**(RTX 5090과 CPU 3코어, Python 3.10과 3.12). 브라우저를 쓰지 않는 테스트는 CI에서 macOS(Apple 실리콘)와 Windows에서도 통과하지만, 그곳에서는 모델 대역을 씁니다. Docker 이미지는 아직 없습니다.
* **웹 앱의 단어 검사는 영어 외 언어에서 검증하지 않았습니다.** 영어는 Whisper `base.en`을 씁니다. 설정 카드에서 고른 다른 언어나 자동 감지는 Whisper `small`(약 460 MB, 한 번만 내려받음)을 씁니다. 언어별 정확도는 측정하지 않았습니다.
* **일괄 처리에는 겹치지 않는 파일 이름이 필요합니다.** `-o`는 폴더 구조를 유지하고, 두 입력이 같은 파일에 쓰게 되거나 결과가 입력을 덮어쓰게 되면 Cleartake는 시작을 거부합니다.
* **PyTorch 때문에 수 GB를 내려받아야 하고,** 처음에는 모델을 받으려면 네트워크가 필요합니다.

## 문서

자세한 문서는 영어입니다: [Install](docs/install.md) | [Usage](docs/usage.md) | [Config](docs/config.md) | [Architecture](docs/architecture.md) | [Benchmark](benchmarks/README.md) | [Contributing](CONTRIBUTING.md) | [Changelog](CHANGELOG.md)

## 크레딧

* [ClearerVoice-Studio](https://github.com/modelscope/ClearerVoice-Studio), 향상 모델(Apache-2.0).
* [faster-whisper](https://github.com/SYSTRAN/faster-whisper)와 Whisper, 단어 검사용.
* [VoiceBank-DEMAND](https://doi.org/10.7488/ds/2117)(CC BY 4.0), 데모 음성과 벤치마크용.
* Microsoft의 DNSMOS P.835, `speechmos`로 실행.

MIT 라이선스입니다. [LICENSE](LICENSE)를 보세요.

Assisted by Claude/Codex.
