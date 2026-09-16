STAGE_GEXIS_DIR := $(CURDIR)/image/stage-gexis
CORE_SRC_DIR := $(CURDIR)/core
UI_DIST_DIR := $(CURDIR)/ui/dist
IMG_NAME := $(shell grep -oP '^IMG_NAME="\K[^"]+' image/config)
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

.PHONY: image ui skins prune fetch-deploy clean provision

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

# Reclaim the two places PRESERVE_CONTAINER=1 lets whole images pile up,
# 2026-09-13. Measured before this existed: 2.2GB in deploy/ and 8.3GB in
# export-image/, from two builds.
#
# 1. deploy/ - build-docker.sh:154 copies this entire directory to the host
#    on every run (`docker cp … | tar -xf -`), so last build's output is
#    re-streamed forever. Already on the host in image/deploy/, which this
#    does NOT touch: the host copy is the artefact you keep.
#
# 2. export-image/*.img - the raw image, which pi-gen's own
#    export-image/prerun.sh deletes and recreates every run. It only ever
#    removes "${IMG_FILENAME}${IMG_SUFFIX}.img", and IMG_SUFFIX is our
#    git-describe version (see the IMAGE_VERSION comment above), different
#    on every build - so prerun's cleanup misses every previous version and
#    each leaks ~4.5GB. Stock pi-gen doesn't have this problem; our
#    versioning introduced it.
#
# Neither is a build cache. The warm build comes from the stage rootfs
# trees (stage0/1/2 and stage-gexis, ~8.1GB), which are untouched here -
# as is the container itself, so CONTINUE=1 still resumes. `make clean` is
# still the only thing that forces a cold build.
#
# Runs before the build, not after, so a failed build leaves its artefacts
# in place to inspect. Reads the volumes through --volumes-from rather than
# by name: they are anonymous, and their hashes change whenever the
# container is recreated. Never `docker start pigen_work` to get at them -
# that re-runs pi-gen's entrypoint and starts a build.
prune:
	@if docker container inspect pigen_work >/dev/null 2>&1; then \
		before=$$(docker run --rm --volumes-from pigen_work pi-gen:latest \
			sh -c 'du -sb /pi-gen/deploy /pi-gen/work/*/export-image 2>/dev/null | awk "{s+=\$$1} END {print s+0}"'); \
		docker run --rm --volumes-from pigen_work pi-gen:latest \
			sh -c 'rm -f /pi-gen/deploy/* /pi-gen/work/*/export-image/*.img /pi-gen/work/*/export-image/*.info'; \
		after=$$(docker run --rm --volumes-from pigen_work pi-gen:latest \
			sh -c 'du -sb /pi-gen/deploy /pi-gen/work/*/export-image 2>/dev/null | awk "{s+=\$$1} END {print s+0}"'); \
		echo "Pruned previous builds from the container: $$(( (before - after) / 1024 / 1024 ))MB reclaimed"; \
	else \
		echo "No pigen_work container - nothing to prune"; \
	fi

# Phase 5 criterion 2: an unknown key or meter.type fails the build here,
# because the vendored PeppyMeter cannot fail on one at parse time
# (Finding 007 section 4) - it would surface as a KeyError when someone
# selects the skin.
skins:
	python3 -c "import sys; sys.path.insert(0, 'core/src'); from gexis_core.skins import main; raise SystemExit(main(['skins']))"

image: ui skins prune
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

