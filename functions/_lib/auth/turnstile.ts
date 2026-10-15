// Cloudflare Turnstile 人机校验。未配置 TURNSTILE_SECRET 时跳过（仅限本地开发）。
import type { AuthEnv } from './util';

export async function verifyTurnstile(env: AuthEnv, token: unknown, ip: string): Promise<boolean> {
  if (!env.TURNSTILE_SECRET) return true;
  if (typeof token !== 'string' || !token) return false;
  const body = new FormData();
  body.append('secret', env.TURNSTILE_SECRET);
  body.append('response', token);
  body.append('remoteip', ip);
  const r = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', { method: 'POST', body });
  if (!r.ok) return false;
  const d = (await r.json()) as { success?: boolean };
  return !!d.success;
}
