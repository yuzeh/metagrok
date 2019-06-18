# Metagrok
A self-play RL system for learning to battle on [Pokémon Showdown](showdown).
This library was used in the work [[ PAPER ]].

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

The first thing to do is to set up the correct Node version and create the headless client:

    scripts/install.sh --no-server
    scripts/compile-headless-client.sh

This creates the headless client at `build/engine.js`.

Most development happens in a local Docker container. To set that up:

    docker build .

[showdown]: https://pokemonshowdown.com
[ps]: https://github.com/Zarel/Pokemon-Showdown
[psc]: https://github.com/Zarel/Pokemon-Showdown-Client
[pmr]: https://github.com/sqreen/PyMiniRacer