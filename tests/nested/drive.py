"""Drives Yakuake in a headless KWin with a fake always-visible top panel.

Checks: windowed geometry, fullscreen covers the panel, leaving fullscreen restores the windowed
geometry (also after a hide/show with RememberFullscreen), and the open animation mode.
Run through tests/nested/run.sh, which provides the isolated D-Bus session and config dirs.
"""
import ctypes
import json
import os
import subprocess
import sys
import time

import dbus
from PIL import Image

out, yakuake_bin = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
SOCKET = "wayland-myyakuake-test"
W, H, PANEL = 1920, 1200, 56
AREA = (0, PANEL, W, H - PANEL)
KEY_LEFTCTRL, KEY_LEFTSHIFT, KEY_F11 = 29, 42, 87

procs = []
logs = {}


def spawn(name, argv, **env):
    logs[name] = open(os.path.join(out, name + ".log"), "w")
    p = subprocess.Popen(argv, env=dict(os.environ, **env), stdout=logs[name], stderr=subprocess.STDOUT)
    procs.append(p)
    return p


kwin = spawn("kwin", ["kwin_wayland", "--virtual", "--no-lockscreen", "--width", str(W), "--height", str(H),
                      "--socket", SOCKET])
bus = dbus.SessionBus()
client_env = dict(WAYLAND_DISPLAY=SOCKET, QT_QPA_PLATFORM="wayland")


