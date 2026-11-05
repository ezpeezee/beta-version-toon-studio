# Setup

## 1. Install the tools
- **Blender 5.2** (the portable zip is fine): https://www.blender.org/download/
- **Python 3.11+**: https://www.python.org/
- **ffmpeg**: https://www.gyan.dev/ffmpeg/builds/
- **Claude Code**, the desktop app or the CLI.

## 2. Add the skill
Copy the `skill` folder to `C:\Users\<you>\.claude\skills\beta-version-toon-studio\`, so that `SKILL.md` sits directly inside it.
Restart Claude Code.

## 3. Add the kit
1. Make a project folder, for example `C:\Users\<you>\toon_project\`.
2. Copy the `kit` folder into it and rename the copy `Reels`.

## 4. Set up Python
In the `Reels` folder, run:
```
python -m venv .venv
.venv\Scripts\pip install numpy scipy pillow opencv-python soundfile faster-whisper
```

## 5. Set your paths
Open `Reels\env.ps1` and set the ffmpeg `bin` folder and the path to `blender.exe`.

## 6. Test
```
cd Reels\pipeline\toon
Copy-Item -Recurse template ..\..\reels\test
.\toon_render_all.ps1 -Reel ..\..\reels\test -Name test -Res 50 -Samples 4
```
You should get `Reels\reels\test\toon\test.mp4`, a 6-second clip. The first run builds the world, which takes a minute or two.

## Use it
Open Claude Code in the `Reels` folder and type:
```
/beta-version-toon-studio a short video about why bread goes stale
```
You can also paste your own script after the command.

To add a voice, save it as `voice.wav` in the reel folder and tell Claude.

## Troubleshooting
- **"blender is not recognized":** set `TOON_BLENDER` in `env.ps1`.
- **Changes to `sets.py` don't show:** add `-World` to rebuild the world.
- **Old frames come back:** render under a new `-Name`.
