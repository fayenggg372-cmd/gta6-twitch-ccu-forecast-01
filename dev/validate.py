"""Reproducible local validation for the gta6-twitch-ccu-forecast-01 entry.

Runs main.py on the four practice cases from the kit and scores the
outputs against the true release-day prints, reconstructed from the same
public source the kit used (SullyGnome.com hourly Twitch category
averages; see input/NOTICE.txt). The answers live in
dev/practice_answers.json; hour 1 of each matches the case's `known`
print exactly, which checks the reconstruction.

Usage (from the repository root):
    python3 dev/validate.py [kit-dir]
"""
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

KIT = Path(sys.argv[1]) if len(sys.argv) > 1 else (
    ROOT / "gta6-twitch-ccu-forecast-01-kit")
LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
ANSWERS = json.loads((Path(__file__).parent / "practice_answers.json").read_text())


def pinball(y, q, tau):
    d = math.log(max(1.0, y)) - math.log(q)
    return 2 * max(tau * d, (tau - 1) * d)


def score(actual, forecast):
    tot, n, covered = 0.0, 0, 0
    for row in forecast["hours"]:
        h = row["hour"]
        y = actual[h - 1]
        if y is None:
            continue
        for tau, q in zip(LEVELS, row["q"]):
            tot += pinball(y, q, tau)
            n += 1
        if row["q"][0] <= y <= row["q"][4]:
            covered += 1
    return tot / n, covered / 23


def main():
    with tempfile.TemporaryDirectory() as tmp:
        outdir = Path(tmp) / "out"
        env = dict(os.environ,
                   MAKEFUN_INPUT_DIR=str(KIT / "input"),
                   MAKEFUN_OUTPUT_DIR=str(outdir))
        subprocess.run([sys.executable, str(ROOT / "main.py")],
                       check=True, env=env)
        losses = []
        for pid in ("p00", "p01", "p02", "p03"):
            case = json.loads((KIT / "input" / f"{pid}.in").read_text())
            fc = json.loads((outdir / f"{pid}.out").read_text())
            actual = [float(x) if x is not None else None for x in ANSWERS[pid]]
            assert [r["hour"] for r in fc["hours"]] == list(range(2, 25))
            for r in fc["hours"]:
                assert len(r["q"]) == 5
                assert all(0 < q <= 1e9 for q in r["q"])
                assert all(r["q"][i] <= r["q"][i + 1] for i in range(4))
            loss, cov = score(actual, fc)
            losses.append(loss)
            miss = [abs(math.log(actual[h - 1]) - math.log(
                next(r for r in fc["hours"] if r["hour"] == h)["q"][2]))
                for h in range(2, 25)]
            print(f"{pid} {case['game']['name'][:28]:28s} "
                  f"loss={loss:.4f} typical_miss="
                  f"{100 * (math.exp(sum(miss) / len(miss)) - 1):5.1f}% "
                  f"coverage90={cov:.2f}")
        print(f"MEAN pinball loss (practice): {sum(losses) / len(losses):.4f}")
        print("House persistence baseline on the same cases: 0.3871")


if __name__ == "__main__":
    main()
