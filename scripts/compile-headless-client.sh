#!/usr/bin/env sh

. scripts/predef

test_compile_working() {
  ./rp metagrok/pkmn/engine/test_engine.py
}

main() {
  start_safe

  import_config

  load_nvm

  start_unsafe
  nvm install $node_version
  start_safe

  work_dir=$metagrok_client_root
  psc_dir="$showdown_root/$showdown_client_dir"

  if [ "$1" != "nobuild" ]; then
    pushd $psc_dir

    npm install

    ./build indexes
    ./build learnsets

    popd
  fi

  rm -rf $work_dir
  mkdir -p $work_dir

  cat \
    js/predef.js \
    js/lib/promise-done-polyfill.js \
    js/lib/cycle.js \
    $psc_dir/data/Pokemon-Showdown/data/abilities.js \
    $psc_dir/data/Pokemon-Showdown/data/aliases.js \
    $psc_dir/data/Pokemon-Showdown/data/items.js \
    $psc_dir/data/Pokemon-Showdown/data/moves.js \
    $psc_dir/data/Pokemon-Showdown/data/pokedex.js \
    $psc_dir/js/battle-scene-stub.js \
    $psc_dir/js/battle-dex.js \
    $psc_dir/js/battle-dex-data.js \
    $psc_dir/js/battle-text-parser.js \
    $psc_dir/js/battle.js \
    js/engine.js \
    > $work_dir/engine.js
  
  # This part is not necessary, nor will it work, unless you have the conda env installed
  # locally as opposed to just in the docker environment.
  # test_compile_working
}

main $*