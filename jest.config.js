module.exports = {
  testEnvironment: 'node',
  testMatch: ['**/tests/firestore/**/*.test.js'],
  setupFilesAfterEnv: ['./tests/firestore/setup.js'],
  testTimeout: 30000,
  maxWorkers: 1,
};
