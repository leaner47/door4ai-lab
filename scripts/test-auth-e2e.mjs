// 账号系统端到端测试。由 scripts/test-auth.sh 调用：node scripts/test-auth-e2e.mjs <dev.log> <截图目录>
// 需要本地 wrangler pages dev 已在 8788 端口运行（AUTH_ENABLED=1，DEV_MAIL_LOG=1，ADMIN_EMAILS=admin@example.com）
import { chromium } from 'playwright';
import { readFileSync } from 'node:fs';
import { execSync } from 'node:child_process';

const BASE = 'http://localhost:8788';
const LOG = process.argv[2];
const SHOTS = process.argv[3];
const results = [];
const ok = (name, cond, extra = '') => { results.push(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? '  — ' + extra : ''}`); };
const sql = (q) => JSON.parse(execSync(`npx wrangler d1 execute door4ai-lab --local --json --command "${q.replace(/"/g, '\\"')}"`, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }))[0].results;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
function lastCode(email) {
  const m = [...readFileSync(LOG, 'utf8').matchAll(new RegExp(`login code for ${email.replace('.', '\\.')}: (\\d{6})`, 'g'))];
  return m.length ? m[m.length - 1][1] : null;
}

const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});

async function newCtx() {
  const ctx = await browser.newContext({ viewport: { width: 1200, height: 900 } });
  const page = await ctx.newPage();
  page.on('pageerror', (e) => console.log('PAGEERROR', e.message));
  const cdp = await ctx.newCDPSession(page);
  await cdp.send('WebAuthn.enable');
  const { authenticatorId } = await cdp.send('WebAuthn.addVirtualAuthenticator', {
    options: { protocol: 'ctap2', transport: 'internal', hasResidentKey: true, hasUserVerification: true, isUserVerified: true, automaticPresenceSimulation: true },
  });
  return { ctx, page, cdp, authenticatorId };
}

