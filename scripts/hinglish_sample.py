#!/usr/bin/env python3
"""Render Hinglish test clips with Kokoro's Hindi voices. Usage: hinglish_sample.py <samples-src/x.json> <out_dir>"""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_episode as b
src, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
b.spoken_kokoro = lambda t: b.re.sub(r"(\d),(?=\d{3}\b)", r"\1", b.speakable(t))  # keep Hindi text as written
for name, v in json.load(open(src))["variants"].items():
    b.CFG["kokoro"].update({"lang_code": v["lang"], "voices": v["voices"]})
    with tempfile.TemporaryDirectory() as td:
        wav = b.kokoro_render(v["lines"], td)
        mp3 = os.path.join(out, name + ".mp3")
        subprocess.check_call(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                               "-ac", "1", "-ar", "44100", "-b:a", "64k", mp3])
        print("wrote", mp3, flush=True)
