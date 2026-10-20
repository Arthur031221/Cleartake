<h1 align="center">
  <img src="assets/logo.svg" width="72" alt=""><br>
  Cleartake
</h1>

<p align="center">
  <strong>Convierte una grabación ruidosa en una toma limpia y comprueba que nadie haya cambiado sus palabras.</strong>
</p>

<p align="center">
  <a href="https://github.com/Arthur031221/Cleartake/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/Arthur031221/Cleartake/ci.yml?style=flat-square&color=ffb02e&label=CI" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-ffb02e?style=flat-square" alt="MIT license"></a>
  <img src="https://img.shields.io/badge/python-3.10%20to%203.12-ffb02e?style=flat-square" alt="Python 3.10 to 3.12">
  <a href="https://arthur031221.github.io/Cleartake/"><img src="https://img.shields.io/badge/live%20demo-open-ffb02e?style=flat-square" alt="Live demo"></a>
</p>

<p align="center">
  <a href="README.md">English</a> | <a href="README.zh-TW.md">繁體中文</a> | <a href="README.zh-CN.md">简体中文</a> | <a href="README.ja.md">日本語</a> | <a href="README.ko.md">한국어</a> | Español | <a href="README.fr.md">Français</a> | <a href="README.de.md">Deutsch</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="assets/demo.gif" alt="Interfaz web de Cleartake: suelta un archivo, escucha antes y después, mira la comprobación de palabras" width="860">
</p>

Hice Cleartake para esa grabación que está bien salvo por el siseo, el ventilador y la sala. Ejecuta un modelo de mejora de voz en tu máquina, ajusta la sonoridad a un objetivo de emisión, conserva la imagen del vídeo byte por byte y luego transcribe el original y el resultado para mostrarte cualquier palabra que haya cambiado. No se sube nada.

```bash
uv tool install git+https://github.com/Arthur031221/Cleartake
cleartake serve --open
```

La puntuación DNSMOS de fondo sube de **2,98 a 4,08** y la general de **2,59 a 3,14** en 103 clips de prueba de VoiceBank-DEMAND, con el motor studio y solo la etapa de mejora, a 13,8 veces el tiempo real en una RTX 5090.<br>
<sub>Método: uno de cada 8 de los 824 enunciados de prueba, intensidad 1,0, sin ajuste de sonoridad, DNSMOS P.835 con `speechmos`, GPU ya calentada. El error de palabras no mejoró con este ruido leve. La tabla completa y sus salvedades están en [benchmarks/README.md](benchmarks/README.md) (en inglés).</sub>

## Antes y después

Un clip del conjunto de demostración (hablante p232 de VoiceBank-DEMAND, 28,4 segundos, 81 palabras), con la configuración por defecto, medido sobre los archivos de [docs/demo](docs/demo).

|  | Original | Cleartake | Qué significa |
| --- | --- | --- | --- |
| DNSMOS general | 2,63 | 3,33 | calidad prevista, de 1 a 5 |
| DNSMOS voz | 3,46 | 3,54 | la voz casi no cambia |
| DNSMOS fondo | 2,86 | 4,14 | lo que desaparece es el ruido |
| Sonoridad integrada | -22,2 LUFS | -16,2 LUFS | preajuste podcast |
| Pico real | -4,3 dBTP | -1,6 dBTP | el techo es -1,5 |
| Palabras cambiadas | | 0 de 81 | Whisper `base.en`, alineadas palabra por palabra |

