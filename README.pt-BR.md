<h1 align="center">
  <img src="assets/logo.svg" width="72" alt=""><br>
  Cleartake
</h1>

<p align="center">
  <strong>Transforma uma gravação com ruído em uma take limpa e confere se ninguém teve as palavras alteradas.</strong>
</p>

<p align="center">
  <a href="https://github.com/Arthur031221/Cleartake/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/Arthur031221/Cleartake/ci.yml?style=flat-square&color=ffb02e&label=CI" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-ffb02e?style=flat-square" alt="MIT license"></a>
  <img src="https://img.shields.io/badge/python-3.10%20to%203.12-ffb02e?style=flat-square" alt="Python 3.10 to 3.12">
  <a href="https://arthur031221.github.io/Cleartake/"><img src="https://img.shields.io/badge/live%20demo-open-ffb02e?style=flat-square" alt="Live demo"></a>
</p>

<p align="center">
  <a href="README.md">English</a> | <a href="README.zh-TW.md">繁體中文</a> | <a href="README.zh-CN.md">简体中文</a> | <a href="README.ja.md">日本語</a> | <a href="README.ko.md">한국어</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.de.md">Deutsch</a> | Português (BR)
</p>

<p align="center">
  <img src="assets/demo.gif" alt="Interface web do Cleartake: solte um arquivo, ouça antes e depois, veja a verificação de palavras" width="860">
</p>

Fiz o Cleartake para aquela gravação que é boa, exceto pelo chiado, pelo ventilador e pela sala. Ele roda um modelo de melhoria de fala na sua máquina, ajusta o loudness para uma meta de transmissão, mantém a imagem do vídeo byte a byte e depois transcreve o original e o resultado para mostrar qualquer palavra que mudou. Nada é enviado.

```bash
uv tool install git+https://github.com/Arthur031221/Cleartake
cleartake serve --open
```

A nota DNSMOS de fundo sobe de **2,98 para 4,08** e a geral de **2,59 para 3,14** em 103 clipes de teste do VoiceBank-DEMAND, com o motor studio e só a etapa de melhoria, a 13,8 vezes o tempo real em uma RTX 5090.<br>
<sub>Método: um a cada 8 dos 824 enunciados de teste, intensidade 1,0, sem etapa de loudness, DNSMOS P.835 via `speechmos`, GPU já aquecida. A taxa de erro de palavras não melhorou com esse ruído leve. A tabela completa e suas ressalvas estão em [benchmarks/README.md](benchmarks/README.md) (em inglês).</sub>

## Antes e depois

Um clipe do conjunto de demonstração (locutor p232 do VoiceBank-DEMAND, 28,4 segundos, 81 palavras), configuração padrão, medido nos arquivos de [docs/demo](docs/demo).

|  | Original | Cleartake | O que significa |
| --- | --- | --- | --- |
| DNSMOS geral | 2,63 | 3,33 | qualidade prevista, de 1 a 5 |
| DNSMOS fala | 3,46 | 3,54 | a voz em si quase não muda |
| DNSMOS fundo | 2,86 | 4,14 | o que some é o ruído |
| Loudness integrado | -22,2 LUFS | -16,2 LUFS | predefinição podcast |
| Pico real | -4,3 dBTP | -1,6 dBTP | o teto é -1,5 |
| Palavras alteradas | | 0 de 81 | Whisper `base.en`, alinhadas palavra por palavra |