# Recover a build whose copy-out was killed. Run `make fetch-deploy`.
#
# build-docker.sh:154 ends every build with
#     ${DOCKER} cp "${CONTAINER_NAME}":/pi-gen/deploy - | tar -xf -
# streaming the whole deploy directory through a pipe. Under host memory
# pressure that is the step that dies - observed twice, 2026-09-13, both
# times with the build itself already complete ("Build finished" in the
# log, image intact in the volume). It is heavier since
# DEPLOY_COMPRESSION=none: 4.5GB streamed rather than 1.28GB.
#
# This has to be a separate target rather than a fallback inside `image`.
# The signal reaches make itself - the log reads
#     make: *** [Makefile:...: image] Terminated
# so by the time the copy has failed there is no recipe left running to
# recover from it.
#
# Copying one file at a time avoids the tar pipe entirely and does not get
# killed (measured: 44s for a 4.5GB image). Then it applies the same
# manifest annotation the `image` target appends, since that step runs
# after the copy and is skipped for exactly the same reason.
#
# The version is read back off the artefact's own filename, not from
# IMAGE_VERSION: a recovery run can happen after the working tree has
# moved on, and a manifest must never claim a version it wasn't built
# from. Build time likewise comes from the recovered build.log rather than
# being re-measured, and is labelled as pi-gen's own elapsed time. That
# log accumulates across CONTINUE=1 runs, so the window is the *last*
# "Begin /pi-gen/stage0" to the *last* "Build finished", and only when the
# second follows the first - otherwise a killed run would be paired with
# an earlier run's ending and report a fabricated duration. (First cut of
# this reported 4186s for a 749s build, for exactly that reason.)
#
# Re-running is safe and cheap: a file already present at the container's
# size is skipped, so only the .info is re-copied - it is always smaller
# in the container than on the host, because the host's has this
# annotation appended - and then re-annotated. The net result is stable,
# one annotation block, image untouched.
fetch-deploy:
	@if ! docker container inspect pigen_work >/dev/null 2>&1; then \
		echo "No pigen_work container - nothing to recover" >&2; exit 1; \
	fi; \
	list=$$(mktemp); trap 'rm -f "$$list"' EXIT; \
	docker run --rm --volumes-from pigen_work pi-gen:latest \
		sh -c 'find /pi-gen/deploy -maxdepth 1 -type f -printf "%f %s\n" 2>/dev/null' > "$$list"; \
	if [ ! -s "$$list" ]; then echo "Container deploy/ is empty - nothing to recover" >&2; exit 1; fi; \
	mkdir -p image/deploy; \
	while read -r f size; do \
		have=$$(stat -c %s "image/deploy/$$f" 2>/dev/null || echo -1); \
		if [ "$$have" = "$$size" ]; then echo "  have   $$f"; continue; fi; \
		echo "  fetch  $$f"; \
		docker cp "pigen_work:/pi-gen/deploy/$$f" "image/deploy/$$f" || exit 1; \
	done < "$$list"; \
	info=$$(ls -t image/deploy/*-$(IMG_NAME)*.info 2>/dev/null | head -1); \
	if [ -z "$$info" ]; then echo "WARNING: no manifest found to annotate"; exit 0; fi; \
	version=$$(basename "$$info" .info | sed 's/^[0-9-]*-$(IMG_NAME)-//'); \
	elapsed=$$(awk -F'[][]' '\
		/Begin \/pi-gen\/stage0$$/ {start=$$2; sline=NR} \
		/Build finished$$/ {end=$$2; eline=NR} \
		END{if(start&&end&&eline>sline){split(start,a,":");split(end,b,":"); \
			d=(b[1]*3600+b[2]*60+b[3])-(a[1]*3600+a[2]*60+a[3]); if(d<0)d+=86400; print d}}' \
		image/deploy/build.log 2>/dev/null); \
	{ echo ""; \
	  echo "Image version: $$version"; \
	  echo "peppyalsa: $(PEPPYALSA_COMMIT) ($(PEPPYALSA_REPO))"; \
	  echo "go-librespot: $(GO_LIBRESPOT_VERSION) ($(GO_LIBRESPOT_REPO))"; \
	  echo "Build time: $${elapsed:-unknown}s (pi-gen elapsed, recovered via make fetch-deploy)"; \
	} >> "$$info"; \
	echo "Annotated $$info with image version ($$version), peppyalsa commit, go-librespot version, and build time"

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