No digo que un reductor de ruido arregle la voz. Cleartake quita el ruido y después audita el resultado, de modo que una palabra cambiada es una línea en un informe y no una sorpresa en antena. [Pruébalo en el navegador](https://arthur031221.github.io/Cleartake/). La página alojada reproduce este mismo clip y no ejecuta nada.

## La cadena de proceso

```
 decode            enhance            finish             check              write
+----------+      +----------+      +----------+      +----------+      +----------+
| any file |  ->  | speech   |  ->  | loudness |  ->  | word     |  ->  | audio or |
| to 48 kHz|      | model    |      | and peak |      | drift    |      | video    |
| mono     |      | on-device|      | target   |      | report   |      | + JSON   |
+----------+      +----------+      +----------+      +----------+      +----------+
 cleartake in.mp4  --engine studio   --preset podcast  --whisper small   -o out/ --json
```

| Lo que haces | Comando | Principio clave |
| --- | --- | --- |
| Limpiar un archivo | `cleartake interview.mp4` | El resultado queda junto a la entrada y la entrada no se toca |
| Limpiar una carpeta | `cleartake episodes/ -o cleaned/` | Un archivo roto no detiene el lote y se omiten los archivos que ya se llaman `.cleartake` |
| Conservar algo de sala | `cleartake talk.wav --strength 0.7` | Se mezcla de nuevo el original en vez de elegir todo o nada |
| Cumplir el objetivo de una plataforma | `cleartake talk.wav --preset youtube` | Primero ganancia, luego limitador, y el informe muestra lo medido |
| Saltar la comprobación de palabras | `cleartake talk.wav --no-check` | La comprobación cuesta una pasada de Whisper, así que se puede apagar |
| Auditar en otro idioma | `cleartake talk.wav --language de --whisper small` | Usa un modelo que sepa leer lo que se dijo |
| Trabajar en el navegador | `cleartake serve --open` | Una app web local: suelta varios archivos, cancela cualquiera y compara con un reproductor A/B, un espectrograma y la lista de palabras |
| Usarlo en un script | `cleartake in.wav --json` | El informe va a stdout y el progreso a stderr |
| Revisar la instalación | `cleartake doctor` | Muestra ffmpeg, el dispositivo y los modelos descargados antes de esperar una descarga |

## Instalación

Necesitas Python 3.10 a 3.12 y ffmpeg. Cleartake todavía no está en PyPI.

```bash
uv tool install git+https://github.com/Arthur031221/Cleartake
cleartake doctor
cleartake your-recording.wav
```

La primera ejecución descarga el modelo que elijas (unos 210 MB para studio, 161 MB para classic) y Whisper `base.en` (unos 141 MB). Después funciona sin conexión. El entorno de la herramienta ocupó 6,2 GB en mi máquina porque PyTorch incluye sus bibliotecas CUDA, y el wheel se instaló en 75 segundos.

## Piezas, por etapa

* **Decodificar.** Entra cualquier contenedor que ffmpeg lea, y la señal interna es de 48 kHz mono en coma flotante. Un vídeo conserva su imagen con `-c:v copy`. Cleartake calcula el hash de los paquetes de vídeo antes y después, y el informe dice `picture_kept: true` solo si coinciden. Solo se conservan la primera pista de vídeo y el audio nuevo, así que las pistas de audio adicionales y los subtítulos se pierden.
* **Mejorar.** `studio` (por defecto) es MossFormer2_SE_48K, banda completa a 48 kHz. `classic` es FRCRN_SE_16K y conserva la voz hasta 8 kHz. No es una opción de velocidad, porque en 3 núcleos de CPU fue a 0,7 veces el tiempo real frente a 3,2 de studio. Ambos vienen de ClearerVoice-Studio con licencia Apache-2.0.
* **Acabar.** Sonoridad integrada EBU R128 medida con `ebur128` de ffmpeg, luego ganancia y luego `alimiter`. Preajustes: podcast -16 LUFS, youtube -14, broadcast -23 con techo de -1,0 dBTP, o `none`.
* **Comprobar.** faster-whisper transcribe las dos versiones en la CPU y las transcripciones se alinean con `difflib`. Cada diferencia sale con su marca de tiempo para que la escuches. La app web las marca en la transcripción.
* **Escribir.** El audio sale como wav, flac, m4a o mp3. `<output>.json` guarda la sonoridad antes y después, el motor, el dispositivo, la velocidad y las diferencias de palabras. Un vídeo sale como mp4, mov o mkv según la entrada, y las entradas webm, m4v y avi salen como mkv.

## Medido

103 clips de VoiceBank-DEMAND, DNSMOS P.835, RTX 5090. El método y cómo repetirlo están en [benchmarks/README.md](benchmarks/README.md).

| Variante | OVRL | SIG | BAK | WER frente a la transcripción limpia | Velocidad |
| --- | --- | --- | --- | --- | --- |
| noisy | 2,59 | 3,22 | 2,98 | 5,4% | n/a |
| classic | 3,17 | 3,44 | 4,06 | 5,1% | 12,7x |
| studio | 3,14 | 3,40 | 4,08 | 6,6% | 13,8x |

Otros tiempos: un vídeo de 76 segundos tardó 6,6 segundos de principio a fin sin la comprobación de palabras (11,5 veces). Un clip de 25 segundos en 3 núcleos de CPU tardó 8,0 segundos con studio y 35,7 con classic.

## Límites que conozco

* **El error de palabras no mejoró.** Con este ruido leve Whisper ya lee bien la entrada. Studio quedó 1,2 puntos por encima de la entrada ruidosa y classic 0,3 puntos por debajo, y con 103 clips no puedo distinguir uno de otro. Dos ejecuciones del mismo comando variaron en torno a medio punto.
* **La comprobación de palabras es un lugar donde escuchar, no un veredicto.** En el benchmark marca alrededor del 7% de las palabras como distintas, e incluye variantes de ortografía y palabras que el original ruidoso entendió mal. No detectará un cambio que Whisper no pueda oír.
* **El objetivo de sonoridad puede fallar en unos 0,5 LU** cuando el techo de pico real detiene antes la ganancia.
* **Las puntuaciones de calidad son predicciones.** DNSMOS es un modelo aprendido, no una prueba de escucha, y solo probé voz en inglés con los tipos de ruido de DEMAND. No medí música, reverberación ni otros idiomas.
* **Los modelos reales solo se ejecutaron en Linux** (una RTX 5090 y 3 núcleos de CPU, Python 3.10 y 3.12). Las pruebas sin navegador también pasan en la CI en macOS (Apple silicon) y Windows, allí con un sustituto de los modelos. Todavía no hay imagen de Docker.
* **La comprobación de palabras de la app web en otros idiomas no está probada.** El inglés usa Whisper `base.en`. Cualquier otro idioma que elijas en la tarjeta de ajustes, o la detección automática, usa Whisper `small` (unos 460 MB, descargado una vez). No he medido su precisión por idioma.
* **El modo por lotes necesita nombres distintos.** `-o` conserva la estructura de carpetas, y Cleartake se niega a empezar si dos entradas escribirían el mismo archivo o si un resultado sustituyera a su entrada.
* **Es una descarga de varios gigabytes** por PyTorch, y la primera ejecución necesita red para los modelos.

## Documentación

La documentación completa está en inglés: [Install](docs/install.md) | [Usage](docs/usage.md) | [Config](docs/config.md) | [Architecture](docs/architecture.md) | [Benchmark](benchmarks/README.md) | [Contributing](CONTRIBUTING.md) | [Changelog](CHANGELOG.md)

## Créditos

* [ClearerVoice-Studio](https://github.com/modelscope/ClearerVoice-Studio) para los modelos de mejora (Apache-2.0).
* [faster-whisper](https://github.com/SYSTRAN/faster-whisper) y Whisper para la comprobación de palabras.
* [VoiceBank-DEMAND](https://doi.org/10.7488/ds/2117) (CC BY 4.0) para los clips de demostración y el benchmark.
* DNSMOS P.835 de Microsoft, ejecutado con `speechmos`.

Licencia MIT. Mira [LICENSE](LICENSE).

Assisted by Claude/Codex.
