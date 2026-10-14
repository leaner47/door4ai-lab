// 手动触发同步：GET /sync-dl?key=<SYNC_KEY>[&app=flclash|claude|codex|<app/platform>][&force=1]
// 不在 /dl 下，所以不经过 Access；靠 SYNC_KEY 保护。
import { syncAll, type Env } from './_lib/mirror';

export const onRequest: PagesFunction<Env> = async ({ request, env }) => {
  const u = new URL(request.url);
  const key = u.searchParams.get('key') || request.headers.get('x-sync-key');
  if (!env.SYNC_KEY || key !== env.SYNC_KEY) return new Response('forbidden', { status: 403 });
  const res = await syncAll(env, u.searchParams.get('app') || undefined, u.searchParams.get('force') === '1');
  return Response.json({ at: new Date().toISOString(), results: res }, { headers: { 'cache-control': 'no-store' } });
};
