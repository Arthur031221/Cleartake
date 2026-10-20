<h1 align="center">
  <img src="assets/logo.svg" width="72" alt=""><br>
  Cleartake
</h1>

<p align="center">
  <strong>Transforme un enregistrement bruyant en prise propre et vérifie que personne n'a vu ses mots changer.</strong>
</p>

<p align="center">
  <a href="https://github.com/Arthur031221/Cleartake/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/Arthur031221/Cleartake/ci.yml?style=flat-square&color=ffb02e&label=CI" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-ffb02e?style=flat-square" alt="MIT license"></a>
  <img src="https://img.shields.io/badge/python-3.10%20to%203.12-ffb02e?style=flat-square" alt="Python 3.10 to 3.12">
  <a href="https://arthur031221.github.io/Cleartake/"><img src="https://img.shields.io/badge/live%20demo-open-ffb02e?style=flat-square" alt="Live demo"></a>
</p>

<p align="center">
  <a href="README.md">English</a> | <a href="README.zh-TW.md">繁體中文</a> | <a href="README.zh-CN.md">简体中文</a> | <a href="README.ja.md">日本語</a> | <a href="README.ko.md">한국어</a> | <a href="README.es.md">Español</a> | Français | <a href="README.de.md">Deutsch</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

Le score DNSMOS d'arrière-plan passe de **2,98 à 4,08** et le score global de **2,59 à 3,14** sur 103 clips de test VoiceBank-DEMAND, avec le moteur studio et la seule étape d'amélioration, à 13,8 fois le temps réel sur une RTX 5090.<br>
<sub>Méthode : un clip sur 8 parmi les 824 énoncés de test, intensité 1,0, sans étape de loudness, DNSMOS P.835 via `speechmos`, GPU déjà chaud. Le taux d'erreur sur les mots ne s'est pas amélioré avec ce bruit léger. Le tableau complet et ses réserves sont dans [benchmarks/README.md](benchmarks/README.md) (en anglais).</sub>

<p align="center">
  <img src="assets/demo.gif" alt="Interface web de Cleartake : déposez un fichier, écoutez avant et après, regardez la vérification des mots" width="860">
</p>

J'ai fait Cleartake pour l'enregistrement qui est bon, sauf le souffle, le ventilateur et la pièce. Il exécute un modèle d'amélioration de la parole sur votre machine, règle le loudness sur une cible de diffusion, garde l'image de la vidéo octet pour octet, puis transcrit l'original et le résultat pour vous montrer chaque mot qui a changé. Rien n'est envoyé.

## Avant et après

Un clip du jeu de démonstration (locuteur p232 de VoiceBank-DEMAND, 28,4 secondes, 81 mots), réglages par défaut, mesuré sur les fichiers de [docs/demo](docs/demo).

|  | Original | Cleartake | Ce que ça veut dire |
| --- | --- | --- | --- |
| DNSMOS global | 2,63 | 3,33 | qualité prédite, de 1 à 5 |
| DNSMOS parole | 3,46 | 3,54 | la voix elle-même bouge à peine |
| DNSMOS fond | 2,86 | 4,14 | ce qui disparaît, c'est le bruit |
| Loudness intégré | -22,2 LUFS | -16,2 LUFS | préréglage podcast |
| Crête vraie | -4,3 dBTP | -1,6 dBTP | le plafond est à -1,5 |
| Mots modifiés | | 0 sur 81 | Whisper `base.en`, alignés mot à mot |

Je ne prétends pas qu'un débruiteur répare la parole. Cleartake retire le bruit puis audite le résultat, si bien qu'un mot modifié devient une ligne dans un rapport et non une surprise à l'antenne. [Essayez dans le navigateur](https://arthur031221.github.io/Cleartake/). La page hébergée joue ce même clip et ne traite rien.

## La chaîne de traitement

