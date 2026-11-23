"""Minimal org.kde.plasmashell /StrutManager: Yakuake asks it for the screen area left by panels."""
import sys

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

x, y, w, h = (int(v) for v in sys.argv[1:5])


class StrutManager(dbus.service.Object):
    @dbus.service.method("org.kde.PlasmaShell.StrutManager", in_signature="s", out_signature="(iiii)")
    def availableScreenRect(self, screen):
        return (x, y, w, h)


DBusGMainLoop(set_as_default=True)
name = dbus.service.BusName("org.kde.plasmashell", dbus.SessionBus())
StrutManager(dbus.SessionBus(), "/StrutManager")
GLib.MainLoop().run()
