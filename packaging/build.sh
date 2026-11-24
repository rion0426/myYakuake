#!/usr/bin/env bash
# Build the myYakuake RPM: upstream release tarball + diff of this branch against the release tag.
# One-time setup: sudo dnf builddep packaging/myYakuake.spec
set -euo pipefail

repo=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
spec=$repo/packaging/myYakuake.spec
version=$(rpmspec -q --qf '%{VERSION}\n' --srpm "$spec")
# Build tree inside the repo (ignored by /build*/ in .gitignore) instead of ~/rpmbuild.
topdir=$repo/build-rpm

mkdir -p "$topdir/SOURCES"
tarball=$topdir/SOURCES/yakuake-$version.tar.xz
[[ -f $tarball ]] || curl -fL -o "$tarball" "https://download.kde.org/stable/release-service/$version/src/yakuake-$version.tar.xz"

git -C "$repo" diff "v$version"..HEAD -- . ':!packaging' ':!tests' > "$topdir/SOURCES/myYakuake.patch"

# Only the latest build is kept; installed releases are upgraded in place by dnf anyway.
rm -f "$topdir"/RPMS/*/myYakuake-*.rpm
rpmbuild --define "_topdir $topdir" -bb "$spec"
echo "RPMs: $topdir/RPMS"
