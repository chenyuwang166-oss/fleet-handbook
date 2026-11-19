'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {evaluate} = require('./scoring.cjs');
const data = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'questions.json'), 'utf8'));

function answers(scores) {
  assert.equal(scores.length, data.questions.length);
  return Object.fromEntries(data.questions.map((question, index) => {
    const option = question.options.find(candidate => candidate.score === scores[index]);
    assert.ok(option, 'Each requested score needs an option');
    return [question.id, option.id];
  }));
}

test('question and level data has stable, bilingual IDs and explicit scoring', () => {
  assert.equal(data.schemaVersion, 1);
  assert.equal(data.questions.length, 9);
  assert.equal(new Set(data.questions.map(question => question.id)).size, 9);
  assert.equal(data.maxScore, 36);
  for (const question of data.questions) {
    assert.ok(question.title.zh && question.title.en);
    assert.deepEqual(question.options.map(option => option.score), [0, 1, 2, 3, 4]);
    assert.equal(new Set(question.options.map(option => option.id)).size, 5);
    for (const option of question.options) assert.ok(option.label.zh && option.label.en);
  }
  assert.deepEqual(data.levels.map(level => [level.level, level.minScore]), [[1, 0], [2, 1], [3, 4], [4, 13], [5, 29]]);
  for (const level of data.levels) {
    for (const field of ['title', 'summary', 'next', 'card']) assert.ok(level[field].zh && level[field].en);
    assert.ok(level.skills.length > 0);
    assert.deepEqual(level.chapters, [[1, 2], [1, 2], [2], [1, 3, 5], [3, 4, 5]][level.level - 1]);
    assert.ok(!Object.hasOwn(level, 'day'), 'Results use handbook chapters instead of launch-week dates');
    assert.equal(level.minScore, level.requires.reduce((sum, gate) => sum + gate.minScore, 0), 'A threshold must not introduce extra requirements beyond the key practices');
    for (const gate of level.requires) {
      assert.ok(data.questions.some(question => question.id === gate.question));
      assert.ok(Number.isInteger(gate.minScore) && gate.minScore >= 0 && gate.minScore <= 4);
    }
  }
});

const typical = [
  [1, [0, 0, 0, 0, 0, 0, 0, 0, 0]],
  [2, [2, 1, 0, 0, 0, 1, 0, 1, 1]],
  [3, [2, 3, 1, 1, 1, 2, 1, 2, 2]],
  [4, [3, 3, 3, 3, 2, 2, 2, 2, 3]],
  [5, [4, 4, 4, 4, 4, 4, 4, 4, 4]]
];
for (const [level, scores] of typical) {
  test('typical complete answers classify as L' + level, () => {
    const result = evaluate(data, answers(scores));
    assert.equal(result.complete, true);
    assert.equal(result.status, 'complete');
    assert.equal(result.level, level);
    assert.equal(result.score, scores.reduce((sum, value) => sum + value, 0));
    assert.equal(result.answered, 9);
    assert.deepEqual(result.missing, []);
    assert.deepEqual(result.errors, []);
  });
}

