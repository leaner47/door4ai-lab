// 支付宝开放平台（RSA2）：电脑网站支付 / 手机网站支付 下单、异步通知验签、查单、退款。
// 只用 WebCrypto，不依赖 Node SDK，能跑在 Cloudflare Pages Functions。
//
// 环境变量：
//   ALIPAY_APP_ID          应用 ID
//   ALIPAY_PRIVATE_KEY     应用私钥（PKCS#1 或 PKCS#8，可带/不带 PEM 头，Secret）
//   ALIPAY_PUBLIC_KEY      支付宝公钥（不是应用公钥！SPKI，可带/不带 PEM 头，Secret）
//   ALIPAY_GATEWAY         可选，默认 https://openapi.alipay.com/gateway.do（沙箱填沙箱网关）

export type AlipayEnv = {
  ALIPAY_APP_ID?: string;
  ALIPAY_PRIVATE_KEY?: string;
  ALIPAY_PUBLIC_KEY?: string;
  ALIPAY_GATEWAY?: string;
};

export const alipayConfigured = (env: AlipayEnv) => !!(env.ALIPAY_APP_ID && env.ALIPAY_PRIVATE_KEY && env.ALIPAY_PUBLIC_KEY);
const gateway = (env: AlipayEnv) => env.ALIPAY_GATEWAY || 'https://openapi.alipay.com/gateway.do';

// ---------- 密钥 ----------
function pemBody(s: string): Uint8Array<ArrayBuffer> {
  const b64 = s.replace(/-----[^-]+-----/g, '').replace(/\s+/g, '');
  const bin = atob(b64);
  const u = new Uint8Array(new ArrayBuffer(bin.length));
  for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  return u;
}

function derLen(n: number): number[] {
  if (n < 0x80) return [n];
  const out: number[] = [];
  while (n > 0) { out.unshift(n & 0xff); n >>= 8; }
  return [0x80 | out.length, ...out];
}

// PKCS#1 RSAPrivateKey → PKCS#8 PrivateKeyInfo（WebCrypto 只认 PKCS#8）
function pkcs1ToPkcs8(pkcs1: Uint8Array): Uint8Array<ArrayBuffer> {
  const algId = [0x30, 0x0d, 0x06, 0x09, 0x2a, 0x86, 0x48, 0x86, 0xf7, 0x0d, 0x01, 0x01, 0x01, 0x05, 0x00];
  const octet = [0x04, ...derLen(pkcs1.length), ...pkcs1];
  const body = [0x02, 0x01, 0x00, ...algId, ...octet];
  return new Uint8Array([0x30, ...derLen(body.length), ...body]);
}

// PKCS#8 的第 2 个元素是 INTEGER 0 后跟 AlgorithmIdentifier；PKCS#1 的第 2 个元素是 INTEGER 0 后跟 INTEGER（模数）
function isPkcs8(der: Uint8Array): boolean {
  let i = 1;
  i += der[i] & 0x80 ? (der[i] & 0x7f) + 1 : 1; // 跳过外层 SEQUENCE 长度
  if (der[i] !== 0x02) return false;
  i += 2 + der[i + 1]; // 跳过 version INTEGER
  return der[i] === 0x30;
}

