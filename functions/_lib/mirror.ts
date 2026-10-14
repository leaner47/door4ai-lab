import { TARGETS, byId, type Target } from './sources';

export type Env = { DL: R2Bucket; SYNC_KEY?: string };
export type Item = { key: string; filename: string; version: string; size: number; sha256: string | null; syncedAt: string; sourceUrl: string };
export type Manifest = { updatedAt: string; items: Record<string, Item>; errors?: Record<string, string> };

const MANIFEST_KEY = 'manifest.json';
const UA = 'door4ai-lab-mirror/1.0 (+https://lab.door4ai.com)';

export async function readManifest(env: Env): Promise<Manifest> {
  const o = await env.DL.get(MANIFEST_KEY);
  if (!o) return { updatedAt: '1970-01-01T00:00:00Z', items: {} };
  return (await o.json()) as Manifest;
}
async function writeManifest(env: Env, m: Manifest) {
  await env.DL.put(MANIFEST_KEY, JSON.stringify(m), { httpMetadata: { contentType: 'application/json' } });
}

export async function syncTarget(env: Env, t: Target, force = false): Promise<{ id: string; status: string; version?: string; error?: string }> {
  const manifest = await readManifest(env);
  try {
    const r = await t.resolve();
    const cur = manifest.items[t.id];
    if (!force && cur && cur.version === r.version) {
      return { id: t.id, status: 'up-to-date', version: r.version };
    }
    const resp = await fetch(r.url, { headers: { 'User-Agent': UA } });
    if (!resp.ok || !resp.body) throw new Error(`download ${resp.status}`);
    const key = `${t.id}/${r.version}/${r.filename}`;
    const len = resp.headers.get('content-length');
    const body: any = len ? resp.body : await resp.arrayBuffer();
    const obj = await env.DL.put(key, body, {
      httpMetadata: { contentType: resp.headers.get('content-type') || 'application/octet-stream' },
      customMetadata: { version: r.version, filename: r.filename, source: r.url },
    });
    if (cur && cur.key !== key) await env.DL.delete(cur.key).catch(() => {});
    const fresh = await readManifest(env); // 重新读一次：其他 target 可能已写入
    fresh.items[t.id] = { key, filename: r.filename, version: r.version, size: obj.size, sha256: r.sha256 ?? null, syncedAt: new Date().toISOString(), sourceUrl: r.url };
    if (fresh.errors) delete fresh.errors[t.id];
    fresh.updatedAt = new Date().toISOString();
    await writeManifest(env, fresh);
    return { id: t.id, status: 'updated', version: r.version };
  } catch (e: any) {
    const fresh = await readManifest(env);
    fresh.errors = { ...(fresh.errors || {}), [t.id]: String(e?.message || e) };
    fresh.updatedAt = new Date().toISOString();
    await writeManifest(env, fresh);
    return { id: t.id, status: 'error', error: String(e?.message || e) };
  }
}

export async function syncAll(env: Env, only?: string, force = false) {
  const list = only ? TARGETS.filter((t) => t.id === only || t.app === only) : TARGETS;
  const out = [];
  for (const t of list) out.push(await syncTarget(env, t, force));
  return out;
}
export { TARGETS, byId };
