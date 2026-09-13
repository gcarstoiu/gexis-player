STAGE_GEXIS_DIR := $(CURDIR)/image/stage-gexis
CORE_SRC_DIR := $(CURDIR)/core
UI_DIST_DIR := $(CURDIR)/ui/dist
PEPPYALSA_REPO := https://github.com/project-owner/peppyalsa
PEPPYALSA_COMMIT := $(shell grep -oP 'git checkout \K[0-9a-f]{40}' image/stage-gexis/00-alsa/01-run-chroot.sh)
GO_LIBRESPOT_REPO := https://github.com/devgianlu/go-librespot
GO_LIBRESPOT_VERSION := $(shell grep -oP 'GO_LIBRESPOT_VERSION="\K[^"]+' image/stage-gexis/02-renderers/01-run.sh)
# Every build gets a version, tagged or not. `--tags --always --dirty`:
# an annotated/lightweight tag on HEAD gives a clean "vX.Y.Z"; without
# one, falls back to the short commit hash rather than failing the
# build outright; "-dirty" if the working tree has uncommitted changes,
# so a manifest can never claim a version it wasn't actually built from.
IMAGE_VERSION := $(shell git describe --tags --always --dirty)

.PHONY: image ui clean provision

# Builds via pi-gen's own build-docker.sh, unmodified. Our custom stage lives
# outside the pinned pi-gen submodule and is bind-mounted in at build time
# (see image/config's STAGE_LIST and image/README.md).
#
# peppyalsa and go-librespot aren't apt packages, so pi-gen's own manifest
# (the .info file, dpkg -l) doesn't cover them. Their pinned versions, the
# image version, and the wall-clock build time are appended here, on the
# host, after the fact — not inside pi-gen.
#
# Filenames carry the version too, 2026-09-11 (George asked after the
# first several builds only had a date to tell them apart). pi-gen's own
# IMG_FILENAME/ARCHIVE_FILENAME default to "${IMG_DATE}-${IMG_NAME}", and
# both are freely overridable - but overriding them directly would need
# git access *inside* the container to compute IMAGE_VERSION, which isn't
# there (only stage-gexis/ and core/ are bind-mounted, not this repo's
# .git - the same reason image/config itself never tried to compute a
# version despite being sourced both host-side and container-side).
# IMG_SUFFIX sidesteps that: pi-gen exports it with no default of its own
# (build.sh's `export IMG_SUFFIX`, unset unless something provides one -
# only stage4/5's own EXPORT_IMAGE files ever set it, and neither stage
# is in our STAGE_LIST) and appends it to every export-image filename
# (.img, .info, .sbom, .bmap, and whichever compressed archive
# DEPLOY_COMPRESSION picks - .zip by default). Passed in via
# PIGEN_DOCKER_OPTS's own `-e` (confirmed this reaches the container
# intact, unlike a plain host-side environment variable, which docker run
# does not inherit automatically) rather than editing build-docker.sh -
# same "don't hand-edit the pinned submodule" reasoning as the
# EXPORT_IMAGE removal below. Result: `2026-09-11-gexis-player-v0.2.1-
# 28-ge916f86-dirty.img`/`.zip` instead of just the date - the manifest
# lookup glob below was widened (`*-gexis-player.info` ->
# `*-gexis-player*.info`) to still find it.
#
# Two speed changes, 2026-09-08 (HANDOFF.md has the measured numbers):
#
# 1. stage2/EXPORT_IMAGE (a file inside the pinned pi-gen submodule) makes
#    pi-gen export a second, unused "-lite" checkpoint image - a full
#    loop-device/zerofree/compress cycle (measured: 6m41s) for an artefact
#    nobody consumes. Removed here, at build time, rather than edited
#    in-place in the submodule: a submodule's working-tree edit isn't
#    durably committable in this repo and `git submodule update` would
#    silently discard it, restoring the wasted export with no warning.
#    Idempotent - safe whether or not the file is already gone.
#
# 2. CONTINUE=1/PRESERVE_CONTAINER=1 (both build-docker.sh's own, documented
#    flags) reuse the previous build's container and volumes instead of
#    starting from scratch, letting pi-gen skip re-populating any stage
#    whose own inputs haven't changed - stage0-2 (the base OS, ~20 minutes)
#    for the common case where only stage-gexis/core changed. Safe on a
#    first/cold build too: CONTINUE=1 only changes behaviour when a
#    container from a previous run actually exists. The trade-off: a
#    successful build now leaves the container behind on purpose (it no
#    longer self-cleans) - `make clean` is how you force a truly fresh
#    build, not just how you recover from a failed one; see its own
#    comment below.

