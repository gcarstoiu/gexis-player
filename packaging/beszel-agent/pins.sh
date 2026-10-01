# The pin for beszel-agent (ADR-0107): the one place it is written. Read by
# packaging/beszel-agent/build.sh and by the Makefile's image annotation.
BESZEL_VERSION="v0.20.0"
BESZEL_ASSET="beszel-agent_linux_arm64.tar.gz"
BESZEL_URL="https://github.com/henrygd/beszel/releases/download/${BESZEL_VERSION}/${BESZEL_ASSET}"
BESZEL_SHA256="dbb292d7309ca00cfd7f3d8f86480991f7c959e65af6506754a55d3e345452ab"
