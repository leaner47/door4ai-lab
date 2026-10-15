// 后台身份校验（Cloudflare Access JWT）单元测试：本地生成 RSA 密钥、模拟 Access 公钥接口。
// 由 scripts/test-auth.sh 先用 esbuild 打包 functions/_lib/auth/admin.ts 再运行。
const { adminEmail } = await import(process.argv[2]);
const { subtle } = globalThis.crypto;
const team = 'door4ai.cloudflareaccess.com', aud = 'aud-123';
const kp = await subtle.generateKey({ name: 'RSASSA-PKCS1-v1_5', modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256' }, true, ['sign', 'verify']);
const other = await subtle.generateKey({ name: 'RSASSA-PKCS1-v1_5', modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256' }, true, ['sign', 'verify']);
const jwk = { ...(await subtle.exportKey('jwk', kp.publicKey)), kid: 'k1' };
globalThis.fetch = async (u) => (String(u) === `https://${team}/cdn-cgi/access/certs` ? new Response(JSON.stringify({ keys: [jwk] })) : new Response('no', { status: 404 }));
const b64u = (b) => Buffer.from(b).toString('base64url');
async function token(payload, key = kp.privateKey, kid = 'k1') {
  const h = b64u(JSON.stringify({ alg: 'RS256', kid })), p = b64u(JSON.stringify(payload));
  const sig = await subtle.sign('RSASSA-PKCS1-v1_5', key, new TextEncoder().encode(`${h}.${p}`));
  return `${h}.${p}.${b64u(new Uint8Array(sig))}`;
}
const env = { ACCESS_TEAM_DOMAIN: team, ACCESS_AUD: aud, ADMIN_EMAILS: 'boss@example.com' };
const req = (t) => new Request('https://lab.door4ai.com/admin/', { headers: t ? { 'cf-access-jwt-assertion': t } : {} });
const exp = Math.floor(Date.now() / 1000) + 600;
const good = { aud: [aud], iss: `https://${team}`, exp, email: 'Boss@example.com' };
const cases = [
  ['有效 JWT + 管理员邮箱', await token(good), 'boss@example.com'],
  ['没有 JWT', null, null],
  ['aud 不对', await token({ ...good, aud: ['other'] }), null],
  ['iss 不对', await token({ ...good, iss: 'https://evil.cloudflareaccess.com' }), null],
  ['已过期', await token({ ...good, exp: Math.floor(Date.now() / 1000) - 10 }), null],
  ['别的私钥伪造签名', await token(good, other.privateKey), null],
  ['未知 kid', await token(good, kp.privateKey, 'k9'), null],
  ['邮箱不在 ADMIN_EMAILS', await token({ ...good, email: 'x@example.com' }), null],
];
let pass = 0;
for (const [name, t, want] of cases) { const got = await adminEmail(env, req(t)); const ok = got === want; pass += ok; console.log(`${ok ? 'PASS' : 'FAIL'}  ${name} → ${got}`); }
const local = await adminEmail({ ...env, DEV_ADMIN_EMAIL: 'boss@example.com' }, req(null));
console.log(`${local === null ? 'PASS' : 'FAIL'}  线上域名上 DEV_ADMIN_EMAIL 不生效 → ${local}`); pass += local === null;
console.log(`${pass}/${cases.length + 1} passed`);
if (pass !== cases.length + 1) process.exit(1);