# ADR-0023's stated cost: "the image build gains a Node build step. Node is
# already on the dev machine; the image pipeline needs it at build time, not
# at runtime." So the UI is compiled here, on the host, and the image ships
# only the static output - no Node, no npm, no toolchain on the device, and
# no npm install under QEMU emulation (which would be slow and would put a
# network fetch inside the image build).
#
# `npm ci` rather than `npm install`: it installs exactly what
# package-lock.json pins and fails if the two disagree, which is the same
# pin-and-verify discipline the rest of this build applies to peppyalsa,
# go-librespot and alsa-lib.
ui:
	cd ui && npm ci && npm run build

image: ui
	@rm -f image/pi-gen/stage2/EXPORT_IMAGE; \
	start=$$(date +%s); \
	( cd image && CONTINUE=1 PRESERVE_CONTAINER=1 PIGEN_DOCKER_OPTS="--volume $(STAGE_GEXIS_DIR):/pi-gen/stage-gexis:ro --volume $(CORE_SRC_DIR):/pi-gen/gexis-core-src:ro --volume $(UI_DIST_DIR):/pi-gen/gexis-ui-dist:ro -e IMG_SUFFIX=-$(IMAGE_VERSION)" \
		./pi-gen/build-docker.sh -c config ); \
	status=$$?; \
	end=$$(date +%s); \
	elapsed=$$((end - start)); \
	echo "Build took $${elapsed}s"; \
	if [ $$status -ne 0 ]; then exit $$status; fi; \
	info=$$(ls -t image/deploy/*-gexis-player*.info 2>/dev/null | grep -v -- '-lite\.info$$' | head -1); \
	if [ -n "$$info" ]; then \
		{ echo ""; \
		  echo "Image version: $(IMAGE_VERSION)"; \
		  echo "peppyalsa: $(PEPPYALSA_COMMIT) ($(PEPPYALSA_REPO))"; \
		  echo "go-librespot: $(GO_LIBRESPOT_VERSION) ($(GO_LIBRESPOT_REPO))"; \
		  echo "Build time: $${elapsed}s"; \
		} >> "$$info"; \
		echo "Annotated $$info with image version ($(IMAGE_VERSION)), peppyalsa commit, go-librespot version, and build time"; \
	else \
		echo "WARNING: could not find deploy manifest (image/deploy/*-gexis-player.info) to annotate"; \
	fi

clean:
	# Two reasons to remove the container, not just one since
	# PRESERVE_CONTAINER=1 (image target, 2026-09-08): a failed run's
	# leftover pigen_work blocks the next attempt with "Container
	# pigen_work already exists" regardless of PRESERVE_CONTAINER,
	# which looks unrelated to whatever actually failed - recovery
	# shouldn't depend on a human remembering that; and a *successful*
	# run now leaves pigen_work around on purpose, for CONTINUE=1 to
	# reuse next time, so this is also the only way left to force a
	# truly from-scratch build (a stale pi-gen submodule bump, a
	# suspected caching bug, or just wanting a clean-room result).
	# "pigen_work" is build-docker.sh's own default CONTAINER_NAME;
	# harmless if it doesn't exist.
	docker rm -v pigen_work 2>/dev/null || true
	rm -rf image/deploy

# Fills in a flashed card's firstrun.sh from image/provision.local.env and
# clears its stale SSH host key entry. See image/README.md.
provision:
	@if [ -z "$(DEVICE)" ]; then \
		echo "Usage: make provision DEVICE=/dev/sdX  (whole disk, not a partition — never guessed)" >&2; \
		exit 1; \
	fi
	./image/provision.sh "$(DEVICE)"
