#!/usr/bin/env python3
"""Render short voice-test MP3s with Kokoro. Usage: voice_sample.py <episodes-src/DATE.json> <out_dir> <combo> [<combo> ...]
combo = name:lang:SU_voice:PRI_voice, e.g. hindi-a:a:hf_alpha:hm_omega (lang a = American English pronunciation, h = Hindi)."""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_episode as b
src, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
lines = json.load(open(src))["lines"][:9]
for ln in lines:
    ln["text"] = ln["text"].replace("I'm Pri", "I'm P").replace("I'm SU", "I'm S")
for combo in sys.argv[3:]:
    name, lang, su, pri = combo.split(":")
    b.CFG["kokoro"].update({"lang_code": lang, "voices": {"SU": su, "PRI": pri}})
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        wav = b.kokoro_render(lines, td)
        mp3 = os.path.join(out, f"{name}.mp3")
        subprocess.check_call(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                               "-ac", "1", "-ar", "44100", "-b:a", "64k", mp3])
        print("wrote", mp3, flush=True)
