#!/usr/bin/env sh

. scripts/predef

install_node() {
  load_nvm

  # nvm.sh depends on some errors falling through
  start_unsafe
  nvm install $node_version
  start_safe
}

install_showdown() {
  # Clone both repos
  mkdir -p $showdown_root
  pushd $showdown_root
  for repo in server client; do
    uri=$(eval echo \$showdown_${repo}_uri)
    sha=$(eval echo \$showdown_${repo}_sha)
    dir=$(eval echo \$showdown_${repo}_dir)

    git clone $uri $dir
    pushd $dir
    git checkout $sha
    popd
  done

  # Set up the server repo
  pushd $showdown_server_dir
  npm install --production
  ./pokemon-showdown -h
  popd
}

main() {
  if [ "$1" = "unsafe" ]; then
    set_unsafe
  else
    set_safe
  fi

  start_unsafe
  start_safe

  import_config

  install_node
  install_showdown
}

main