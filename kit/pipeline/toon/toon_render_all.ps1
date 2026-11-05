# Whole reel, all cores and the GPU: cards (4 processes) -> N parallel Blender renders on disjoint frames
# -> PNG check -> compose. Finished cards and frames are skipped, so a rerun only does what is missing
# (delete a shot's frames to re-render it).
# .\toon_render_all.ps1 -Reel <reel folder> -Name full_v1 [-Res 100] [-Samples 16] [-N 4] [-Audio voice.wav] [-World] [-NoCaptions]
param([Parameter(Mandatory)][string]$Reel, [string]$Name = 'full_v1', [int]$Res = 100, [int]$Samples = 16, [int]$N = 4,
      [string]$Audio = '', [switch]$World, [switch]$NoCaptions)
$k = Split-Path -Parent $MyInvocation.MyCommand.Path
$Reel = (Resolve-Path $Reel).Path
$Reels = (Resolve-Path "$k\..\..").Path   # <ROOT>\Reels
$py = "$Reels\.venv\Scripts\python.exe"
if (Test-Path "$Reels\env.ps1") { Push-Location $Reels; . .\env.ps1 | Out-Null; Pop-Location }
$bl = if ($env:TOON_BLENDER) { $env:TOON_BLENDER } else { 'blender' }   # set TOON_BLENDER to blender.exe, or put Blender on PATH
if (-not $Audio) { $Audio = if (Test-Path "$Reel\voice_polished.wav") { "$Reel\voice_polished.wav" } else { "$Reel\voice.wav" } }
$t = "$Reel\toon"; $fr = "$t\_frames_$Name"; New-Item -ItemType Directory -Force $t, $fr | Out-Null
if ($World -or -not (Test-Path "$t\world.blend")) { & $bl -b --factory-startup -P "$k\toon_world.py" -- $Reel "$t\world.blend" 2>$null | Select-String -Pattern 'WORLD_OK|Error|Traceback|File "' | Select-Object -First 8 }
& $py "$k\toon_story.py" $Reel | Select-Object -Last 3
$Len = [int](& $py -c "import sys; sys.path.insert(0, sys.argv[1]); from toon_story import load_story; print(load_story(sys.argv[2]).LEN)" $k $Reel)
Set-Content "$Reel\STATUS.txt" "toon: step=cards pass=$Name" -Encoding utf8
$cs = 0..3 | ForEach-Object {
    $i = $_; $list = (0..($Len - 1) | Where-Object { $_ % 4 -eq $i }) -join ','
    Start-Process -FilePath $py -ArgumentList @("`"$k\toon_cards.py`"", "`"$Reel`"", "`"$t\_cards`"", $list) -NoNewWindow -PassThru -RedirectStandardOutput "$t\_cards_$i.log" -RedirectStandardError "$t\_cards_$i.err"
}
$cs | Wait-Process
Set-Content "$Reel\STATUS.txt" "toon: step=render pass=$Name res=$Res x$N" -Encoding utf8
Add-Content "$Reel\render_log.txt" "$(Get-Date -Format s) toon $Name res=$Res samples=$Samples : whole reel, $N parallel" -Encoding utf8
$have = @{}; Get-ChildItem $fr -Filter *.png | ForEach-Object { $have[[int]($_.BaseName -split '_')[-1]] = 1 }
$ps = @()
for ($i = 0; $i -lt $N; $i++) {
    $list = (0..($Len - 1) | Where-Object { $_ % $N -eq $i -and -not $have[$_] }) -join ','
    if (-not $list) { continue }
    if ($list -notmatch ',') { $list = "$list,$list" }
    $ps += Start-Process -FilePath $bl -ArgumentList @('-b', "`"$t\world.blend`"", '-P', "`"$k\toon_render.py`"", '--', "`"$Reel`"", "`"$t\_cards`"", "`"$fr`"", $Res, $Samples, $list) -NoNewWindow -PassThru -RedirectStandardOutput "$t\_render_$i.log" -RedirectStandardError "$t\_render_$i.err"
}
$ps | Wait-Process
# two processes must never write the same frame; drop any broken PNG so the next run fills it
& $py -c "import sys, glob, os`nfrom PIL import Image`nb = 0`nfor p in glob.glob(sys.argv[1] + '/*.png'):`n    try: Image.open(p).load()`n    except Exception: os.remove(p); b += 1`nprint('PNG', len(glob.glob(sys.argv[1] + '/*.png')), 'broken removed', b)" $fr
$opt = @(); if ($NoCaptions) { $opt += '--no-captions' }
if (Test-Path "$Reel\voice_words.json") { $opt += @('--words', "$Reel\voice_words.json") }
& $py "$k\toon_compose.py" $Reel $fr "$t\$Name.mp4" --audio $Audio @opt | Select-Object -Last 2
Set-Content "$Reel\STATUS.txt" "toon: step=done pass=$Name file=toon\$Name.mp4" -Encoding utf8
