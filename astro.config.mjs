import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://lab.door4ai.com',
  integrations: [sitemap({ filter: (p) => !/\/(login|account)\/$/.test(p) })],
});
