STAGE_GEXIS_DIR := $(CURDIR)/image/stage-gexis

.PHONY: image clean

# Builds via pi-gen's own build-docker.sh, unmodified. Our custom stage lives
# outside the pinned pi-gen submodule and is bind-mounted in at build time
# (see image/config's STAGE_LIST and image/README.md).
image:
	cd image && PIGEN_DOCKER_OPTS="--volume $(STAGE_GEXIS_DIR):/pi-gen/stage-gexis:ro" \
		./pi-gen/build-docker.sh -c config

clean:
	rm -rf image/deploy
