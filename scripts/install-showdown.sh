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
    if [ -z "$(eval echo \$no_${repo})" ]; then
      uri=$(eval echo \$showdown_${repo}_uri)
      sha=$(eval echo \$showdown_${repo}_sha)
      dir=$(eval echo \$showdown_${repo}_dir)

      git clone $uri $dir
      pushd $dir
      git checkout $sha
      popd

      if [ "$repo" = "server" ]; then
        pushd $showdown_server_dir
        npm install --production
        ./pokemon-showdown -h
        popd
      fi
    else 
      echo "Not installing $repo"
    fi
  done
}

parse_args() {
  no_server=
  no_client=

  while [ "$1" != "" ]; do
    case "$1" in 
      --no-server) no_server=1; shift; ;;
      --no-client) no_client=1; shift; ;;
      *) die "Unknown flag: $1" ;;
    esac
  done
}

main() {
  start_unsafe
  start_safe

  import_config

  install_node
  install_showdown
}

parse_args $*
main