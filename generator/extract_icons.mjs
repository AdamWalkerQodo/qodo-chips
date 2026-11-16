// One-time: copy the Lucide icon shapes the chips use out of the portal's lucide-react into assets/icons.json.
import fs from 'node:fs';
const dir = process.argv[2];
const names = ['bug','book-marked','paperclip','monitor','palette','link','users','scroll','brain','shield-plus','menu','sun-dim','diamond','bolt','move-up-right','eye','clipboard-check','pen-tool','triangle','square-check','square-dot','check','x','circle-slash','sparkles','arrow-big-left','rocket','scale','skip-forward','circle-check','circle-x','triangle-alert','circle-minus','external-link','wrench','pause'];
const out = {};
for (const n of names) {
  const src = fs.readFileSync(`${dir}/${n}.js`, 'utf8');
  const m = src.match(/const __iconNode = (\[[\s\S]*?\]);\nconst /);
  out[n] = new Function('return ' + m[1])().map(([tag, attrs]) => { const { key, ...rest } = attrs; return [tag, rest]; });
}
fs.writeFileSync('assets/icons.json', JSON.stringify(out));
console.log(Object.keys(out).length, 'icons');
