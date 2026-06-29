# Deep-debug pass — findings & fixes (2026-06-27)

A 12-agent adversarial debug workflow (per-subsystem probes + static review + snapshot fuzz, ~1.3M
tokens) hunted what the 233-test suite didn't cover. It found **72 issues: 6 blockers, 28 majors, 20
minors, 18 nits.** All blockers + the high-impact majors/minors are **fixed and regression-tested
(suite now 239 green)**. The theme: in a conversation-first game, loose substring parser rules let
ordinary sentences fire destructive verbs.

## BLOCKERS — all fixed
1. **Conversation could rattle-can the car.** `'color' in low and ('change'|'different'|'new')` +
   `'spray'/'paint' in low` made "the canyon is a different color" / "spray her with the hose" parse
   to `respray`; the place-keyed confirm gate then executed it on the *second* such sentence — a new
   player could destroy the central relationship in two messages. → respray now needs unambiguous
   paint intent (`respray|repaint|rattlecan|spray paint|paint (her|the car|over)`), word-boundary.
2. **NYE repossessed a car you legally own.** `check_calendar` had `pass` where it needed `return` for
   the no-heat exemption, so a bought / blessed / self-driving / faked-death car got "taken" for CES at
   New Year's. → real early-return for `no_heat | bought | report_withdrawn | self_driving | faked_death`.
3. **`passes` / `snow` / `weather` crashed.** A prior edit ate the `def closures_text` header, orphaning
   its body inside `airtag_sweep`; the command raised AttributeError. → `closures_text` restored.
4. **Infinite money.** The poker rizzbreaker win was checkpointed (cash banked), and the rewind riz-floor
   re-charged the gauge to the threshold for free → bank $12k, rewind, repeat. → spending a rizzbreaker
   now drops `peak_riz` to the spent level, so the floor can't re-charge the gauge.

## MAJORS / MINORS — fixed
- **Parser collisions:** "put on music" → gambling (`startswith 'put '`); "i have 300 cash" → *broke*,
  zeroing your cash; bare "pardon" → the pardon endgame; "cover" inside "dis**cover**"; "i need to go to
  vegas" → restroom; "peel out of here" → peel; "drink the water" → alcohol; "coffee break" → caffeine;
  "buy a **5 gallon** jerry can" → qty 5. All tightened (word-boundaries / intent guards / unit-aware qty).
- **Negation railroads:** "no, I won't fill you up" sealed the favor; "I would never floor it" busted you
  at a stop. → refusal/negation guards on both. Gas-aggression no longer opens an armed standoff on
  benign pump talk ("the money", "freeze").
- **The chase suggested a move that surrendered:** "go dark" (which she literally tells you to do) parsed
  to `drive` and triggered surrender. → a tactic always beats the surrender check.
- **18+ gate bypasses:** rewind cleared it / deflection skipped it / "twelve", "4", "8th grade",
  "underage" didn't parse. → gate persists across rewind (META_PERSIST), the age step is non-deflectable,
  and worded numbers + minor-signals are caught.
- **Exploits:** respray→peel laundered −13.5 heat/cycle (→ peel restores full); a 2nd standoff disarm
  re-ran the desperado unlock for unbounded Riz (→ once only); the bond floor un-armed a COLD car on
  rewind, free anti-theft laundering (→ floor won't lift COLD out of COLD).
- **Transit:** a new "drive to X" mid-conversation silently fast-forwarded to the OLD destination; the
  fast-forward was a substring match ("keep going on that story"); it opened even when she should sleep /
  the pass was snowed shut. All three fixed.
- **Owner/stops:** short status commands (`heat report`, `map`) no longer burn an encounter round (a long
  *sentence* that parses as one still reaches the officer); bare-number offers ("offer 80000") now parse.
- **Misc:** heat dashboard ledger `LOG_KEEP` 16→48 (reconciles on long ALPR-heavy trips); survival
  telegraph emits the higher threshold on a multi-hour tick; "no problem" reads as can-drive-stick;
  two-digit bets ("bet 50") parse; "call me" with nothing after no longer names you "Call";
  non-numeric `camera_density` override is guarded; `events_seen`/`beats_seen` persist across rewind;
  no rizzbreaker bigamy after marrying Alma; "lay low here" → lie-low.

## Deferred (low-impact nits, noted not fixed)
Owner lowball doesn't advance its round; OSM-geocoded towns whose name *contains* a reserved city
("Renova" ⊃ "Reno") get skipped by suggestions; alertness floors at 0.40 no matter how drunk; the heat
"DO THIS" advice is stale once you've applied every disguise; a name equal to a console verb ("Map") is
swallowed; swapplate accepts "steal a plate" as a synonym. None break play — flagged for a later pass.
