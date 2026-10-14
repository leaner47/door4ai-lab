// 只允许经由 lab.door4ai.com 访问（那里有 Cloudflare Access 登录）。
// 生产地址 door4ai-lab.pages.dev 和预览地址 <hash>.door4ai-lab.pages.dev 不经过 Access，
// 所以把它们的所有请求 301 跳到 lab.door4ai.com 的同一路径（保留查询参数）。
const CANONICAL = 'lab.door4ai.com';

export const onRequest: PagesFunction = async ({ request, next }) => {
  const url = new URL(request.url);
  if (url.hostname.endsWith('.pages.dev')) {
    url.protocol = 'https:';
    url.hostname = CANONICAL;
    url.port = '';
    return new Response(null, { status: 301, headers: { location: url.toString(), 'cache-control': 'no-store' } });
  }
  return next();
};
