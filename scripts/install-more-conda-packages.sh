#!/usr/bin/env sh

# For convenience, any conda package installs during dev time should be added here to avoid 
# triggering a full rebuild of the Docker container. However, this file should contain no executable
# commands at commit time.

# conda install tqdm