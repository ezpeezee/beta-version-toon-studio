# Whole-reel pass: cards, render, compose. Finished cards/frames are skipped, so a rerun only does what is missing.
# .\toon_pass.ps1 -Reel <reel folder> -Name preview_v1 [-Res 50] [-Samples 4] [-Audio voice.wav] [-World] [-NoCaptions]
param([Parameter(Mandatory)][string]$Reel, [string]$Name = 'blockout_v1', [int]$Res = 50, [int]$Samples = 4, [string]$Audio = '', [switch]$World, [switch]$NoCaptions)
$k = Split-Path -Parent $MyInvocation.MyCommand.Path
$Reel = (Resolve-Path $Reel).Path
if (-not $Audio) { $Audio = "$Reel\voice.wav" }
$Reels = (Resolve-Path "$k\..\..").Path   # <ROOT>\Reels
$py = "$Reels\.venv\Scripts\python.exe"
if (Test-Path "$Reels\env.ps1") { Push-Location $Reels; . .\env.ps1 | Out-Null; Pop-Location }
$bl = if ($env:TOON_BLENDER) { $env:TOON_BLENDER } else { 'blender' }   # set TOON_BLENDER to blender.exe, or put Blender on PATH
$t = "$Reel\toon"; New-Item -ItemType Directory -Force $t | Out-Null
if ($World -or -not (Test-Path "$t\world.blend")) { & $bl -b --factory-startup -P "$k\toon_world.py" -- $Reel "$t\world.blend" 2>$null | Select-String -Pattern 'WORLD_OK|Error|Traceback|File "' | Select-Object -First 8 }
Set-Content "$Reel\STATUS.txt" "toon: step=cards pass=$Name" -Encoding utf8
& $py "$k\toon_story.py" $Reel
& $py "$k\toon_cards.py" $Reel "$t\_cards" 1
Set-Content "$Reel\STATUS.txt" "toon: step=render pass=$Name res=$Res" -Encoding utf8
Add-Content "$Reel\render_log.txt" "$(Get-Date -Format s) toon $Name res=$Res samples=$Samples : whole reel" -Encoding utf8
& $bl -b "$t\world.blend" -P "$k\toon_render.py" -- $Reel "$t\_cards" "$t\_frames_$Name" $Res $Samples 1 2>&1 | Select-String -Pattern 'RENDER_OK|Error|Traceback|File "' | Select-Object -First 12
$cap = @(); if ($NoCaptions) { $cap = @('--no-captions') }
& $py "$k\toon_compose.py" $Reel "$t\_frames_$Name" "$t\$Name.mp4" --audio $Audio @cap
Set-Content "$Reel\STATUS.txt" "toon: step=done pass=$Name file=toon\$Name.mp4" -Encoding utf8
