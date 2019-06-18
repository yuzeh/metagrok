# Metagrok (README WIP)
A self-play RL system for learning to battle on [Pokémon Showdown](showdown).
This code was used in the work [[ PAPER ]].

## How does it work?
There are three pieces of functionality that make this system work:

* **Handling communications with the outside world.**
  Currently it is able to connect to a generic [Pokémon Showdown server](ps) using the websocket
  interface. It can also battle over the `stdio` interface provided by
  `./pokemon-showdown simulate-battle`.
* **Processing Showdown server messages into a structured format.**
  We repurpose the [Showdown client](psc) code to create a headless client -- one that does not
  interact with DOM elements and does not assume it is running on a web page.
  To have the resulting JavaScript code work with Python, we embed a V8 runtime
  (using [Python Mini Racer](pmr)) in our program. 
* **Performing an action in-game and learning from its mistakes.**
  The main decision maker is a neural network. See [[ PAPER ]] for high level details and a
  schematic of the neural network architecture.

## How do I get it to run?

Most development happens in a local Docker container. To set that up:

    docker build . --tag metagrok:latest

This docker container freezes versioning for three main components:

* Python environment and conda packages
* Node.js version
* Pokémon Showdown server commit SHA

Any update to one of these things require a rebuild of the docker container.
In particular, no source code (i.e. nothing in the `metagrok/` or the `js/` directories) is frozen.
For convenience during development, any new conda packages that are installed should simply be
appended to `scripts/install-more-conda-packages.sh`.

To develop code in this environment, run in a terminal window:

    docker run -it -v $(pwd):/root/workspace --entrypoint /bin/bash metagrok:latest

    # inside the docker instance
    (metagrok) [root@6a31f1d57424]# cd workspace

### Building Showdown-related components

The first thing to do is to set up the correct Node version, download both showdown repos, and
create the headless client:

    scripts/install.sh
    scripts/compile-headless-client.sh

This creates the headless client at `build/engine.js`.

The rest of this section contains common things one might want to do with a Showdown bot.

### Evaluating a bot against another bot

    ./rp metagrok/exe/head2head.py \
        --format gen7randombattle \
        --p1 ,metagrok.pkmn.engine.baselines.MostDamageMovePlayerTypeAware \
        --p2 metagrok.pkmn.models.V3Quad:static/sample-v3-quad-model.pytorch \
        --num-matches 10 --parallelism 4

### Evaluating a bot against humans on a Pokémon Showdown server

    # Set up showdown server on localhost:8000
    ./rp metagrok/exe/smogon_eval.py \
        metagrok.pkmn.models.V3Quad:static/sample-v3-quad-model.pytorch \
        --num-matches 10 \
        --max-concurrent 5 \
        --host localhost --port 8000

### Training the bot

TODO add this portion

[showdown]: https://pokemonshowdown.com
[ps]: https://github.com/Zarel/Pokemon-Showdown
[psc]: https://github.com/Zarel/Pokemon-Showdown-Client
[pmr]: https://github.com/sqreen/PyMiniRacer