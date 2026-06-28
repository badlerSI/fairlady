# CODEX BRIEF — RIDE OR DIE Location Plates (GPT-image batch)

**Goal:** generate one dithered "location plate" for every town and visitable POI in the
game — **252 plates total** (251 POIs in `backend/content/pois.json` + the `sema_north_hall`
start node). Plates must match the **established state-art style** already in
`frontend/scenes_wm/*.png` (e.g. `virginia_city.png`, `big_sur.png`, `palm_springs.png`):
a tight cyan/teal **4-color ordered-dither duotone** of a real place, 320x200, full-bleed.

Engine note: Ben generates images in **ChatGPT (GPT-image)**. These prompts are written for
GPT-image. GPT-image will NOT give you a clean 4-color palette by itself — it renders a
near-photo. **The 4-color dither is applied in a deterministic post-process** (recipe in §4),
NOT begged for in the prompt. The prompt's job is to nail the right *real subject and
composition*; the post-process makes every plate match.

---

## 1. MASTER STYLE BLOCK  *(prepend verbatim to EVERY per-POI prompt)*

> Retro 1980s computer-game location backdrop, single wide establishing shot, full-bleed,
> 16:10 landscape, no text, no logos, no watermark, no people in the foreground, no UI,
> no border or frame. Photographic realism of the real place, slightly moody and
> cinematic, strong directional light (golden hour or blue-hour), deep atmospheric haze
> in the distance, high tonal contrast with a bright sky and dark land. Composition reads
> instantly at thumbnail size: one clear subject, simple silhouette, generous sky.
> Painted from a real reference of the actual location. SUBJECT:

Then append the per-POI **SUBJECT** string from the tables in §3.

**Hard constraints to keep in the prompt every time** (GPT-image drifts otherwise):
`no text`, `no people`, `no frame/border`, `16:10 wide`, `single subject`, `bright sky`.
A bright sky and a dark foreground is what makes the duotone ramp read after dithering —
keep it in every prompt.

---

## 2. NAMING + OUTPUT

- **Filename:** `roi_loc_<poi_id>.png` — `poi_id` is the exact `id` field from `pois.json`
  (e.g. `roi_loc_virginia_city.png`, `roi_loc_reno.png`, `roi_loc_sema_north_hall.png`).
- **Output dir:** `media/transmission/loc/` (create it; full-bleed plates — **transparency NOT
  needed**, ship opaque PNG).
- **Final size:** **320 x 200** PNG, 8-bit palette (the 5 colors in §4). Generate large
  (1024x640, 16:10) then downscale+dither to 320x200 — never upscale.
- **Manifest:** `media/transmission/loc/manifest.json`, **keyed by `poi_id`**. Scaffold is
  provided alongside this brief (`manifest.json`) — every plate pre-listed with
  `status: "pending"`; flip to `"done"` as you render. Schema per entry:
  `{ "file", "region", "kind", "name", "tier", "status" }`. Top-level carries `palette`,
  `size`, `dir`, `count`, and `style: "roi_loc_dither_v1"`.

---

## 3. PER-POI PROMPTS  (grouped by state)

**Marquee POIs** carry a **bespoke, real-photo-grounded SUBJECT** — render these first and
hand-check them; they are the showcase plates and the reference anchors. **Tail POIs** carry a
**templated SUBJECT keyed to the real place name and kind** (city -> real main-street/skyline;
park -> signature vista; track -> the circuit at night; museum/amusement -> the real
building/marquee; gas -> the lonely fuel stop). Every one of the 252 is covered below.

> For each row: final prompt = **[§1 MASTER STYLE BLOCK]** + **[SUBJECT cell]**.

> **Signage exception:** four marquee subjects ARE defined by their lettered signs — `reno`
> (the "BIGGEST LITTLE CITY IN THE WORLD" arch), `fremont` (Vegas Vic / casino neon),
> `neon_museum` (dead casino signs), `salvation_mountain` ("GOD IS LOVE"). For ONLY these four,
> drop the `no text` constraint from §1 and keep the sign legible — the sign is the landmark.
> All other 248 plates keep `no text`.

### 3.1 NEVADA (52 plates — 16 marquee)

