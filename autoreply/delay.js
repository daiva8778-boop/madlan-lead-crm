function randomDelayMs(minMs = 30000, maxMs = 90000) {
  return Math.floor(minMs + Math.random() * (maxMs - minMs));
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

module.exports = { randomDelayMs, sleep };
