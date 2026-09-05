STAGE_GEXIS_DIR := $(CURDIR)/image/stage-gexis
PEPPYALSA_REPO := https://github.com/project-owner/peppyalsa
PEPPYALSA_COMMIT := $(shell grep -oP 'git checkout \K[0-9a-f]{40}' image/stage-gexis/00-alsa/01-run-chroot.sh)

.PHONY: image clean provision

# Builds via pi-gen's own build-docker.sh, unmodified. Our custom stage lives
# outside the pinned pi-gen submodule and is bind-mounted in at build time
# (see image/config's STAGE_LIST and image/README.md).
#
# peppyalsa isn't an apt package, so pi-gen's own manifest (the .info file,
# dpkg -l) doesn't cover it. Its pinned commit and the wall-clock build time
# are appended here, on the host, after the fact — not inside pi-gen.
image:
	@start=$$(date +%s); \
	( cd image && PIGEN_DOCKER_OPTS="--volume $(STAGE_GEXIS_DIR):/pi-gen/stage-gexis:ro" \
		./pi-gen/build-docker.sh -c config ); \
	status=$$?; \
	end=$$(date +%s); \
	elapsed=$$((end - start)); \
	echo "Build took $${elapsed}s"; \
	if [ $$status -ne 0 ]; then exit $$status; fi; \
	info=$$(ls image/deploy/*-gexis-player.info 2>/dev/null | grep -v -- '-lite\.info$$'); \
	if [ -n "$$info" ]; then \
		{ echo ""; \
		  echo "peppyalsa: $(PEPPYALSA_COMMIT) ($(PEPPYALSA_REPO))"; \
		  echo "Build time: $${elapsed}s"; \
		} >> "$$info"; \
		echo "Annotated $$info with peppyalsa commit and build time"; \
	else \
		echo "WARNING: could not find deploy manifest (image/deploy/*-gexis-player.info) to annotate"; \
	fi

clean:
	rm -rf image/deploy

# Fills in a flashed card's firstrun.sh from image/provision.local.env and
# clears its stale SSH host key entry. See image/README.md.
provision:
	@if [ -z "$(DEVICE)" ]; then \
		echo "Usage: make provision DEVICE=/dev/sdX  (whole disk, not a partition — never guessed)" >&2; \
		exit 1; \
	fi
	./image/provision.sh "$(DEVICE)"
