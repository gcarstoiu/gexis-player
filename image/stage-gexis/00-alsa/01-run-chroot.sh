git clone https://github.com/project-owner/peppyalsa.git /tmp/peppyalsa
cd /tmp/peppyalsa
git checkout 7dcb0c5e783e0c86315a0f655684613affd3e9d2

aclocal
libtoolize
autoconf
automake --add-missing
./configure --prefix=/usr
make
make install

cd /
rm -rf /tmp/peppyalsa
