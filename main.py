"""gta6-twitch-ccu-forecast-01: forecast GTA VI's launch-day Twitch viewers,
hour by hour (hours 2..24, UTC, 2026-11-19), as five quantiles an hour.

Method (see README.md for the full write-up and validation numbers)
--------------------------------------------------------------------
The program is a *comparables* forecaster. It reads the case file only
(no network, no model call) and, at run time, rebuilds the release-day
curve of every past launch in the case's `comparables`:

* For each comparable, take its 24 hourly viewer counts on its release
  day (UTC) and its hour-1 count v1. Work in logs: r_h = ln(v_h / v1).
* Classify each comparable by its unlock pattern, from the `unlock`
  text the case ships: `rolling` (midnight-local rolling unlock, the
  pattern GTA VI itself uses), `simultaneous` (one global unlock),
  `early_access` (early-access contaminated) and `unknown`; `weak`
  launches (free-to-play / slow-burn) are dropped outright. The primary
  pool is the rolling launches -- the only launches whose hour 1 is,
  like GTA VI's, *before* the US unlock while Europe is already playing.
  If that pool is too small, fall back to rolling + simultaneous +
  unknown, then to every comparable.
* Per hour h, two estimates of the log-ratio distribution are combined:
    1. an OLS fit of r_h on ln(v1) over the pool (bigger launches ramp
       less from hour 1), with ln(v1) *clamped* to the pool's observed
       range, so a first hour larger than any past launch (GTA VI's
       will be) cannot extrapolate the curve into a collapse; and
    2. the pool's empirical quantiles of r_h.
  The median is a 60/40 blend (fit/empirical) in log space and the
  spread averages the two estimates' deviations, so the bands stay
  honest about how much launch days differ. Quantiles are lightly
  smoothed across neighbouring hours.
* The forecast is p1 * exp(quantile), p1 the case's hour-1 print.

Why not the house persistence baseline? Persistence says every hour
equals hour 1. Past launches do not do that: they dip overnight, step
up at the US unlock (hours 5-6 and 8-9 UTC) and peak in the US evening
at roughly 1.2x-2.4x hour 1 for large rolling launches. On the four
practice launches this program scores a mean pinball loss of ~0.19
against the house baseline's 0.39 (see README.md / dev/validate.py).

Output: /output/<id>.out = {"hours": [{"hour": h, "q": [q05, q25, q50,
q75, q95]}, ...]} for h = 2..24, exactly as the contest specifies.

Run locally:
    mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py

Standard library only. Deterministic: no randomness, no clock, no
network; the same case always yields the same bytes.
"""

import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

# The quantile levels the contest scores, in the order each row lists them.
LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]

# Blend weight of the regression fit vs the pool's empirical quantiles
# for the log-median (0.6 fit / 0.4 empirical). Tuned on the practice
# launches; the blend is what keeps the forecast sane when hour 1 is
# larger than any past launch's.
W_REG = 0.6
# Minimum pool size before falling back to a wider pool.
MIN_POOL = 6
# Persistence baseline's spread (house baseline), used only when the
# case carries no usable comparables at all.
BASE_SIGMA = 0.15
BASE_Z = [-1.645, -0.674, 0, 0.674, 1.645]


def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def round2(x):
    """x rounded to 2 decimals, half up (as the starter does)."""
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if float(value).is_integer() else value