const boundaries = [
  [2, [0, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0],
  [3, [1, 2, 0, 0, 0, 0, 0, 0, 0], 0, 2],
  [4, [2, 2, 3, 2, 0, 0, 0, 0, 3], 3, 4],
  [5, [2, 2, 3, 3, 2, 4, 4, 4, 4], 4, 0]
];
for (const [level, below, toBoundaryIndex, aboveBoundaryIndex] of boundaries) {
  test('L' + level + ' threshold: one below, exactly at, one above', () => {
    const threshold = data.levels.find(candidate => candidate.level === level).minScore;
    for (let delta = 0; delta <= 2; delta += 1) {
      const scores = below.slice();
      if (delta >= 1) scores[toBoundaryIndex] += 1;
      if (delta >= 2) scores[aboveBoundaryIndex] += 1;
      const result = evaluate(data, answers(scores));
      assert.equal(result.score, threshold - 1 + delta);
      assert.equal(result.level, delta === 0 ? level - 1 : level);
    }
  });
}

const gateCases = [
  ['roles are required for L2', 0, 0, 1],
  ['separate role rounds are required for L3', 0, 1, 2],
  ['written multi-AI relay is required for L3', 1, 1, 2],
  ['same-provider work cannot reach L4', 2, 1, 3],
  ['separate work across providers cannot reach L4', 2, 2, 3],
  ['review without a cross-provider rule cannot reach L4', 3, 2, 3],
  ['human-only review cannot reach L4', 3, 1, 3],
  ['reused roles without standing departments cannot reach L5', 4, 2, 4],
  ['only one memory action cannot reach L5', 5, 3, 4],
  ['slogans alone cannot reach L5', 6, 2, 4],
  ['values still awaiting review or a decision cannot reach L5', 6, 3, 4],
  ['human outside the organization cannot reach L5', 7, 3, 4],
  ['stopping when the AI says it is done cannot reach L4', 8, 0, 3],
  ['checking items without separating completion, delivery and acceptance cannot reach L4', 8, 2, 3],
  ['separate checks without recording unfinished work cannot reach L5', 8, 3, 4]
];
for (const [name, index, score, expected] of gateCases) {
  test('non-compensable practice: ' + name, () => {
    const scores = Array(9).fill(4);
    scores[index] = score;
    const result = evaluate(data, answers(scores));
    assert.equal(result.complete, true);
    assert.ok(result.score >= data.levels.find(level => level.level === 5).minScore, 'Counterexample must meet the L5 total threshold');
    assert.equal(result.thresholdLevel, 5);
    assert.equal(result.level, expected);
    assert.ok(result.unmetGates.some(gate => gate.questions.includes('q' + (index + 1))));
  });
}

test('L4 does not require L5 departments, memory or values to supplement its score', () => {
  const result = evaluate(data, answers([3, 2, 3, 3, 0, 0, 0, 2, 3]));
  assert.equal(result.score, 16);
  assert.equal(result.level, 4);
});

test('all empty answers stay incomplete, with no L1 classification', () => {
  for (const empty of [undefined, null, {}, Object.fromEntries(data.questions.map(question => [question.id, '']))]) {
    const result = evaluate(data, empty);
    assert.equal(result.complete, false);
    assert.equal(result.status, 'incomplete');
    assert.equal(result.level, null);
    assert.equal(result.score, 0);
    assert.equal(result.missing.length, 9);
  }
});

test('one missing answer prevents classification even with a high partial score', () => {
  const input = answers(Array(9).fill(4));
  delete input.q9;
  const result = evaluate(data, input);
  assert.equal(result.score, 32);
  assert.equal(result.status, 'incomplete');
  assert.equal(result.level, null);
  assert.deepEqual(result.missing, ['q9']);
});

test('invalid answer values and unknown IDs prevent classification', () => {
  for (const invalid of [-1, 0, 4, 5, NaN, true, {}, [], 'q1-99', 'q2-4']) {
    const input = {...answers(Array(9).fill(4)), q1: invalid};
    const result = evaluate(data, input);
    assert.equal(result.status, 'invalid');
    assert.equal(result.level, null);
    assert.ok(result.errors.some(error => error.question === 'q1' && error.code === 'invalid-option'));
  }
  const unknown = evaluate(data, {...answers(Array(9).fill(4)), q10: 'q10-4'});
  assert.equal(unknown.level, null);
  assert.equal(unknown.status, 'invalid');
  assert.deepEqual(unknown.errors, [{question: 'q10', code: 'unknown-question'}]);
  for (const invalidContainer of [[], 'text', 7, false]) {
    assert.equal(evaluate(data, invalidContainer).status, 'invalid');
  }
});

test('Chinese and English labels produce identical results for every typical case', () => {
  const localized = language => {
    const copy = JSON.parse(JSON.stringify(data));
    copy.questions.forEach(question => {
      question.title = question.title[language];
      question.options.forEach(option => { option.label = option.label[language]; });
    });
    copy.levels.forEach(level => {
      for (const field of ['title', 'summary', 'next', 'card']) level[field] = level[field][language];
    });
    return copy;
  };
  for (const [, scores] of typical) {
    assert.deepEqual(evaluate(localized('zh'), answers(scores)), evaluate(localized('en'), answers(scores)));
  }
});

test('evaluation leaves source data and answers unchanged', () => {
  const input = answers(Array(9).fill(4));
  const beforeData = JSON.stringify(data);
  const beforeInput = JSON.stringify(input);
  evaluate(data, input);
  assert.equal(JSON.stringify(data), beforeData);
  assert.equal(JSON.stringify(input), beforeInput);
});

test('card traits reflect only reported practices, with no invented counts', () => {
  assert.deepEqual(evaluate(data, answers(Array(9).fill(4))).traits, ['review']);
  assert.deepEqual(evaluate(data, answers(Array(9).fill(0))).traits, []);
  assert.deepEqual(evaluate(data, answers([0, 0, 1, 0, 0, 0, 0, 0, 0])).traits, ['several-ais']);
  assert.deepEqual(evaluate(data, answers([0, 0, 2, 0, 0, 0, 0, 0, 0])).traits, ['providers']);
  assert.deepEqual(evaluate(data, answers([0, 0, 0, 2, 0, 2, 3, 0, 0])).traits, ['review', 'files']);
  assert.deepEqual(evaluate(data, answers([0, 0, 0, 0, 0, 3, 0, 0, 0])).traits, ['handoff']);
  assert.deepEqual(evaluate(data, answers([0, 0, 0, 0, 0, 4, 4, 0, 0])).traits, ['memory', 'values']);
});

test('all five card levels omit traits already stated in their summaries without backfill', () => {
  const expected = [[], [], ['roles'], ['workflow'], ['review']];
  for (const [index, level] of data.levels.entries()) {
    const scores = Array(9).fill(0);
    for (const gate of level.requires) scores[Number(gate.question.slice(1)) - 1] = gate.minScore;
    const result = evaluate(data, answers(scores));
    assert.equal(result.level, level.level);
    assert.deepEqual(result.traits, expected[index]);
  }
  assert.equal(data.levels[4].title.zh, '常设的 AI 舰队');
  assert.ok(data.levels[4].summary.zh.startsWith('常设的 AI 舰队：'));
  const withDelivery = evaluate(data, answers([2, 2, 0, 0, 0, 0, 0, 0, 2]));
  assert.equal(withDelivery.level, 3);
  assert.deepEqual(withDelivery.traits, ['roles', 'delivery'], 'Defined outputs add a practice beyond passing work along');
});

test('each card trait requires its own practice even when other scores are high', () => {
  const cases = [['review', 3, 1], ['memory', 5, 3], ['values', 6, 3]];
  for (const [trait, index, score] of cases) {
    const scores = Array(9).fill(4);
    scores[index] = score;
    assert.ok(!evaluate(data, answers(scores)).traits.includes(trait));
  }
  assert.deepEqual(evaluate(data, {}).traits, []);
  assert.deepEqual(evaluate(data, {...answers(Array(9).fill(4)), q1:'invalid'}).traits, []);
});