| poi_id | kind | tier | SUBJECT (insert after the master style block) |
|---|---|---|---|
| `austin_nv` | city | **MARQUEE** | the near-ghost mining town of Austin Nevada clinging to the western slope of the Toiyabe Range, US-50 climbing through weathered 1860s stone storefronts, Stokes Castle the lone three-story granite tower on the ridge above |
| `carson_city` | city | **MARQUEE** | the Nevada State Capitol in Carson City, its silver-domed sandstone statehouse behind iron fencing and old trees, the eastern slope of the Sierra beyond |
| `las_vegas` | city | **MARQUEE** | the Las Vegas Strip skyline at dusk seen from the south, the high-rise casino towers and the Strat needle against a desert sky |
| `reno` | city | **MARQUEE** | the Reno arch over Virginia Street reading 'RENO — THE BIGGEST LITTLE CITY IN THE WORLD', neon arch spanning the downtown street with casino marquees behind it, Sierra foothills on the horizon |
| `tonopah` | city | **MARQUEE** | downtown Tonopah Nevada at night, the historic Mizpah Hotel's brick facade and the garish Clown Motel sign glowing beside it, mine headframes on the dark hill above, the darkest desert sky full of stars |
| `virginia_city` | city | **MARQUEE** | the Comstock-era boardwalk of Virginia City Nevada, false-front 1870s saloons and brick storefronts stepping up Mount Davidson, old mine works on the slope above the town |
| `area51_gate` | encounter | **MARQUEE** | the back gate to Area 51, a cattle guard and a dirt road stopped by orange posts and warning signs threatening deadly force, a white security truck watching from a low hill, cameras on poles, distant Groom range |
| `fremont` | encounter | **MARQUEE** | Fremont Street in old downtown Las Vegas at night under the barrel-vault canopy of millions of LED bulbs, the Vegas Vic neon cowboy, a zipline cable overhead, dense vintage casino signage |
| `goldfield` | encounter | **MARQUEE** | Goldfield Nevada ghost town, the haunted Goldfield Hotel's brick facade on an empty highway corner, a yard of welded junk art cars, weathered storefronts of a town that was once Nevada's biggest |
| `hoover_dam` | encounter | **MARQUEE** | Hoover Dam, the 726-foot curved Depression-era concrete arch dam wedged in Black Canyon, the intake towers and the Colorado River far below, the Mike O'Callaghan bypass bridge arcing across the gorge |
| `rachel` | encounter | **MARQUEE** | the Extraterrestrial Highway, the lonely Little A'Le'Inn at Rachel Nevada, a flying-saucer sign and a tow-truck dangling a model UFO, empty SR-375 running dead straight to the horizon under a UFO-watching sky |
| `sema_north_hall` | encounter | **MARQUEE** | the SEMA show floor inside the Las Vegas Convention Center North Hall at night, a white Datsun 240Z on a mirrored turntable under hard show spotlights, exhibitor booths and banners receding into haze, rev-limiter crowd |
| `seven_magic` | encounter | **MARQUEE** | Seven Magic Mountains, towering stacks of fluorescent-painted boulders rising from the Jean dry lakebed south of Las Vegas, totem columns of round rocks against flat desert and far mountains |
| `sphere` | encounter | **MARQUEE** | the Sphere in Las Vegas at night, the colossal spherical LED building rendered as a giant glowing eyeball, the freeway and Strip towers small beneath it |
| `neon_museum` | museum | **MARQUEE** | the Neon Museum Boneyard in Las Vegas at dusk, rows of dead retired casino neon signs leaned together in a fenced desert lot, an old Stardust and motel script sign catching the last light |
| `berlin_nv` | park | **MARQUEE** | Berlin-Ichthyosaur State Park, a silver-rush ghost town of grey weathered wooden mine buildings, a fenced fossil shelter behind holding fifty-foot ichthyosaur sea-monster bones in the ground |
| `alamo_nv` | city | tail | the real Alamo NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `amargosa_valley` | city | tail | the real Amargosa Valley NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `battle_mountain` | city | tail | the real Battle Mountain NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `beatty` | city | tail | the real Beatty NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `boulder_city` | city | tail | the real Boulder City NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `caliente_nv` | city | tail | the real Caliente NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `elko` | city | tail | the real Elko NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `ely` | city | tail | the real Ely NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `eureka_nv` | city | tail | the real Eureka NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `fernley` | city | tail | the real Fernley NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `gardnerville` | city | tail | the real Gardnerville NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `genoa_nv` | city | tail | the real Genoa NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `gerlach` | city | tail | the real Gerlach NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `hawthorne_nv` | city | tail | the real Hawthorne NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `jackpot_nv` | city | tail | the real Jackpot NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `laughlin` | city | tail | the real Laughlin NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `lovelock` | city | tail | the real Lovelock NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `mesquite` | city | tail | the real Mesquite NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `mina_nv` | city | tail | the real Mina NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `overton_nv` | city | tail | the real Overton NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `pahrump` | city | tail | the real Pahrump NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `pioche` | city | tail | the real Pioche NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `primm` | city | tail | the real Primm NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `searchlight` | city | tail | the real Searchlight NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `wells_nv` | city | tail | the real Wells NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `west_wendover` | city | tail | the real West Wendover NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `winnemucca` | city | tail | the real Winnemucca NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `yerington` | city | tail | the real Yerington NV: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `fallon` | encounter | tail | the real signature scene of Fallon / NAS Fallon NV: its most recognizable landmark, sign, or street, a moody establishing view |
| `moapa` | gas | tail | a lonely highway fuel stop at Glendale / Moapa NV at dusk, pump island and small store, the real surrounding desert or terrain, neon on wet asphalt |
| `sema_chevron` | gas | tail | a lonely highway fuel stop at Paradise Road Chevron NV at dusk, pump island and small store, the real surrounding desert or terrain, neon on wet asphalt |
| `pinball` | museum | tail | the real exterior architecture of Pinball Hall of Fame, its recognizable building facade and entrance, street view |
| `great_basin` | park | tail | the signature vista of Great Basin National Park, its single most iconic real landform or view, a wide cinematic landscape with no people |
| `valley_of_fire` | park | tail | the signature vista of Valley of Fire State Park, its single most iconic real landform or view, a wide cinematic landscape with no people |
| `lv_motor_speedway` | track | tail | Las Vegas Motor Speedway road-racing circuit at night, the start/finish straight and pit wall under track lighting, grandstand and the real surrounding terrain |
| `spring_mountain` | track | tail | Spring Mountain Motorsports Ranch road-racing circuit at night, the start/finish straight and pit wall under track lighting, grandstand and the real surrounding terrain |

