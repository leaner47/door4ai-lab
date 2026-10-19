import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

export default defineConfig({
  site: 'https://lab.door4ai.com',
  markdown: { remarkPlugins: [remarkMath], rehypePlugins: [[rehypeKatex, { output: 'html' }]] },
  integrations: [sitemap({ filter: (p) => !/\/(login|account|admin)\/$/.test(p) })],
});
