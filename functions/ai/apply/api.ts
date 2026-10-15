// /ai/apply/api —— 「AI账号申请」（学员申请 ChatGPT / Claude 等账号）
// 路径在 /ai 下：现在由 Cloudflare Access 保护；自建账号启用后由中间件 gate（ai/apply → 需登录）保护。
// 存储：R2 桶 DL 的 apply/<id>.json（D1 开通后可迁表）。管理员 = ADMIN_EMAILS 里的邮箱。
//   GET    → { email, admin, items }（管理员看全部，其他人只看自己的）
//   POST   → 提交申请 { services[], other?, purpose, contact, note? }
//   PATCH  → 管理员改状态 { id, status: pending|approved|rejected, reply? }
import { authEnabled, type AuthEnv } from '../../_lib/auth/util';
import { getSession, isAdmin } from '../../_lib/auth/session';

type Env = AuthEnv & { DL: R2Bucket };
type Status = 'pending' | 'approved' | 'rejected';
type Item = {
  id: string; email: string; services: string[]; other?: string; purpose: string; contact: string; note?: string;
  status: Status; reply?: string; createdAt: string; updatedAt: string;
};

export const SERVICES = ['ChatGPT Plus', 'ChatGPT Pro', 'Claude Pro', 'Claude Max', 'Gemini Advanced', '其他'];
const PREFIX = 'apply/';
const json = (data: unknown, status = 200) =>
  Response.json(data, { status, headers: { 'cache-control': 'no-store' } });
const clip = (v: unknown, n: number) => String(v ?? '').trim().slice(0, n);

async function whoami(env: Env, request: Request): Promise<string | null> {
  if (authEnabled(env)) {
    const { session } = await getSession(env.DB, request);
    return session ? session.user.email.toLowerCase() : null;
  }
  // Cloudflare Access 在放行的请求上附带已验证的邮箱
  const e = request.headers.get('cf-access-authenticated-user-email');
  return e ? e.toLowerCase() : null;
}

async function all(env: Env): Promise<Item[]> {
  const out: Item[] = [];
  let cursor: string | undefined;
  do {
    const page = await env.DL.list({ prefix: PREFIX, cursor, limit: 500 });
    const objs = await Promise.all(page.objects.map((o) => env.DL.get(o.key).then((r) => (r ? r.json<Item>() : null))));
    objs.forEach((x) => x && out.push(x));
    cursor = page.truncated ? page.cursor : undefined;
  } while (cursor);
  return out.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

export const onRequest: PagesFunction<Env> = async ({ request, env }) => {
  const email = await whoami(env, request);
  if (!email) return json({ error: '请先登录' }, 401);
  const admin = isAdmin(env, email);

  if (request.method === 'GET') {
    const items = (await all(env)).filter((x) => admin || x.email === email);
    return json({ email, admin, services: SERVICES, items });
  }

  if (request.method === 'POST') {
    const b = await request.json<any>().catch(() => ({}));
    const services = (Array.isArray(b.services) ? b.services : []).map(String).filter((s: string) => SERVICES.includes(s));
    const purpose = clip(b.purpose, 2000), contact = clip(b.contact, 200), other = clip(b.other, 200), note = clip(b.note, 2000);
    if (!services.length) return json({ error: '至少选一种账号' }, 400);
    if (services.includes('其他') && !other) return json({ error: '选了「其他」请写明是什么账号' }, 400);
    if (purpose.length < 10) return json({ error: '用途说明至少写 10 个字' }, 400);
    if (!contact) return json({ error: '请留下 WhatsApp 或微信' }, 400);
    // 简单防刷：同一邮箱 24 小时内最多 5 条
    const mine = (await all(env)).filter((x) => x.email === email);
    if (mine.filter((x) => Date.now() - Date.parse(x.createdAt) < 864e5).length >= 5) return json({ error: '24 小时内最多提交 5 次申请' }, 429);
    const t = new Date().toISOString();
    const id = `${Date.now().toString(36)}-${crypto.randomUUID().slice(0, 8)}`;
    const item: Item = { id, email, services, other: other || undefined, purpose, contact, note: note || undefined, status: 'pending', createdAt: t, updatedAt: t };
    await env.DL.put(PREFIX + id + '.json', JSON.stringify(item), { httpMetadata: { contentType: 'application/json' } });
    return json({ ok: true, item }, 201);
  }

  if (request.method === 'PATCH') {
    if (!admin) return json({ error: '没有权限' }, 403);
    const b = await request.json<any>().catch(() => ({}));
    const id = clip(b.id, 64);
    if (!/^[a-z0-9-]+$/.test(id)) return json({ error: 'id 不对' }, 400);
    if (!['pending', 'approved', 'rejected'].includes(b.status)) return json({ error: 'status 不对' }, 400);
    const obj = await env.DL.get(PREFIX + id + '.json');
    if (!obj) return json({ error: '找不到这条申请' }, 404);
    const item = await obj.json<Item>();
    item.status = b.status; item.reply = clip(b.reply, 1000) || undefined; item.updatedAt = new Date().toISOString();
    await env.DL.put(PREFIX + id + '.json', JSON.stringify(item), { httpMetadata: { contentType: 'application/json' } });
    return json({ ok: true, item });
  }

  return json({ error: 'Method not allowed' }, 405);
};
