---
name: beta-version-toon-studio
description: Make a short 9:16 toon-style animated video (flat drawn characters standing in a simple Blender 3D set, 30 fps) from an idea or from the user's own script, through to final.mp4 and a short posting caption. Use when the user says toon video, toon reel, cartoon short, Beta Version Toon Studio, or asks to animate a script in this kit's style.
---

# Beta Version Toon Studio

A free, open edition of the Beta Version toon kit. You write two small data files per video (`sets.py` for the world, `story.py` for the shots); the kit renders, captions and mixes.

The kit lives in the user's `Reels\` folder (see the repo's SETUP.md). Paths below are relative to it. Read `pipeline\toon\API.md` and the files in `pipeline\toon\template\` once, then write from them. Open engine files only when something is broken.

## What this edition does
- One character design for everyone: a vest figure in five colour sets, picked by the card id. Use plain role ids (`engineer`, `banker`, `worker`, `A`, `B` ...); costumes, period clothes and real-person heads are not part of this edition.
- Ready-made modern sets only: `street`, `desert`, `rooftop`, `sea`, `bank`, `trading`, `datacenter`, `factory`, `store`, or `room_set` from the template. Don't build historical or real-place worlds.
- A calm, simple look: soft daylight, flat colour, gentle camera moves, a few talking poses.

## Workflow
1. **Script.**
   - **The user gave a script:** use it word for word.
   - **The user gave an idea:** write a simple script, 30-60 s, about 2.5 words per second, one sentence per line, plain spoken English.
   - Save it as `reels\<date>-<slug>\script.txt`, one line per sentence.
2. **Reel folder.** Copy `pipeline\toon\template\` to `reels\<date>-<slug>\`.
3. **Voice.**
   - **The user has a recording or TTS file:** save it as `voice.wav` (48 kHz) in the reel folder, then run `python toon_words.py <reel>` for word timings. Read `voice_check.txt` and tell the user about any words that weren't heard.
   - **No voice yet:** run `python toon_fake_words.py <reel>` for placeholder timings. The video renders with silence, and the voice can be swapped in later.
4. **Shot list.**
   - Write `SHOTLIST.md`: one line per sentence, saying what the line says and what we see.
   - Keep to 2-4 places, each used for several lines.
   - Show what each line says with a character doing it, a sign, a number on a plate, or a prop.
5. **Build.**
   - `sets.py`: ready sets 60 m apart (`from toon_sets import *`), plus plates for any words or numbers the script needs.
   - `story.py`:
     - one `shot()` per idea, timed to the word timings;
     - `dolly`, `wide_push`, `track` or `arc` for the camera;
     - `acting(a, b)` while someone talks;
     - `cut` or `dissolve` joins.
   - Then run `python toon_story.py <reel>` and fix anything it flags.
6. **Look.**
   - Run `.\toon_look.ps1 -Reel <reel> -Name look1 -Frames "a,b,c" -World` (use `-World` after any `sets.py` change).
   - Check the contact sheet:
     - characters are in frame;
     - no camera sits inside a wall;
     - text can be read.
   - Fix problems and render the stills again.
7. **Render.**
   - Run `.\toon_render_all.ps1 -Reel <reel> -Name full_v1`. Add `-Res 50 -Samples 4` for a quick preview.
   - The output is `reels\<reel>\toon\full_v1.mp4`.
   - To fix a shot, delete its frames and run the command again: only the missing frames render.
8. **Sound (optional).**
   - Run `python toon_mix.py <reel> --voice voice.wav --cues cues.csv` for a few sound effects and a music bed (cues are explained in API.md).
   - Mux the mix onto the video with ffmpeg (copy the video stream) as `final.mp4`.
9. **Caption.**
   - Write `posting_pack.md`: a title, a 2-line caption with 3-5 hashtags, and the line "Made with Beta Version Toon Studio".

Run renders in the background and read only the result line. Keep replies short.

## Traps
- After editing `sets.py`, rebuild the world (`-World`), or the old world is used.
- Finished cards and frames are reused. After changing a pose or shot, delete that shot's files or render under a new `-Name`.
- In story.py, `vis={obj: scale}` SETS an object's scale.
- Blender's Python has no PIL, so story.py must not import modules that need it.
- Keep API keys in a `.env` file. Never print them or put them in the reel folder.
