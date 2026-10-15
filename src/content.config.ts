import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const blog = defineCollection({
  loader: glob({ base: './src/content/blog', pattern: '**/*.{md,mdx}' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.coerce.date(),
    updatedDate: z.coerce.date().optional(),
    tags: z.array(z.string()).default([]),
    lab: z.string().optional(), // path to an interactive lab page under /public/labs
    series: z.string().optional(), // e.g. 'ai-mastery' → listed under AI从入门到精通
    order: z.number().optional(),  // position within the series
    access: z.enum(['free', 'paid']).optional(), // free = 登录即可看（试听）；不写则课程文章需购买
  }),
});

export const collections = { blog };
