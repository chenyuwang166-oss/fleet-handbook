import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const dir = path.dirname(fileURLToPath(import.meta.url));
const root = path.dirname(dir);
const htmlPath = path.join(root, 'index.html');
const data = JSON.parse(fs.readFileSync(path.join(root, 'questions.json'), 'utf8'));
const engine = fs.readFileSync(path.join(dir, 'scoring.cjs'), 'utf8').trim();
let html = fs.readFileSync(htmlPath, 'utf8');

function replaceScript(id, body) {
  const pattern = new RegExp('(<script\\b[^>]*\\bid=["\\\']' + id + '["\\\'][^>]*>)[\\s\\S]*?(</script\\s*>)', 'g');
  const matches = [...html.matchAll(pattern)];
  if (matches.length !== 1) throw new Error('Expected exactly one script with id=' + id + ', found ' + matches.length);
  html = html.replace(pattern, function (_, open, close) { return open + '\n' + body + '\n' + close; });
}

// Escaping < prevents data text from ever ending its enclosing script element.
replaceScript('question-data', JSON.stringify(data, null, 2).replace(/</g, '\\u003c'));
if (/<\/script/i.test(engine)) throw new Error('Scoring source must not contain a closing script tag');
replaceScript('scoring-engine', engine);
fs.writeFileSync(htmlPath, html, 'utf8');
console.log('Synced questions.json and scoring.cjs into index.html');