### 3.2 CALIFORNIA (119 plates — 12 marquee)

| poi_id | kind | tier | SUBJECT (insert after the master style block) |
|---|---|---|---|
| `amargosa` | encounter | **MARQUEE** | the Amargosa Opera House at Death Valley Junction, a lone white Spanish-colonial adobe theater in empty desert, its interior walls painted with a permanent trompe-l'oeil audience |
| `calico` | encounter | **MARQUEE** | Calico Ghost Town above Barstow, a restored silver-boom mining town of red-clay false-front buildings and plank sidewalks on a dry desert hillside |
| `golden_gate` | encounter | **MARQUEE** | the Golden Gate Bridge in fog, the international-orange towers half-swallowed by mist, the deck and cables vanishing into the bank, the Marin headland dark in the foreground |
| `integratron` | encounter | **MARQUEE** | the Integratron near Landers, a pure-white domed wooden parabolic building alone in the high Mojave desert, Joshua trees and bare mountains behind it |
| `madonna_inn` | encounter | **MARQUEE** | the Madonna Inn in San Luis Obispo, an extravagant pink Swiss-kitsch hotel with a pink-and-white facade and a famous rock-grotto waterfall, garish romantic resort architecture |
| `monterey` | encounter | **MARQUEE** | Monterey California, Cannery Row and the historic waterfront, the Monterey Bay Aquarium smokestacks, cypress leaning into coastal fog, sea otters in the kelp |
| `oakland_aisha` | encounter | **MARQUEE** | the AiSha Garage in downtown Oakland, a 1926 red-brick auto garage with 'AiSHALLC' hand-painted across the roofline and a kanji on the roll-up door, the Oakland skyline rising behind |
| `richmond_koinoya` | encounter | **MARQUEE** | the koiNOya shop interior in Richmond California, a cluttered Edo-era relic shop, naginata and ceremonial blades racked like umbrellas each carved with a playing-card suit, dim and crowded |
| `salvation_mountain` | encounter | **MARQUEE** | Salvation Mountain near the Salton Sea, a hand-painted adobe hill covered in folk-art flowers and scripture reading 'GOD IS LOVE', painted waterfalls and a yellow brick road climbing the mound |
| `petersen` | museum | **MARQUEE** | the Petersen Automotive Museum in Los Angeles, the building's wild red ribbons of stainless steel wrapping a silver facade, Wilshire Boulevard out front |
| `bodie` | park | **MARQUEE** | the Bodie ghost town in the Bodie Hills, weathered unpainted wood-frame houses and a brick bank standing in 'arrested decay', sagebrush high desert, no living soul |
| `racetrack_playa` | park | **MARQUEE** | the Racetrack Playa in Death Valley, a cracked dry mud lakebed with a single sailing stone at the end of a long scored trail, the Grandstand dark rock outcrop and bare mountains beyond |
| `disneyland` | amusement | tail | the marquee entrance and signature ride of Disneyland, its most recognizable real coaster or icon against the sky at dusk |
| `knotts` | amusement | tail | the marquee entrance and signature ride of Knott's Berry Farm, its most recognizable real coaster or icon against the sky at dusk |
| `magic_mountain` | amusement | tail | the marquee entrance and signature ride of Six Flags Magic Mountain, its most recognizable real coaster or icon against the sky at dusk |
| `santa_cruz_boardwalk` | amusement | tail | the marquee entrance and signature ride of Santa Cruz Beach Boardwalk, its most recognizable real coaster or icon against the sky at dusk |
| `santa_monica` | amusement | tail | the marquee entrance and signature ride of Santa Monica Pier, its most recognizable real coaster or icon against the sky at dusk |
| `seaworld_sd` | amusement | tail | the marquee entrance and signature ride of SeaWorld San Diego, its most recognizable real coaster or icon against the sky at dusk |
| `universal` | amusement | tail | the marquee entrance and signature ride of Universal Studios Hollywood, its most recognizable real coaster or icon against the sky at dusk |
| `alturas` | city | tail | the real Alturas CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `bakersfield` | city | tail | the real Bakersfield CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `barstow` | city | tail | the real Barstow CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `berkeley` | city | tail | the real Berkeley CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `bishop` | city | tail | the real Bishop CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `blythe` | city | tail | the real Blythe CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `borrego_springs` | city | tail | the real Borrego Springs CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `bridgeport_ca` | city | tail | the real Bridgeport CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `chico` | city | tail | the real Chico CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `el_centro` | city | tail | the real El Centro CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `eureka_ca` | city | tail | the real Eureka CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `fort_bragg_ca` | city | tail | the real Fort Bragg CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `fresno` | city | tail | the real Fresno CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `gilroy` | city | tail | the real Gilroy CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `half_moon_bay` | city | tail | the real Half Moon Bay CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `independence_ca` | city | tail | the real Independence CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `indio` | city | tail | the real Indio CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `julian_ca` | city | tail | the real Julian CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `lancaster_ca` | city | tail | the real Lancaster CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `lee_vining` | city | tail | the real Lee Vining / Tioga Pass CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `lone_pine` | city | tail | the real Lone Pine CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `long_beach` | city | tail | the real Long Beach CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `los_angeles` | city | tail | the real Los Angeles CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `malibu` | city | tail | the real Malibu CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `mammoth_lakes` | city | tail | the real Mammoth Lakes CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `mariposa_ca` | city | tail | the real Mariposa CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `mendocino` | city | tail | the real Mendocino CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `modesto` | city | tail | the real Modesto CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `mojave` | city | tail | the real Mojave CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `mount_shasta_city` | city | tail | the real Mount Shasta CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `napa` | city | tail | the real Napa CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `needles` | city | tail | the real Needles CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `nevada_city_ca` | city | tail | the real Nevada City CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `oakhurst` | city | tail | the real Oakhurst CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `oceanside` | city | tail | the real Oceanside CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `ojai` | city | tail | the real Ojai CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `palm_desert` | city | tail | the real Palm Desert CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `palm_springs` | city | tail | the real Palm Springs CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `pasadena` | city | tail | the real Pasadena CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `paso_robles` | city | tail | the real Paso Robles CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `petaluma` | city | tail | the real Petaluma CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `placerville` | city | tail | the real Placerville CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `redding` | city | tail | the real Redding CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `ridgecrest` | city | tail | the real Ridgecrest CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `riverside` | city | tail | the real Riverside CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `sacramento` | city | tail | the real Sacramento CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `salinas` | city | tail | the real Salinas CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `san_diego` | city | tail | the real San Diego CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `san_francisco` | city | tail | the real San Francisco CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `san_jose` | city | tail | the real San Jose CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `san_luis_obispo` | city | tail | the real San Luis Obispo CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `san_simeon` | city | tail | the real San Simeon CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `santa_barbara` | city | tail | the real Santa Barbara CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `santa_maria` | city | tail | the real Santa Maria CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `santa_rosa` | city | tail | the real Santa Rosa CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `solvang` | city | tail | the real Solvang CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `sonora_ca` | city | tail | the real Sonora CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `south_lake_tahoe` | city | tail | the real South Lake Tahoe CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `stockton` | city | tail | the real Stockton CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `susanville` | city | tail | the real Susanville CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `tecopa` | city | tail | the real Tecopa CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `tehachapi` | city | tail | the real Tehachapi CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `temecula` | city | tail | the real Temecula CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `trona` | city | tail | the real Trona CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `truckee` | city | tail | the real Truckee CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `twentynine_palms` | city | tail | the real Twentynine Palms CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `ventura` | city | tail | the real Ventura CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `victorville` | city | tail | the real Victorville CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `visalia` | city | tail | the real Visalia CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `weed_ca` | city | tail | the real Weed CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `yreka` | city | tail | the real Yreka CA: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `artesia` | encounter | tail | the real signature scene of Artesia / Little India CA: its most recognizable landmark, sign, or street, a moody establishing view |
| `east_la` | encounter | tail | the real signature scene of East Los Angeles CA: its most recognizable landmark, sign, or street, a moody establishing view |
| `koreatown_la` | encounter | tail | the real signature scene of Koreatown CA: its most recognizable landmark, sign, or street, a moody establishing view |
| `little_tokyo` | encounter | tail | the real signature scene of Little Tokyo CA: its most recognizable landmark, sign, or street, a moody establishing view |
| `livermore` | encounter | tail | the real signature scene of Livermore CA: its most recognizable landmark, sign, or street, a moody establishing view |
| `sf_chinatown` | encounter | tail | the real signature scene of Chinatown CA: its most recognizable landmark, sign, or street, a moody establishing view |
| `sf_japantown` | encounter | tail | the real signature scene of Japantown CA: its most recognizable landmark, sign, or street, a moody establishing view |
| `sf_mission` | encounter | tail | the real signature scene of The Mission CA: its most recognizable landmark, sign, or street, a moody establishing view |
| `sf_north_beach` | encounter | tail | the real signature scene of North Beach CA: its most recognizable landmark, sign, or street, a moody establishing view |
| `venice_beach` | encounter | tail | the real signature scene of Venice Beach CA: its most recognizable landmark, sign, or street, a moody establishing view |
| `willow_creek` | encounter | tail | the real signature scene of Bigfoot country CA: its most recognizable landmark, sign, or street, a moody establishing view |
| `zzyzx` | encounter | tail | the real signature scene of Zzyzx CA: its most recognizable landmark, sign, or street, a moody establishing view |
| `amboy_ca` | gas | tail | a lonely highway fuel stop at Amboy CA at dusk, pump island and small store, the real surrounding desert or terrain, neon on wet asphalt |
| `baker_ca` | gas | tail | a lonely highway fuel stop at Baker CA at dusk, pump island and small store, the real surrounding desert or terrain, neon on wet asphalt |
| `stovepipe` | gas | tail | a lonely highway fuel stop at Stovepipe Wells CA at dusk, pump island and small store, the real surrounding desert or terrain, neon on wet asphalt |
| `getty` | museum | tail | the real exterior architecture of The Getty Center, its recognizable building facade and entrance, street view |
| `big_sur` | park | tail | the signature vista of Big Sur, its single most iconic real landform or view, a wide cinematic landscape with no people |
| `death_valley` | park | tail | the signature vista of Death Valley NP, its single most iconic real landform or view, a wide cinematic landscape with no people |
| `joshua_tree` | park | tail | the signature vista of Joshua Tree National Park, its single most iconic real landform or view, a wide cinematic landscape with no people |
| `kings_canyon` | park | tail | the signature vista of Kings Canyon National Park, its single most iconic real landform or view, a wide cinematic landscape with no people |
| `sequoia` | park | tail | the signature vista of Sequoia National Park, its single most iconic real landform or view, a wide cinematic landscape with no people |
| `yosemite` | park | tail | the signature vista of Yosemite National Park, its single most iconic real landform or view, a wide cinematic landscape with no people |
| `auto_club` | track | tail | Auto Club Speedway road-racing circuit at night, the start/finish straight and pit wall under track lighting, grandstand and the real surrounding terrain |
| `buttonwillow` | track | tail | Buttonwillow Raceway Park road-racing circuit at night, the start/finish straight and pit wall under track lighting, grandstand and the real surrounding terrain |
| `chuckwalla` | track | tail | Chuckwalla Valley Raceway road-racing circuit at night, the start/finish straight and pit wall under track lighting, grandstand and the real surrounding terrain |
| `laguna_seca` | track | tail | WeatherTech Raceway Laguna Seca road-racing circuit at night, the start/finish straight and pit wall under track lighting, grandstand and the real surrounding terrain |
| `sonoma` | track | tail | Sonoma Raceway road-racing circuit at night, the start/finish straight and pit wall under track lighting, grandstand and the real surrounding terrain |
| `thunderhill` | track | tail | Thunderhill Raceway Park road-racing circuit at night, the start/finish straight and pit wall under track lighting, grandstand and the real surrounding terrain |
| `willow_springs` | track | tail | Willow Springs International Raceway road-racing circuit at night, the start/finish straight and pit wall under track lighting, grandstand and the real surrounding terrain |

