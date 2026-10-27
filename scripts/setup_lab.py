#!/usr/bin/env python3
"""One-time setup for the Agentic SDLC lab (Windows, macOS, Linux).

Clone the course repository into a folder named after YOUR copy, then run this
once from that folder with your default Python (3.10 or newer):

    git clone https://github.com/EchoKernel05/agentic-sdlc-lab.git agentic-sdlc-lab-work
    cd agentic-sdlc-lab-work
    python scripts/setup_lab.py --name agentic-sdlc-lab-work

It turns the clone into your own copy: the course repository becomes the
read-only remote 'upstream', your own GitHub repository <you>/<name> is created
and becomes 'origin', and the lab branches are pushed to it. Then it creates the
Python environment, installs the packages, saves the lab environment variables,
opens the 12 lab issues in your repository (only if it has none) and runs the
unit tests. Nothing is ever pushed to the course repository. Safe to run again.

Options: --name NAME (your copy's name; default: this folder's name),
         --offline (skip all GitHub steps), --skip-venv.
"""
import json, os, pathlib, platform, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
UPSTREAM = os.environ.get("LAB_UPSTREAM", "https://github.com/EchoKernel05/agentic-sdlc-lab.git")
TEMPLATE_NAME = "agentic-sdlc-lab"
WINDOWS = platform.system() == "Windows"
OFFLINE = "--offline" in sys.argv
SKIP_VENV = "--skip-venv" in sys.argv
VENV_PY = ROOT / ".venv" / ("Scripts/python.exe" if WINDOWS else "bin/python")


