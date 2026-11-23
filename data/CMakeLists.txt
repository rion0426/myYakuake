add_subdirectory(icons)
add_subdirectory(skins)

# Installed under myYakuake names so the package coexists with the distribution's Yakuake.
ecm_generate_dbus_service_file(
    NAME org.kde.myyakuake
    EXECUTABLE ${KDE_INSTALL_FULL_BINDIR}/myyakuake
    DESTINATION ${KDE_INSTALL_DBUSSERVICEDIR}
)

install(FILES org.kde.yakuake.desktop DESTINATION ${KDE_INSTALL_APPDIR} RENAME org.kde.myyakuake.desktop)
install(FILES yakuake.notifyrc DESTINATION ${KDE_INSTALL_KNOTIFYRCDIR} RENAME myyakuake.notifyrc)