Não digo que um redutor de ruído conserta a fala. O Cleartake remove o ruído e depois audita o resultado, de modo que uma palavra alterada vira uma linha no relatório e não uma surpresa no ar. [Experimente no navegador](https://arthur031221.github.io/Cleartake/). A página hospedada toca esse mesmo clipe e não processa nada.

## O pipeline

```
 decode            enhance            finish             check              write
+----------+      +----------+      +----------+      +----------+      +----------+
| any file |  ->  | speech   |  ->  | loudness |  ->  | word     |  ->  | audio or |
| to 48 kHz|      | model    |      | and peak |      | drift    |      | video    |
| mono     |      | on-device|      | target   |      | report   |      | + JSON   |
+----------+      +----------+      +----------+      +----------+      +----------+
 cleartake in.mp4  --engine studio   --preset podcast  --whisper small   -o out/ --json
```

| O que você faz | Comando | Princípio-chave |
| --- | --- | --- |
| Limpar um arquivo | `cleartake interview.mp4` | O resultado fica ao lado da entrada e a entrada nunca é tocada |
| Limpar uma pasta | `cleartake episodes/ -o cleaned/` | Um arquivo com defeito não para o lote, e arquivos que já se chamam `.cleartake` são ignorados |
| Manter um pouco da sala | `cleartake talk.wav --strength 0.7` | Mistura-se o original de volta em vez de escolher tudo ou nada |
| Atingir a meta de uma plataforma | `cleartake talk.wav --preset youtube` | Primeiro ganho, depois limitador, e o relatório mostra o valor medido |
| Pular a verificação de palavras | `cleartake talk.wav --no-check` | A verificação custa uma passada do Whisper, então dá para desligar |
| Auditar em outro idioma | `cleartake talk.wav --language de --whisper small` | Use um modelo que saiba ler o que foi dito |
| Trabalhar no navegador | `cleartake serve --open` | Um app web local: solte vários arquivos, cancele qualquer um e compare com um player A/B, um espectrograma e a lista de palavras |
| Usar em script | `cleartake in.wav --json` | O relatório vai para stdout e o progresso para stderr |
| Conferir a instalação | `cleartake doctor` | Mostra ffmpeg, o dispositivo e os modelos baixados antes de você esperar um download |

## Instalação

Você precisa de Python 3.10 a 3.12 e ffmpeg. O Cleartake ainda não está no PyPI.

```bash
uv tool install git+https://github.com/Arthur031221/Cleartake
cleartake doctor
cleartake your-recording.wav
```

A primeira execução baixa o modelo escolhido (cerca de 210 MB para studio, 161 MB para classic) e o Whisper `base.en` (cerca de 141 MB). Depois disso tudo roda offline. O ambiente da ferramenta tinha 6,2 GB na minha máquina porque o PyTorch traz suas bibliotecas CUDA, e o wheel foi instalado em 75 segundos.

## Peças, por etapa

* **Decodificar.** Qualquer contêiner que o ffmpeg leia entra, e o sinal interno é 48 kHz mono em ponto flutuante. Um vídeo mantém a imagem com `-c:v copy`. O Cleartake calcula o hash dos pacotes de vídeo antes e depois, e o relatório diz `picture_kept: true` só quando os hashes batem. Só o primeiro fluxo de vídeo e o áudio novo são mantidos, então faixas de áudio extras e legendas se perdem.
* **Melhorar.** `studio` (padrão) é o MossFormer2_SE_48K, banda cheia em 48 kHz. `classic` é o FRCRN_SE_16K e mantém a fala até 8 kHz. Não é uma opção de velocidade, porque em 3 núcleos de CPU rodou a 0,7 vez o tempo real contra 3,2 do studio. Ambos vêm do ClearerVoice-Studio sob Apache-2.0.
* **Finalizar.** Loudness integrado EBU R128 medido pelo `ebur128` do ffmpeg, depois ganho, depois `alimiter`. Predefinições: podcast -16 LUFS, youtube -14, broadcast -23 com teto de -1,0 dBTP, ou `none`.
* **Verificar.** O faster-whisper transcreve as duas versões na CPU, e as transcrições são alinhadas com `difflib`. Cada diferença é listada com o tempo para você poder ouvir. O app web as marca na transcrição.
* **Gravar.** O áudio sai em wav, flac, m4a ou mp3. `<output>.json` registra o loudness antes e depois, o motor, o dispositivo, a velocidade e as diferenças de palavras. Um vídeo sai como mp4, mov ou mkv conforme a entrada, e entradas webm, m4v e avi saem como mkv.

## Medido

103 clipes do VoiceBank-DEMAND, DNSMOS P.835, RTX 5090. O método e como repetir estão em [benchmarks/README.md](benchmarks/README.md).

| Variante | OVRL | SIG | BAK | WER contra a transcrição limpa | Velocidade |
| --- | --- | --- | --- | --- | --- |
| noisy | 2,59 | 3,22 | 2,98 | 5,4% | n/a |
| classic | 3,17 | 3,44 | 4,06 | 5,1% | 12,7x |
| studio | 3,14 | 3,40 | 4,08 | 6,6% | 13,8x |

Outros tempos: um vídeo de 76 segundos levou 6,6 segundos de ponta a ponta sem a verificação de palavras (11,5 vezes). Um clipe de 25 segundos em 3 núcleos de CPU levou 8,0 segundos com studio e 35,7 com classic.

## Limites que conheço

* **A taxa de erro de palavras não melhorou.** Com esse ruído leve o Whisper já lê bem a entrada. O studio ficou 1,2 ponto acima da entrada com ruído e o classic 0,3 ponto abaixo, e com 103 clipes não consigo distinguir os dois. Duas execuções do mesmo comando variaram cerca de meio ponto.
* **A verificação de palavras é um lugar para ouvir, não um veredito.** No benchmark ela marca cerca de 7% das palavras como diferentes, incluindo variantes de grafia e palavras que o original com ruído entendeu errado. Ela não pega uma mudança que o Whisper não consegue ouvir.
* **A meta de loudness pode ser perdida em cerca de 0,5 LU** quando o teto de pico real para o ganho primeiro.
* **As notas de qualidade são previstas.** O DNSMOS é um modelo treinado, não um teste de audição, e só rodei fala em inglês com os tipos de ruído do DEMAND. Música, reverberação e outros idiomas não foram medidos.
* **Só foi testado no Linux** (uma RTX 5090 e 3 núcleos de CPU, Python 3.10 e 3.12). macOS e Windows devem funcionar e não os executei. Ainda não há imagem Docker.
* **O app web só verifica em inglês.** Ele sempre usa o Whisper `base.en`. Para outros idiomas, use a CLI com `--whisper small --language de`.
* **O modo em lote precisa de nomes distintos.** `-o` mantém a estrutura de pastas, e o Cleartake se recusa a começar se duas entradas escreveriam o mesmo arquivo ou se um resultado substituísse a entrada.
* **É um download de vários gigabytes** por causa do PyTorch, e a primeira execução precisa de rede para os modelos.

## Documentação

A documentação completa está em inglês: [Install](docs/install.md) | [Usage](docs/usage.md) | [Config](docs/config.md) | [Architecture](docs/architecture.md) | [Benchmark](benchmarks/README.md) | [Contributing](CONTRIBUTING.md) | [Changelog](CHANGELOG.md)

## Créditos

* [ClearerVoice-Studio](https://github.com/modelscope/ClearerVoice-Studio) pelos modelos de melhoria (Apache-2.0).
* [faster-whisper](https://github.com/SYSTRAN/faster-whisper) e Whisper para a verificação de palavras.
* [VoiceBank-DEMAND](https://doi.org/10.7488/ds/2117) (CC BY 4.0) pelos clipes de demonstração e pelo benchmark.
* DNSMOS P.835 da Microsoft, executado com `speechmos`.

Licença MIT. Veja [LICENSE](LICENSE).

Assisted by Claude/Codex.
