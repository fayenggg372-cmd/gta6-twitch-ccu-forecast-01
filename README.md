# Forecast GTA VI's launch-day Twitch viewers hour by hour

Entry for the make.fun bounty
[`gta6-twitch-ccu-forecast-01`](https://make.fun/c/gta6-twitch-ccu-forecast-01)
— $250, deadline 2026-11-19T01:00:00Z.

`main.py` (Python 3.13, standard library only, no network) reads one case
`/input/<id>.in` and writes `/output/<id>.out`: for each of hours 2–24 of
2026-11-19 UTC, five quantiles (5%, 25%, 50%, 75%, 95%) of the concurrent
viewers in Twitch's "Grand Theft Auto VI" category.

## How it works

The program is a **comparables forecaster**: everything it needs is in
the case file, and it refits itself at run time from the case's own
`comparables` (past big launches' hourly Twitch curves, SullyGnome.com).

1. **Release-day curves.** For each comparable, take its 24 hourly
   viewer counts on its release day (UTC) and its hour-1 count `v1`.
   Work in logs: `r_h = ln(v_h / v1)`.
2. **Unlock regime.** Each comparable is classified from the `unlock`
   note the case ships: `rolling` (midnight-local rolling unlock),
   `simultaneous` (one global unlock), `early_access` (early-access
   contaminated) or `unknown`; `weak` launches (free-to-play /
   slow-burn) are dropped. The primary pool is the **rolling** launches
   — the only ones whose hour 1 is, like GTA VI's, *before* the US
   unlock while Europe is already playing. (GTA VI unlocks at local
   midnight: New Zealand 2026-11-18T11:00Z, CET 23:00Z, UK 00:00Z, US
   Eastern 05:00Z, US Pacific 08:00Z.) If the rolling pool has fewer
   than 6 launches, fall back to rolling + simultaneous + unknown, then
   to all non-weak comparables. The Grand Theft Auto VI category's own
   pre-release history is not a launch and is excluded.
3. **Per-hour forecast.** Two estimates of the log-ratio distribution
   are blended:
   - an OLS fit of `r_h` on `ln(v1)` over the pool — bigger launches
     ramp less from hour 1 — with `ln(v1)` **clamped** to the pool's
     observed range, so a first hour larger than any past launch's
     (GTA VI's will be) cannot extrapolate the curve into a collapse;
   - the pool's empirical quantiles of `r_h`.
   
   The median is a 60/40 blend (fit / empirical) in log space; the
   spread averages the two estimates' deviations, so the bands stay
   honest about how much launch days differ. Quantiles are lightly
   smoothed across neighbouring hours. The forecast is
   `p1 * exp(quantile)`, `p1` the case's hour-1 print.

**Why not persistence?** The house baseline says every hour equals
hour 1. Past launches do not do that: they dip overnight, step up at
the US unlock (hours 5–6 and 8–9 UTC) and peak in the US evening at
roughly 1.2×–2.4× hour 1 for large rolling launches. A pure
`ln(v1)` regression looked even better on the practice cases but
extrapolates to an evening *below* hour 1 at GTA-VI scale (0.5×–0.7×),
which contradicts the unlock mechanics — the US, the largest Twitch
market, is still locked at hour 1. The blend is the hedge: at an
hour-1 print of 1,000,000 it forecasts a median evening peak of
~1.5× hour 1, with a 90% band of roughly 0.85×–4.2×.

## Validation (local, reproducible)

The kit ships no reference answers, so the practice answers were
reconstructed from the same public source the kit used (SullyGnome
hourly averages; `dev/practice_answers.json`, hour 1 matches each
case's `known` print exactly). Run:

```sh
python3 dev/validate.py
```

| case | game | hour-1 viewers | pinball loss | typical miss | 90% coverage |
|---|---|---|---|---|---|
| p00 | Marvel's Wolverine | 23,357 | 0.2673 | 57.6% | 0.96 |
| p01 | Red Dead Redemption 2 | 116,550 | 0.1294 | 22.6% | 1.00 |
| p02 | God of War Ragnarök | 269,517 | 0.1316 | 18.4% | 0.96 |
| p03 | Marvel's Spider-Man 2 | 119,087 | 0.2219 | 34.4% | 0.70 |
| **mean** | | | **0.1876** | | **0.90** |

House persistence baseline on the same cases: **0.3871** (matches the
0.387 stated in the competition rules, which checks the scoring).
Leave-one-out over the 37 usable comparables: 0.44 for the regression
variant vs 0.93 for persistence; the rolling-pool blend used here is
the variant that also behaves sanely above the training range.

## Running it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Reads every `*.in` in the input directory, writes one `<id>.out` per
case. Deterministic (no randomness, clock or network); runs in well
under a second per case on the kit's inputs. Output is exactly
`{"hours": [{"hour": h, "q": [q05, q25, q50, q75, q95]}, ...]}`,
hours 2–24, quantiles finite, > 0, ≤ 1e9, non-decreasing.

## Submission status

Built and validated locally; **not submitted**. Local git commit
`cbd429bc50b8159d9e7b03a308dfc6e261299ba2`. Account @plucky-owl-46
(escrow funded, 250 USDC; entry fee none). Deadline
2026-11-19T01:00:00Z. To submit: create the public GitHub repo under
Seto's account, push this commit, bundle the transcripts (see
`dev/BUNDLE.md` — the bundle must be run from the top-level agent so
the usage rows attach), and submit only with Seto's explicit approval.

## Data & attribution

- Viewer counts: SullyGnome.com hourly Twitch category averages
  (factual public counts, quoted with attribution; see the kit's
  `input/NOTICE.txt`). Practice answers in `dev/` were read once from
  SullyGnome's public chart JSON for the four practice games' release
  months, for validation only — `main.py` never touches the network.
- Unlock times: the `unlock` notes shipped in each case file, plus the
  competition rules (rolling midnight unlock).

## Files

- `main.py` — the entry (the only file the grader runs).
- `README.md` — this file.
- `LICENSE` — MIT (as the kit's starter).
- `dev/validate.py`, `dev/practice_answers.json` — local validation
  only; not used by `main.py`.
- `gta6-twitch-ccu-forecast-01-kit/` — the competition kit (reference).
