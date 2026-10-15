// 账号系统端到端测试。由 scripts/test-auth.sh 调用：node scripts/test-auth-e2e.mjs <dev.log> <截图目录>
// 需要本地 wrangler pages dev 已在 8788 端口运行（AUTH_ENABLED=1，DEV_MAIL_LOG=1，ADMIN_EMAILS=admin@example.com）
import { chromium } from 'playwright';
import { readFileSync } from 'node:fs';
import { execSync } from 'node:child_process';
import { createHmac } from 'node:crypto';

// 测试端自己算 TOTP（RFC 6238，SHA-1，6 位，30 秒）
function b32(s) { const A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'; let bits = 0, v = 0; const out = []; for (const c of s.replace(/\s/g, '')) { v = (v << 5) | A.indexOf(c); bits += 5; if (bits >= 8) { out.push((v >>> (bits - 8)) & 255); bits -= 8; } } return Buffer.from(out); }
function totp(secret, step = Math.floor(Date.now() / 30000)) { const msg = Buffer.alloc(8); msg.writeBigUInt64BE(BigInt(step)); const mac = createHmac('sha1', b32(secret)).update(msg).digest(); const o = mac[mac.length - 1] & 15; return String((mac.readUInt32BE(o) & 0x7fffffff) % 1e6).padStart(6, '0'); }
const nowStep = () => Math.floor(Date.now() / 30000);

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

process.on('unhandledRejection', () => {});
process.on('uncaughtException', async (e) => { console.log(results.join('\n')); console.log('\nERROR', e.message.split('\n')[0]); for (const [i, p] of pages.entries()) await p.screenshot({ path: `${SHOTS}/fail-${i}.png`, fullPage: true }).catch(() => {}); process.exit(1); });
const pages = [];
const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});

async function newCtx() {
  const ctx = await browser.newContext({ viewport: { width: 1200, height: 900 } });
  const page = await ctx.newPage();
  pages.push(page);
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
ok('右上角账号菜单显示已登录邮箱', (await A.page.textContent('#acct-email')) === userA);
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

// ---------- 10. 两步验证（TOTP + 恢复码） ----------
const T = await newCtx();
const userT = 'carol@example.com';
await emailLogin(T.page, userT, '/account/');
await T.page.goto(BASE + '/account/');
await T.page.waitForSelector('#totp-card:not([hidden])');
await T.page.click('#totp-start');
await T.page.waitForSelector('#totp-setup:not([hidden])');
const secret = (await T.page.textContent('#totp-secret')).replace(/\s/g, '');
ok('开启两步验证：显示二维码和 otpauth 链接', (await T.page.getAttribute('#totp-apple', 'href')).startsWith('otpauth://totp/Door4AI%20Lab') && !!(await T.page.$('#totp-qr svg')));
await T.page.screenshot({ path: `${SHOTS}/totp-setup.png`, fullPage: true });
await T.page.fill('#totp-code', '000000');
await T.page.click('#totp-enable');
await T.page.waitForSelector('#err-totp:not([hidden])');
ok('错误动态码不能开启', (await T.page.textContent('#err-totp')).includes('动态码不对'));
const enableStep = nowStep();
await T.page.fill('#totp-code', totp(secret, enableStep));
await T.page.click('#totp-enable');
await T.page.waitForSelector('#totp-codes:not([hidden])');
const recCodes = await T.page.$$eval('#codes li', (els) => els.map((e) => e.textContent));
ok('开启后显示 10 个恢复码', recCodes.length === 10, recCodes[0]);
await T.page.screenshot({ path: `${SHOTS}/totp-codes.png`, fullPage: true });
await T.page.click('#codes-done');
await T.page.waitForSelector('#totp-on:not([hidden])');
ok('账号页显示已开启、剩余 10 个', (await T.page.textContent('#rec-left')) === '10');

// 退出，用邮箱验证码重新登录 → 需要第二步
await T.page.click('#logout');
await T.page.waitForURL(BASE + '/');
await sleep(61000); // 验证码发送限流 60 秒
await T.page.goto(BASE + '/login/?next=%2Faccount%2F');
await T.page.waitForSelector('#step-email:not([hidden])');
await T.page.fill('#email', userT);
await T.page.click('#send');
await T.page.waitForSelector('#step-code:not([hidden])');
await sleep(300);
await T.page.fill('#code', lastCode(userT));
await T.page.waitForSelector('#step-mfa:not([hidden])');
ok('开启两步验证后，邮箱验证码登录要求第二步', true);
const noSession = await T.page.evaluate(() => fetch('/api/me').then((r) => r.json()));
ok('第二步之前没有会话', noSession.user === null);
await T.page.fill('#mfa', '000000');
await T.page.click('#mfa-go');
await T.page.waitForSelector('#err3:not([hidden])');
ok('错误动态码不能通过第二步', (await T.page.textContent('#err3')).includes('不对'));
const usedCode = totp(secret, nowStep());
await T.page.fill('#mfa', usedCode);
await T.page.click('#mfa-go');
await T.page.waitForURL(/\/account\//, { timeout: 10000 });
ok('输入当前动态码后登录成功', T.page.url().endsWith('/account/'), T.page.url());
const replay = await T.page.evaluate((c) => fetch('/api/me/totp/recovery', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ code: c }) }).then((r) => r.status), usedCode);
ok('刚用过的动态码不能再用（防重放）', replay === 400, String(replay));

