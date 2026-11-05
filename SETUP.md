# Setup

## The easy way: let Claude Code do it
Install Claude Code (desktop app or CLI), open it in an empty folder and paste:
```
Set up github.com/ezpeezee/beta-version-toon-studio on my PC, and run its test.
```
It works through the steps below for you. If a tool is missing, it shows you the install command first.
With the tools already installed, the whole setup and test take about three minutes.

## 1. Install the tools
- **Blender 5.2** (the portable zip is fine): https://www.blender.org/download/
- **Python 3.11+**, **ffmpeg** and **Git**, for example with winget:
  ```
  winget install Python.Python.3.12
  winget install Gyan.FFmpeg
  winget install Git.Git
  ```
- **Claude Code**, the desktop app or the CLI.

A fresh PC downloads about 1 GB in total (Blender about 350 MB, Python + ffmpeg + Git about 185 MB, Python packages about 250 MB).

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
.venv\Scripts\python -m pip install numpy scipy pillow opencv-python soundfile faster-whisper
```

## 5. Set your paths
Open `Reels\env.ps1` and set the ffmpeg `bin` folder and the path to `blender.exe`.
- **ffmpeg from winget** lives under `%LOCALAPPDATA%\Microsoft\WinGet\Packages\`, not `C:\ffmpeg`. Find its folder with:
  ```
  Split-Path (Get-Command ffmpeg).Source
  ```
- **Portable Blender:** point `TOON_BLENDER` at the `blender.exe` inside the unzipped folder, for example
  `C:\Users\<you>\blender-5.2.2-windows-x64\blender.exe`.

## 6. Test
```
cd Reels\pipeline\toon
Copy-Item -Recurse template ..\..\reels\test
.\toon_render_all.ps1 -Reel ..\..\reels\test -Name test -Res 50 -Samples 4
```
You should get `Reels\reels\test\toon\test.mp4`, a silent 6-second clip. The first run builds the world, which takes a minute or two.

## Use it
Open Claude Code in the `Reels` folder and type:
```
/beta-version-toon-studio a short video about why bread goes stale
```
You can also paste your own script after the command.

To add a voice, save it as `voice.wav` in the reel folder and tell Claude. The first time it times a voice, it downloads a speech model.

## Troubleshooting
- **"blender is not recognized":** set `TOON_BLENDER` in `env.ps1`.
- **"running scripts is disabled on this system":** run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or start the script with `powershell -ExecutionPolicy Bypass -File ...`.
- **Changes to `sets.py` don't show:** add `-World` to rebuild the world.
- **Old frames come back:** render under a new `-Name`.
- **Stuck?** DM [@beta_versionhq on Instagram](https://www.instagram.com/beta_versionhq/).
