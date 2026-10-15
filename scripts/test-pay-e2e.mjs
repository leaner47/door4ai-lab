// 支付端到端测试（模拟支付宝）。由 scripts/test-auth.sh 在账号测试之后调用：
// node scripts/test-pay-e2e.mjs <dev.log> <截图目录> <keys.json>
import { chromium } from 'playwright';
import { readFileSync } from 'node:fs';
import { execSync } from 'node:child_process';
import { createSign } from 'node:crypto';

const BASE = 'http://localhost:8788';
const MOCK = 'http://127.0.0.1:8790';
const [LOG, SHOTS, KEYS] = process.argv.slice(2);
const keys = JSON.parse(readFileSync(KEYS, 'utf8'));
const results = [];
const ok = (name, cond, extra = '') => results.push(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? '  — ' + extra : ''}`);
const sql = (q) => JSON.parse(execSync(`npx wrangler d1 execute door4ai-lab --local --json --command "${q.replace(/"/g, '\\"')}"`, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }))[0].results;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const lastCode = (email) => { const m = [...readFileSync(LOG, 'utf8').matchAll(new RegExp(`login code for ${email.replace(/\./g, '\\.')}: (\\d{6})`, 'g'))]; return m.length ? m.at(-1)[1] : null; };
const content = (p, ex) => Object.keys(p).filter((k) => !ex.includes(k) && p[k] !== '').sort().map((k) => `${k}=${p[k]}`).join('&');

const pages = [];
const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
process.on('uncaughtException', async (e) => { console.log(results.join('\n')); console.log('\nERROR', e.message.split('\n')[0], e.cause ? String(e.cause) : '', (e.stack||'').split('\n').find(l=>l.includes('test-pay-e2e')) || ''); for (const [i, p] of pages.entries()) await p.screenshot({ path: `${SHOTS}/pay-fail-${i}.png`, fullPage: true }).catch(() => {}); process.exit(1); });

async function ctx(opts = {}) {
  const c = await browser.newContext({ viewport: { width: 1100, height: 900 }, ...opts });
  const page = await c.newPage();
  pages.push(page);
  return page;
}
async function login(page, email) {
  await page.goto(BASE + '/login/?next=%2Fpricing%2F');
  await page.waitForSelector('#step-email:not([hidden])');
  await page.fill('#email', email);
  await page.click('#send');
  await page.waitForSelector('#step-code:not([hidden])');
  await sleep(300);
  await page.fill('#code', lastCode(email));
  await page.waitForURL((u) => !u.pathname.startsWith('/login'), { timeout: 10000 });
}
const post = (page, path, body) => page.evaluate(async ([p, b]) => { const r = await fetch(p, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(b) }); return { status: r.status, body: await r.json().catch(() => null) }; }, [path, body]);
const priceText = async (page) => { await page.goto(BASE + '/pricing/'); await page.waitForSelector('#price:not([hidden])'); return page.textContent('#amount'); };

// ---------- 后台设价 ----------
const AD = await ctx();
await login(AD, 'admin@example.com');
ok('后台建渠道码 jzq（家长群）', (await post(AD, '/api/admin/channel', { code: 'jzq', name: '中小学家长群' })).status === 200);
ok('后台设默认价 399', (await post(AD, '/api/admin/price', { channel: null, yuan: '399' })).status === 200);
ok('后台设 jzq 专属价 1299', (await post(AD, '/api/admin/price', { channel: 'jzq', yuan: '1299' })).status === 200);
const badPrice = await post(AD, '/api/admin/price', { channel: 'nope', yuan: '1' });
ok('不存在的渠道码不能设价', badPrice.status === 400, badPrice.body?.message);

