# The pin for beszel-agent (ADR-0107): the one place it is written. Read by
# packaging/beszel-agent/build.sh and by the Makefile's image annotation.
BESZEL_VERSION="v0.21.0"
BESZEL_ASSET="beszel-agent_linux_arm64.tar.gz"
BESZEL_URL="https://github.com/henrygd/beszel/releases/download/${BESZEL_VERSION}/${BESZEL_ASSET}"
BESZEL_SHA256="82804205a370a790679e836c3c3d658bc804205517e1c3f676dba9fad064ade5"