### 3.3 ARIZONA (43 plates — 6 marquee)

| poi_id | kind | tier | SUBJECT (insert after the master style block) |
|---|---|---|---|
| `lake_havasu` | encounter | **MARQUEE** | the original London Bridge reassembled stone by stone at Lake Havasu City Arizona, the 19th-century stone-arch bridge spanning a blue desert channel, palm trees and boats beneath it |
| `meteor_crater` | encounter | **MARQUEE** | Meteor Crater in Arizona, a vast three-quarter-mile impact bowl gouged into the flat desert, raised rim and tiny viewing platform for scale, off old Route 66 |
| `page` | encounter | **MARQUEE** | Horseshoe Bend near Page Arizona, the emerald Colorado River curving 270 degrees around a towering red sandstone cliff, vertigo overlook from the rim |
| `sedona` | encounter | **MARQUEE** | the red-rock spires of Sedona Arizona, Cathedral Rock and Bell Rock glowing crimson, green junipers below and a deep blue sky |
| `grand_canyon_south` | park | **MARQUEE** | the Grand Canyon South Rim at Mather Point, layered red-and-ochre canyon walls dropping a mile to the Colorado, immense space and distant buttes at golden hour |
| `monument_valley` | park | **MARQUEE** | Monument Valley on the Navajo line, the iconic Mitten buttes and Merrick Butte rising from red desert floor, the long straight highway running toward them, the most-filmed Western horizon |
| `castles_coasters` | amusement | tail | the marquee entrance and signature ride of Castles N' Coasters, its most recognizable real coaster or icon against the sky at dusk |
| `ajo` | city | tail | the real Ajo AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `bullhead_city` | city | tail | the real Bullhead City AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `casa_grande` | city | tail | the real Casa Grande AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `chinle` | city | tail | the real Chinle AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `flagstaff` | city | tail | the real Flagstaff AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `gila_bend` | city | tail | the real Gila Bend AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `globe_az` | city | tail | the real Globe AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `holbrook` | city | tail | the real Holbrook AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `kayenta` | city | tail | the real Kayenta AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `kingman` | city | tail | the real Kingman AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `parker_az` | city | tail | the real Parker AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `payson_az` | city | tail | the real Payson AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `phoenix` | city | tail | the real Phoenix AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `prescott` | city | tail | the real Prescott AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `quartzsite` | city | tail | the real Quartzsite AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `seligman` | city | tail | the real Seligman AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `show_low` | city | tail | the real Show Low AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `superior_az` | city | tail | the real Superior AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `tuba_city` | city | tail | the real Tuba City AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `tucson` | city | tail | the real Tucson AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `wickenburg` | city | tail | the real Wickenburg AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `willcox` | city | tail | the real Willcox AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `williams` | city | tail | the real Williams AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `window_rock` | city | tail | the real Window Rock AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `winslow_az` | city | tail | the real Winslow AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `yuma` | city | tail | the real Yuma AZ: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `bisbee` | encounter | tail | the real signature scene of Bisbee AZ: its most recognizable landmark, sign, or street, a moody establishing view |
| `jerome_az` | encounter | tail | the real signature scene of Jerome AZ: its most recognizable landmark, sign, or street, a moody establishing view |
| `nogales` | encounter | tail | the real signature scene of Nogales AZ: its most recognizable landmark, sign, or street, a moody establishing view |
| `oatman` | encounter | tail | the real signature scene of Oatman AZ: its most recognizable landmark, sign, or street, a moody establishing view |
| `tombstone` | encounter | tail | the real signature scene of Tombstone AZ: its most recognizable landmark, sign, or street, a moody establishing view |
| `why_az` | gas | tail | a lonely highway fuel stop at Why AZ at dusk, pump island and small store, the real surrounding desert or terrain, neon on wet asphalt |
| `heard` | museum | tail | the real exterior architecture of Heard Museum, its recognizable building facade and entrance, street view |
| `grand_canyon_north` | park | tail | the signature vista of Grand Canyon NP, its single most iconic real landform or view, a wide cinematic landscape with no people |
| `petrified_forest` | park | tail | the signature vista of Petrified Forest National Park, its single most iconic real landform or view, a wide cinematic landscape with no people |
| `saguaro` | park | tail | the signature vista of Saguaro National Park, its single most iconic real landform or view, a wide cinematic landscape with no people |

