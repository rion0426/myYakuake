#!/bin/bash
# End-to-end check in a headless, isolated KWin: own D-Bus session, own config dirs, own Wayland
# socket. Nothing here touches the running desktop session or ~/.config.
# Usage: tests/nested/run.sh [myyakuake-binary] [output-dir]   (default binary: build/bin/myyakuake)
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
bin=$(realpath "${1:-$here/../../build/bin/myyakuake}")
out=${2:-$(mktemp -d /tmp/myyakuake-test.XXXXXX)}
mkdir -p "$out"/{config,state,cache,data}
echo "output: $out"
# 8x slower compositor animations, so a screenshot lands inside the open animation.
printf '[KDE]\nAnimationDurationFactor=8\n' >"$out/config/kdeglobals"
# Plain Fade as the window open/close effect (Plasma's default Scale also zooms the window).
printf '[Plugins]\nscaleEnabled=false\nfadeEnabled=true\n' >"$out/config/kwinrc"
# Qt logs to journald when stderr is not a terminal; the driver reads KWin script output from kwin.log.
export QT_FORCE_STDERR_LOGGING=1
export XDG_CONFIG_HOME=$out/config XDG_STATE_HOME=$out/state XDG_CACHE_HOME=$out/cache XDG_DATA_HOME=$out/data
# A build-tree binary needs its data (skins under share/myyakuake) installed somewhere.
build=$(realpath "$here/../../build")
if [[ $bin == "$build"/* ]]; then
    cmake --install "$build" --prefix "$out/prefix" >/dev/null
    export XDG_DATA_DIRS=$out/prefix/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}
fi

# D-Bus-activated helpers of the private session (ksecretd, xdg-desktop-portal-gtk) outlive it.
cleanup() {
    local pid
    for pid in $(pgrep -u "$(id -u)"); do
        if tr '\0' '\n' <"/proc/$pid/environ" 2>/dev/null | grep -qx "XDG_CONFIG_HOME=$out/config"; then
            kill "$pid" 2>/dev/null || true
        fi
    done
}
trap cleanup EXIT
dbus-run-session -- python3 "$here/drive.py" "$out" "$bin"
