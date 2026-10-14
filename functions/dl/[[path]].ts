import { readManifest, syncTarget, byId, TARGETS, type Env } from '../_lib/mirror';

const STALE_MS = 24 * 3600 * 1000;

export const onRequestGet: PagesFunction<Env> = async ({ request, env, params, waitUntil }) => {
  const parts = (params.path as string[] | undefined) || [];
  const manifest = await readManifest(env);

  // /dl/ 或 /dl/manifest.json：当前镜像状态（版本、大小、校验值）
  if (parts.length === 0 || parts[0] === 'manifest.json') {
    const items: Record<string, any> = {};
    for (const t of TARGETS) {
      const it = manifest.items[t.id];
      items[t.id] = it
        ? { label: t.label, filename: it.filename, version: it.version, size: it.size, sha256: it.sha256, syncedAt: it.syncedAt }
        : { label: t.label, missing: true, error: manifest.errors?.[t.id] };
    }
    return Response.json({ updatedAt: manifest.updatedAt, items }, { headers: { 'cache-control': 'no-store' } });
  }

  // /dl/<app>/<platform>：下载
  const id = parts.slice(0, 2).join('/');
  const t = byId(id);
  if (!t) return new Response('Not found', { status: 404 });
  const it = manifest.items[id];

  // 后台刷新：超过 24h 没同步就顺手检查一次，不阻塞本次下载
  const age = Date.now() - Date.parse(it?.syncedAt || manifest.updatedAt || '1970-01-01');
  if (!it || age > STALE_MS) waitUntil(syncTarget(env, t).catch(() => {}));

  if (!it) {
    return new Response('该安装包还没有同步到镜像，请一分钟后再试。', {
      status: 503, headers: { 'content-type': 'text/plain; charset=utf-8', 'retry-after': '60' },
    });
  }

  const obj = await env.DL.get(it.key, { range: request.headers, onlyIf: request.headers });
  if (!obj) return new Response('Not found', { status: 404 });
  const h = new Headers();
  obj.writeHttpMetadata(h);
  h.set('etag', obj.httpEtag);
  h.set('accept-ranges', 'bytes');
  h.set('content-disposition', `attachment; filename="${it.filename}"; filename*=UTF-8''${encodeURIComponent(it.filename)}`);
  h.set('cache-control', 'private, max-age=0');
  if (!('body' in obj)) return new Response(null, { status: 304, headers: h });
  const body = (obj as R2ObjectBody).body;
  const range = (obj as any).range as { offset?: number; length?: number } | undefined;
  if (range) {
    const start = range.offset ?? 0;
    const end = range.length != null ? start + range.length - 1 : obj.size - 1;
    h.set('content-range', `bytes ${start}-${end}/${obj.size}`);
    h.set('content-length', String(end - start + 1));
    return new Response(body, { status: 206, headers: h });
  }
  h.set('content-length', String(obj.size));
  return new Response(body, { headers: h });
};
