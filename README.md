# Ripple Daily

Daily AI-voiced podcast of Ripple's top 10 India market stories (SU × Pri, 7–10 min, English).

**Flow:** the scheduled "Ripple Daily podcast" task (8:07 IST) writes `episodes-src/<date>.json` from the Ripple Feed and pushes it here → the **Build episode** action checks the script, voices it with ElevenLabs Text to Dialogue (SU + PRI voice clones), masters the MP3, and updates `feed.xml` → GitHub Pages serves the feed → Spotify picks up the new episode.

- `config.json`: show metadata and voice IDs (not secret).
- Secret `ELEVENLABS_API_KEY`: repo Settings → Secrets and variables → Actions.
- `scripts/check_script.py`: guard rails (speakers, length, disclaimer, no buy/sell, every number traceable to the Feed).
- Episodes older than 180 days drop out of the feed.
