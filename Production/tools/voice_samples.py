"""Render short Hindi sample clips for several characters with Indic Parler-TTS.

Run from the repository root (needs Production/requirements-voice.txt):

    python Production/tools/voice_samples.py

Clips are written to Production/Voice_Samples/ as mono WAV files. Edit SAMPLES to
try other voices or lines; speaker names and descriptions follow the model card.
"""

from __future__ import annotations

from pathlib import Path
import sys
import wave

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Production' / 'Voice_Samples'
MODEL_ID = 'ai4bharat/indic-parler-tts'
QUALITY = ('Very clear, close-up studio recording with no background noise.')

# (file stem, speaker name, seed, Hindi line, voice description)
SAMPLES = (
    ('Vikram', 'Aman', 11, 'मुंशीजी, लाल कपड़ा, चौकी का दीया और देखने की जगह लिखिए।',
     'Aman speaks in Hindi with a deep, calm, authoritative male voice at a slow, measured pace. ' + QUALITY),
    ('Gopal', 'Rohit', 23, 'महाराज, मुझे लगा मैं जानता हूँ वहाँ कौन था।',
     "Rohit speaks in Hindi with a slightly higher, tired, older working man's voice at a moderate "
     'pace with some hesitation. ' + QUALITY),
    ('Betal', 'Rohit', 41, 'राजन, सच सुनना आसान है, पर उसे मान लेना बहुत कठिन होता है।',
     'Rohit speaks in Hindi with a low, raspy, sly, mysterious male voice, slowly and with long '
     'dramatic pauses. ' + QUALITY),
    ('Rani', 'Divya', 7, 'यह बात मैंने अपनी आँखों से देखी है, महाराज।',
     'Divya speaks in Hindi with a warm, gentle, confident female voice at a moderate pace. ' + QUALITY),
    ('Bachchi', 'Divya', 5, 'चाचा, देखो, मेरा हाथ पानी को छू रहा है!',
     'Divya speaks in Hindi with a high-pitched, bright, excited young girl\'s voice at a fast pace. ' + QUALITY),
)


def main() -> int:
    import numpy as np
    import torch
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer

    cuda = torch.cuda.is_available()
    device = 'cuda' if cuda else 'cpu'
    dtype = torch.float16 if cuda else torch.float32  # fp16 lets the 3.8 GB model fit small GPUs
    model = ParlerTTSForConditionalGeneration.from_pretrained(MODEL_ID, torch_dtype=dtype).to(device)
    prompt_tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    description_tokenizer = AutoTokenizer.from_pretrained(model.config.text_encoder._name_or_path)
    print(f'Loaded {MODEL_ID} on {device} ({dtype})', flush=True)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    for stem, speaker, seed, text, description in SAMPLES:
        torch.manual_seed(seed)
        described = description_tokenizer(description, return_tensors='pt').to(device)
        prompt = prompt_tokenizer(text, return_tensors='pt').to(device)
        with torch.no_grad():
            generation = model.generate(
                input_ids=described.input_ids, attention_mask=described.attention_mask,
                prompt_input_ids=prompt.input_ids, prompt_attention_mask=prompt.attention_mask)
        audio = generation.float().cpu().numpy().squeeze()
        peak = float(np.max(np.abs(audio))) or 1.0
        pcm = (audio / max(peak, 1.0) * 32767 * 0.9).astype('<i2')
        target = OUTPUT / f'{stem}_{speaker}.wav'
        with wave.open(str(target), 'wb') as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(int(model.config.sampling_rate))
            stream.writeframes(pcm.tobytes())
        print(f'{target.name}: {len(pcm) / model.config.sampling_rate:.2f}s', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
