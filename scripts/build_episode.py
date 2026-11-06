#!/usr/bin/env python3
"""Ripple Daily: episodes-src/<date>.json -> episodes/<date>.mp3 + feed.xml.
Needs env ELEVENLABS_API_KEY and ffmpeg. Usage: build_episode.py <episodes-src/DATE.json>"""
import json, os, re, subprocess, sys, tempfile, time, urllib.request, urllib.error, urllib.parse, datetime as dt
from email.utils import format_datetime
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "config.json")))
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

def speakable(t):
    t = re.sub(r"₹\s?([\d,.]+)\s*(lakh crore|crore|lakh)?", lambda m: f"{m.group(1)} {m.group(2) or ''} rupees".replace("  ", " "), t)
    t = t.replace("$", "")  # "$9 billion" is written as "9 billion dollars" by the script writer; strip strays
    return re.sub(r"\s+", " ", t).strip()

def chunks(lines, limit):
    cur, n = [], 0
    for ln in lines:
        L = len(ln["text"])
        if cur and n + L > limit:
            yield cur; cur, n = [], 0
        cur.append(ln); n += L
    if cur: yield cur

def api(path, body=None):
    req = urllib.request.Request("https://api.elevenlabs.io" + path, method="POST" if body is not None else "GET",
          data=json.dumps(body).encode() if body is not None else None,
          headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def ensure_voice(k):
    """Library voices must be in the account's My Voices before the API can use them; add them if missing."""
    vid = CFG["voices"][k]
    try:
        api(f"/v1/voices/{vid}"); return
    except urllib.error.HTTPError as e:
        if e.code not in (400, 404): sys.exit(f"ElevenLabs {e.code} checking voice {k}: {e.read().decode(errors='replace')[:300]}")
    name = CFG.get("voice_names", {}).get(k, k)
    q = urllib.parse.quote(name.split(" - ")[0])
    found = [v for v in api(f"/v1/shared-voices?page_size=100&search={q}").get("voices", []) if v["voice_id"] == vid]
    if not found: sys.exit(f"voice {k} ({vid}) not in your ElevenLabs voices or the public library")
    r = api(f"/v1/voices/add/{found[0]['public_owner_id']}/{vid}", {"new_name": name})
    CFG["voices"][k] = r.get("voice_id") or vid
    print(f"added library voice {name} for {k}", flush=True)

def spoken_kokoro(t):
    t = speakable(t)
    t = re.sub(r"(\d)\s?%", r"\1 percent", t)
    t = t.replace("S&P", "S and P").replace("&", " and ")
    t = re.sub(r"(\d),(?=\d{3}\b)", r"\1", t)  # 23,960.60 -> 23960.60 so the number reads as one
    return re.sub(r"\s+", " ", t).strip()

def kokoro_render(lines, td):
    """Free, open-source voices (Kokoro-82M, Apache 2.0), rendered on the build machine's CPU."""
    import numpy as np, soundfile as sf
    from kokoro import KPipeline
    k = CFG["kokoro"]; sr = 24000
    pipe = KPipeline(lang_code=k["lang_code"])
    pieces, prev = [], None
    for i, ln in enumerate(lines):
        if prev is not None:
            gap = k["pause_switch"] if ln["speaker"] != prev else k["pause_same"]
            pieces.append(np.zeros(int(sr * gap), dtype=np.float32))
        for _, _, audio in pipe(spoken_kokoro(ln["text"]), voice=k["voices"][ln["speaker"]], speed=k["speed"]):
            a = audio.numpy() if hasattr(audio, "numpy") else np.asarray(audio)
            pieces.append(a.astype(np.float32))
        prev = ln["speaker"]
        if i % 10 == 0: print(f"line {i}/{len(lines)}", flush=True)
    p = os.path.join(td, "kokoro.wav")
    sf.write(p, np.concatenate(pieces), sr)
    print(f"kokoro: {len(lines)} lines, {dur(p):.1f}s", flush=True)
    return p

def tts(chunk, prev_ids):
    t = CFG["tts"]
    body = {"inputs": [{"text": speakable(l["text"]), "voice_id": CFG["voices"][l["speaker"]]} for l in chunk],
            "model_id": t["model_id"], "seed": t["seed"]}
    if t.get("language_code"): body["language_code"] = t["language_code"]
    if prev_ids: body["previous_request_ids"] = prev_ids[-3:]
    url = f"https://api.elevenlabs.io/v1/text-to-dialogue?output_format={t['output_format']}"
    for attempt in range(4):
        req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
              headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read(), r.headers.get("request-id")
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:500]
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(20 * (attempt + 1)); continue
            sys.exit(f"ElevenLabs {e.code}: {msg}")

def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).decode())