def opt(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def say(text):
    print(f"\n== {text}", flush=True)


def run(cmd, check=True, capture=True, env=None):
    res = subprocess.run(cmd, cwd=ROOT, text=True, env=env, capture_output=capture)
    if check and res.returncode != 0:
        out = ((res.stdout or "") + (res.stderr or "")) if capture else ""
        sys.exit(f"FAILED: {' '.join(map(str, cmd))}\n{out}")
    return res


def need(tool, hint):
    if not shutil.which(tool):
        sys.exit(f"'{tool}' was not found. {hint}")


def repo_key(url):
    url = url.strip().rstrip("/").replace("\\", "/")
    if url.endswith(".git"):
        url = url[:-4]
    parts = url.replace(":", "/").split("/")
    return "/".join(parts[-2:]).lower()


def remote_url(name):
    res = run(["git", "remote", "get-url", name], check=False)
    return res.stdout.strip() if res.returncode == 0 else ""


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


def make_own_copy(name):
    """If 'origin' is the course repository, turn this clone into the student's own copy."""
    origin = remote_url("origin")
    if origin and repo_key(origin) != repo_key(UPSTREAM):
        print(f"origin is already your own copy: {origin}")
        return "" if OFFLINE else origin_full()
    if name.lower() == TEMPLATE_NAME:
        sys.exit(f"Choose a name different from the course repository's ('{TEMPLATE_NAME}'),"
                 f" for example: python scripts/setup_lab.py --name agentic-sdlc-lab-work")
    say("Making this clone your own copy")
    if origin:
        if remote_url("upstream"):
            run(["git", "remote", "remove", "origin"])
        else:
            run(["git", "remote", "rename", "origin", "upstream"])
    elif not remote_url("upstream"):
        run(["git", "remote", "add", "upstream", UPSTREAM])
    run(["git", "fetch", "-q", "upstream"])
    print(f"upstream = {remote_url('upstream')} (course repository, read-only)")
    target = opt("--origin-url")
    full = ""
    if OFFLINE and not target:
        print("offline: no GitHub repository created; run again without --offline to create it")
        return ""
    if not OFFLINE:
        user = run(["gh", "api", "user", "--jq", ".login"]).stdout.strip()
        full = f"{user}/{name}"
        if repo_key(full) == repo_key(UPSTREAM):
            sys.exit("That name would be the course repository itself. Choose another --name.")
        if run(["gh", "repo", "view", full], check=False).returncode != 0:
            run(["gh", "repo", "create", full, "--public", "--description", "My Agentic SDLC lab copy"])
            print(f"created https://github.com/{full}")
        else:
            print(f"https://github.com/{full} already exists: using it")
        target = target or f"https://github.com/{full}.git"
    run(["git", "remote", "add", "origin", target])
    prefix = "refs/remotes/upstream/"
    refs = run(["git", "for-each-ref", "--format=%(refname)", prefix]).stdout.split()
    branches = [r[len(prefix):] for r in refs if r.startswith(prefix) and r[len(prefix):] != "HEAD"]
    order = ["lab-start", "main"] + sorted(b for b in branches if b not in ("lab-start", "main"))
    for b in order:
        if b in branches:
            run(["git", "push", "-q", "--force", "origin", f"refs/remotes/upstream/{b}:refs/heads/{b}"])
            print(f"  pushed {b}")
    if full:
        run(["gh", "repo", "edit", full, "--default-branch", "lab-start"], check=False)
    run(["git", "fetch", "-q", "origin"])
    run(["git", "checkout", "-q", "-B", "lab-start", "origin/lab-start"])
    print(f"origin = {target} (your copy)")
    return full


def main():
    say("Checking the tools")
    if sys.version_info < (3, 10):
        sys.exit(f"Python 3.10 or newer is needed (this is {platform.python_version()}).")
    need("git", "Install Git, then open a new terminal.")
    print(f"Python {platform.python_version()} ({sys.executable}), git found")
    if not OFFLINE:
        need("gh", "Install the GitHub CLI, then open a new terminal.")
        if run(["gh", "auth", "status"], check=False).returncode != 0:
            sys.exit("The GitHub CLI is not logged in. Run: gh auth login")
        print("GitHub CLI logged in")

    name = opt("--name", ROOT.name)
    lab_repo = make_own_copy(name)

    if not SKIP_VENV:
        say("Python environment (.venv) and packages (takes a minute)")
        if not VENV_PY.exists():
            run([sys.executable, "-m", "venv", str(ROOT / ".venv")])
        run([str(VENV_PY), "-m", "pip", "install", "-q", "--upgrade", "pip"])
        run([str(VENV_PY), "-m", "pip", "install", "-q", "-e", ".[dev]",
             "-r", "lab_mcp/requirements.txt", "pyyaml"])
        print(f"Ready: {VENV_PY}")

    if not OFFLINE:
        lab_repo = lab_repo or origin_full()
        use_own_repo(lab_repo)
        print(f"gh commands in this folder now use: {lab_repo}")

    say("Environment variables (saved for your user)")
    db = (pathlib.Path(tempfile.gettempdir()) / "lab_test.db").as_posix()
    values = {"AUTH_JWT_SECRET_KEY": "test-secret-key-for-local-dev-only",
              "TEST_DATABASE_URL": f"sqlite:///{db}", "PYTHONUTF8": "1"}
    if lab_repo:
        values["LAB_REPO"] = lab_repo
    if WINDOWS:
        for k, v in values.items():
            run(["setx", k, v])
    else:
        rc = pathlib.Path.home() / (".zshrc" if "zsh" in os.environ.get("SHELL", "") else ".bashrc")
        text = rc.read_text() if rc.exists() else ""
        if "# agentic-sdlc-lab" not in text:
            rc.write_text(text + "\n# agentic-sdlc-lab\n" + "".join(f'export {k}="{v}"\n' for k, v in values.items()))
        print(f"Added to {rc}")
    for k, v in values.items():
        os.environ[k] = v
        print(f"  {k} = {v}")

    if not OFFLINE and lab_repo:
        say(f"GitHub issues in {lab_repo} (your copy)")
        run(["gh", "repo", "edit", lab_repo, "--enable-issues"], check=False)
        data = json.loads((ROOT / "scripts" / "lab_issues.json").read_text(encoding="utf-8"))
        for label in data["labels"]:
            run(["gh", "label", "create", label, "--repo", lab_repo, "--force"], check=False)
        res = run(["gh", "issue", "list", "--repo", lab_repo, "--state", "all", "--limit", "1",
                   "--json", "number"], check=False)
        if res.returncode == 0 and res.stdout.strip() in ("", "[]"):
            for it in data["issues"]:
                with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
                    f.write(it["body"])
                run(["gh", "issue", "create", "--repo", lab_repo, "--title", it["title"],
                     "--body-file", f.name, "--label", ",".join(it["labels"])])
                os.unlink(f.name)
                print(f"  created: {it['title']}")
        else:
            print("  issues already exist: not creating them again")

    say("Unit tests")
    py = str(VENV_PY) if VENV_PY.exists() else sys.executable
    res = run([py, "-m", "pytest", "tests/unit", "-q"], check=False, env=os.environ.copy())
    last = [l for l in res.stdout.strip().splitlines() if l.strip()]
    print(last[-1] if last else res.stderr)

    say("Setup finished")
    print("Close this terminal and open a NEW one, so the saved variables are loaded.")
    print("Then start a lab with:  python scripts/start_lab.py 1.2")


if __name__ == "__main__":
    main()