let keyCache: { priv?: CryptoKey; pub?: CryptoKey; src?: string } = {};
async function keys(env: AlipayEnv) {
  const src = `${env.ALIPAY_PRIVATE_KEY}|${env.ALIPAY_PUBLIC_KEY}`;
  if (keyCache.src === src && keyCache.priv && keyCache.pub) return keyCache as { priv: CryptoKey; pub: CryptoKey };
  const der = pemBody(env.ALIPAY_PRIVATE_KEY!);
  const priv = await crypto.subtle.importKey('pkcs8', isPkcs8(der) ? der : pkcs1ToPkcs8(der), { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['sign']);
  const pub = await crypto.subtle.importKey('spki', pemBody(env.ALIPAY_PUBLIC_KEY!), { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify']);
  keyCache = { priv, pub, src };
  return { priv, pub };
}

const toB64 = (buf: ArrayBuffer) => { let s = ''; for (const b of new Uint8Array(buf)) s += String.fromCharCode(b); return btoa(s); };

// 待签名串：参数按 key 字典序，key=value 用 & 连接；空值不参与；sign 不参与（请求签名时 sign_type 参与，验签时不参与）
export function signContent(params: Record<string, string | undefined>, exclude: string[]): string {
  return Object.keys(params)
    .filter((k) => !exclude.includes(k) && params[k] !== undefined && params[k] !== '')
    .sort()
    .map((k) => `${k}=${params[k]}`)
    .join('&');
}

export async function rsaSign(env: AlipayEnv, content: string): Promise<string> {
  const { priv } = await keys(env);
  return toB64(await crypto.subtle.sign('RSASSA-PKCS1-v1_5', priv, new TextEncoder().encode(content)));
}

export async function rsaVerify(env: AlipayEnv, content: string, signB64: string): Promise<boolean> {
  const { pub } = await keys(env);
  try {
    return await crypto.subtle.verify('RSASSA-PKCS1-v1_5', pub, pemBody(signB64), new TextEncoder().encode(content));
  } catch {
    return false;
  }
}

// 支付宝要求北京时间 yyyy-MM-dd HH:mm:ss
function bjTime(t = Date.now()): string {
  const d = new Date(t + 8 * 3600 * 1000);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getUTCFullYear()}-${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())} ${p(d.getUTCHours())}:${p(d.getUTCMinutes())}:${p(d.getUTCSeconds())}`;
}

async function signedParams(env: AlipayEnv, method: string, biz: Record<string, unknown>, extra: Record<string, string> = {}) {
  const params: Record<string, string> = {
    app_id: env.ALIPAY_APP_ID!,
    method,
    format: 'JSON',
    charset: 'utf-8',
    sign_type: 'RSA2',
    timestamp: bjTime(),
    version: '1.0',
    biz_content: JSON.stringify(biz),
    ...extra,
  };
  params.sign = await rsaSign(env, signContent(params, ['sign']));
  return params;
}

export const yuan = (cents: number) => (cents / 100).toFixed(2);

// 下单：返回跳转到支付宝收银台的 URL（GET）。mode = page（电脑扫码/登录）| wap（手机唤起支付宝）
export async function createPayUrl(
  env: AlipayEnv,
  o: { outTradeNo: string; amount: number; subject: string; notifyUrl: string; returnUrl: string; mode: 'page' | 'wap'; timeoutMinutes?: number },
): Promise<string> {
  const biz = {
    out_trade_no: o.outTradeNo,
    total_amount: yuan(o.amount),
    subject: o.subject,
    product_code: o.mode === 'wap' ? 'QUICK_WAP_WAY' : 'FAST_INSTANT_TRADE_PAY',
    timeout_express: `${o.timeoutMinutes ?? 30}m`,
    ...(o.mode === 'wap' ? { quit_url: o.returnUrl } : {}),
  };
  const params = await signedParams(env, o.mode === 'wap' ? 'alipay.trade.wap.pay' : 'alipay.trade.page.pay', biz, {
    notify_url: o.notifyUrl,
    return_url: o.returnUrl,
  });
  return `${gateway(env)}?${new URLSearchParams(params)}`;
}

// 异步通知验签：除 sign、sign_type 外全部参数参与
export async function verifyNotify(env: AlipayEnv, form: Record<string, string>): Promise<boolean> {
  if (!form.sign) return false;
  return rsaVerify(env, signContent(form, ['sign', 'sign_type']), form.sign);
}

// 服务端调用（查单、退款）。响应走 HTTPS 直连支付宝网关，再校验响应签名。
async function call(env: AlipayEnv, method: string, biz: Record<string, unknown>): Promise<any> {
  const params = await signedParams(env, method, biz);
  const r = await fetch(gateway(env), {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded;charset=utf-8' },
    body: new URLSearchParams(params),
  });
  const text = await r.text();
  const key = method.replace(/\./g, '_') + '_response';
  const data = JSON.parse(text);
  // 响应签名针对原文里 "<key>": 后面那段 JSON 的原始字节（不能重新序列化）
  const at = text.indexOf(`"${key}"`);
  const signAt = text.lastIndexOf('"sign"');
  if (data.sign && at >= 0 && signAt > at) {
    const start = text.indexOf('{', at);
    const end = text.lastIndexOf('}', signAt);
    if (!(await rsaVerify(env, text.slice(start, end + 1), data.sign))) throw new Error('alipay response signature invalid');
  } else if (data[key]?.code === '10000') {
    throw new Error('alipay response not signed'); // 成功响应必须带签名
  }
  return data[key];
}

export async function queryTrade(env: AlipayEnv, outTradeNo: string) {
  const res = await call(env, 'alipay.trade.query', { out_trade_no: outTradeNo });
  return res as { code: string; msg: string; sub_code?: string; trade_status?: string; total_amount?: string; trade_no?: string };
}

export async function refundTrade(env: AlipayEnv, outTradeNo: string, amount: number, reason: string) {
  const res = await call(env, 'alipay.trade.refund', { out_trade_no: outTradeNo, refund_amount: yuan(amount), refund_reason: reason, out_request_no: `${outTradeNo}-R` });
  return res as { code: string; msg: string; sub_code?: string; sub_msg?: string; fund_change?: string };
}
