# Look-dev stills only: cards for the listed frames, render, one contact sheet. NEW -Name every time: existing frames are skipped (stale stills otherwise).
# .\toon_look.ps1 -Reel <reel folder> -Name look1 -Frames "40,130,250" [-Res 50] [-Samples 16] [-World]
# The frame list needs a comma ("846,846" for one frame).
param([Parameter(Mandatory)][string]$Reel, [string]$Name = 'look1', [Parameter(Mandatory)][string]$Frames, [int]$Res = 50, [int]$Samples = 16, [switch]$World)
$k = Split-Path -Parent $MyInvocation.MyCommand.Path
$Reel = (Resolve-Path $Reel).Path
$Reels = (Resolve-Path "$k\..\..").Path   # <ROOT>\Reels
$py = "$Reels\.venv\Scripts\python.exe"
if (Test-Path "$Reels\env.ps1") { Push-Location $Reels; . .\env.ps1 | Out-Null; Pop-Location }
$bl = if ($env:TOON_BLENDER) { $env:TOON_BLENDER } else { 'blender' }   # set TOON_BLENDER to blender.exe, or put Blender on PATH
$t = "$Reel\toon"; New-Item -ItemType Directory -Force $t | Out-Null
if ($World -or -not (Test-Path "$t\world.blend")) { & $bl -b --factory-startup -P "$k\toon_world.py" -- $Reel "$t\world.blend" 2>$null | Select-String -Pattern 'WORLD_OK|Error|Traceback|File "' | Select-Object -First 8 }
& $py "$k\toon_cards.py" $Reel "$t\_cards" $Frames | Select-Object -Last 1
$w = Measure-Command { cmd /c "`"$bl`" -b `"$t\world.blend`" -P `"$k\toon_render.py`" -- `"$Reel`" `"$t\_cards`" `"$t\_look\$Name`" $Res $Samples $Frames 2>&1" | Select-String -Pattern 'RENDER_OK|Error|Traceback|line \d+' | Select-Object -First 10 }
"render seconds: $([int]$w.TotalSeconds)"
& $py -c "from PIL import Image;import glob,sys;n=sys.argv[1];fs=sorted(glob.glob(n+'/*.png'));w,h=360,640;c=min(5,len(fs));r=(len(fs)+c-1)//c;s=Image.new('RGB',(w*c,h*r));[s.paste(Image.open(f).convert('RGB').resize((w,h)),(i%c*w,i//c*h)) for i,f in enumerate(fs)];s.save(n+'_sheet.jpg',quality=88);print(len(fs))" "$t\_look\$Name"