def wait_for(cond, what, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        if kwin.poll() is not None:
            sys.exit(f"FAIL: kwin exited while waiting for {what}; see kwin.log")
        try:
            if cond():
                return
        except dbus.DBusException:
            pass
        time.sleep(0.1)
    sys.exit(f"FAIL: timeout waiting for {what}")


def kwin_iface(path, iface):
    return dbus.Interface(bus.get_object("org.kde.KWin", path), iface)


script_seq = 0


def kwin_eval(body):
    """Runs a KWin script and returns the JSON it prints with print_result()."""
    global script_seq
    script_seq += 1
    tag = f"RESULT{script_seq}:"
    path = os.path.join(out, f"probe{script_seq}.js")
    with open(path, "w") as f:
        f.write(f"function print_result(v) {{ console.info('{tag}' + JSON.stringify(v)); }}\n{body}\n")
    scripting = kwin_iface("/Scripting", "org.kde.kwin.Scripting")
    sid = scripting.loadScript(path, f"probe{script_seq}", signature="ss")
    kwin_iface(f"/Scripting/Script{sid}", "org.kde.kwin.Script").run()
    end = time.time() + 5
    while time.time() < end:
        logs["kwin"].flush()
        with open(os.path.join(out, "kwin.log")) as f:
            for line in f:
                if tag in line:
                    scripting.unloadScript(f"probe{script_seq}")
                    return json.loads(line.split(tag, 1)[1])
        time.sleep(0.05)
    sys.exit(f"FAIL: no result from KWin script {path}")


def yakuake_window():
    return kwin_eval("""
const w = workspace.windowList().find(w => w.resourceClass === "org.kde.yakuake");
const p = workspace.windowList().find(w => w.dock);
print_result(w ? {x: w.frameGeometry.x, y: w.frameGeometry.y, w: w.frameGeometry.width, h: w.frameGeometry.height,
                  fullScreen: w.fullScreen, layer: w.layer, active: w.active, panelLayer: p ? p.layer : null} : null);
""")


def screenshot(name):
    r, w = os.pipe()
    res = kwin_iface("/org/kde/KWin/ScreenShot2", "org.kde.KWin.ScreenShot2").CaptureActiveScreen(
        dbus.Dictionary({}, signature="sv"), dbus.types.UnixFd(w))
    os.close(w)
    data = b""
    while chunk := os.read(r, 1 << 20):
        data += chunk
    os.close(r)
    width, height, stride, fmt = int(res["width"]), int(res["height"]), int(res["stride"]), int(res["format"])
    mode = {4: "BGRX", 5: "BGRA", 6: "BGRA", 16: "RGBX", 17: "RGBA", 18: "RGBA"}[fmt]
    img = Image.frombuffer("RGBA", (width, height), data, "raw", mode, stride, 1).convert("RGB")
    img.save(os.path.join(out, name + ".png"))
    return img


def yakuake(path, iface):
    return dbus.Interface(bus.get_object("org.kde.yakuake", path), iface)


def toggle():
    yakuake("/yakuake/window", "org.kde.yakuake").toggleWindowState()


# --- libei keyboard; KWin hands out the socket over D-Bus ----------------------------------
ei = ctypes.CDLL("libei.so.1")
for fn, res, args in [
    ("ei_new_sender", ctypes.c_void_p, [ctypes.c_void_p]),
    ("ei_setup_backend_fd", ctypes.c_int, [ctypes.c_void_p, ctypes.c_int]),
    ("ei_dispatch", None, [ctypes.c_void_p]),
    ("ei_get_event", ctypes.c_void_p, [ctypes.c_void_p]),
    ("ei_event_get_type", ctypes.c_int, [ctypes.c_void_p]),
    ("ei_event_get_seat", ctypes.c_void_p, [ctypes.c_void_p]),
    ("ei_event_get_device", ctypes.c_void_p, [ctypes.c_void_p]),
    ("ei_event_unref", ctypes.c_void_p, [ctypes.c_void_p]),
    ("ei_device_ref", ctypes.c_void_p, [ctypes.c_void_p]),
    ("ei_device_has_capability", ctypes.c_bool, [ctypes.c_void_p, ctypes.c_int]),
    ("ei_device_start_emulating", None, [ctypes.c_void_p, ctypes.c_uint32]),
    ("ei_device_keyboard_key", None, [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_bool]),
    ("ei_device_frame", None, [ctypes.c_void_p, ctypes.c_uint64]),
    ("ei_now", ctypes.c_uint64, [ctypes.c_void_p]),
]:
    getattr(ei, fn).restype = res
    getattr(ei, fn).argtypes = args
ei.ei_seat_bind_capabilities.restype = ctypes.c_int
CAP_KEYBOARD = 1 << 2
EV_SEAT_ADDED, EV_DEVICE_RESUMED = 3, 8
EIS_KEYBOARD = 1


def connect_keyboard():
    fd, _cookie = kwin_iface("/org/kde/KWin/EIS/RemoteDesktop", "org.kde.KWin.EIS.RemoteDesktop").connectToEIS(EIS_KEYBOARD)
    ctx = ei.ei_new_sender(None)
    assert ei.ei_setup_backend_fd(ctx, os.dup(fd.take())) == 0
    end = time.time() + 5
    while time.time() < end:
        ei.ei_dispatch(ctx)
        while ev := ei.ei_get_event(ctx):
            t = ei.ei_event_get_type(ev)
            if t == EV_SEAT_ADDED:
                ei.ei_seat_bind_capabilities(ctypes.c_void_p(ei.ei_event_get_seat(ev)),
                                             ctypes.c_int(CAP_KEYBOARD), ctypes.c_void_p(None))
            elif t == EV_DEVICE_RESUMED:
                dev = ei.ei_device_ref(ei.ei_event_get_device(ev))
                if ei.ei_device_has_capability(dev, CAP_KEYBOARD):
                    ei.ei_device_start_emulating(dev, 1)
                    ei.ei_event_unref(ev)
                    return ctx, dev
            ei.ei_event_unref(ev)
        time.sleep(0.02)
    sys.exit("FAIL: no EIS keyboard device")


def chord(ctx, dev, *keys):
    for down, seq in ((True, keys), (False, reversed(keys))):
        for k in seq:
            ei.ei_device_keyboard_key(dev, k, down)
            ei.ei_device_frame(dev, ei.ei_now(ctx))
            ei.ei_dispatch(ctx)
            time.sleep(0.02)


failures = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        failures.append(msg)


def same_rect(win, rect):
    return (win["x"], win["y"], win["w"], win["h"]) == tuple(rect)


def brightest_row(img):
    """Row of the tab bar, the brightest horizontal band of the Yakuake window (panel rows excluded)."""
    xs = range(100, img.width - 100, 20)
    rows = [(sum(sum(img.getpixel((x, y))) for x in xs), y) for y in range(PANEL, img.height)]
    return max(rows)[1]


def start_yakuake(animation):
    with open(os.path.join(os.environ["XDG_CONFIG_HOME"], "yakuakerc"), "w") as f:
        f.write(f"""[Dialogs]
FirstRun=false

[Window]
Width=100
Height=50
VerticalPosition=50
ShowTitleBar=false
KeepOpen=true

[Animation]
OpenAnimation={animation}

[Behavior]
RememberFullscreen=true
""")
    p = spawn("yakuake-" + animation, [yakuake_bin], **client_env)
    wait_for(lambda: bus.name_has_owner("org.kde.yakuake"), "yakuake on D-Bus")
    time.sleep(2)
    return p


def stop_yakuake(p):
    p.terminate()
    p.wait(timeout=10)
    wait_for(lambda: not bus.name_has_owner("org.kde.yakuake"), "yakuake to quit")


def open_animation_row(name):
    """Opens Yakuake; returns the tab bar row shortly after the open and once settled."""
    toggle()
    time.sleep(0.3)  # run.sh slows animations 8x, so this is early in the open animation
    early = brightest_row(screenshot(name + "-opening"))
    time.sleep(3)
    return early, brightest_row(screenshot(name + "-open"))


try:
    wait_for(lambda: bus.name_has_owner("org.kde.KWin"), "KWin on D-Bus")
    spawn("plasmashell", [sys.executable, os.path.join(here, "fake_plasmashell.py"), *map(str, AREA)])
    # /usr/bin/qml is Qt 5 on Fedora; the panel needs the Qt 6 runtime for layer-shell-qt 6.
    spawn("panel", ["/usr/lib64/qt6/bin/qml", os.path.join(here, "panel.qml")],
          QT_WAYLAND_SHELL_INTEGRATION="layer-shell", **client_env)
    wait_for(lambda: bus.name_has_owner("org.kde.plasmashell"), "fake plasmashell")
    ctx, kbd = connect_keyboard()

    # Height=50% of the work area, centered in it (VerticalPosition=50).
    height = (H - PANEL) * 50 // 100
    windowed = (0, PANEL + (H - PANEL - height) // 2, W, height)

    yak = start_yakuake("Slide")
    early, settled = open_animation_row("1-slide")
    print("slide: tab bar row early", early, "settled", settled)
    check(early < settled - 20, "Slide mode slides the window in from the top")

    win = yakuake_window()
    print("opened:", win)
    check(win is not None and same_rect(win, windowed), f"windowed geometry {windowed}")

    chord(ctx, kbd, KEY_LEFTCTRL, KEY_LEFTSHIFT, KEY_F11)
    time.sleep(3)
    win = yakuake_window()
    print("fullscreen:", win)
    check(win["fullScreen"] and same_rect(win, (0, 0, W, H)), "fullscreen covers the whole screen")
    check(win["layer"] > win["panelLayer"], "fullscreen stacks above the panel")
    screenshot("2-fullscreen")

    chord(ctx, kbd, KEY_LEFTCTRL, KEY_LEFTSHIFT, KEY_F11)
    time.sleep(3)
    win = yakuake_window()
    print("restored:", win)
    check(not win["fullScreen"] and same_rect(win, windowed), "leaving fullscreen restores windowed geometry")
    screenshot("3-restored")

    # RememberFullscreen: hide while fullscreen, reopen (new toplevel created fullscreen), leave it.
    chord(ctx, kbd, KEY_LEFTCTRL, KEY_LEFTSHIFT, KEY_F11)
    time.sleep(3)
    toggle()
    time.sleep(3)
    toggle()
    time.sleep(3)
    win = yakuake_window()
    print("reopened fullscreen:", win)
    check(win["fullScreen"] and same_rect(win, (0, 0, W, H)), "reopened in fullscreen")
    screenshot("4-reopened-fullscreen")

    chord(ctx, kbd, KEY_LEFTCTRL, KEY_LEFTSHIFT, KEY_F11)
    time.sleep(3)
    win = yakuake_window()
    print("restored after reopen:", win)
    check(not win["fullScreen"] and same_rect(win, windowed), "leaving fullscreen after reopen restores windowed geometry")
    screenshot("5-restored-after-reopen")
    stop_yakuake(yak)

    yak = start_yakuake("Fade")
    early, settled = open_animation_row("6-fade")
    print("fade: tab bar row early", early, "settled", settled)
    check(abs(early - settled) <= 2, "Fade mode opens in place (no slide)")
    stop_yakuake(yak)

    print("PASS" if not failures else f"{len(failures)} FAILURE(S)")
finally:
    for p in reversed(procs):
        p.terminate()
    for p in reversed(procs):
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
sys.exit(1 if failures else 0)