```
 decode            enhance            finish             check              write
+----------+      +----------+      +----------+      +----------+      +----------+
| any file |  ->  | speech   |  ->  | loudness |  ->  | word     |  ->  | audio or |
| to 48 kHz|      | model    |      | and peak |      | drift    |      | video    |
| mono     |      | on-device|      | target   |      | report   |      | + JSON   |
+----------+      +----------+      +----------+      +----------+      +----------+
 cleartake in.mp4  --engine studio   --preset podcast  --whisper small   -o out/ --json
```

| Ce que vous faites | Commande | Principe clé |
| --- | --- | --- |
| Nettoyer un fichier | `cleartake interview.mp4` | Le résultat se place à côté de l'entrée et l'entrée n'est jamais touchée |
| Nettoyer un dossier | `cleartake episodes/ -o cleaned/` | Un fichier défaillant n'arrête pas le lot, et les fichiers déjà nommés `.cleartake` sont ignorés |
| Garder un peu de la pièce | `cleartake talk.wav --strength 0.7` | On remélange l'original au lieu de choisir tout ou rien |
| Viser la cible d'une plateforme | `cleartake talk.wav --preset youtube` | D'abord le gain, ensuite le limiteur, et le rapport donne la mesure |
| Sauter la vérification des mots | `cleartake talk.wav --no-check` | La vérification coûte une passe Whisper, on peut donc la couper |
| Auditer dans une autre langue | `cleartake talk.wav --language de --whisper small` | Utilisez un modèle qui sait lire ce qui a été dit |
| Travailler dans le navigateur | `cleartake serve --open` | Une appli web locale avec lecteur A/B, spectrogramme et liste de mots |
| L'utiliser dans un script | `cleartake in.wav --json` | Le rapport va sur stdout et la progression sur stderr |
| Vérifier l'installation | `cleartake doctor` | Affiche ffmpeg, le périphérique et les modèles téléchargés avant d'attendre un téléchargement |

## Installation

Il faut Python 3.10 à 3.12 et ffmpeg. Cleartake n'est pas encore sur PyPI.

```bash
uv tool install git+https://github.com/Arthur031221/Cleartake
cleartake doctor
cleartake your-recording.wav
```

La première exécution télécharge le modèle choisi (environ 210 Mo pour studio, 161 Mo pour classic) et Whisper `base.en` (environ 141 Mo). Ensuite tout fonctionne hors ligne. L'environnement de l'outil pesait 6,2 Go sur ma machine parce que PyTorch embarque ses bibliothèques CUDA, et le wheel s'est installé en 75 secondes.

## Les pièces, par étape

* **Décoder.** Tout conteneur lisible par ffmpeg est accepté, et le signal interne est en 48 kHz mono flottant. Une vidéo garde son image avec `-c:v copy`. Cleartake calcule l'empreinte des paquets vidéo avant et après, et le rapport indique `picture_kept: true` seulement si elles correspondent. Seuls le premier flux vidéo et le nouvel audio sont conservés, donc les pistes audio supplémentaires et les sous-titres sont perdus.
* **Améliorer.** `studio` (par défaut) est MossFormer2_SE_48K, pleine bande à 48 kHz. `classic` est FRCRN_SE_16K et garde la parole jusqu'à 8 kHz. Ce n'est pas une option de vitesse, car sur 3 cœurs de CPU il a tourné à 0,7 fois le temps réel contre 3,2 pour studio. Les deux viennent de ClearerVoice-Studio sous licence Apache-2.0.
* **Finir.** Loudness intégré EBU R128 mesuré par `ebur128` de ffmpeg, puis gain, puis `alimiter`. Préréglages : podcast -16 LUFS, youtube -14, broadcast -23 avec un plafond de -1,0 dBTP, ou `none`.
* **Vérifier.** faster-whisper transcrit les deux versions sur le CPU, et les transcriptions sont alignées avec `difflib`. Chaque différence est listée avec son horodatage pour que vous puissiez l'écouter. L'appli web les marque sur la transcription.
* **Écrire.** L'audio sort en wav, flac, m4a ou mp3. `<output>.json` consigne le loudness avant et après, le moteur, le périphérique, la vitesse et les différences de mots. Une vidéo sort en mp4, mov ou mkv selon l'entrée, et les entrées webm, m4v et avi sortent en mkv.

