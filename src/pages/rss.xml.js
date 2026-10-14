import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
export async function GET(context) {
  const posts = await getCollection('blog');
  return rss({
    title: 'Door4AI Lab',
    description: '动手理解 AI 的可交互教学博客',
    site: context.site,
    items: posts.map((p) => ({ title: p.data.title, description: p.data.description, pubDate: p.data.pubDate, link: `/posts/${p.id}/` })),
  });
}
