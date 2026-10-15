// 路径 → 访问要求。
import { LABS, POSTS } from '../access-map';

export type Requirement = { kind: 'public' } | { kind: 'login' } | { kind: 'admin' } | { kind: 'paid'; needs: string[]; label: string };

const PUBLIC: Requirement = { kind: 'public' };
const LOGIN: Requirement = { kind: 'login' };

function forPost(slug: string): Requirement {
  const p = POSTS[slug];
  if (!p) return LOGIN; // 未知文章：至少要登录
  if (p.access === 'free') return LOGIN;
  const needs = [`post:${slug}`];
  if (p.series) needs.unshift(`series:${p.series}`);
  return { kind: 'paid', needs, label: p.series ? `series:${p.series}` : `post:${slug}` };
}

export function requirementFor(pathname: string): Requirement {
  const path = pathname.replace(/\/{2,}/g, '/');
  const seg = path.split('/').filter(Boolean);
  if (seg.length === 0) return PUBLIC;
  switch (seg[0]) {
    case 'posts':
      return seg[1] ? forPost(decodeURIComponent(seg[1])) : LOGIN;
    case 'labs': {
      const slug = seg[1] ? LABS[`labs/${seg[1]}`] : undefined;
      return slug ? forPost(slug) : LOGIN;
    }
    case 'admin':
      return { kind: 'admin' };
    case 'ai':
      return seg[1] === 'apply' ? LOGIN : PUBLIC; // AI账号申请：需登录
    case 'resources':
    case 'dl':
    case 'account':
      return LOGIN;
    default:
      return PUBLIC; // / /ai /login /pricing /api /_astro /logos /favicon.svg /rss.xml ……
  }
}
