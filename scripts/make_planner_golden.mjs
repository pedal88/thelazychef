// Expected planner results for tests/test_recipe_v2_planner.py, made by the prototype's own code.
//
//   node scripts/make_planner_golden.mjs > tests/fixtures/planner_golden.json
//
// Takes the v2 adapter (fromV2), index, fit and schedule from docs/prototypes/fem-retter-pilot.html
// unchanged, and runs them on the reference recipes and the Opus results from phase 0b. The Python
// planner (services/recipe_v2/planner.py) must give the same plans.
import { readFileSync, readdirSync } from 'node:fs';

const html = readFileSync('docs/prototypes/fem-retter-pilot.html', 'utf8');
const lines = html.split('\n');
const from = start => {
  const i = lines.findIndex(l => l.startsWith(start));
  if (i < 0) throw new Error('not found: ' + start);
  if (!start.startsWith('function')) return lines[i];
  const j = lines.findIndex((l, k) => k > i && l === '}');
  return lines.slice(i, j + 1).join('\n');
};
const code = [
  'const RECIPES=[], MISE={}, STAPLES=new Set(); let loadedN=0;',
  from('const I='), from('const S='), from('const EQCAT='), from('const UNIT_NO='), from('const def='),
  from('function deriveMise('), from('function fromV2('), from('function index('), from('function fit('), from('function schedule('),
  'return {fromV2, index, schedule};',
].join('\n');
const { fromV2, index, schedule } = new Function(code)();

const sources = [];
for (const f of readdirSync('data/pilot_v2/fasit').sort()) sources.push(['fasit/' + f, JSON.parse(readFileSync('data/pilot_v2/fasit/' + f, 'utf8'))]);
for (const set of ['fasit', 'db']) {
  const dir = `data/pilot_v2/results_0b/opus-low/${set}`;
  for (const f of readdirSync(dir).sort()) sources.push([`opus-low/${set}/${f}`, JSON.parse(readFileSync(`${dir}/${f}`, 'utf8')).recipe]);
}

const out = {};
for (const [name, v2] of sources) {
  const r = fromV2(v2, '');
  index(r);
  out[name] = {};
  for (const mode of ['calm', 'prep', 'jit']) {
    const s = schedule(r, mode);
    out[name][mode] = {
      T: s.T, A: s.A, cookStart: s.cookStart, serveStart: s.serveStart,
      order: s.order.map(x => x.id), over: s.over, me: s.me,
      ahead: Object.keys(s.ahead).filter(k => s.ahead[k]).sort(),
      plan: Object.fromEntries(Object.entries(s.plan).map(([k, p]) => [k, { start: p.start, end: p.end, use: p.use, during: p.during || null }])),
    };
  }
}
console.log(JSON.stringify(out, null, 1));
