#!/usr/bin/env bash
# Dropen3 Linux developer setup (Ubuntu/Debian-focused, other distros supported
# when their Python/system dependencies are preinstalled).
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="python3.12"
INSTALL_SYSTEM=true
RUN_TESTS=true
RUN_DOCTOR=true
ALLOW_DEADSnakes=false

info() { printf '\n[INFO] %s\n' "$*"; }
warn() { printf '\n[WARN] %s\n' "$*" >&2; }
die() { printf '\n[ERROR] %s\n' "$*" >&2; exit 1; }
usage() {
  cat <<'USAGE'
Usage: bash packaging/setup_linux.sh [options]

Options:
  --python PATH           Python 3.12 interpreter (default: python3.12)
  --no-system-packages    Do not install Linux system packages
  --enable-deadsnakes     Allow adding the third-party Deadsnakes PPA on Ubuntu 22.04
  --skip-tests            Skip pytest execution
  --skip-doctor           Skip Dropen3 system doctor
  -h, --help              Show this help

System packages may require sudo on Debian/Ubuntu. The script never installs
Python from third-party repositories without explicit approval or changes
the system's default Python interpreter. Run as a regular user, not with sudo.
USAGE
}

while (($#)); do
  case "$1" in
    --python) (($# >= 2)) || die 'Missing argument for --python'; PYTHON_BIN="$2"; shift 2 ;;
    --no-system-packages) INSTALL_SYSTEM=false; shift ;;
    --enable-deadsnakes) ALLOW_DEADSnakes=true; shift ;;
    --skip-tests) RUN_TESTS=false; shift ;;
    --skip-doctor) RUN_DOCTOR=false; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1 (try --help)" ;;
  esac
done

[[ "$(uname -s)" == "Linux" ]] || die 'This script is for Linux only.'
[[ "$EUID" -ne 0 ]] || die 'Run as a regular user (without sudo). The script will request sudo when needed.'
[[ -f "$ROOT_DIR/pyproject.toml" ]] || die "pyproject.toml not found in $ROOT_DIR"

if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  info "System: ${PRETTY_NAME:-${ID:-Linux}} ($(uname -m))"
fi

# Install the project-standard Python only if it is missing. Ubuntu 22.04
# needs a separately approved third-party repository for Python 3.12.
apt_available() {
  local candidate
  candidate="$(apt-cache policy "$1" 2>/dev/null | awk '/Candidate:/ {print $2; exit}')"
  [[ -n "$candidate" && "$candidate" != "(none)" ]]
}

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  if [[ "$PYTHON_BIN" == "python3.12" && "$INSTALL_SYSTEM" == true ]] && command -v apt-get >/dev/null 2>&1; then
    command -v sudo >/dev/null 2>&1 || die 'sudo is unavailable. Install Python 3.12 manually.'
    info 'Python 3.12 missing; checking configured apt repositories'
    sudo apt-get update
    if ! apt_available python3.12 && [[ "${ID:-}" == "ubuntu" && "${VERSION_ID:-}" == "22.04" ]]; then
      if [[ "$ALLOW_DEADSnakes" != true ]]; then
        if [[ -t 0 ]]; then
          printf '\nPython 3.12 is not available from the configured Ubuntu 22.04 repositories.\n' >&2
          printf 'Deadsnakes is a third-party PPA, not an official Ubuntu repository.\n' >&2
          printf 'Add ppa:deadsnakes/ppa to install Python 3.12? [y/N] ' >&2
          read -r response
          case "$response" in y|Y|yes|YES) ALLOW_DEADSnakes=true ;; esac
        fi
      fi
      if [[ "$ALLOW_DEADSnakes" == true ]]; then
        info 'Installing repository management utility and adding Deadsnakes PPA with approval'
        sudo apt-get install -y software-properties-common
        sudo add-apt-repository -y ppa:deadsnakes/ppa
        sudo apt-get update
      else
        die 'Python 3.12 is missing. Install it manually or rerun with --enable-deadsnakes to explicitly authorize the third-party PPA.'
      fi
    fi
    if apt_available python3.12; then
      info 'Installing Python 3.12 and matching venv/Tk packages'
      packages=(python3.12)
      apt_available python3.12-venv && packages+=(python3.12-venv)
      apt_available python3.12-tk && packages+=(python3.12-tk)
      sudo apt-get install -y "${packages[@]}"
    fi
  fi
