# OWNER SECRET — design note (FLESH THIS OUT)

> Ben flagged this in the build batch: *"make a note here that we need to flesh out this character
> and story."* This is that note. The mechanics are **in and working**; the character and the prose
> are deliberately a first-draft skeleton for Ben to rewrite.

## The secret (one sentence)
The man who built the white Z **is not really hunting her to get her back — he is waiting for her to
be GONE**, because the day she vanishes for good he collects the $100k insurance and is finally free
(money + closure) to rebuild his **true** car: **Mayumi**, the 1970 he loved, the one that burned on
the 580. The white Z was always the *understudy who pays for the revival*. 愛車 — "ride or die" — was
never about her.

This sits directly on top of the lore that already exists in the engine:
- `STORIES["long_beach"]` → **Mayumi**, the first build, burned on the 580 (a fuel line, eight minutes).
- `STORIES["livermore"]` → storage **unit 137**, the scorched Mayumi shell under a tarp; "some of me
  *was* her" (door hinges, the diff). He looks at the white Z and sees a ghost wearing his work.
- `MORNING_BEAT` → Pebble/17-Mile at dawn: "the understudy gets the lights either way."

The owner secret is the **payoff** of that thread: the understudy framing wasn't just melancholy —
it's the literal economics of his plan.

## How it triggers (both implemented)
1. **Ask her "where were you painted?"** somewhere **quiet** (a remote/park/spot, no cameras). She
   first deflects with the paint-booth fact (Fresno, Kilimanjaro White, the hand-laid spade, PPF so
   it'd "peel off clean someday"); asked again somewhere dark she cracks it herself (`OWNER_SECRET`,
   +6 bond — she's choosing to tell you). Parser: `("origin", {"which": "painted"})`.
2. **Wander into Fresno** (a camera-dense CA city — "accidentally going to fresno" is a real risk).
   The **painter** — an old friend of his — spills it. `STORIES["fresno"]`, flag `owner_secret`.

Either path sets `s.flags["owner_secret"]` and reveals **fresno** + **livermore** as destinations.

## What it unlocks
- **The Mexico ending acknowledges it** (`cross_border`): if `owner_secret` is set, the crossing adds
  a beat — he let the BOLO go stale on purpose; "you both win, querido."
- **The fake-your-own-death fireball ending** (`endings.fake_death`, win key `fake_death`):
  - **Requires:** `owner_secret` known · the **ace-of-spades carbon hood in hand** (still on her OR in
    the hatch after a hood swap — if you SOLD it, no spade to plant) · **dark country** (camera
    density 0, not a city) · ~$3,000 cash (`FAKE_DEATH_COST`: junk '70 shell + accelerant + tow).
  - **Effect:** decoy Z wears the spade hood, torched off a dark shoulder; adjuster signs "total
    loss," CARTALK plate burns with it. Sets `no_heat` (you're a closed file), `faked_death`, status
    `won`. Awards **OFFICIALLY DEAD** + **RIDE OR DIE**; +3,500 to the tally (the richest exit).
  - Beautiful synergy with the disguise ladder: you'd typically **respray + swap the plate** on the
    real car first, then burn the *old* white identity off the decoy. The hood-swap literally hands
    you the spade to plant.

## TODO — what still wants Ben's hand
- **The owner as a character.** He has no name yet. Give him one. Right now he's "the man who built
  her." He needs a voice, a face, a few lines of his own — maybe a found voicemail, a Hagerty forum
  post, a text thread Ace surfaces. How much does he know that *she* knows? Does he suspect she's
  awake?
- **The painter in Fresno.** Currently a single narrated beat. Could be a real talk-to NPC (a voice
  in the casting doc) — an old craftsman who laid the spade by hand and feels for both of them.
- **The morality of the fireball.** It's framed as "everyone wins," but it's insurance fraud and a
  staged death. Is there a cost? A bond beat where she's *spooked* by how easily you'd die for this?
  A version where the owner figures out it was faked?
- **Mayumi as a presence.** She's lore right now. Could the rebuild be *visible* at the end — a glimpse
  of unit 137 with the tarp off, work lights on, the real car coming back? An aftergame postcard?
- **The 愛車 / AiSha / Mayumi naming.** The translation thread ("ride or die" ≈ 愛車 ≈ the dead car's
  name) is doing a lot of quiet work. Worth making explicit and exact once, in Ben's voice.

## Where the code lives
- `engine/game.py`: `LORE["painted"]`, `STORIES["fresno"]`, `OWNER_SECRET` / `OWNER_SECRET_NUDGE`,
  `_crack_owner_secret()`, the `which == "painted"` branch in `_origin_beat()`.
- `engine/endings.py`: `can_fake_death()`, `fake_death()`, `_has_spade_hood()`, `FAKE_DEATH_COST`,
  the `owner_secret` beat in `cross_border()`, the scorecard award + tally.
- `engine/commands.py`: the `where were you painted` and `fake your death` / `burn the decoy` parses.