## Mesuré

103 clips VoiceBank-DEMAND, DNSMOS P.835, RTX 5090. La méthode et la façon de la refaire sont dans [benchmarks/README.md](benchmarks/README.md).

| Variante | OVRL | SIG | BAK | WER par rapport à la transcription propre | Vitesse |
| --- | --- | --- | --- | --- | --- |
| noisy | 2,59 | 3,22 | 2,98 | 5,4% | n/a |
| classic | 3,17 | 3,44 | 4,06 | 5,1% | 12,7x |
| studio | 3,14 | 3,40 | 4,08 | 6,6% | 13,8x |

Autres durées : une vidéo de 76 secondes a pris 6,6 secondes de bout en bout sans la vérification des mots (11,5 fois). Un clip de 25 secondes sur 3 cœurs de CPU a pris 8,0 secondes avec studio et 35,7 secondes avec classic.

## Limites que je connais

* **Le taux d'erreur sur les mots ne s'est pas amélioré.** Avec ce bruit léger, Whisper lit déjà bien l'entrée. Studio finit 1,2 point au-dessus de l'entrée bruitée et classic 0,3 point en dessous, et sur 103 clips je ne peux pas les départager. Deux exécutions de la même commande ont varié d'environ un demi-point.
* **La vérification des mots est un endroit où écouter, pas un verdict.** Sur le benchmark elle signale environ 7% des mots comme différents, ce qui inclut des variantes d'orthographe et des mots que l'original bruité avait mal compris. Elle ne verra pas un changement que Whisper ne peut pas entendre.
* **La cible de loudness peut être manquée d'environ 0,5 LU** quand le plafond de crête vraie arrête le gain en premier.
* **Les scores de qualité sont prédits.** DNSMOS est un modèle appris, pas un test d'écoute, et je n'ai essayé que de la parole anglaise avec les types de bruit de DEMAND. La musique, la réverbération et les autres langues ne sont pas mesurées.
* **Seul Linux a été testé** (une RTX 5090 et 3 cœurs de CPU, Python 3.10 et 3.12). macOS et Windows devraient fonctionner et je ne les ai pas essayés. Il n'y a pas encore d'image Docker.
* **L'appli web ne vérifie qu'en anglais.** Elle utilise toujours Whisper `base.en`. Pour les autres langues, lancez la CLI avec `--whisper small --language de`.
* **Le mode par lot demande des noms distincts.** `-o` conserve l'arborescence, et Cleartake refuse de démarrer si deux entrées écrivaient le même fichier ou si un résultat remplaçait son entrée.
* **C'est un téléchargement de plusieurs gigaoctets** à cause de PyTorch, et la première exécution a besoin du réseau pour les modèles.

## Documentation

La documentation complète est en anglais : [Install](docs/install.md) | [Usage](docs/usage.md) | [Config](docs/config.md) | [Architecture](docs/architecture.md) | [Benchmark](benchmarks/README.md) | [Contributing](CONTRIBUTING.md) | [Changelog](CHANGELOG.md)

## Crédits

* [ClearerVoice-Studio](https://github.com/modelscope/ClearerVoice-Studio) pour les modèles d'amélioration (Apache-2.0).
* [faster-whisper](https://github.com/SYSTRAN/faster-whisper) et Whisper pour la vérification des mots.
* [VoiceBank-DEMAND](https://doi.org/10.7488/ds/2117) (CC BY 4.0) pour les clips de démonstration et le benchmark.
* DNSMOS P.835 de Microsoft, exécuté avec `speechmos`.

Licence MIT. Voir [LICENSE](LICENSE).

Assisted by Claude/Codex.
