# Run once per shell (the kit's .ps1 helpers do it for you): puts ffmpeg on PATH and tells the kit where Blender is.
# Edit the two paths below for this PC.
$env:PATH = "C:\ffmpeg\bin;" + $env:PATH
$env:TOON_BLENDER = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
"reel env ready"
