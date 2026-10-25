# The pin for beszel-agent (ADR-0107): the one place it is written. Read by
# packaging/beszel-agent/build.sh and by the Makefile's image annotation.
BESZEL_VERSION="v0.21.1"
BESZEL_ASSET="beszel-agent_linux_arm64.tar.gz"
BESZEL_URL="https://github.com/henrygd/beszel/releases/download/${BESZEL_VERSION}/${BESZEL_ASSET}"
BESZEL_SHA256="a6ea544976b9a74398ac88d5da5bb96813d9a2e353a37bbfdb6a903fa8ba1838"
