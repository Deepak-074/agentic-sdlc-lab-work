#!/usr/bin/env python3
"""Start (or restart) a lab from its clean starting point.

    python scripts/start_lab.py 1.2
    python scripts/start_lab.py 1.3
    python scripts/start_lab.py 2.2   (also 2.3, 2.4a, 2.4b, 3.2, 3.3, capstone)

Every lab has its own start branch (start/lab-1.2, start/lab-1.3, ...), kept
in the instructor's repository. This script:
  1. saves any uncommitted work in a git stash (nothing is lost);
  2. resets YOUR copy of the start branch on GitHub to the instructor's version;
  3. makes that start branch your repository's default branch (so issue forms
     and the cloud agent's setup file come from it);
  4. creates your work branch (lab/1-2, lab/1-3, ...) from it and switches to it;
  5. runs the unit tests.
Labs do not depend on each other: you can start any lab at any time.
Options: --offline (skip the GitHub steps 2 and 3).
"""
import datetime, os, pathlib, platform, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
UPSTREAM = os.environ.get("LAB_UPSTREAM", "https://github.com/EchoKernel05/agentic-sdlc-lab.git")
LABS = {"1.2": "start/lab-1.2", "1.3": "start/lab-1.3",
        "2.2": "start/lab-2.2", "2.3": "start/lab-2.3", "2.4a": "start/lab-2.4a", "2.4b": "start/lab-2.4b",
        "3.2": "start/lab-3.2", "3.3": "start/lab-3.3", "capstone": "start/capstone"}
OFFLINE = "--offline" in sys.argv
WINDOWS = platform.system() == "Windows"


def run(cmd, check=True):
    res = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if check and res.returncode != 0:
        sys.exit(f"FAILED: {' '.join(cmd)}\n{res.stdout}{res.stderr}")
    return res


def repo_slug(url):
    u = url.strip().rstrip("/")
    if u.endswith(".git"):
        u = u[:-4]
    parts = u.replace(":", "/").split("/")
    return "/".join(parts[-2:]).lower() if len(parts) >= 2 else u.lower()


def repo_key(url):
    """'owner/name' from a git URL or path, lower-case, without .git."""
    url = url.strip().rstrip("/").replace("\\", "/")
    if url.endswith(".git"):
        url = url[:-4]
    parts = url.replace(":", "/").split("/")
    return "/".join(parts[-2:]).lower()


def refuse_course_repo():
    """Never run inside the instructor's course repository itself."""
    res = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ROOT, text=True, capture_output=True)
    if res.returncode == 0 and repo_key(res.stdout) == repo_key(UPSTREAM):
        sys.exit("STOP: 'origin' is still the course repository (" + res.stdout.strip() + ").\n"
                 "Run the one-time setup first; it creates your own copy and switches to it:\n"
                 "  python scripts/setup_lab.py --name agentic-sdlc-lab-work")


def origin_full():
    """'owner/name' of the 'origin' remote, case preserved ('' if there is none)."""
    res = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ROOT, text=True, capture_output=True)
    if res.returncode != 0:
        return ""
    url = res.stdout.strip().rstrip("/").replace("\\", "/")
    if url.endswith(".git"):
        url = url[:-4]
    parts = url.replace(":", "/").split("/")
    return "/".join(parts[-2:])


def use_own_repo(full):
    """Point every later gh command in this folder at the student's copy, never the course repository."""
    if not full or full.lower() == repo_key(UPSTREAM):
        sys.exit("STOP: the target repository is the course repository (" + (full or "unknown") + ").\n"
                 "Run the setup first: python scripts/setup_lab.py --name agentic-sdlc-lab-work")
    subprocess.run(["gh", "repo", "set-default", full], cwd=ROOT, text=True, capture_output=True)


def main():
    refuse_course_repo()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args or args[0] not in LABS:
        sys.exit(f"Usage: python scripts/start_lab.py <lab>   (labs: {', '.join(LABS)})")
    lab = args[0]
    start = LABS[lab]
    work = "lab/" + lab.replace(".", "-")
    run(["git", "fetch", "-q", "upstream", "+refs/heads/eval-hidden:refs/remotes/upstream/eval-hidden"], check=False)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    if "upstream" not in run(["git", "remote"]).stdout.split():
        run(["git", "remote", "add", "upstream", UPSTREAM])
    print(f"Getting {start} from the instructor's repository")
    if run(["git", "fetch", "-q", "upstream", f"+refs/heads/{start}:refs/remotes/upstream/{start}"],
           check=False).returncode != 0:
        print("  upstream not reachable: using your own copy (origin)")
        run(["git", "fetch", "-q", "origin", f"+refs/heads/{start}:refs/remotes/upstream/{start}"])
    base = f"refs/remotes/upstream/{start}"

    if run(["git", "status", "--porcelain"]).stdout.strip():
        run(["git", "stash", "push", "-u", "-m", f"start_lab backup {stamp}"])
        print(f"  uncommitted changes saved: git stash list  (start_lab backup {stamp})")

    if not OFFLINE:
        print(f"Resetting {start} on GitHub to the clean version")
        res = run(["git", "push", "-q", "--force", "origin", f"{base}:refs/heads/{start}"], check=False)
        if res.returncode != 0:
            print(f"  could not update origin/{start} (it may be protected); continuing")
        repo = origin_full()
        try:
            use_own_repo(repo)
            ok = run(["gh", "repo", "edit", repo, "--default-branch", start], check=False).returncode == 0
        except FileNotFoundError:
            ok = False
        print(f"  default branch on GitHub: {start}" if ok else "  could not set the default branch (gh missing?)")
    run(["git", "fetch", "-q", "origin"], check=False)

    if run(["git", "rev-parse", "-q", "--verify", f"refs/heads/{work}"], check=False).returncode == 0:
        run(["git", "branch", "-f", f"backup/{work}-{stamp}", work])
        print(f"  your previous {work} is saved as backup/{work}-{stamp}")
    run(["git", "checkout", "-q", "-B", work, base])
    run(["git", "branch", "-q", "--set-upstream-to", f"origin/{start}"], check=False)
    print(f"You are on '{work}', starting from '{start}'")

    venv = ROOT / ".venv" / ("Scripts/python.exe" if WINDOWS else "bin/python")
    py = str(venv) if venv.exists() else sys.executable
    env = dict(os.environ)
    env.setdefault("AUTH_JWT_SECRET_KEY", "test-secret-key-for-local-dev-only")
    res = subprocess.run([py, "-m", "pytest", "tests/unit", "-q"], cwd=ROOT, text=True,
                         capture_output=True, env=env)
    lines = [l for l in res.stdout.splitlines() if l.strip()]
    print("Unit tests: " + (lines[-1] if lines else "could not run"))
    print(f"When you open a pull request, use:  --base {start}")


if __name__ == "__main__":
    main()
