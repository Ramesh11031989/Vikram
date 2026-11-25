# Local instrumental score

Chapter 1 uses **ACE-Step 1.5 Turbo 2B, Q4_K_M** through the native `acestep.cpp` runtime. The workstation has an i5-10300H, 16 GB of RAM and a GTX 1650 with 4 GB of VRAM. The generator uses the diffusion model directly with an instrumental cue, a Q8 text encoder and the VAE. The three local files total 2.57 GB. The original model and this GGUF release are published under MIT. [ACE-Step model card](https://huggingface.co/ACE-Step/Ace-Step1.5) · [Native runtime](https://github.com/ServeurpersoCom/acestep.cpp/tree/973517b) · [GGUF files](https://huggingface.co/Serveurperso/ACE-Step-1.5-GGUF/tree/main)

| Model considered | Fit for the film |
| --- | --- |
| ACE-Step Turbo 2B GGUF | Native Windows Vulkan and CPU backends, instrumental prompts and stereo 48 kHz output for multi-phrase underscore. [Runtime](https://github.com/ServeurpersoCom/acestep.cpp) |
| Stable Audio 3.0 Small-Music and Small-SFX | CPU inference and up to 120 seconds. The separate SFX model is useful for sound design. Self-hosting is governed by the Stability AI Community License. [Runtime comparison](https://stability.ai/explainers/self-hosted-vs-api-generative-audio-choosing-a-deployment-model) · [License terms](https://kb.stability.ai/knowledge-base/stable-audio-commerical-and-usage-licensing) |
| MusicGen Small and its Indian-classical derivatives | The 300M base is compact. Its weights are marked CC BY-NC 4.0, and the Indian-classical fine-tune builds on that base. [MusicGen model card](https://huggingface.co/facebook/musicgen-small) · [Indian-classical fine-tune](https://github.com/Tanishq-Soni77/musicgen-indian-classical) |
| DiffRhythm 2 | The project lists instrumental music generation as pending. The published inference example uses lyrics and a reference WAV. [Upstream repository](https://github.com/xiaomi-research/diffrhythm2) |

## Generate a cue

The cue sheet has three starting points. `river_mystery` uses bansuri and tanpura for the night river, `royal_court` uses a restrained sarangi motif, and `quiet_refuge` uses a warm drone and sparse tabla. Edit the captions and seeds in [Music_Cues.json](Music_Cues.json) to audition variants. The script requests an instrumental and writes a stereo 48 kHz, 16-bit WAV into `Renders/Audio/Music/` by default. Cue lengths describe the music sketch, so an editor can place and trim approved takes against picture and dialogue in Unity.

```powershell
$python = 'D:\Tools\Blender\blender-5.2.2-windows-x64\5.2\python\bin\python.exe'
& $python Production/tools/generate_music.py --list
& $python Production/tools/generate_music.py river_mystery --dry-run
& $python Production/tools/generate_music.py river_mystery --device CPU
```

Use `--seed` to make another take. The script defaults to the CPU backend. On this workstation the runtime enumerates the GTX 1650 as `Vulkan1`. To reuse the workflow for a later episode, put its cue sheet at `Production/E02/Audio/Music/Music_Cues.json` and run with `--episode E02`.

## First audition

[River at night](Review/E01_river_mystery_15s_4516.wav) is the first take from the `river_mystery` cue at seed `4516`. The engine wrote 15.04 seconds of stereo, 48 kHz, 16-bit audio. The first CPU run took about 9½ minutes, including weight loading. This is the raw model output for a listening review before placement and mixing against dialogue.

[Royal court](Review/E01_royal_court_18s_4517.wav) is the `royal_court` cue at seed `4517`. The same model wrote the full 18-second stereo WAV using `--device Vulkan1` on the GTX 1650. Both cues are used in the Unity testimony cut, with score ducking during dialogue.

## Runtime files

The default runtime directory is `Renders/Tools/ACE-Step.cpp`. The three model files belong in its `models` folder. The `ace-synth.exe` and GGML DLLs belong in the same directory under `build/Release`. The Python wrapper uses the command-line synthesizer directly and generates locally after the one-time download. The weights have public download links. [Upstream Windows binaries](https://www.serveurperso.com/temp/acestep.cpp-win64/build/Release/) · [CLI source](https://github.com/ServeurpersoCom/acestep.cpp/blob/973517be024ff8b6bbd50e0adc9e308ab2ed71b3/tools/ace-synth.cpp)

| Filename | Bytes |
| --- | ---: |
| `acestep-v15-turbo-Q4_K_M.gguf` | 1,445,710,272 |
| `Qwen3-Embedding-0.6B-Q8_0.gguf` | 784,144,960 |
| `vae-BF16.gguf` | 337,420,928 |
