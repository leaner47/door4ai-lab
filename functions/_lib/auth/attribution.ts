// 注册来源归因：首次触达 f + 最后触达 l，存在 30 天的第一方 Cookie 里，注册时落库。
import { b64url, cookieName, fromB64url, getCookie, now, setCookie } from './util';

export type Touch = {
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  ref?: string;
  referer_host?: string;
  landing_path?: string;
  at: number;
};
export type Attribution = { f: Touch; l: Touch };

const MAX_AGE = 30 * 86400;
const clip = (s: string | null, n = 80) => (s ? s.slice(0, n) : undefined);

export function readAttribution(request: Request): Attribution | null {
  const raw = getCookie(request, cookieName(request, 'src'));
  if (!raw) return null;
  try {
    const a = JSON.parse(new TextDecoder().decode(fromB64url(raw)));
    return a && a.f && a.l ? a : null;
  } catch {
    return null;
  }
}

function touchFrom(request: Request): { touch: Touch; campaign: boolean } {
  const url = new URL(request.url);
  const q = url.searchParams;
  let refererHost: string | undefined;
  const referer = request.headers.get('referer');
  if (referer) {
    try {
      const h = new URL(referer).hostname;
      if (h !== url.hostname) refererHost = clip(h, 120);
    } catch {}
  }
  const touch: Touch = {
    utm_source: clip(q.get('utm_source')),
    utm_medium: clip(q.get('utm_medium')),
    utm_campaign: clip(q.get('utm_campaign')),
    ref: clip(q.get('ref'), 40),
    referer_host: refererHost,
    landing_path: clip(url.pathname, 200),
    at: now(),
  };
  const campaign = !!(touch.utm_source || touch.utm_medium || touch.utm_campaign || touch.ref || touch.referer_host);
  return { touch, campaign };
}

// 在页面请求上调用：需要更新时返回 Set-Cookie，否则返回 null。
export function attributionCookie(request: Request): string | null {
  const { touch, campaign } = touchFrom(request);
  const prev = readAttribution(request);
  let next: Attribution;
  if (!prev) next = { f: touch, l: touch };
  else if (campaign) next = { f: prev.f, l: touch };
  else return null;
  const value = b64url(new TextEncoder().encode(JSON.stringify(next)));
  return setCookie(request, 'src', value, MAX_AGE);
}

export async function persistAttribution(db: D1Database, userId: string, a: Attribution | null): Promise<void> {
  const rows: [string, Touch][] = a ? [['first', a.f], ['last', a.l]] : [['first', { at: now() }]];
  await db.batch(
    rows.map(([touch, t]) =>
      db
        .prepare(
          `INSERT OR IGNORE INTO signup_attribution
             (user_id, touch, utm_source, utm_medium, utm_campaign, ref, referer_host, landing_path, at)
           VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)`,
        )
        .bind(userId, touch, t.utm_source ?? null, t.utm_medium ?? null, t.utm_campaign ?? null, t.ref ?? null, t.referer_host ?? null, t.landing_path ?? null, t.at),
    ),
  );
}