// 再退出，用恢复码登录
await T.page.waitForSelector('#main:not([hidden])');
await T.page.click('#logout');
await T.page.waitForURL(BASE + '/');
await sleep(61000); // 验证码发送限流 60 秒
await T.page.goto(BASE + '/login/');
await T.page.waitForSelector('#step-email:not([hidden])');
await T.page.fill('#email', userT);
await T.page.click('#send');
await T.page.waitForSelector('#step-code:not([hidden])');
await sleep(300);
await T.page.fill('#code', lastCode(userT));
await T.page.waitForSelector('#step-mfa:not([hidden])');
await T.page.fill('#mfa', recCodes[0]);
await T.page.click('#mfa-go');
await T.page.waitForURL(/recovery=used/, { timeout: 10000 });
await T.page.waitForSelector('#totp-on:not([hidden])');
ok('恢复码可以登录，剩余 9 个', (await T.page.textContent('#rec-left')) === '9');

// ---------- 11. 后台 ----------
const notAdmin = await T.page.goto(BASE + '/admin/');
ok('非管理员访问 /admin → 403', notAdmin.status() === 403, String(notAdmin.status()));
const apiNotAdmin = await T.page.evaluate(() => fetch('/api/admin/stats').then((r) => r.status));
ok('非管理员调后台接口 → 403', apiNotAdmin === 403);

const AD = D.page; // admin@example.com，已登录
await AD.goto(BASE + '/admin/');
await AD.waitForFunction(() => document.getElementById('who')?.textContent === 'admin@example.com');
await AD.waitForFunction(() => document.querySelectorAll('#kpis div').length === 7);
const kpiUsers = await AD.textContent('#kpis div:first-child b');
ok('后台概览：注册总数 = 3（alice、admin、carol；bob 没完成验证不算）', Number(kpiUsers) === 3, kpiUsers);
ok('后台概览：来源表含 xhs-01', (await AD.textContent('#by-source')).includes('xhs-01'));
ok('后台概览：问卷含小红书', (await AD.textContent('#by-survey')).includes('小红书'));
await AD.screenshot({ path: `${SHOTS}/admin-stats.png`, fullPage: true });

// 渠道码
await AD.click('.tabs button[data-tab=channels]');
await AD.fill('#ch-code', 'xhs-01');
await AD.fill('#ch-name', '小红书 10 月笔记');
await AD.click('#ch-form button');
await AD.waitForSelector('#channels tr td b');
const chCells = await AD.$$eval('#channels tr:first-child td', (tds) => tds.map((t) => t.textContent.trim()));
ok('新建渠道码并统计到首次触达注册 1、付费 0', chCells[0].includes('xhs-01') && chCells[2] === '1' && chCells[4] === '0', chCells.join(' | '));
await AD.click('#channels button[data-qr]');
await AD.waitForSelector('#qr-box svg');
await AD.screenshot({ path: `${SHOTS}/admin-channels.png`, fullPage: true });

// 给还没注册的邮箱开通，然后他登录即可看课
await AD.click('.tabs button[data-tab=users]');
await AD.waitForSelector('#g-scope option', { state: 'attached' });
await AD.fill('#g-email', 'dave@example.com');
await AD.selectOption('#g-scope', 'series:ai-mastery');
await AD.click('#grant button');
await AD.waitForSelector('#detail:not([hidden]) h3');
ok('后台给新邮箱开通全套', (await AD.textContent('#detail')).includes('AI 从入门到精通'));
await AD.screenshot({ path: `${SHOTS}/admin-user.png`, fullPage: true });
const E = await newCtx();
await emailLogin(E.page, 'dave@example.com');
await E.page.goto(BASE + '/posts/attention-qkv/');
ok('被开通的新用户登录后可看课程', E.page.url().endsWith('/posts/attention-qkv/'));

// 撤销 → 失去权限；强制下线 → 回登录页
AD.once('dialog', (d) => d.accept());
await AD.click('#detail button[data-revoke]');
await AD.waitForSelector('#detail .tag.off');
await E.page.goto(BASE + '/posts/attention-qkv/');
ok('撤销权益后跳购买页', /\/pricing\//.test(E.page.url()));
await AD.click('#detail button[data-act=logout]');
await AD.waitForSelector('#detail-msg:not([hidden])');
await E.page.goto(BASE + '/resources/');
ok('后台强制下线后需要重新登录', /\/login\//.test(E.page.url()));
await AD.click('.tabs button[data-tab=audit]');
await AD.waitForSelector('#audit tr td');
const auditText = await AD.textContent('#audit');
ok('操作日志记录开通/撤销/下线/渠道码', ['开通', '撤销权益', '强制下线', '新建渠道码'].every((w) => auditText.includes(w)));

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
