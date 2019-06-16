if (typeof Promise !== 'function' && typeof Promise !== 'object') {
  throw new Error('Promise does not exist');
}

if (typeof Promise.prototype.done !== 'function') {
  Promise.prototype.done = function() {
    this.then.apply(this, arguments).then(null, (e) => setTimeout(() => {throw e;}, 0));
  };
}
