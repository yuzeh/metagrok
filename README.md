# Metagrok (README WIP)
A self-play Reinforcement Learning system for learning to battle on [Pokémon Showdown][showdown].
This code was used in work [A Self-Play Policy Optimization Approach To Battling Pokémon][paper].

## How does it work?
There are three pieces of functionality that make this system work:

* **Handling communications with the outside world.**
  Currently it is able to connect to a generic [Pokémon Showdown server][ps] using the websocket
  interface. It can also battle over the `stdio` interface provided by
  `./pokemon-showdown simulate-battle`.
* **Processing Showdown server messages into a structured format.**
  We repurpose the [Showdown client][psc] code to create a headless client -- one that does not
  interact with DOM elements and does not assume it is running on a web page.
  To have the resulting JavaScript code work with Python, we embed a V8 runtime
  (using [Python Mini Racer][pmr]) in our program. 
* **Performing an action in-game and learning from its mistakes.**
  The main decision maker is a neural network. See [the paper][paper] for high level details and a
  schematic of the neural network architecture.

## How do I get it to run?

Most development happens in a local Docker container. To set that up:

    docker build . --tag metagrok:latest

This docker container freezes versioning for three main components:

* Python environment and conda packages
* Node.js version
* Pokémon Showdown server commit SHA

Any update to one of these things require a rebuild of the Docker container.
In particular, no source code (i.e. nothing in the `metagrok/` or the `js/` directories) is frozen.
For convenience during development, any new conda packages that are installed should simply be
appended to `scripts/install-more-conda-packages.sh`.

To develop code in this environment, run in a terminal window:

    docker run -it -v $(pwd):/root/workspace --entrypoint /bin/bash metagrok:latest

    # inside the Docker instance
    (metagrok) [root@6a31f1d57424]# cd workspace

### Building Showdown-related components

The first thing to do is to set up the correct Node version, download both Showdown repos, and
create the headless client:

    scripts/install.sh
    scripts/compile-headless-client.sh

This creates the headless client at `build/engine.js`.

The rest of this section contains common things one might want to do with a Showdown bot.

### Evaluating a bot against another bot

    ./rp metagrok/exe/head2head.py \
        --format gen7randombattle \
        --p1 ,metagrok.pkmn.engine.baselines.MostDamageMovePlayerTypeAware \
        --p2 metagrok.pkmn.models.v3_capacity.QuadCapacity:static/sample-v3-quad-model.pytorch \
        --num-matches 10

### Evaluating a bot against humans on a Pokémon Showdown server

    # Set up showdown server on localhost:8000
    ./rp metagrok/exe/smogon_eval.py \
        metagrok.pkmn.models.v3_capacity.QuadCapacity:static/sample-v3-quad-model.pytorch \
        --num-matches 8 \
        --max-concurrent 4 \
        --host localhost --port 8000

### Training the bot

    ./rp metagrok/exe/integrated_rl_script.py \
        expts/XX-test.json \
        data/test-integrated-rl-script

### Are there unit tests???

Yes, there are some unit tests, though code coverage is woefully low. In the Docker environment, run
`nose2` to execute all of the Python unit tests. 

## How can I help?

There's a lot of jank in this code, so there's a lot to do.
A few things that come to mind for me:

* Make it so that we can have a different `dex` directory per model
* Fix `challenge_bot.py` (an agent on a Showdown server that only responds to challenges)
* Refactor the code so that this project makes sense as a package on PyPI

Please open an issue with a proposed plan before starting to do any work!


[showdown]: https://pokemonshowdown.com
[ps]: https://github.com/Zarel/Pokemon-Showdown
[psc]: https://github.com/Zarel/Pokemon-Showdown-Client
[pmr]: https://github.com/sqreen/PyMiniRacer
[paper]: https://www.yuzeh.com/assets/CoG-2019-Pkmn.pdf