def build_feed():
    s = CFG["show"]; base = s["base_url"]
    idx_p = os.path.join(ROOT, "episodes", "index.json")
    eps = json.load(open(idx_p)) if os.path.exists(idx_p) else []
    cutoff = (dt.datetime.now(IST).date() - dt.timedelta(days=s["keep_days"])).isoformat()
    keep = [e for e in eps if e["date"] >= cutoff]
    for e in eps:
        if e["date"] < cutoff:
            p = os.path.join(ROOT, "episodes", e["file"])
            if os.path.exists(p): os.remove(p)
    json.dump(keep, open(idx_p, "w"), indent=1)
    items = []
    for e in sorted(keep, key=lambda x: x["date"], reverse=True):
        items.append(f"""  <item>
    <title>{escape(e['title'])}</title>
    <description>{escape(e['description'])}</description>
    <enclosure url="{base}episodes/{e['file']}" length="{e['bytes']}" type="audio/mpeg"/>
    <guid isPermaLink="false">ripple-daily-{e['date']}</guid>
    <pubDate>{e['pubDate']}</pubDate>
    <itunes:duration>{e['seconds']}</itunes:duration>
    <itunes:episode>{e['episode']}</itunes:episode>
    <itunes:episodeType>full</itunes:episodeType>
    <itunes:image href="{base}{s['cover']}"/>
    <itunes:explicit>{s['explicit']}</itunes:explicit>
  </item>""")
    owner = f"\n    <itunes:email>{escape(s['owner_email'])}</itunes:email>" if s.get("owner_email") else ""
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:podcast="https://podcastindex.org/namespace/1.0">
<channel>
  <title>{escape(s['title'])}</title>
  <link>{s['site_url']}</link>
  <atom:link href="{base}feed.xml" rel="self" type="application/rss+xml"/>
  <language>{s['language']}</language>
  <description>{escape(s['description'])}</description>
  <itunes:subtitle>{escape(s['subtitle'])}</itunes:subtitle>
  <itunes:summary>{escape(s['description'])}</itunes:summary>
  <itunes:author>{escape(s['author'])}</itunes:author>
  <itunes:owner>
    <itunes:name>{escape(s['owner_name'])}</itunes:name>{owner}
  </itunes:owner>
  <itunes:image href="{base}{s['cover']}"/>
  <image><url>{base}{s['cover']}</url><title>{escape(s['title'])}</title><link>{s['site_url']}</link></image>
  <itunes:category text="{s['category']}"><itunes:category text="{s['subcategory']}"/></itunes:category>
  <itunes:explicit>{s['explicit']}</itunes:explicit>
  <itunes:type>episodic</itunes:type>
  <podcast:locked>no</podcast:locked>
{chr(10).join(items)}
</channel>
</rss>
"""
    open(os.path.join(ROOT, "feed.xml"), "w").write(feed)

def main(src):
    ep = json.load(open(src)); date = ep["date"]
    # Keep show notes honest and numbering stable whatever the script writer put in.
    note = ("Voices are AI-generated with open-source Kokoro voices." if CFG["tts"].get("engine") == "kokoro"
            else "Voices are AI-generated (ElevenLabs library voices Hope and Mark).")
    ep["description"] = re.sub(r"Voices are AI-generated[^.]*\.", note, ep["description"])
    srcs = sorted(f[:-5] for f in os.listdir(os.path.join(ROOT, "episodes-src")) if f.endswith(".json"))
    if date in srcs: ep["episode"] = srcs.index(date) + 1
    # On-air host names are S and P (speaker codes stay SU / PRI).
    rename = lambda t: re.sub(r"\bPri\b", "P", re.sub(r"\bSU\b", "S", t))
    for ln in ep["lines"]: ln["text"] = rename(ln["text"])
    ep["description"] = rename(ep["description"])
    out = os.path.join(ROOT, "episodes", f"ripple-daily-{date}.mp3")
    kokoro = CFG["tts"].get("engine") == "kokoro"
    if not kokoro:
        for k in ("SU", "PRI"):
            if not CFG["voices"].get(k): sys.exit(f"voice id for {k} missing in config.json")
        if not os.environ.get("ELEVENLABS_API_KEY"): sys.exit("ELEVENLABS_API_KEY secret is empty: add it in repo Settings > Secrets and variables > Actions")
        for k in ("SU", "PRI"): ensure_voice(k)
    with tempfile.TemporaryDirectory() as td:
        parts, ids = [], []
        if kokoro:
            parts = [kokoro_render(ep["lines"], td)]
        else:
          for i, ch in enumerate(chunks(ep["lines"], CFG["tts"]["chunk_chars"])):
            audio, rid = tts(ch, ids)
            if rid: ids.append(rid)
            p = os.path.join(td, f"c{i:02d}.mp3"); open(p, "wb").write(audio); parts.append(p)
            print(f"chunk {i}: {len(ch)} lines, {dur(p):.1f}s", flush=True)
        lst = os.path.join(td, "list.txt")
        open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
        subprocess.check_call(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ac", "1", "-ar", "44100", "-b:a", "64k",
            "-metadata", f"title={ep['title']}", "-metadata", "artist=Ripple Daily", out])
    secs = round(dur(out))
    print(f"episode: {out} {secs}s")
    if not 240 <= secs <= 660:
        sys.exit(f"duration {secs}s outside 4:00-11:00, not publishing")
    idx_p = os.path.join(ROOT, "episodes", "index.json")
    eps = [e for e in (json.load(open(idx_p)) if os.path.exists(idx_p) else []) if e["date"] != date]
    pub = dt.datetime.fromisoformat(ep.get("publishAt") or f"{date}T08:30:00+05:30")
    eps.append({"date": date, "episode": ep.get("episode") or len(eps) + 1, "title": ep["title"],
                "description": ep["description"], "file": os.path.basename(out),
                "bytes": os.path.getsize(out), "seconds": secs, "pubDate": format_datetime(pub)})
    json.dump(eps, open(idx_p, "w"), indent=1)
    build_feed()

if __name__ == "__main__":
    if sys.argv[1] == "--feed-only": build_feed()
    else: main(sys.argv[1])
