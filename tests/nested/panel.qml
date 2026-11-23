// Stand-in for an always-visible Plasma panel: a top layer-shell surface with an exclusive zone.
import QtQuick
import org.kde.layershell 1.0 as LayerShell

Window {
    width: 1920
    height: 56
    visible: true
    color: "#ff0000"
    LayerShell.Window.scope: "dock"
    LayerShell.Window.layer: LayerShell.Window.LayerTop
    LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorLeft | LayerShell.Window.AnchorRight
    LayerShell.Window.exclusionZone: 56
}
