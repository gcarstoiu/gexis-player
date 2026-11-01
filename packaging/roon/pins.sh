# The pin for roon (ADR-0107): the one place it is written. Read by
# packaging/roon/build.sh. Roon Bridge itself is not pinned (ADR-0172
# decision 5): image/stage-gexis/14-roon/files/components/roonbridge.env.
PLUGIN_VERSION="0.1.0"
PLUGIN_ASSET="gexis-roon-${PLUGIN_VERSION}.tar.gz"
PLUGIN_URL="https://github.com/gcarstoiu/gexis-roon/releases/download/v${PLUGIN_VERSION}/${PLUGIN_ASSET}"
PLUGIN_SHA256="4d8d6b163d5e61af6caeca718b065a8ee76618c9dc1ddaf9bf2a0df7a0d127ef"
