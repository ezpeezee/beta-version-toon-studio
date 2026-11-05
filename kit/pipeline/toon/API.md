# toon kit API (read this file and the template; open engine code only if these can't answer and something is broken)
Kit: `Reels\pipeline\toon\`. 9:16, 30 fps, flat inked characters on lens-facing cards in a Blender EEVEE world. New reel = copy `template\` to `Reels\reels\<date>-<slug>\`, edit `story.py` + `sets.py`.
Start from `template\` (story.py, sets.py, cues.csv). Pictures: `SETS.jpg`, `PROPS.jpg`, `COSTUMES.jpg`, `POSES_NEW.jpg`.

## Reel folder
`story.py` `sets.py` `hooks.py`(optional) `voice_words.json` `voice.wav` `cues.csv` `assets\`(own pngs; kit `assets\` has view_sky/far/mid/near, slip, bill) `avatar\` `sound\` `costs.csv` `STATUS.txt` `render_log.txt`
`toon\` (generated): `world.blend` `_cards\` `_frames_<Name>\` `_look\<Name>\` `<Name>.mp4` `avatar_frames\`
`voice_words.json`: `[{"word","start","end","line"}]` seconds; drives captions + sound gaps.

## story.py
`from toon_story import *` then define:
- `LEN` total frames. `SHOTS=[(fn, first, last), ...]` contiguous, fn(f)->state dict. Frames rendered per shot: first-3 .. last+3 (the 6 f dissolve overlap).
- `GRADE=[(f,(r,g,b,sat)),...]` eased per-frame grade in compose. `WHIPS={join frame,...}` joins done as whip (blur slide), older reels; new reels use `JOINS` below.
- optional: `SET_G={set:(r,g,b)}` card tint per set; `CAM_DROP={set:(z_hi,span,drop)}` lowers target when cam z < z_hi; `CAST={id:dict}` extra characters; `PROP_TEXT=dict(drive=('A','B'),clipboard='X',label='X')`.
Helpers: `tk(f,[(frame,val|tuple)..])` eased keys, `st` stepped keys, `ease(t)`, `over(t)` pop with overshoot 0..1, `base(f,seed,**pose)` idle life (blink, bob, sway), `talk(f)` mouth every 3 f, `walking(pose,f,v,T=12,dirn=1)` v=card px/frame, feet planted, `axis(f,CAM,TGT,y,off)` world x on the camera line, `card(id,x,y,z,M,sq,grade,pose)`, `tickets_at`, `random`, `math`.
Shot builder: `shot(set, cam, tgt, lens=24, roll=0, cards=(), **extra)`; cam/tgt/lens/roll/card x,y,z = value or keyed list `[(f,v)..]`; card = `dict(id,x,y,z=0,M=.00115,sq=1,grade,pose='name'|dict|stepped keys [(f,pose)..],seed=0,walk=dict(v,T,dirn),walk_on=(f0,f1),talk=(f0,f1))`; extra values may be callables of f. Or write `def S1(f): return dict(...)` by hand (Knight style).
State dict keys (all optional except cam, set):
- `cam=(pos,tgt,lens)` world metres including the set's x offset, e.g. set at ox=60: pos `(60-3.5,-4.5,3)`; lens mm; `roll` deg; `set` name (only used for SET_G/CAM_DROP; the camera position picks the set, sets sit at distinct x, e.g. 0, -60, 60, 120, 180).
- Framing: 9:16 at lens 24 and 3 m distance shows about 2 m of width, so keep cards within about +-.6 m of the camera axis.
- `cards=[card(...)]` max 10, drawn in order; x,y,z are world values including the set's offset; `M` metres per card px (.00115 = 2.2 m tall); `sq` squeeze x (turn trick); `z` lifts the card.
- `vis={obj: scale}` pop objects listed in sets `HIDDEN` (0 hides, `over(t)` pops). `objs={obj: dict(show,loc,rot(deg),scale)}`; `loc` is relative to the object's parent group. `texts={text_obj: 'body'}` (3D text; plate text object is `<plate>_tx`).
- `tickets=[stream]`, `bills=[stream]` flying sprites; stream=`dict(src,to,[via],frames,spread,rate,a,b)` (per-frame spawn between a..b) or `dict(src,vel,g,life,...)`.
- `fx=dict(x,y,z,items=[...])` flat sprite card at a world point; items `('ring',x,y,r,w,(r,g,b))`, `('star',x,y,size,n)`, `('z',x,y,size)` in card px (1200x1900, feet y=1860).
- `screens={obj: 'folder'}` shows `<reel>\toon\<folder>\{frame:04d}.png` on that object's image texture (avatar on a monitor: `screens=dict(mon_avatar='avatar_frames')`).
- any other key (e.g. `mon_z`, `racks`, `plugs`, `bell`, `lever`, `flip`, `tally`, `spark`, `wire_glow`) is read only by the reel's `hooks.py`.
### Pose keys (base(f,seed,**kw); presets in `POSES`: idle laptop cheer shock shrug slump happy)
`view` front|q_r|back; `eyes` smug|dot|happy|shut|slit|ring; `brows` None|flat|up|angry|sad; `mouth` tick|line|o|pout|wide|smile|open; `sweat` bool; `tilt` deg; `lean` `bob` px; `knee`; `hat_y` `hat_rot` (cap hop); `hand_l` `hand_r` (x,y) card px; `bend_l` `bend_r`; `feet` `toe` `hip` (set by walking); `prop`: `laptop`(brand logo) | `drive`(+`ph`) | `clipboard` | `mallet`(+`ham_rot`) | `label` | `pistol`(right hand, barrel to +x, +`gun_rot` deg; muzzle about hand+(230,-60) px); `fx` list; `star` bool.
More pose keys (off by default): `sit` True or seat drop px (presets sit, sit_desk; needs a seat in the world), `body` 'q'|'q_back' three-quarter torso (presets turn, turn_back), `foreshorten` 0..1 seen from above (preset high), `stretch_l` `stretch_r` long reaching arm, hand at stretch x its distance from the shoulder (preset reach), `hem` px sway of a long hem. More cast keys: `robe_long`, `skirt` `skirt_hem` `skirt_flare` `skirt_trim`, `hair_style` long|bob|bun|ponytail, `lashes`, `earrings`. Women and more roles: `<role>_f` for every role, queen (king_f), kurta, kurta_f, saree_f, office_f. Pictures: `COSTUMES.jpg`, `POSES_NEW.jpg`.
Add/override with `CAST={'X':dict(style='vest', vest=4 rgb, hair=, cap=3 rgb|None)}`. In this edition every character is drawn from the same design (a vest figure in one of five colour sets, chosen by id), so costumes, period clothes and real-person heads are not available.
Keep hands out of the head box (x 340..870, y < 860) unless intended: `python toon_story.py <reel>` lists overlaps.

## Camera, light and effects (Studio edition)
This edition keeps a simple, calm look on purpose: camera moves are scaled down (`CAM_GAIN`), shots use one soft daylight setup, and acting steps between a few plain poses. Story variables for bloom, motion blur, depth of field, grade, finish, rim light, frame lock, lenses and whips are accepted but ignored. Joins are `cut` or `dissolve`.
Camera moves return `dict(cam,tgt,roll)`; use as `shot(set, **dolly(cam,tgt,a,b), cards=...)`: `dolly(cam,tgt,a,b)`, `push`/`pull`, `wide_push(wide,close,tgt,a,b,hold=20)`, `arc(tgt,r,z,a,b,deg0,deg1)`, `crane(cam,tgt,a,b,up,tilt)`, `track(cam,tgt,a,b,dist=1)`; `low(pos,z=.45)` lowers a camera position. `hero_cam(x,y,...)` -> (cam, tgt) framing a card.
Effects: `burst(kind,f,f0,x,y,size=200,seed=1,**kw)` returns items fired at frame f0 (card px, 1200x1900); kinds smoke fire boom sparks dust debris money confetti steam sweat impact. Use in a shot: `fx=lambda f: dict(x=0,y=.1,z=0,items=burst('sparks',f,110,600,700,500,3))`.
Acting: `pose=acting(a,b,seed=1,at={frame:'pose'})` steps through a few talking poses; `pose=acted([(f,'pose'),...])` your own keys. Presets: idle laptop cheer shock shrug slump happy explain think point_r.
Captions: Poppins Bold at y=.7. Joins: `JOINS={boundary_frame:dict(kind='cut'|'dissolve')}`.

## sets.py
`from toon_lib import *` (bpy, math, sc, ROOT, KIT, REEL, BRAND, TEX, MODELS included; `bpy` is usable directly, e.g. `bpy.ops.mesh.primitive_uv_sphere_add` for a sphere; `plate` text faces -Y, toward the camera; `image_plane` takes a parent), build with:
`room_set(name, ox, floor=(h,h), wall=(h,h), wain=(h,h), trim=h, view=True, wy=2.7)` ready room, back wall at y=wy, camera side -Y.
`mat(name,hex,rough,metal,glow)` `painted(name,hex,hex2,scale)` flat painted surface (this edition draws flat colour; texture arguments are ignored)
`group(name,parent,loc)` `bx(name,size,loc,mat,parent,bevel)` `cyl(name,r,depth,loc,mat,parent,rot,seg)`
`text3d(name,body,size,loc,mat,parent,rz,ext,font_)` `plate(name,body,size,loc,bg_hex,fg_hex,pad,parent,depth,font_,flat_,aged_)` (3D text on a contrasting plate; always use plates for readable text. `font_`: None = Anton, or `slab serif chalk type black` (FONTS; `get_font`); `flat_=True` prints flat (paint, chalk)) `image_plane(name,asset('x.png'),width,loc,parent,rx=90,lit=False)` (lit=True: a printed map, poster, flag or photo lit by the scene with a shadow; default unlit = screens and overlays) `asset(name)` (reel `assets\` then kit) `set_ceiling(prefix,parent,w,y0,y1,z)` `distant_view(prefix,cx,wy)` `card_plane`
Logo: `image_plane('brand', BRAND, .6, loc)` on a dark `bx` plate (ready sets already carry one).
Sets at different x (0, -60, 60 ...) so the camera never sees another set; world coordinates: x right, y away from camera, z up, metres.
`python toon_view.py <reel>` / `toon_pcb.py <reel>` / `toon_flat.py <reel> placeholder|screen <name> "L1" "L2"` write pngs to `<reel>\assets`.

### Ready sets: `from toon_sets import *` in sets.py (includes everything from toon_lib; about 20 s build each)
`street_set desert_set rooftop_set sea_set bank_set trading_set datacenter_set factory_set store_set (name, ox=0, **colours)`, e.g. `street_set('street',0); trading_set('floor',60)`; ox 60 m apart, characters at about (ox,0,0), camera on the -Y side, 32 m sky dome. Colours by keyword (`sky_top=`, `sky_hor=`, `walls=`). Each carries a logo on a prop. Helpers: `sky(name,ox,top,horizon,mid)`, `clouds(name,ox,n,seed,...)`, `haze(name,ox,y,hex,alpha,h,w,z0)`, `sunbeam(name,loc,w,h,rot,hex,alpha)`, `skyline(name,ox,y,...)`, `fog`, `win_mat`, `flat`, `screen_mat`.

### Crowds, vehicles, inserts: `from toon_props import *` in sets.py
`crowd(name,x0,x1,y0,y1,n,seed=1,z=0,height=1.9,bob=.03,grade=None,heads_only=False)` many small flat people; keep it behind the action (close up the legs read as long sticks). `grandstand(name,loc,w,rows,seed,depth,rise,crowd_h,bob,grade,heads_only,hex)`.
`car van bus train_car cargo_ship forklift (name,loc,hex)`, `truck(name,loc,hex,cab_hex)`; face +X, top-level groups. `traffic(name,y,z,ox,n,speed,wrap=60,seed,spread=36,kinds)` moving convoy; speed m/frame; keep wrap > 2*speed*LEN and n small (8 in 36 m overlap).
`phone(name,loc,screen_png,screen_lines,parent,hex,scale=1,hero=False)` keep lines few and big, `calendar(name,loc,pages,size,parent,days,start,period)` (period=True: printed pages from calendar_png on curled, dog-eared sheets on a nail, lit by the scene; hang on plain wall, not over a window), `newspaper(name,loc,headline,sub,size,bend,parent,glow=0)` (lit by the scene; glow=.35 was the old self-lit look), `sign_board(name,loc,lines,hex,parent,size,width)`.
In story.py `from toon_props_story import *`: `objs=calendar_flip('cal',f,f0,n_pages,every=6)`; `newspaper_png(reel,name,headline,sub)`, `calendar_png(reel,name,pages,year,days,start,top,paper)` (old-newsprint calendar pages: serif masthead, rules, typewriter weekdays, fine print) and `age_paper(pil_image,seed)` (grain, stain, worn edges for any printed texture: maps, posters) before the world is built.
Movers from toon_sets and toon_props merge automatically; just append to your own `MOVERS` if you add any.

## hooks.py (optional, reel-specific Blender logic)
`setup(R)` once after load; `apply(R,s,k,f,keep)` per frame after generic keys; `cards_extra(out,C)` once in the card step (extra pngs). `R` has `ob`(objects) `bpy` `S`(story) `CARDS` `REEL` `load(path)` `show(name,on)` `pop` `face_cam` `srgb` `Vector` `set_tex`. Every per-frame texture you `R.load` MUST be added to `keep` or it renders black.

## Commands (PowerShell, run from the kit folder; each prints its own result line)
`python toon_fake_words.py <reel> [wps]` placeholder `voice_words.json` from `script.txt`, until the voice exists.
`.\toon_pass.ps1 -Reel <reel> -Name preview_v1 [-Res 50] [-Samples 4] [-Audio <wav>] [-World] [-NoCaptions]` whole reel: cards, render, compose -> `toon\<Name>.mp4`. Builds world.blend if missing; `-World` forces a rebuild after sets.py edits.
`.\toon_look.ps1 -Reel <reel> -Name look2 -Frames "40,130,250" [-Res 50 -Samples 16]` stills + `_look\<Name>_sheet.jpg`.
`.\toon_look.ps1 -Reel <reel> -Name look2 -Frames "40,130,250" [-Res 50 -Samples 16]` stills + `_look\<Name>_sheet.jpg`.
Whole reel in parallel (preferred): `.\toon_render_all.ps1 -Reel <reel> -Name full_v1 [-Res 100] [-Samples 16] [-N 4] [-Audio <wav>] [-World] [-NoCaptions]` = cards (4 processes) -> N Blender processes on disjoint frames -> PNG check -> compose (captions; silence if there is no voice yet). Finished cards and frames are skipped, so a rerun only fills what is missing.
Word timings for any voice: `python toon_words.py <reel> [voice.wav]` (faster-whisper small.en, GPU if CUDA 12 is there, else CPU) -> `voice_words.json` matched to `script.txt` + `voice_check.txt` (what was heard; words not heard are interpolated and listed).
Sound: `python toon_mix.py <reel> --voice <wav> --cues cues.csv` -> `sound\final_mix.wav` + `final_nomusic.wav` (-14 LUFS, TP <= -1, bed -21.7 dB under voice, +5 dB in gaps >= .3 s). cues.csv `frame,dur_f,kind,level_db_vs_voice,arg`; kinds: tap click pop whoosh thud ding paper bell alarm boing stab ticks roll slam buzz blip zip rise; level -6 loudest .. -26. Settings are named constants at the top of the file; `mix_extra.py` in the reel may add bespoke cues.

## Traps
- `scatter` props between the camera and the hero block the hero or fill the frame: start its y range about 1.8 m in front of the camera, and check stills. `fore` shapes use compose, so they don't appear in `toon_look` stills.
- Heroes get lost in a crowd of the same size: put the crowd 5 m+ behind them and end the push close (head about 25 % of width).
- A `look` adds to a set's own lamps: on bright sets (bank, store) start with golden or office and check a still.
- FX sprites are small at default `M`: money or confetti meant to fill the frame needs `M` about .0026 and `life` about 110.
- A prop at the same y as a card covers it; seats go behind the card (y +.4).
- Inserts (newspaper, calendar) float: place them behind the other shots' cameras, and fill the frame so nothing shows below.
- Weak so far: `sit` is a wide-kneed stance, `body='q'` is subtle, street and rooftop floors look mottled, store aisles barely read.
- `toon_look` / render skip existing frames: use a NEW `-Name` (or delete the files) or the stills are stale.
- Hero cards are cached per shot+frame in `toon\_cards`: when a walk or pose changes, delete that shot's card files (`_cards\<id>\<shot>_*.png`), else old art is reused.
- Frame lists need a comma: `"846,846"` for one frame; a frame inside two shots' padding renders in both.
- `free(keep)` unloads every image not in `keep`: per-frame textures in hooks must be added to `keep`.
- Renderer frames are `s{shot:02d}_{frame:04d}.png`. Partial re-render: rename `_frames_<Name>` to the next version (`_frames_preview_v2`), delete only the changed frames, rerun `toon_pass` with that Name (compose reads that folder; finished frames are skipped).
- `world.blend` is cached: rebuild with `-World` after any sets.py change.
- Run `. Reels\env.ps1` first in a plain shell (ffmpeg); it overwrites `$sp`, `$d`, `$here`.
- No text mentioning AI on screen. Captions come from `voice_words.json`; text on screen = 3D plates.
