# The pin for roon (ADR-0107): the one place it is written. Read by
# packaging/roon/build.sh. Roon Bridge itself is not pinned (ADR-0172
# decision 5): image/stage-gexis/14-roon/files/components/roonbridge.env.
PLUGIN_VERSION="0.1.0"
PLUGIN_ASSET="gexis-roon-${PLUGIN_VERSION}.tar.gz"
PLUGIN_URL="https://github.com/gcarstoiu/gexis-roon/releases/download/v${PLUGIN_VERSION}/${PLUGIN_ASSET}"
PLUGIN_SHA256="7c7a7bc96cb11c99248ae994544397cfdc4e9fd814718ee9fe2075bbddd1c0ea"
