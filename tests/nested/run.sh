#!/bin/bash
# End-to-end check in a headless, isolated KWin: own D-Bus session, own config dirs, own Wayland
# socket. Nothing here touches the running desktop session or ~/.config.
# Usage: tests/nested/run.sh [yakuake-binary] [output-dir]   (default binary: build/bin/yakuake)
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
bin=$(realpath "${1:-$here/../../build/bin/yakuake}")
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
exec dbus-run-session -- python3 "$here/drive.py" "$out" "$bin"