### 3.4 UTAH (38 plates — 4 marquee)

| poi_id | kind | tier | SUBJECT (insert after the master style block) |
|---|---|---|---|
| `arches` | park | **MARQUEE** | Delicate Arch in Arches National Park, the lone freestanding sandstone arch on the slickrock bowl rim at sunset, the snowy La Sal Mountains framed through it |
| `bryce` | park | **MARQUEE** | the Bryce Canyon amphitheater, thousands of orange hoodoo spires stepping down a snow-dusted rim at 8000 feet, Thor's Hammer, pine and blue shadow |
| `zion` | park | **MARQUEE** | Zion Canyon, sheer 2000-foot Navajo sandstone walls in red and cream, the Virgin River and cottonwoods on the canyon floor, the Watchman peak at the canyon mouth |
| `bonneville` | track | **MARQUEE** | the Bonneville Salt Flats, an endless dead-flat white salt pan to a curved horizon, faint black timing-mile line receding to a vanishing point, the Silver Island Mountains low and distant under a huge sky |
| `lagoon` | amusement | tail | the marquee entrance and signature ride of Lagoon Amusement Park, its most recognizable real coaster or icon against the sky at dusk |
| `beaver_ut` | city | tail | the real Beaver UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `blanding` | city | tail | the real Blanding UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `bluff_ut` | city | tail | the real Bluff UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `cedar_city` | city | tail | the real Cedar City UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `delta_ut` | city | tail | the real Delta UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `escalante_ut` | city | tail | the real Escalante UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `fillmore_ut` | city | tail | the real Fillmore UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `green_river_ut` | city | tail | the real Green River UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `hanksville` | city | tail | the real Hanksville UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `heber_city` | city | tail | the real Heber City UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `helper_ut` | city | tail | the real Helper UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `hurricane_ut` | city | tail | the real Hurricane UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `kanab` | city | tail | the real Kanab UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `logan_ut` | city | tail | the real Logan UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `mexican_hat` | city | tail | the real Mexican Hat UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `moab` | city | tail | the real Moab UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `monticello_ut` | city | tail | the real Monticello UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `ogden` | city | tail | the real Ogden UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `panguitch` | city | tail | the real Panguitch UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `park_city` | city | tail | the real Park City UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `price_ut` | city | tail | the real Price UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `provo` | city | tail | the real Provo UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `salt_lake_city` | city | tail | the real Salt Lake City UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `springdale` | city | tail | the real Springdale UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `st_george` | city | tail | the real St. George UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `tooele` | city | tail | the real Tooele UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `torrey_ut` | city | tail | the real Torrey UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `vernal_ut` | city | tail | the real Vernal UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `wendover_ut` | city | tail | the real Wendover UT: its recognizable main street or skyline and the surrounding landscape it is actually known for, a wide establishing view at golden hour |
| `nhmu` | museum | tail | the real exterior architecture of Natural History Museum of Utah, its recognizable building facade and entrance, street view |
| `canyonlands` | park | tail | the signature vista of Canyonlands National Park, its single most iconic real landform or view, a wide cinematic landscape with no people |
| `capitol_reef` | park | tail | the signature vista of Capitol Reef National Park, its single most iconic real landform or view, a wide cinematic landscape with no people |
| `goblin_valley` | park | tail | the signature vista of Goblin Valley State Park, its single most iconic real landform or view, a wide cinematic landscape with no people |

