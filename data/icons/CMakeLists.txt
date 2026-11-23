foreach(size 16 22 32 48 64 128 256)
    install(FILES ${size}-apps-yakuake.png
            DESTINATION ${KDE_INSTALL_ICONDIR}/hicolor/${size}x${size}/apps
            RENAME myyakuake.png)
endforeach()
