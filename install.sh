#!/usr/bin/env bash
# install.sh -- install scanbench from a release tag into its own venv.
#
# Usage: bash install.sh [vX.Y.Z]      (without argument: newest release tag)
#
# Environment (all optional):
#   SCANBENCH_HOME  root of the installation; default $XDG_DATA_HOME/scanbench
#                   (~/.local/share/scanbench). Example: ~/scripts/scanbench.d
#   SCANBENCH_BIN   directory for the launcher link; default ~/.local/bin
#   SCANBENCH_REPO  git URL; default https://github.com/peddanet/scanbench.git
#
# Privilege level: normal user. Everything is written below the home
# directory; "sudo pip" would write into the system Python, which PEP 668
# marks as externally managed. Only the system packages (sane-utils,
# sane-airscan) need sudo, and this script does not install them.
set -euo pipefail

REPO="${SCANBENCH_REPO:-https://github.com/peddanet/scanbench.git}"
ROOT="${SCANBENCH_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/scanbench}"
BIN="${SCANBENCH_BIN:-$HOME/.local/bin}"
ROOT="${ROOT/#\~/$HOME}"
BIN="${BIN/#\~/$HOME}"

die() { echo "install.sh: $*" >&2; exit 1; }

for tool in git python3; do
  command -v "$tool" >/dev/null 2>&1 || die "'$tool' is missing"
done

# 1. Choose the tag: the given one, or the newest vX.Y.Z on the remote.
TAG="${1:-}"
if [[ -z "$TAG" ]]; then
  TAG=$(git ls-remote --tags --refs "$REPO" 'v*' \
        | sed 's#.*refs/tags/##' | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' \
        | sort -V | tail -n 1)
  [[ -n "$TAG" ]] || die "no release tag found in $REPO"
fi
echo "Installing scanbench $TAG into $ROOT/venv"

# 2. Fresh venv per installation, so an old release leaves nothing behind.
python3 -m venv --clear "$ROOT/venv"
"$ROOT/venv/bin/pip" install --quiet --upgrade pip
"$ROOT/venv/bin/pip" install --quiet "git+$REPO@$TAG"

# 3. The installed program must report the tag's version.
REPORTED=$("$ROOT/venv/bin/scanbench" --version)
[[ "$REPORTED" == "scanbench ${TAG#v}" ]] \
  || die "version mismatch: tag $TAG, program reports '$REPORTED'"

# 4. Launcher link and desktop entry (desktop file and icon below ~/.local/share).
mkdir -p "$BIN"
ln -sfn "$ROOT/venv/bin/scanbench" "$BIN/scanbench"
"$ROOT/venv/bin/scanbench" install-desktop
echo "Done: $REPORTED, launcher $BIN/scanbench"
case ":$PATH:" in
  *":$BIN:"*) ;;
  *) echo "Note: $BIN is not in PATH; the desktop launcher works regardless." ;;
esac
