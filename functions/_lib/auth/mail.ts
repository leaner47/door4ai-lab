// 发送登录验证码（Resend HTTP API）。本地开发设 DEV_MAIL_LOG=1 时只打印到日志。
import type { AuthEnv } from './util';

export async function sendLoginCode(env: AuthEnv, email: string, code: string): Promise<{ ok: boolean; error?: string }> {
  if (env.DEV_MAIL_LOG === '1') {
    console.log(`[dev-mail] login code for ${email}: ${code}`);
    return { ok: true };
  }
  if (!env.RESEND_API_KEY || !env.MAIL_FROM) return { ok: false, error: 'mail_not_configured' };

  // 标题里放验证码：iPhone / Mac 的 Apple 邮件能识别并自动填入 autocomplete="one-time-code" 输入框
  const subject = `${code} 是你的 Door4AI Lab 登录验证码`;
  const text = `你的登录验证码是：${code}\n\n10 分钟内有效。如果不是你本人操作，忽略这封邮件即可。\n\nDoor4AI Lab · https://lab.door4ai.com`;
  const html = `<div style="font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;font-size:15px;line-height:1.7;color:#1d2126">
<p>你的登录验证码是：</p>
<p style="font-size:30px;font-weight:700;letter-spacing:6px;margin:8px 0 16px">${code}</p>
<p style="color:#5f6670">10 分钟内有效。如果不是你本人操作，忽略这封邮件即可。</p>
<p style="color:#5f6670">Door4AI Lab · <a href="https://lab.door4ai.com">lab.door4ai.com</a></p></div>`;

  const r = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { authorization: `Bearer ${env.RESEND_API_KEY}`, 'content-type': 'application/json' },
    body: JSON.stringify({ from: env.MAIL_FROM, to: [email], subject, text, html }),
  });
  if (!r.ok) return { ok: false, error: `resend_${r.status}` };
  return { ok: true };
}
