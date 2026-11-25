#!/usr/bin/env bash
# install.sh -- install scanbench from a release tag into its own venv.
#
# Usage: bash install.sh [vX.Y.Z]      (without argument: newest release tag)
#
# Layout (XDG): $XDG_DATA_HOME/scanbench/venvs/X.Y.Z per release (default
# ~/.local/share/scanbench), "venv" there as a link to the active one; the
# active and the previous release are kept. One venv per release on purpose
# (deviation from dev-conventions v8, CONTRIBUTING.md): a running scanbench
# keeps its own files while a newer release is installed next to it.
#
# Environment (all optional):
#   SCANBENCH_BIN   directory for the launcher link; default ~/.local/bin
#   SCANBENCH_REPO  git URL; default https://github.com/peddanet/scanbench.git
# SCANBENCH_HOME of older releases is ignored; scanbench moves old files into
# the XDG folders on its first start.
#
# Privilege level: normal user. Everything is written below the home
# directory; "sudo pip" would write into the system Python, which PEP 668
# marks as externally managed. Only the system packages (sane-utils,
# sane-airscan) need sudo, and this script does not install them.
set -euo pipefail

REPO="${SCANBENCH_REPO:-https://github.com/peddanet/scanbench.git}"
DATA="${XDG_DATA_HOME:-}"
[[ "$DATA" == /* ]] || DATA="$HOME/.local/share"   # XDG: relative values are invalid
ROOT="$DATA/scanbench"
BIN="${SCANBENCH_BIN:-$HOME/.local/bin}"
BIN="${BIN/#\~/$HOME}"
[[ -z "${SCANBENCH_HOME:-}" ]] \
  || echo "Note: SCANBENCH_HOME is no longer used; installing into $ROOT"

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
echo "Installing scanbench $TAG into $ROOT/venvs/${TAG#v}"

# 2. Every release gets its own venv in venvs/X.Y.Z. A running scanbench keeps
#    using its own venv; nothing it has loaded is touched by the installation.
VERSION="${TAG#v}"
TARGET="$ROOT/venvs/$VERSION"
[[ -L "$ROOT/venv" || ! -e "$ROOT/venv" ]] \
  || die "$ROOT/venv is a directory from an older layout; remove it first"
python3 -m venv --clear "$TARGET"
"$TARGET/bin/pip" install --quiet --upgrade pip
"$TARGET/bin/pip" install --quiet "git+$REPO@$TAG"

# 3. The installed program must report the tag's version.
REPORTED=$("$TARGET/bin/scanbench" --version)
[[ "$REPORTED" == "scanbench $VERSION" ]] \
  || die "version mismatch: tag $TAG, program reports '$REPORTED'"

# 4. Switch the active release atomically: a new link is renamed over the
#    old one (mv -T), so there is no moment without a valid "venv" link.
ln -sfn "venvs/$VERSION" "$ROOT/venv.new"
mv -T "$ROOT/venv.new" "$ROOT/venv"

# 5. Keep the active and the previous release, remove older ones.
mapfile -t OLD < <(find "$ROOT/venvs" -mindepth 1 -maxdepth 1 -printf '%f\n' \
                     | sort -V | head -n -2)
for old in "${OLD[@]}"; do
  [[ "$old" == "$VERSION" ]] || rm -rf "${ROOT:?}/venvs/$old"
done

# 6. Launcher link and desktop entry through the stable link, so both stay
#    valid across releases (desktop file and icon below ~/.local/share).
mkdir -p "$BIN"
ln -sfn "$ROOT/venv/bin/scanbench" "$BIN/scanbench"
#    The menu entry carries no data paths; SCANBENCH_BIN only if it was set
#    in the environment. The first start of the new release here also moves
#    files of the old single-root layout (reported on the terminal).
"$ROOT/venv/bin/scanbench" install-desktop --exec "$ROOT/venv/bin/scanbench"
echo "Done: $REPORTED, launcher $BIN/scanbench"
case ":$PATH:" in
  *":$BIN:"*) ;;
  *) echo "Note: $BIN is not in PATH; the desktop launcher works regardless." ;;
esac