fi
command -v "$PYTHON_BIN" >/dev/null 2>&1 || die "Python 3.12 not found ($PYTHON_BIN). Install it from a trusted source supported by your distribution, then rerun. Do not replace /usr/bin/python3."
"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3,12) else 1)' || die "Expected Python 3.12; got $("$PYTHON_BIN" --version 2>&1)"
info "Using $("$PYTHON_BIN" --version 2>&1) at $(command -v "$PYTHON_BIN")"

if command -v apt-get >/dev/null 2>&1; then
  PKGS=()
  if ! command -v git >/dev/null 2>&1; then PKGS+=(git); fi
  if ! (ldconfig -p 2>/dev/null || true) | grep -q 'libGL.so.1'; then PKGS+=(libgl1); fi
  if ! (ldconfig -p 2>/dev/null || true) | grep -q 'libglib-2.0.so.0'; then PKGS+=(libglib2.0-0); fi
  if ! "$PYTHON_BIN" -c 'import venv, ensurepip' >/dev/null 2>&1; then
    if apt_available python3.12-venv; then PKGS+=(python3.12-venv); fi
  fi
  if ! "$PYTHON_BIN" -c 'import tkinter' >/dev/null 2>&1; then
    if apt_available python3.12-tk; then PKGS+=(python3.12-tk); else PKGS+=(python3-tk); fi
  fi
  if ((${#PKGS[@]})); then
    if [[ "$INSTALL_SYSTEM" == true ]]; then
      info "Installing missing OS packages: ${PKGS[*]}"
      command -v sudo >/dev/null 2>&1 || die "sudo unavailable. Install these packages manually: ${PKGS[*]}"
      sudo apt-get update
      sudo apt-get install -y "${PKGS[@]}"
    else
      warn "System packages may be missing: ${PKGS[*]} (--no-system-packages)"
    fi
  fi
else
  warn 'No apt-get detected. Install Tk, OpenGL (libGL) and GLib with your distro package manager if missing.'
fi

"$PYTHON_BIN" -c 'import tkinter' >/dev/null 2>&1 || die 'Tkinter unavailable for the selected Python 3.12. Install the matching Python Tk package, then retry.'
"$PYTHON_BIN" -c 'import venv, ensurepip' >/dev/null 2>&1 || die 'Python venv/ensurepip unavailable. Install the Python 3.12 venv package, then retry.'

if [[ -e "$VENV_DIR" && ! -x "$VENV_DIR/bin/python" ]]; then
  die "$VENV_DIR already exists but is not a usable Linux virtual environment. Move/rename it manually, then rerun."
fi
if [[ ! -d "$VENV_DIR" ]]; then
  info "Creating virtual environment at $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  info "Checking existing virtual environment at $VENV_DIR"
  "$VENV_DIR/bin/python" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3,12) else 1)' || die "Existing .venv has an incompatible Python version. Preserve it with: mv .venv .venv-backup-$(date +%Y%m%d%H%M%S) ; then rerun."
  info "Reusing compatible virtual environment"
fi

VENV_PY="$VENV_DIR/bin/python"
info 'Installing Dropen3 and development test dependencies (editable mode)'
"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install -e "$ROOT_DIR[test]"
"$VENV_PY" -m pip check
"$VENV_PY" -c 'import dropen3; print("Dropen3 module import: OK")' || die "Could not import dropen3 after installation."

cd "$ROOT_DIR"
if [[ "$RUN_TESTS" == true ]]; then
  info 'Running pytest'
  "$VENV_PY" -m pytest -q || die 'Tests failed. Environment was installed, but cannot be considered validated.'
fi
if [[ "$RUN_DOCTOR" == true ]]; then
  info 'Running system doctor'
  "$VENV_PY" -m dropen3 doctor || die 'System doctor returned an error. Review its output before using the GUI.'
fi

info 'Setup finished successfully.'
printf '\nNext steps:\n  source .venv/bin/activate\n  python -m dropen3 gui\n  python -m pytest -q\n'
printf '\nVS Code: open the repository with "code ." and select .venv/bin/python.\n'
printf 'For reproducibility, keep a lock/constraints file; editable install alone does not freeze transitive versions.\n'
