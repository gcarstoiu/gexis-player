git clone https://github.com/project-owner/peppyalsa.git /tmp/peppyalsa
cd /tmp/peppyalsa
git checkout 7dcb0c5e783e0c86315a0f655684613affd3e9d2

# **One write per spectrum frame, instead of one per band** (Finding 052).
# Upstream sends the thirty bands as thirty 4-byte writes, so the FIFO is a
# plain byte stream with nothing in it to mark where a frame starts. A reader
# whose poll lands part-way through one splices the tail of that frame onto
# the head of the next, and the bars at one end of the display show bands
# from the other. A write of at most PIPE_BUF is atomic, and a frame is well
# under that, so writing it in one call makes the pipe record-oriented.
#
# `git apply` and not `patch`: it fails loudly on a mismatch, which is what
# should happen if the pinned commit above is ever moved.
git apply --verbose /tmp/peppyalsa-one-write-per-frame.patch
grep -q 'frame_buffer' src/spectrum.c || { echo "ERROR: the peppyalsa patch did not apply" >&2; exit 1; }
rm -f /tmp/peppyalsa-one-write-per-frame.patch

aclocal
libtoolize
autoconf
automake --add-missing
./configure --prefix=/usr
make
make install

cd /
rm -rf /tmp/peppyalsa
