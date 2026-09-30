# ADR-0107: every package is built here - arm64 Debian trixie, the device's
# own architecture and Python (3.13), under qemu on the build machine.
FROM arm64v8/debian:trixie
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      python3 python3-venv python3-pip python3-pil dpkg-dev fakeroot ca-certificates apt-utils gnupg \
      curl libarchive-tools unzip git \
      build-essential automake autoconf libtool pkg-config libasound2-dev libfftw3-dev \
 && rm -rf /var/lib/apt/lists/*
