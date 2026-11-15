# The pin for go-librespot (ADR-0107): the one place it is written. Read by
# packaging/go-librespot/build.sh and by the Makefile's image annotation.
# ADR-0181: upstream's own build of its master at 775ba5883 (its workflow's run
# 43070007237, 2026-11-11), which fixes the Android app closing (upstream issue
# 434) before any release does. Upstream keeps that build 7 days, so it is
# fetched from our `inputs` mirror; the first release containing the commit
# replaces it (check-upstream.sh says when).
GO_LIBRESPOT_VERSION="v0.10.5+git20261111.775ba58"
GO_LIBRESPOT_COMMIT="775ba588394ce8f3c983447cbc73e73a53ec545c"
GO_LIBRESPOT_ASSET="go-librespot_linux_arm64.tar.gz"
GO_LIBRESPOT_URL="https://github.com/gcarstoiu/gexis-player/releases/download/inputs/6bc182075bb3037896001707037f9de91030988a5a1489295fdee32c5953127b"
GO_LIBRESPOT_SHA256="6bc182075bb3037896001707037f9de91030988a5a1489295fdee32c5953127b"