async function emailLogin(page, email, from = '/posts/attention-qkv/') {
  await page.goto(BASE + from);
  await page.waitForURL(/\/login\//);
  await page.fill('#email', email);
  await page.click('#send');
  await page.waitForSelector('#step-code:not([hidden])');
  await sleep(300);
  const code = lastCode(email);
  await page.fill('#code', code); // 6 位自动提交
  await page.waitForURL((u) => !u.pathname.startsWith('/login'), { timeout: 10000 });
  return code;
}

// ---------- 1. 新用户：带渠道参数进站 → 邮箱验证码注册 ----------
const A = await newCtx();
const userA = 'alice@example.com';
await A.page.goto(BASE + '/?utm_source=xhs&utm_medium=post&ref=xhs-01');
await emailLogin(A.page, userA);
ok('新用户邮箱验证码注册后进入欢迎页', /\/account\/\?welcome=new/.test(A.page.url()), A.page.url());
await A.page.waitForSelector('#main:not([hidden])');
ok('账号页显示邮箱', (await A.page.textContent('#email')) === userA);
ok('导航显示已登录邮箱', (await A.page.textContent('#auth')).includes(userA));
await A.page.screenshot({ path: `${SHOTS}/account-welcome.png`, fullPage: true });

const attr = sql(`SELECT a.touch, a.utm_source, a.utm_medium, a.ref, a.landing_path FROM signup_attribution a JOIN users u ON u.id=a.user_id WHERE u.email='${userA}' ORDER BY a.touch`);
ok('注册来源写入（首次触达 utm_source=xhs, ref=xhs-01）', attr.some((r) => r.touch === 'first' && r.utm_source === 'xhs' && r.ref === 'xhs-01' && r.landing_path === '/'), JSON.stringify(attr));

// ---------- 2. 设置 Passkey + 填来源问卷 ----------
await A.page.click('#pk-add-welcome');
await A.page.waitForFunction(() => document.querySelectorAll('#pks li').length === 1, null, { timeout: 10000 });
ok('欢迎页设置 Passkey 成功', (await A.page.$$('#pks li')).length === 1);
await A.page.selectOption('#src', '小红书');
await A.page.click('#survey button[type=submit]');
await sleep(500);
const survey = sql(`SELECT survey_answer FROM signup_attribution a JOIN users u ON u.id=a.user_id WHERE u.email='${userA}' AND touch='first'`);
ok('来源问卷写入', survey[0]?.survey_answer === '小红书', JSON.stringify(survey));

// ---------- 3. 未购买 → 课程页跳购买页；实验页同样 ----------
await A.page.goto(BASE + '/posts/attention-qkv/');
ok('未购买访问课程 → 购买页', /\/pricing\/\?need=series%3Aai-mastery/.test(A.page.url()), A.page.url());
await A.page.screenshot({ path: `${SHOTS}/pricing.png`, fullPage: true });
const labResp = await A.page.goto(BASE + '/labs/kv-cache/');
ok('未购买访问实验页 → 购买页', /\/pricing\//.test(A.page.url()));
await A.page.goto(BASE + '/resources/');
ok('登录后资源页可看', A.page.url().endsWith('/resources/'));

// ---------- 4. 赠送全套权益 → 可看课程和实验 ----------
sql(`INSERT INTO entitlements (id, user_id, scope, source, starts_at) SELECT 'test-ent-1', id, 'series:ai-mastery', 'grant', 0 FROM users WHERE email='${userA}'`);
const r4 = await A.page.goto(BASE + '/posts/attention-qkv/');
ok('有权益后课程页可看', A.page.url().endsWith('/posts/attention-qkv/') && r4.status() === 200);
ok('课程页 cache-control 为 private', (r4.headers()['cache-control'] || '').includes('private'));
const r4b = await A.page.goto(BASE + '/labs/kv-cache/');
ok('有权益后实验页可看', A.page.url().endsWith('/labs/kv-cache/') && r4b.status() === 200);
await A.page.goto(BASE + '/account/');
await A.page.waitForSelector('#main:not([hidden])');
ok('账号页列出已购课程', (await A.page.textContent('#ents')).includes('AI 从入门到精通'));
await A.page.screenshot({ path: `${SHOTS}/account.png`, fullPage: true });

// ---------- 5. 单会话：另一台设备用 Passkey 登录同一账号 → 第一台被踢 ----------
const { credentials } = await A.cdp.send('WebAuthn.getCredentials', { authenticatorId: A.authenticatorId });
const B = await newCtx();
for (const c of credentials) await B.cdp.send('WebAuthn.addCredential', { authenticatorId: B.authenticatorId, credential: c });
await B.page.goto(BASE + '/login/?next=%2Fposts%2Fkv-cache-quantization%2F');
await B.page.waitForSelector('#step-email:not([hidden])').catch(() => {});
// 虚拟验证器会自动完成 Passkey 自动填充登录；若没有，再点按钮
await B.page.click('#pk-login', { timeout: 1500 }).catch(() => {});
await B.page.waitForURL(/\/posts\/kv-cache-quantization\//, { timeout: 10000 }).catch(() => {});
ok('第二台设备 Passkey 登录成功并回到原页面', B.page.url().endsWith('/posts/kv-cache-quantization/'), B.page.url());

await A.page.goto(BASE + '/posts/attention-qkv/');
ok('第一台设备被踢回登录页并带提示', /\/login\/\?.*kicked=1/.test(A.page.url()), A.page.url());
await A.page.waitForSelector('#kicked:not([hidden])');
await A.page.screenshot({ path: `${SHOTS}/login-kicked.png`, fullPage: true });
const active = sql(`SELECT count(*) AS n FROM sessions s JOIN users u ON u.id=s.user_id WHERE u.email='${userA}' AND revoked_at IS NULL`);
ok('数据库里该账号只有 1 个有效会话', active[0].n === 1, JSON.stringify(active));

// ---------- 6. 错误码、限流 ----------
const C = await newCtx();
await C.page.goto(BASE + '/login/');
await C.page.waitForSelector('#step-email:not([hidden])');
await C.page.fill('#email', 'bob@example.com');
await C.page.click('#send');
await C.page.waitForSelector('#step-code:not([hidden])');
await C.page.fill('#code', '000000');
await C.page.waitForSelector('#err2:not([hidden])');
ok('错误验证码提示剩余次数', (await C.page.textContent('#err2')).includes('还可以再试'), await C.page.textContent('#err2'));
const rl = await C.page.evaluate(async () => {
  const r = await fetch('/api/auth/otp', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ email: 'bob@example.com' }) });
  return [r.status, (await r.json()).message];
});
ok('60 秒内重复发送被限流', rl[0] === 429, rl.join(' '));
const csrf = await (await fetch(BASE + '/api/auth/otp', { method: 'POST', headers: { 'content-type': 'application/json', origin: 'https://evil.example' }, body: '{"email":"x@example.com"}' })).status;
ok('跨站来源的写请求被拒绝', csrf === 403, String(csrf));

// ---------- 7. 管理员邮箱无需权益 ----------
const D = await newCtx();
await emailLogin(D.page, 'admin@example.com');
await D.page.goto(BASE + '/posts/computer-anatomy/');
ok('ADMIN_EMAILS 里的邮箱可直接看课程', D.page.url().endsWith('/posts/computer-anatomy/'));

// ---------- 8. 退出 ----------
await B.page.goto(BASE + '/account/');
await B.page.waitForSelector('#main:not([hidden])');
await B.page.click('#logout');
await B.page.waitForURL(BASE + '/');
await B.page.goto(BASE + '/posts/attention-qkv/');
ok('退出后访问课程 → 登录页（无 kicked 提示）', /\/login\//.test(B.page.url()) && !B.page.url().includes('kicked'));

// ---------- 9. 手机宽度无横向滚动 ----------
const M = await browser.newContext({ viewport: { width: 390, height: 844 }, colorScheme: 'dark' });
const mp = await M.newPage();
await mp.goto(BASE + '/login/');
await mp.waitForSelector('#step-email:not([hidden])');
const ovf = await mp.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
ok('登录页 390px 无横向滚动', !ovf);
await mp.screenshot({ path: `${SHOTS}/login-mobile-dark.png`, fullPage: true });

await browser.close();
console.log(results.join('\n'));
console.log(`\n${results.filter((r) => r.startsWith('PASS')).length}/${results.length} passed`);
