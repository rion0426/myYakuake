/*
  SPDX-FileCopyrightText: 2008-2014 Eike Hein <hein@kde.org>

  SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
*/

#include "mainwindow.h"

#include <KAboutData>
#include <KCrash>
#include <KDBusService>
#include <KLocalizedString>

#include <QApplication>
#include <QCommandLineParser>

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);
    app.setQuitOnLastWindowClosed(false);

    // Own component name: separate config (myyakuakerc), data dir, D-Bus service
    // (org.kde.myyakuake), Wayland app id and global shortcuts, so it runs next to Yakuake.
    KLocalizedString::setApplicationDomain(QByteArrayLiteral("myyakuake"));

    KAboutData aboutData(QStringLiteral("myyakuake"),
                         QStringLiteral("myYakuake"),
                         QStringLiteral(YAKUAKE_VERSION),
                         xi18nc("@title", "A drop-down terminal emulator based on KDE Konsole technology."),
                         KAboutLicense::GPL,
                         xi18nc("@info:credit", "(c) 2008-2018 The Yakuake Team"),
                         QString(),
                         QStringLiteral("https://github.com/rion0426/myYakuake"));

    aboutData.setOrganizationDomain(QByteArray("kde.org"));
    // The default is derived from the homepage (com.github.…); the app id must match the desktop file.
    aboutData.setDesktopFileName(QStringLiteral("org.kde.myyakuake"));
    aboutData.setProductName(QByteArray("myyakuake"));

    aboutData.addAuthor(xi18nc("@info:credit", "Eike Hein"), xi18nc("@info:credit", "Maintainer, Lead Developer"), QStringLiteral("hein@kde.org"));
    aboutData.addAuthor(xi18nc("@info:credit", "Francois Chazal"), xi18nc("@info:credit", "Project Founder, Legacy skin (Inactive)"));
    aboutData.addCredit(xi18nc("@info:credit", "Daniel 'suslik' D."), xi18nc("@info:credit", "Plastik skin"), QStringLiteral("dd@accentsolution.com"));
    aboutData.addCredit(xi18nc("@info:credit", "Juan Carlos Torres"),
                        xi18nc("@info:credit", "Tab bar drag and drop support, Prevent Closing toggle"),
                        QStringLiteral("carlosdgtorres@gmail.com"));
    aboutData.addCredit(xi18nc("@info:credit", "Gustavo Ribeiro Croscato"),
                        xi18nc("@info:credit", "Icon on tabs with Prevent Closing enabled"),
                        QStringLiteral("croscato@gmail.com"));
    aboutData.addCredit(xi18nc("@info:credit", "Danilo Cesar Lemes de Paula"),
                        xi18nc("@info:credit", "Actions to grow terminals"),
                        QStringLiteral("danilo.eu@gmail.com"));

    aboutData.setTranslator(i18nc("NAME OF TRANSLATORS", "Your names"), i18nc("EMAIL OF TRANSLATORS", "Your emails"));

    KAboutData::setApplicationData(aboutData);
    QCommandLineParser parser;

    aboutData.setupCommandLine(&parser);
    parser.process(app);
    aboutData.processCommandLine(&parser);

    app.setWindowIcon(QIcon::fromTheme(QStringLiteral("myyakuake")));

    KDBusService service(KDBusService::Unique);

    KCrash::initialize();
    MainWindow mainWindow;
    mainWindow.hide();
    QObject::connect(&service, &KDBusService::activateRequested, &mainWindow, &MainWindow::toggleWindowState);

    return app.exec();
}