---

## 4. GENERATION RECIPE  (runnable, skimmable)

### 4.0 The look, exactly
The established `scenes_wm` plates use a **strict 5-color palette** — a 4-tone dark->cyan ramp
plus a bright sky highlight — with **heavy ordered (Bayer 8x8) dithering** at 320x200:

| role | hex | rgb |
|---|---|---|
| shadow / land | `#0e0c0a` | 14,12,10 |
| dark teal | `#13262a` | 19,38,42 |
| mid teal | `#1f6f7d` | 31,111,125 |
| cyan | `#38d6ec` | 56,214,236 |
| sky highlight | `#b8f4ff` | 184,244,255 |

**Style anchor / reference plate:** use `frontend/scenes_wm/virginia_city.png` as the canonical
look reference — it's a marquee town already rendered in the exact target style (town stepping
up a dark slope, bright cyan sky, full dither). Match its contrast and palette on every plate.

### 4.1 Batch order
1. **Render the style reference first.** Make `roi_loc_virginia_city.png`, run it through the
   post-process (§4.3), eyeball it against `scenes_wm/virginia_city.png`. Lock the dither
   settings here. Every later plate uses the *same* settings -> consistency for free.
2. **All MARQUEE plates** (38), state by state, hand-checked.
3. **Tail plates** by state in table order (NV -> CA -> AZ -> UT).
4. Flip each `manifest.json` entry to `status:"done"`; note any GPT-image misses to redo.

