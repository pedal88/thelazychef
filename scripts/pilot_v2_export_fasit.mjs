// Eksporterer de fem håndlagde rettene i docs/prototypes/fem-retter.html til v2-JSON (fasit for fase 0).
// Kjør: node scripts/pilot_v2_export_fasit.mjs
//
// Prototypen bruker korte ID-er (sp, gu), {stegId}-referanser i teksten, waits og eq/tools.
// v2 (schemas/recipe_v2.py) har i1/s1/c1, bare {iN} i teksten, ingen waits og equipment som liste.
// method finnes ikke i prototypen og settes for hånd under.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const html = fs.readFileSync(path.join(root, 'docs/prototypes/fem-retter.html'), 'utf8');
const start = html.indexOf('/* ---------- datamodell ---------- */');
const end = html.indexOf('/* Mise-elementer');
const ctx = {};
vm.runInNewContext(html.slice(start, end) + '\nthis.out={carbonara:carbonara(),brownies:brownies(),tikka:tikka(),lasagne:lasagne(),burger:burger(true)};', ctx);

const UNIT = { g: 'g', dl: 'dl', ss: 'tbsp', ts: 'tsp', stk: 'piece', fedd: 'clove', cm: 'cm', klype: 'pinch', 'håndfull': 'handful', skive: 'slice', blad: 'leaf' };
const MODE = { grill: 'grill_element' };
const METHOD = {
  carbonara: { w: 'boil', e2: 'whisk', g1: 'slice', g2: 'pan_fry', p1: 'boil', p2: 'drain', t1: 'mix', t2: 'mix', end: 'serve' },
  brownies: { ov: 'preheat', f0: 'prepare', d1: 'sift', n1: 'chop', s1: 'melt', s2: 'whisk', s3: 'fold', s4: 'bake', s5: 'cool', end: 'slice' },
  tikka: { ov: 'preheat', m1: 'mix', m2: 'marinate', s1: 'chop', s0: 'mix', k1: 'chop', r1: 'rinse', m3: 'grill', s2: 'saute', s3: 'saute', s4: 'simmer', s5: 'simmer', r2: 'simmer', r3: 'rest', end: 'serve' },
  lasagne: { ov: 'preheat', k1: 'chop', k2: 'sear', k3: 'saute', k4: 'simmer', h1: 'saute', h2: 'simmer', l1: 'assemble', l3: 'bake', l4: 'rest', g1: 'rinse', g2: 'slice', g3: 'mix', g4: 'mix', end: 'serve' },
  burger: { ov: 'preheat', b1: 'knead', b2: 'proof', b3: 'shape', b4: 'proof', b5: 'brush', b6: 'bake', b7: 'cool', f1: 'slice', f2: 'season', f3: 'roast', u1: 'shape', t1: 'slice', d1: 'mix', u2: 'pan_fry', u3: 'melt', b8: 'slice', end: 'assemble' },
};

function convert(key, r) {
  const comps = r.comps.filter(c => c.id !== 'ovn');
  const cid = Object.fromEntries(comps.map((c, k) => [c.id, 'c' + (k + 1)]));
  const iid = Object.fromEntries(r.ings.map((i, k) => [i.id, 'i' + (k + 1)]));
  // Stegrekkefølge: prototypens rekkefølge. Ovnen (komponent «ovn») får komponenten til første steg som venter på den.
  const sid = Object.fromEntries(r.steps.map((s, k) => [s.id, 's' + (k + 1)]));
  const byId = Object.fromEntries(r.steps.map(s => [s.id, s]));
  const compOf = s => {
    if (s.c !== 'ovn') return cid[s.c];
    const w = r.steps.find(t => (t.waits || []).includes(s.id));
    return cid[w ? w.c : comps[0].id];
  };
  const text = s => s.text.replace(/\{(\w+)\}/g, (m, id) => {
    if (iid[id]) return '{' + iid[id] + '}';
    const st = byId[id];
    if (st) return st.out || st.short.toLowerCase();
    throw new Error(`${key}: ukjent referanse ${id}`);
  });
  return {
    title: r.title,
    servings: r.fixed ? 1 : r.base,
    components: comps.map(c => ({ local_id: cid[c.id], name: c.name })),
    ingredients: r.ings.map(i => {
      const o = { local_id: iid[i.id], component_id: cid[i.c], name: i.name };
      if (i.amount != null) { o.amount = i.amount; o.unit = UNIT[i.unit] || i.unit; }
      if (i.prep) o.prep_style = i.prep;
      return o;
    }),
    steps: r.steps.map(s => {
      const o = {
        local_id: sid[s.id], component_id: compOf(s), phase: s.phase, short: s.short, text: text(s),
        uses: s.uses.map(u => iid[String(u).split('@')[0]]), after: s.after.map(a => sid[a]),
        active_minutes: s.active, passive_minutes: s.passive,
      };
      if (s.hold != null) o.holds_minutes = s.hold;
      o.method = METHOD[key][s.id];
      if (!o.method) throw new Error(`${key}: mangler method for ${s.id}`);
      o.equipment = [...(s.eq ? [s.eq] : []), ...(s.tools || [])];
      if (s.temp) o.temp_c = s.temp;
      if (s.mode) o.mode = MODE[s.mode] || s.mode;
      o.setup = !!s.setup;
      if (s.done) o.done_when = s.done;
      return o;
    }),
  };
}

const outDir = path.join(root, 'data/pilot_v2/fasit');
fs.mkdirSync(outDir, { recursive: true });
for (const [key, r] of Object.entries(ctx.out)) {
  fs.writeFileSync(path.join(outDir, key + '.json'), JSON.stringify(convert(key, r), null, 2) + '\n');
  console.log('skrev', key);
}
