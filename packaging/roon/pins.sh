# The pin for roon (ADR-0107): the one place it is written. Read by
# packaging/roon/build.sh. Roon Bridge itself is not pinned (ADR-0172
# decision 5): image/stage-gexis/14-roon/files/components/roonbridge.env.
PLUGIN_VERSION="0.2.0"
PLUGIN_ASSET="gexis-roon-${PLUGIN_VERSION}.tar.gz"
PLUGIN_URL="https://github.com/gcarstoiu/gexis-roon/releases/download/v${PLUGIN_VERSION}/${PLUGIN_ASSET}"
PLUGIN_SHA256="60f2651ef589b2a4fe69c924a2b0cf1e9a3998e94e7751ae0bafb2499aec124f"
