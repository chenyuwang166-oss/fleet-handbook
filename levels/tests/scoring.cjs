(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.FleetScoring = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  // All classification thresholds and required practices come from questions.json.
  // Language only changes labels, never answer IDs or classification.
  // Card traits describe reported practices; they never change level or score.
  function cardTraits(scores, level) {
    const traits = [];
    if (scores.q4 >= 2) traits.push('review');
    if (scores.q6 === 4) traits.push('memory');
    if (scores.q7 === 4) traits.push('values');
    if (scores.q3 >= 2) traits.push('providers');
    if (scores.q5 >= 3) traits.push('departments');
    if (scores.q8 === 4) traits.push('human');
    if (scores.q2 >= 2) traits.push('workflow');
    if (scores.q1 >= 1) traits.push('roles');
    if (scores.q9 >= 2) traits.push('delivery');
    if (scores.q6 === 3) traits.push('handoff');
    if (scores.q6 === 2) traits.push('files');
    if (!traits.length) traits.push(scores.q3 === 0 ? 'one-ai' : 'several-ais');
    // Remove practices already stated in that level's bilingual summary.
    // Keep the original shortlist; do not fill removed slots with extra traits.
    const described = {
      1: ['one-ai'],
      2: ['roles'],
      3: ['workflow', 'several-ais'],
      4: ['providers', 'review', 'roles'],
      5: ['departments', 'memory', 'values', 'human']
    };
    return traits.slice(0, 3).filter(function (trait) { return !described[level].includes(trait); });
  }

  function evaluate(data, answers) {
    const validContainer = answers !== null && typeof answers === 'object' && !Array.isArray(answers);
    const source = validContainer ? answers : {};
    const missing = [];
    const errors = [];
    const scores = {};
    let score = 0;
    let answered = 0;
    if (!validContainer && answers !== undefined && answers !== null) errors.push({question: null, code: 'invalid-answers'});
    const known = new Set(data.questions.map(function (question) { return question.id; }));
    Object.keys(source).forEach(function (id) {
      if (!known.has(id)) errors.push({question: id, code: 'unknown-question'});
    });
    data.questions.forEach(function (question) {
      const hasAnswer = Object.prototype.hasOwnProperty.call(source, question.id);
      const answer = hasAnswer ? source[question.id] : undefined;
      if (answer === undefined || answer === null || answer === '') {
        missing.push(question.id);
        return;
      }
      const option = question.options.find(function (candidate) { return candidate.id === answer; });
      if (!option) {
        errors.push({question: question.id, code: 'invalid-option'});
        return;
      }
      scores[question.id] = option.score;
      score += option.score;
      answered += 1;
    });
    const complete = missing.length === 0 && errors.length === 0;
    if (!complete) {
      return {complete: false, status: errors.length ? 'invalid' : 'incomplete', level: null, score: score, answered: answered, missing: missing, errors: errors, thresholdLevel: null, unmetGates: [], traits: []};
    }
    const levels = data.levels.slice().sort(function (a, b) { return a.level - b.level; });
    let level = null;
    let thresholdLevel = null;
    const unmetGates = [];
    levels.forEach(function (candidate) {
      if (score < candidate.minScore) return;
      thresholdLevel = candidate.level;
      const unmet = candidate.requires.filter(function (gate) { return scores[gate.question] < gate.minScore; });
      if (unmet.length === 0) level = candidate.level;
      else unmetGates.push({level: candidate.level, questions: unmet.map(function (gate) { return gate.question; })});
    });
    return {complete: true, status: 'complete', level: level, score: score, answered: answered, missing: [], errors: [], thresholdLevel: thresholdLevel, unmetGates: unmetGates, traits: cardTraits(scores, level)};
  }

  return Object.freeze({evaluate: evaluate});
});
