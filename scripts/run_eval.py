#!/usr/bin/env python3
"""Score one agent run against the hidden test for a task and append to experiments/results.csv.

Usage: python scripts/run_eval.py --task t1 --variant A --run 1 --branch exp/A/t1/1 --base exp/A-base
       [--minutes 4.5] [--corrections 0]

The hidden tests are NOT in your working folder (so the agent cannot read them). They live on the
'eval-hidden' branch and are copied into a temporary copy of your branch only while scoring.
"""
import argparse, csv, os, pathlib, re, subprocess, sys, tempfile

ap = argparse.ArgumentParser()
for k in ("task", "variant", "run", "branch"):
    ap.add_argument("--" + k, required=True)
ap.add_argument("--base", default="lab-start")
ap.add_argument("--minutes", default="")
ap.add_argument("--corrections", default="0")
a = ap.parse_args()
sh = lambda *c, **k: subprocess.run(c, capture_output=True, text=True, **k)

ref = next((r for r in ("upstream/eval-hidden", "origin/eval-hidden", "eval-hidden")
            if sh("git", "rev-parse", "-q", "--verify", r).returncode == 0), None)
if not ref:
    sys.exit("Hidden tests not found. Run: git fetch upstream eval-hidden")
names = [n for n in sh("git", "ls-tree", "--name-only", f"{ref}:eval/hidden").stdout.split()
         if n.startswith(f"test_{a.task}_")]
if not names:
    sys.exit(f"No hidden test for task {a.task}")
hidden = names[0]

wt = tempfile.mkdtemp(prefix="eval-")
sh("git", "worktree", "add", "--detach", wt, a.branch)
(pathlib.Path(wt) / "tests/unit" / hidden).write_text(sh("git", "show", f"{ref}:eval/hidden/{hidden}").stdout)
env = {**os.environ, "AUTH_JWT_SECRET_KEY": os.environ.get("AUTH_JWT_SECRET_KEY", "x")}
r = sh(sys.executable, "-m", "pytest", f"tests/unit/{hidden}", "-q", cwd=wt, env=env)
full = sh(sys.executable, "-m", "pytest", "tests/unit", "-q", "--ignore", f"tests/unit/{hidden}", cwd=wt, env=env)
stat = sh("git", "diff", "--shortstat", f"{a.base}..{a.branch}").stdout
changed = sum(int(x) for x in re.findall(r"(\d+) (?:insertion|deletion)", stat))
sh("git", "worktree", "remove", "--force", wt)

out = pathlib.Path("experiments/results.csv"); out.parent.mkdir(exist_ok=True)
new = not out.exists()
with out.open("a", newline="") as f:
    w = csv.writer(f)
    if new:
        w.writerow(["task", "variant", "run", "hidden_pass", "existing_tests_pass", "lines_changed", "minutes", "human_corrections"])
    w.writerow([a.task, a.variant, a.run, r.returncode == 0, full.returncode == 0, changed, a.minutes, a.corrections])
print(f"{a.task} {a.variant}#{a.run}: hidden={'PASS' if r.returncode == 0 else 'FAIL'} "
      f"existing={'PASS' if full.returncode == 0 else 'FAIL'} lines={changed}")