def quantile(sorted_vals, tau):
    n = len(sorted_vals)
    if n == 0:
        return 0.0
    if n == 1:
        return sorted_vals[0]
    pos = tau * (n - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def median(vals):
    s = sorted(vals)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def classify_unlock(unlock_text):
    """Unlock regime of a comparable, from its `unlock` note.

    Order matters: a launch can mention midnight-local rolling *and* be
    early-access contaminated (Hogwarts) or have a simultaneous PC
    unlock that dominates its hour 1 (ELDEN RING); the contamination /
    simultaneity is what shapes hour 1, so it wins.
    """
    u = (unlock_text or "").lower()
    if "tier: weak" in u:
        return "weak"
    if "early-access-contaminated" in u:
        return "early_access"
    if "simultaneous" in u or "single global" in u:
        return "simultaneous"
    if "rolling" in u or "midnight local" in u:
        return "rolling"
    return "unknown"


def release_day_viewers(comp):
    """The comparable's 24 hourly viewer counts on its release UTC day.

    Returns a list of 24 entries (None where the source has no point).
    """
    try:
        day_start = parse_ts(comp["day_start"])
    except (KeyError, ValueError, TypeError):
        return None
    day = [None] * 24
    for pt in comp.get("hourly") or []:
        try:
            viewers = pt["viewers"]
            t = parse_ts(pt["from"])
        except (KeyError, ValueError, TypeError):
            continue
        if viewers is None:
            continue
        h = int((t - day_start).total_seconds() // 3600) + 1
        if 1 <= h <= 24:
            day[h - 1] = viewers
    return day


def ols_log_ratio(pool, hour):
    """OLS of log(v_h / v_1) on ln(v_1) over the pool.

    Returns (intercept, slope, sorted residuals, sorted ln(v1)) or None
    when too few points carry that hour.
    """
    pts = []
    for comp in pool:
        day = comp["day"]
        v1 = day[0]
        vh = day[hour - 1]
        if v1 is None or vh is None or v1 < 1 or vh < 1:
            continue
        pts.append((math.log(v1), math.log(vh / v1)))
    if len(pts) < 5:
        return None
    mx = sum(p[0] for p in pts) / len(pts)
    my = sum(p[1] for p in pts) / len(pts)
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    slope = sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx if sxx > 0 else 0.0
    intercept = my - slope * mx
    residuals = sorted(p[1] - (intercept + slope * p[0]) for p in pts)
    return intercept, slope, residuals, sorted(p[0] for p in pts)


def hour_log_quantiles(pool, p1, hour):
    """The five blended log-ratio quantiles for one hour.

    Blends the ln(v1) regression (clamped to the pool's range) with the
    pool's empirical quantiles; the spread averages both spreads.
    """
    emp = sorted(
        math.log(comp["day"][hour - 1] / comp["day"][0])
        for comp in pool
        if comp["day"][hour - 1] is not None and comp["day"][0] is not None
        and comp["day"][0] >= 1 and comp["day"][hour - 1] >= 1
    )
    if not emp:
        return [0.0] * 5
    emp_q = [quantile(emp, tau) for tau in LEVELS]
    fit = ols_log_ratio(pool, hour)
    if fit is None:
        med = emp_q[2]
        return [q - med + med for q in emp_q]  # empirical quantiles as-is
    intercept, slope, residuals, xs = fit
    lv = math.log(max(1.0, p1))
    x = min(max(lv, xs[0]), xs[-1])  # clamp: never extrapolate the line
    mu_reg = intercept + slope * x
    res_q = [quantile(residuals, tau) for tau in LEVELS]
    med_res = res_q[2]
    med = W_REG * (mu_reg + med_res) + (1 - W_REG) * emp_q[2]
    return [
        med + 0.5 * ((res_q[j] - med_res) + (emp_q[j] - emp_q[2]))
        for j in range(5)
    ]


def forecast_case(case, name):
    known = case.get("known") or []
    first = next((k for k in known if k.get("hour") == 1), None)
    if first is not None and first.get("viewers"):
        p1 = max(1.0, float(first["viewers"]))
    else:
        # Defensive fallback: hour 1 missing (never happens in the
        # contest) -- use the last pre-checkpoint hourly mean, else 1.
        p1 = 1.0
        hist = case.get("history_hourly") or case.get("history") or []
        if hist:
            last = hist[-1]
            v = last.get("viewers")
            if v:
                p1 = max(1.0, float(v))

    # Build the comparable pools from the case's own data.
    comps = []
    for comp in case.get("comparables") or []:
        if "before release" in (comp.get("name") or ""):
            continue  # GTA VI's own pre-release category: not a launch
        day = release_day_viewers(comp)
        if day is None or day[0] is None or day[0] < 1:
            continue
        comps.append({
            "name": comp.get("name", ""),
            "day": day,
            "regime": classify_unlock(comp.get("unlock", "")),
        })

    rolling = [c for c in comps if c["regime"] == "rolling"]
    clean = [c for c in comps
             if c["regime"] in ("rolling", "simultaneous", "unknown")]
    if len(rolling) >= MIN_POOL:
        pool = rolling
    elif len(clean) >= MIN_POOL:
        pool = clean
    else:
        pool = [c for c in comps if c["regime"] != "weak"] or comps

    forecast_hours = [r["hour"] for r in case.get("forecast") or []]
    if len(forecast_hours) != 23 or sorted(forecast_hours) != list(range(2, 25)):
        forecast_hours = list(range(2, 25))

    if not pool:
        # No usable comparables at all: fall back to the house
        # persistence baseline so the case is still valid.
        hours = []
        for h in forecast_hours:
            qs = [round2(p1 * math.exp(z * BASE_SIGMA * math.sqrt(h - 1)))
                  for z in BASE_Z]
            hours.append({"hour": h, "q": _clean_quantiles(qs)})
        return {"hours": hours}

    # Blended log-quantiles per hour, smoothed across neighbours.
    raw = {h: hour_log_quantiles(pool, p1, h) for h in forecast_hours}
    hours = []
    for h in forecast_hours:
        qs = []
        for j in range(5):
            neigh = [raw[hh][j] for hh in (h - 1, h, h + 1) if hh in raw]
            qs.append(sum(neigh) / len(neigh))
        vals = [round2(p1 * math.exp(q)) for q in qs]
        hours.append({"hour": h, "q": _clean_quantiles(vals)})
    return {"hours": hours}


def _clean_quantiles(vals):
    """Enforce the output contract: finite, > 0, <= 1e9, non-decreasing."""
    out = []
    prev = 0.01
    for v in vals:
        if v is None or not math.isfinite(v):
            v = prev
        v = max(0.01, min(1e9, float(v)))
        v = max(v, prev)
        out.append(round2(v))
        prev = out[-1]
    return out


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        out_path = OUTPUT_DIR / f"{path.stem}.out"
        out_path.write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
