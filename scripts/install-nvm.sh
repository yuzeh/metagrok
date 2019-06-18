#!/usr/bin/env sh

. scripts/predef

set -e

import_config

curl https://raw.githubusercontent.com/creationix/nvm/v0.34.0/install.sh | bash
export NVM_DIR=/root/.nvm
. $NVM_DIR/nvm.sh
nvm install $node_version
nvm alias default $node_version
nvm use default