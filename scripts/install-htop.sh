#!/usr/bin/env sh

yum -y install ncurses ncurses-devel wget
wget http://hisham.hm/htop/releases/2.0.2/htop-2.0.2.tar.gz
tar xvfvz htop-2.0.2.tar.gz
cd htop-2.0.2
./configure
make
make install
cd ..
rm -rf htop-2.0.2*