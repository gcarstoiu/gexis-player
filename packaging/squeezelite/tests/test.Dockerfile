# ADR-0145: the decoder tests' container - amd64 Debian trixie, the same release
# and libraries as the device, natively on the build machine: Squeezelite's
# Build-Depends, and what makes the test files (flac, sox, ffmpeg).
FROM debian:trixie
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential pkg-config git ca-certificates dpkg-dev libasound2-dev \
  libavformat-dev libfaad-dev libflac-dev liblirc-dev libmad0-dev libmpg123-dev \
  libopus-dev libopusfile-dev libsoxr-dev libssl-dev libvorbis-dev \
  python3 python3-numpy ffmpeg flac sox \
 && rm -rf /var/lib/apt/lists/*
