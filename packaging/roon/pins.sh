# The pin for roon (ADR-0107): the one place it is written. Read by
# packaging/roon/build.sh. Roon Bridge itself is not pinned (ADR-0172
# decision 5): image/stage-gexis/14-roon/files/components/roonbridge.env.
PLUGIN_VERSION="0.2.1"
PLUGIN_ASSET="gexis-roon-${PLUGIN_VERSION}.tar.gz"
PLUGIN_URL="https://github.com/gcarstoiu/gexis-roon/releases/download/v${PLUGIN_VERSION}/${PLUGIN_ASSET}"
PLUGIN_SHA256="414b5dedaffab5f1c9e0b37955cc54e1ad6b0661fbab67d2f221a22f04efb3b5"
