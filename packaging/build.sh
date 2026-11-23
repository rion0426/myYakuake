#!/usr/bin/env bash
# Build the myYakuake RPM: upstream release tarball + diff of this branch against the release tag.
# One-time setup: sudo dnf builddep packaging/myYakuake.spec
set -euo pipefail

repo=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
spec=$repo/packaging/myYakuake.spec
version=$(rpmspec -q --qf '%{VERSION}\n' --srpm "$spec")
topdir=$(rpm --eval '%{_topdir}')

mkdir -p "$topdir/SOURCES"
tarball=$topdir/SOURCES/yakuake-$version.tar.xz
[[ -f $tarball ]] || curl -fL -o "$tarball" "https://download.kde.org/stable/release-service/$version/src/yakuake-$version.tar.xz"

git -C "$repo" diff "v$version"..HEAD -- app/ > "$topdir/SOURCES/myYakuake.patch"

rpmbuild -bb "$spec"
