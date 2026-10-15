// 登录 / 账号页共用的前端小工具
export async function api<T = any>(path: string, body?: unknown, method = 'POST'): Promise<T> {
  const r = await fetch(path, {
    method,
    credentials: 'same-origin',
    headers: body === undefined ? {} : { 'content-type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  let data: any = null;
  try { data = await r.json(); } catch {}
  if (!r.ok) throw new Error(data?.message || `请求失败（${r.status}）`);
  return data as T;
}

export const getMe = () => fetch('/api/me', { credentials: 'same-origin' }).then((r) => r.json());

export function nextParam(): string {
  const n = new URLSearchParams(location.search).get('next');
  return n && n.startsWith('/') && !n.startsWith('//') ? n : '/ai/';
}

export const inWeChat = () => /MicroMessenger/i.test(navigator.userAgent);

// WebAuthn 用户主动取消时浏览器抛 NotAllowedError / AbortError，不当成错误提示
export const isCancel = (e: any) => e && (e.name === 'NotAllowedError' || e.name === 'AbortError' || e.code === 'ERROR_CEREMONY_ABORTED');

export function show(el: HTMLElement | null, text: string, kind: 'err' | 'ok' | 'info' = 'err') {
  if (!el) return;
  el.textContent = text;
  el.dataset.kind = kind;
  el.hidden = !text;
}
