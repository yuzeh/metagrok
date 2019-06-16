var engine = (function() {
  const battles = {};

  return {
    start: function (key) {
      battles[key] = new Battle();
      battles[key].play();
    },

    transition: function (key, changes) {
      changes = changes.toString();
      const battle = battles[key];
      if (!battle) {
        throw new Error(`COULD NOT FIND ${key}`);
      }
      battle.add(changes);
      battle.fastForwardTo(-1);
    },

    fetch: function (key) {
      return JSON.parse(JSON.stringify(JSON.decycle(battles[key])));
    },

    stop: function (key) {
      battles[key].destroy();
      delete battles[key];
    },
  };
})();

this.engine = engine;