### 4.2 GPT-image generation (per plate)
- Prompt = §1 block + the row's SUBJECT. Request **16:10 / landscape wide**.
- Generate at the largest wide size available (~1024x640 or 1536x1024), pick the cleanest of
  ~2 takes (marquee: up to 3-4 takes; tail: 1-2). Reject any take with text, people in front,
  or a framed border — those survive dithering and look wrong.
- Save the raw GPT-image output to a `media/transmission/loc/_raw/` staging folder.

### 4.3 Deterministic 4-color dither post-process  (THIS is what makes the set match)
Run identical settings on every raw image. ImageMagick one-liner (palette file = the 5 hex
above as a 5x1 PNG, `loc_palette.png`):

```bash
# one-time: build the fixed palette swatch
magick -size 5x1 xc:'#0e0c0a' xc:'#13262a' xc:'#1f6f7d' xc:'#38d6ec' xc:'#b8f4ff' +append loc_palette.png

# per plate (raw -> final 320x200 dithered plate)
magick _raw/roi_loc_<id>.png \
  -resize 320x200^ -gravity center -extent 320x200 \
  -modulate 100,135 -level 4%,96% \
  -remap loc_palette.png -dither Riemersma \
  -define png:color-type=3 \
  media/transmission/loc/roi_loc_<id>.png
```

