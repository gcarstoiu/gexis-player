#!/bin/bash -e

# The release and everything it names. apt resolves the operating system's
# packages from the archives, as the stages' package lists did (with
# Recommends, as pi-gen's 00-packages installs them), and ours from the local
# files - the exact versions gexis-player depends on.
apt-get -o Acquire::Retries=3 install -y /tmp/gexis-debs/*.deb
rm -rf /tmp/gexis-debs

installed="$(dpkg-query -W -f='${Version}' gexis-player)"
echo "gexis-player ${installed} installed"
