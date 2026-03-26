export default {
  testEnvironment: 'node',
  testMatch: ['**/*.test.js'],
  testTimeout: 180000,
  extensionsToTreatAsEsm: ['.ts'],
  moduleNameMapper: {
    '^(\\.{1,2}/.*)\\.js$': '$1',
  },
};
