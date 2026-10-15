// 构建前运行：读 src/content/blog/*.md 的 frontmatter，生成 functions/_lib/access-map.ts，
// 供门禁中间件判断每篇文章 / 实验页需要什么权益。
// 规则：access: free → 登录即可；否则属于 series 的文章需要 series:<name> 或 post:<slug> 权益；
//       不属于任何 series 的文章登录即可。
import { readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, basename } from 'node:path';

const dir = 'src/content/blog';
const posts = {};
const labs = {};

for (const f of readdirSync(dir).filter((f) => /\.mdx?$/.test(f)).sort()) {
  const src = readFileSync(join(dir, f), 'utf8');
  const m = src.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!m) continue;
  const fm = {};
  for (const line of m[1].split(/\r?\n/)) {
    const kv = line.match(/^([A-Za-z_][\w-]*):\s*(.*)$/);
    if (kv) fm[kv[1]] = kv[2].trim().replace(/^["']|["']$/g, '');
  }
  const slug = basename(f).replace(/\.mdx?$/, '');
  const access = fm.access === 'free' ? 'free' : fm.series ? 'paid' : 'free';
  posts[slug] = { access, ...(fm.series ? { series: fm.series } : {}) };
  if (fm.lab) {
    const p = fm.lab.replace(/^\/+|\/+$/g, ''); // labs/<name>
    labs[p] = slug;
  }
}

const out = `// 自动生成，勿手改：scripts/gen-access-map.mjs（npm run build 时运行）
export type PostAccess = { access: 'free' | 'paid'; series?: string };
export const POSTS: Record<string, PostAccess> = ${JSON.stringify(posts, null, 2)};
export const LABS: Record<string, string> = ${JSON.stringify(labs, null, 2)};
`;
writeFileSync('functions/_lib/access-map.ts', out);
console.log(`access-map: ${Object.keys(posts).length} posts, ${Object.keys(labs).length} labs`);
