#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Run inside debian:trixie with a Pibuz checkout at /src (Finding 097):
#   git clone --branch v2.5.1 https://github.com/PhilipVinc/pibuz src
#   docker run --rm -v "$PWD/src:/src" -v "$PWD/image/tools/build-pibuz-dev.sh:/build.sh" \
#     -v gexis-pibuz-cargo:/root/.cargo/registry debian:trixie /build.sh
# Output: src/target/aarch64-unknown-linux-gnu/release/pibuz (1 min 38 s of
# compiling on the build host, 2026-09-28).
#
# Dev build of Pibuz from its tagged source, for gexis only (George, 2026-09-28:
# "You can build 2.5.1 for dev purposes"). Cross-compiled in Debian trixie, the
# device's own release, so it links against the glibc gexis has.
set -euo pipefail
dpkg --add-architecture arm64
apt-get update -qq
apt-get install -y -qq curl ca-certificates build-essential pkg-config gcc-aarch64-linux-gnu libc6-dev-arm64-cross libasound2-dev:arm64 >/dev/null
curl -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain stable >/dev/null
. "$HOME/.cargo/env"
rustup target add aarch64-unknown-linux-gnu
cd /src
export PKG_CONFIG_ALLOW_CROSS=1 PKG_CONFIG_SYSROOT_DIR=/ PKG_CONFIG_PATH=/usr/lib/aarch64-linux-gnu/pkgconfig
export CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc CC_aarch64_unknown_linux_gnu=aarch64-linux-gnu-gcc AR_aarch64_unknown_linux_gnu=aarch64-linux-gnu-ar
cargo build --release --locked -p pibuz --target aarch64-unknown-linux-gnu
rustc --version