- `-resize ^ ... -extent` = fill 320x200 full-bleed (crop, never letterbox).
- `-modulate/-level` = push saturation+contrast so the scene lands cleanly on the cyan ramp
  (tune ONCE on the reference plate, then freeze).
- `-remap loc_palette.png` = forces the exact 5-color palette -> identical across all 252.
- `-dither Riemersma` ~ the ordered look; if it reads too noisy vs. the anchor, swap to
  `-ordered-dither o8x8` after `-remap`. Pick one on the reference plate and keep it.

Pillow alternative (if scripting in Python): `img.convert('RGB')` ->
`img.resize((320,200))` -> `img.quantize(palette=pal_img, dither=Image.FLOYDSTEINBERG)`.
Use whichever matches `scenes_wm/virginia_city.png` best, then **lock it**.

### 4.4 Consistency checklist (per plate, before marking done)
- [ ] exactly 320x200, opaque PNG, only the 5 palette colors present
- [ ] bright cyan sky region reads; land is dark; clear single subject at thumbnail size
- [ ] no text / no border / no foreground people survived
- [ ] same dither + contrast settings as the locked reference (`virginia_city`)
- [ ] `manifest.json[poi_id].status = "done"`

### 4.5 Totals
- **252 plates**: NV 52 (16 marquee) - CA 119 (12) - AZ 43 (6) - UT 38 (4) = **38 marquee +
  214 tail**. Source of truth for ids/kinds/names: `backend/content/pois.json`.
