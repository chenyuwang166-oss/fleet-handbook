'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {evaluate} = require('./scoring.cjs');
const root = path.join(__dirname, '..');

function script(html, id) {
  const pattern = new RegExp('<script\\b[^>]*\\bid=["\\\']' + id + '["\\\'][^>]*>([\\s\\S]*?)</script\\s*>', 'g');
  const matches = [...html.matchAll(pattern)];
  assert.equal(matches.length, 1, 'Expected one embedded script with id=' + id);
  return matches[0][1].trim();
}

test('offline HTML embeds exactly the question data and tested scoring source', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  const data = JSON.parse(fs.readFileSync(path.join(root, 'questions.json'), 'utf8'));
  assert.deepEqual(JSON.parse(script(html, 'question-data')), data);
  assert.equal(script(html, 'scoring-engine'), fs.readFileSync(path.join(__dirname, 'scoring.cjs'), 'utf8').trim());
});

test('browser scoring and Node scoring produce the same results', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  const data = JSON.parse(script(html, 'question-data'));
  const context = vm.createContext({});
  vm.runInContext(script(html, 'scoring-engine'), context, {timeout: 1000});
  assert.equal(typeof context.FleetScoring.evaluate, 'function');
  const cases = [{}, {q1: 'invalid'}];
  for (let score = 0; score <= 4; score += 1) {
    cases.push(Object.fromEntries(data.questions.map(question => [question.id, question.options[score].id])));
  }
  // Exercise every gate near its boundary, as well as complete and partial inputs.
  for (const level of data.levels) {
    for (const gate of level.requires) {
      const input = Object.fromEntries(data.questions.map(question => [question.id, question.options[4].id]));
      const question = data.questions.find(candidate => candidate.id === gate.question);
      input[question.id] = question.options.find(option => option.score === gate.minScore - 1).id;
      cases.push(input);
    }
  }
  for (const input of cases) {
    const browserResult = context.FleetScoring.evaluate(data, input);
    assert.deepEqual(JSON.parse(JSON.stringify(browserResult)), evaluate(data, input));
  }
});
