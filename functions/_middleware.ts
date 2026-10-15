// 全站中间件
// 1) door4ai-lab.pages.dev 及预览地址一律 301 到 lab.door4ai.com 同路径（保留查询参数）。
// 2) AUTH_ENABLED=1 且绑定了 D1 时：自建账号门禁（文章 / 实验页按权益放行，资源页登录即可），
//    并在页面请求上记录注册来源 Cookie。否则不做任何事，沿用 Cloudflare Access。
import { authEnabled, type AuthEnv } from './_lib/auth/util';
import { getSession, hasEntitlement, isAdmin } from './_lib/auth/session';
import { requirementFor } from './_lib/auth/gate';
import { attributionCookie } from './_lib/auth/attribution';

const CANONICAL = 'lab.door4ai.com';

const redirect = (location: string, status = 302) =>
  new Response(null, { status, headers: { location, 'cache-control': 'no-store' } });

const isPageRequest = (request: Request) =>
  request.method === 'GET' && (request.headers.get('accept') || '').includes('text/html');

export const onRequest: PagesFunction<AuthEnv> = async ({ request, env, next }) => {
  const url = new URL(request.url);
  if (url.hostname.endsWith('.pages.dev')) {
    url.protocol = 'https:';
    url.hostname = CANONICAL;
    url.port = '';
    return redirect(url.toString(), 301);
  }
  if (!authEnabled(env)) return next();

  const req = requirementFor(url.pathname);
  const srcCookie = isPageRequest(request) ? attributionCookie(request) : null;

  if (req.kind !== 'public') {
    const target = url.pathname + url.search;
    const { session, replaced } = await getSession(env.DB, request);
    if (!session) {
      const q = new URLSearchParams({ next: target });
      if (replaced) q.set('kicked', '1');
      const res = redirect(`/login/?${q}`);
      if (srcCookie) res.headers.append('set-cookie', srcCookie);
      return res;
    }
    if (req.kind === 'paid' && !isAdmin(env, session.user.email) && !(await hasEntitlement(env.DB, session.user.id, req.needs))) {
      return redirect(`/pricing/?${new URLSearchParams({ need: req.label, next: target })}`);
    }
  }

  const res = await next();
  if (req.kind === 'public' && !srcCookie) return res;
  const out = new Response(res.body, res);
  if (req.kind !== 'public') out.headers.set('cache-control', 'private, no-store');
  if (srcCookie) out.headers.append('set-cookie', srcCookie);
  return out;
};
