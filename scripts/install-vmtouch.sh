#!/usr/bin/env sh

mkdir -p /opt
cd /opt

git clone --depth 1 --recursive https://github.com/hoytech/vmtouch.git --branch v1.3.1
cd vmtouch
make
make install
