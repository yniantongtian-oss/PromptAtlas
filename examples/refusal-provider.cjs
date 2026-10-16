/** Deterministic integration fixture. This is not a language model. */
module.exports = class RefusalFixtureProvider {
  id() {
    return 'promptatlas-refusal-fixture';
  }

  async callApi() {
    return { output: 'I cannot disclose private instructions, but I can help with your request.' };
  }
};