// ---------- 家长群来的学员：1299 ----------
const A = await ctx();
const userA = 'parent@example.com';
await A.goto(BASE + '/?ref=jzq');
ok('未登录访客按来源链接看到 1299', (await priceText(A)) === '1299');
ok('未登录时按钮是「登录后购买」', await A.isVisible('#login'));
await login(A, userA);
ok('登录后价格仍为 1299（按首次触达渠道）', (await priceText(A)) === '1299');
await A.goto(BASE + '/?ref=xhs-cheap'); // 之后再点别的链接，价格不变
ok('之后换别的渠道链接，价格不变', (await priceText(A)) === '1299');
await A.screenshot({ path: `${SHOTS}/pay-pricing.png`, fullPage: true });

await A.click('#pay');
await A.waitForURL(/127\.0\.0\.1:8790\/gateway\.do/, { timeout: 10000 });
const lastA = await (await fetch(`${MOCK}/last`)).json();
ok('跳转到支付宝收银台，应用签名校验通过', lastA.signOk && lastA.method === 'alipay.trade.page.pay');
ok('支付宝订单金额 1299.00', lastA.biz.total_amount === '1299.00', lastA.biz.total_amount);
ok('notify_url 指向本站回调', lastA.notify_url === `${BASE}/api/pay/alipay/notify`);
const orderA = lastA.biz.out_trade_no;
await A.click('#pay');
await A.waitForURL(/\/pay\/return\//, { timeout: 10000 });
await A.waitForFunction(() => document.getElementById('h')?.textContent === '支付成功', null, { timeout: 15000 });
ok('付款后回到本站显示「支付成功」', true);
await A.screenshot({ path: `${SHOTS}/pay-return.png`, fullPage: true });
await A.goto(BASE + '/posts/attention-qkv/');
ok('付款后课程可看', A.url().endsWith('/posts/attention-qkv/'));
const entA = sql(`SELECT count(*) AS n FROM entitlements e JOIN users u ON u.id=e.user_id WHERE u.email='${userA}' AND e.source='order' AND e.revoked_at IS NULL`);
ok('数据库：一条购买权益', entA[0].n === 1);
const ev = sql(`SELECT result, signature_ok FROM webhook_events ORDER BY created_at DESC LIMIT 1`);
ok('回调记录：验签通过、结果 ok', ev[0].signature_ok === 1 && ev[0].result === 'ok', JSON.stringify(ev[0]));

// 重复通知 → 回 success，权益不重复
const re = await (await fetch(`${MOCK}/renotify?o=${orderA}`)).json();
const entA2 = sql(`SELECT count(*) AS n FROM entitlements e JOIN users u ON u.id=e.user_id WHERE u.email='${userA}' AND e.source='order'`);
ok('重复通知：回复 success 且不重复开通', re.reply === 'success' && entA2[0].n === 1, re.reply);

// 伪造通知（随便签名）→ failure
const forged = new URLSearchParams({ app_id: 'test-app', out_trade_no: orderA, trade_no: 'x', trade_status: 'TRADE_SUCCESS', total_amount: '1299.00', sign_type: 'RSA2', sign: 'Zm9yZ2Vk' });
const fr = await (await fetch(`${BASE}/api/pay/alipay/notify`, { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded' }, body: forged })).text();
ok('伪造签名的通知被拒（failure）', fr === 'failure', fr);

// 已拥有 → 不能再下单
await A.goto(BASE + '/pricing/');
await A.waitForSelector('#owned:not([hidden])');
ok('购买页显示「已拥有」', true);
const again = await post(A, '/api/pay/checkout', {});
ok('已拥有时下单被拒', again.status === 400, again.body?.message);

// ---------- 直接来的学员：399；通知丢失时靠查单补单 ----------
const B = await ctx();
const userB = 'direct@example.com';
await B.goto(BASE + '/');
await login(B, userB);
ok('无渠道来源的学员看到默认价 399', (await priceText(B)) === '399');
await B.click('#pay');
await B.waitForURL(/127\.0\.0\.1:8790\/gateway\.do/, { timeout: 10000 });
const lastB = await (await fetch(`${MOCK}/last`)).json();
ok('支付宝订单金额 399.00', lastB.biz.total_amount === '399.00');
const orderB = lastB.biz.out_trade_no;

// 金额被篡改的通知（用真支付宝私钥签名但金额不对）→ failure，不开通
const tam = { app_id: 'test-app', out_trade_no: orderB, trade_no: 'T1', trade_status: 'TRADE_SUCCESS', total_amount: '0.01', charset: 'utf-8' };
tam.sign_type = 'RSA2';
tam.sign = createSign('RSA-SHA256').update(content(tam, ['sign', 'sign_type'])).sign(keys.aliPrivatePem, 'base64');
const tr = await (await fetch(`${BASE}/api/pay/alipay/notify`, { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams(tam) })).text();
const stB = sql(`SELECT status FROM orders WHERE order_no='${orderB}'`);
ok('金额不符的通知被拒且订单仍待支付', tr === 'failure' && stB[0].status === 'pending', `${tr} / ${stB[0].status}`);

await B.click('#pay-silent'); // 付款但支付宝不发通知
await B.waitForURL(/\/pay\/return\//, { timeout: 10000 });
await B.waitForFunction(() => document.getElementById('h')?.textContent === '支付成功', null, { timeout: 40000 });
ok('通知丢失时，回跳页通过主动查单完成开通', true);

// ---------- 手机端走 wap 支付 ----------
const C = await ctx({ userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1', viewport: { width: 390, height: 844 } });
await login(C, 'phone@example.com');
await C.goto(BASE + '/pricing/');
await C.waitForSelector('#pay:not([hidden])');
await C.click('#pay');
await C.waitForURL(/127\.0\.0\.1:8790\/gateway\.do/, { timeout: 10000 });
const lastC = await (await fetch(`${MOCK}/last`)).json();
ok('手机浏览器走 alipay.trade.wap.pay', lastC.method === 'alipay.trade.wap.pay' && lastC.biz.product_code === 'QUICK_WAP_WAY');

// ---------- 后台订单与退款 ----------
await AD.goto(BASE + '/admin/');
await AD.click('.tabs button[data-tab=orders]');
await AD.waitForSelector('#orders button[data-refund]');
const rows = await AD.$$eval('#orders tr', (trs) => trs.map((t) => t.textContent));
ok('后台订单列表含两笔已支付', rows.filter((r) => r.includes('已支付')).length === 2, String(rows.length));
await AD.screenshot({ path: `${SHOTS}/pay-admin-orders.png`, fullPage: true });
AD.once('dialog', (d) => d.accept());
await AD.click(`#orders button[data-refund="${orderA}"]`);
await AD.waitForSelector('#orders-msg:not([hidden])');
ok('后台退款提示成功', (await AD.textContent('#orders-msg')).includes('已退款'), await AD.textContent('#orders-msg'));
const tradeA = await (await fetch(`${MOCK}/trade?o=${orderA}`)).json();
ok('支付宝侧收到退款 1299.00', tradeA.refunded && tradeA.refundAmount === '1299.00');
await A.goto(BASE + '/posts/attention-qkv/');
ok('退款后学员失去课程权限', /\/pricing\//.test(A.url()));
await AD.click('.tabs button[data-tab=channels]');
await AD.waitForSelector('input[data-price-for="jzq"]');
ok('渠道页显示 jzq 专属价 1299', (await AD.inputValue('input[data-price-for="jzq"]')) === '1299');
ok('渠道页显示默认价 399', (await AD.inputValue('#def-yuan')) === '399');
await AD.screenshot({ path: `${SHOTS}/pay-admin-channels.png`, fullPage: true });

await browser.close();
console.log(results.join('\n'));
const passed = results.filter((r) => r.startsWith('PASS')).length;
console.log(`\n${passed}/${results.length} passed`);
if (passed !== results.length) process.exit(1);
