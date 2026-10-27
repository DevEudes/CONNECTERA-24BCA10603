"""
Connectera — one-command installation (Windows, macOS, Linux).

    Windows : double-click setup.bat   (or run:  py setup_project.py)
    macOS   : ./setup.sh               (or run:  python3 setup_project.py)

What it does:
  1. creates the virtual environment  .venv
  2. installs the dependencies        (requirements.txt)
  3. creates the configuration file   .env  (with a random SECRET_KEY)
  4. connects to MySQL and creates the "connectera" database
     → if MySQL is not installed, it falls back to SQLite automatically
  5. creates the tables and loads the demo data (students, posts, events…)

It can be run again at any time (it resets the demo data).
"""
import os
import secrets
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
WINDOWS = os.name == "nt"
VENV_PY = VENV / ("Scripts/python.exe" if WINDOWS else "bin/python")
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
CHILD_ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def say(msg):
    print(msg, flush=True)


def run(*args):
    subprocess.run([str(a) for a in args], cwd=ROOT, env=CHILD_ENV, check=True)


# ---------------------------------------------------------------- .env helpers
def read_env():
    values = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                values[k.strip()] = v.strip()
    return values


def set_env(key, value):
    """Set KEY=value in .env (replaces an existing or commented line)."""
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        bare = line.lstrip("# ").strip()
        if bare.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- MySQL check
MYSQL_CHECK = r"""
import sys, pymysql
host, port, user, password, name = sys.argv[1:6]
try:
    conn = pymysql.connect(host=host, port=int(port), user=user, password=password, connect_timeout=5)
except Exception as e:
    print("ERR", e); sys.exit(1)
with conn.cursor() as c:
    c.execute(f"CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
conn.close()
"""


def mysql_ok(env):
    res = subprocess.run(
        [str(VENV_PY), "-c", MYSQL_CHECK, env.get("DB_HOST", "127.0.0.1"), env.get("DB_PORT", "3306"),
         env.get("DB_USER", "root"), env.get("DB_PASSWORD", ""), env.get("DB_NAME", "connectera")],
        cwd=ROOT, env=CHILD_ENV, capture_output=True, text=True)
    return res.returncode == 0


def configure_database():
    env = read_env()
    if env.get("DB_ENGINE") == "sqlite":
        say("🗄  Database: SQLite (file db.sqlite3) — set in .env")
        return
    if mysql_ok(env):
        say(f"🗄  Database: MySQL — `{env.get('DB_NAME', 'connectera')}` ready")
        return
    say("\n⚠️  Could not connect to MySQL with the settings of the .env file.")
    say("   • If MySQL is installed, type the password of the MySQL user "
        f"'{env.get('DB_USER', 'root')}'.")
    say("   • If MySQL is NOT installed, just press Enter: SQLite will be used (nothing to install).")
    try:
        password = input("   MySQL password (Enter = use SQLite): ")
    except EOFError:
        password = ""
    if password:
        env["DB_PASSWORD"] = password
        if mysql_ok(env):
            set_env("DB_PASSWORD", password)
            say("🗄  Database: MySQL — connected and `connectera` database created")
            return
        say("❌ Still impossible to connect to MySQL with this password.")
    set_env("DB_ENGINE", "sqlite")
    say("🗄  Database: SQLite (file db.sqlite3). To switch to MySQL later, see README.md.")


# ---------------------------------------------------------------- main
def main():
    say("=" * 60)
    say("  Connectera — installation")
    say("=" * 60)
    if sys.version_info < (3, 10):
        say(f"❌ Python 3.10 or newer is required (you have {sys.version.split()[0]}).")
        say("   Download it from https://www.python.org/downloads/")
        sys.exit(1)
    say(f"🐍 Python {sys.version.split()[0]}")

    if not VENV_PY.exists():
        say("📦 Creating the virtual environment (.venv)…")
        venv.EnvBuilder(with_pip=True).create(VENV)
    say("📦 Installing dependencies (1-2 minutes the first time)…")
    run(VENV_PY, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "--upgrade", "pip")
    run(VENV_PY, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "-r", "requirements.txt")

    if not ENV_FILE.exists():
        ENV_FILE.write_text(ENV_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        set_env("SECRET_KEY", secrets.token_urlsafe(50))
        say("📝 .env created")
    configure_database()

    say("🏗  Creating the tables…")
    run(VENV_PY, "manage.py", "migrate", "--noinput", "-v", "0")
    say("🌱 Loading the demo data…")
    run(VENV_PY, "manage.py", "seed", "--no-download")

    launcher = "run.bat" if WINDOWS else "./run.sh"
    say("\n" + "=" * 60)
    say("✅ Installation complete!")
    say(f"   ▶ Start the app : {launcher}   (or F5 in VS Code)")
    say("   ▶ Then open     : http://127.0.0.1:8000")
    say("   ▶ Demo account  : marie@connectera.app / Demo@1234")
    say("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        say(f"\n❌ A step failed ({' '.join(map(str, e.cmd[:3]))}…). Read the message above, fix it and run again.")
        sys.exit(1)
