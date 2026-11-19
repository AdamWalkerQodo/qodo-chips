// Copy the Lucide icon shapes the chips use into assets/icons.json.
// Usage: node generator/extract_icons.mjs <path to node_modules/lucide-react/dist/esm/icons>
import fs from 'node:fs';
const dir = process.argv[2];
const names = ['bug','book-marked','paperclip','monitor','palette','link','users','scroll','brain','shield-plus','menu','sun-dim','diamond','bolt','move-up-right','eye','clipboard-check','pen-tool','triangle','square-check','square-dot','check','x','circle-slash','sparkles','laptop','rocket','scale','skip-forward','circle-check','circle-x','triangle-alert','circle-minus','external-link','wrench','pause','file-text','circle-ellipsis','flask-conical','trending-up','settings','refresh-cw','clock','bomb','waypoints','flame','wand-sparkles','info','text-align-start','code','search','bot','git-pull-request','circle-dot'];
const out = {};
for (const n of names) {
  const src = fs.readFileSync(`${dir}/${n}.js`, 'utf8');
  const m = src.match(/const __iconNode = (\[[\s\S]*?\]);\nconst /);
  out[n] = new Function('return ' + m[1])().map(([tag, attrs]) => { const { key, ...rest } = attrs; return [tag, rest]; });
}
fs.writeFileSync(new URL('./assets/icons.json', import.meta.url), JSON.stringify(out));
console.log(Object.keys(out).length, 'icons');
