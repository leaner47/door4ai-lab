// 本地模拟支付宝网关（仅测试用）：node scripts/mock-alipay.mjs <keys.json> [port]
// - GET  /gateway.do?...   收银台：校验应用签名，显示「确认支付」页面
// - GET  /pay?o=&notify=1  模拟付款：记为已付，(可选)发签名的异步通知，然后跳回 return_url
// - POST /gateway.do       alipay.trade.query / alipay.trade.refund：校验签名，返回带支付宝签名的 JSON
// - GET  /last             最近一次收银台请求的参数（测试断言用）
import http from 'node:http';
import { readFileSync } from 'node:fs';
import { createSign, createVerify } from 'node:crypto';

const keys = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const PORT = Number(process.argv[3] || 8790);
const trades = new Map(); // out_trade_no → { params, biz, paid, tradeNo, refunded }
let last = null;

const content = (p, exclude) => Object.keys(p).filter((k) => !exclude.includes(k) && p[k] !== '' && p[k] != null).sort().map((k) => `${k}=${p[k]}`).join('&');
const verifyApp = (p) => createVerify('RSA-SHA256').update(content(p, ['sign'])).verify(keys.appPublicPem, p.sign, 'base64');
const signAli = (s) => createSign('RSA-SHA256').update(s).sign(keys.aliPrivatePem, 'base64');

async function sendNotify(t) {
  const now = new Date(Date.now() + 8 * 3600e3).toISOString().replace('T', ' ').slice(0, 19);
  const p = {
    app_id: t.params.app_id, out_trade_no: t.biz.out_trade_no, trade_no: t.tradeNo, trade_status: 'TRADE_SUCCESS',
    total_amount: t.biz.total_amount, gmt_payment: now, notify_time: now, notify_type: 'trade_status_sync', notify_id: 'n' + Date.now(), charset: 'utf-8', version: '1.0',
  };
  p.sign_type = 'RSA2';
  p.sign = signAli(content(p, ['sign', 'sign_type']));
  const r = await fetch(t.params.notify_url, { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams(p) });
  t.lastNotify = { body: new URLSearchParams(p).toString(), reply: await r.text() };
}

process.on('unhandledRejection', (e) => console.error('mock unhandled', e));
const server = http.createServer(async (req, res) => {
  try { await handle(req, res); } catch (e) { console.error('mock error', e); res.writeHead(500); res.end(String(e)); }
});
async function handle(req, res) {
  const url = new URL(req.url, `http://127.0.0.1:${PORT}`);
  const send = (code, body, type = 'text/html; charset=utf-8') => { res.writeHead(code, { 'content-type': type, connection: 'close' }); res.end(body); };

  if (req.method === 'GET' && url.pathname === '/gateway.do') {
    const p = Object.fromEntries(url.searchParams);
    if (!verifyApp(p)) return send(400, 'BAD_APP_SIGNATURE');
    const biz = JSON.parse(p.biz_content);
    trades.set(biz.out_trade_no, { params: p, biz, paid: false, tradeNo: '2026' + Date.now() });
    last = { method: p.method, biz, notify_url: p.notify_url, return_url: p.return_url, signOk: true };
    return send(200, `<!doctype html><meta charset="utf-8"><title>模拟支付宝</title><h1>模拟支付宝收银台</h1><p id="amt">${biz.total_amount}</p><p>${biz.subject}</p>
      <a id="pay" href="/pay?o=${encodeURIComponent(biz.out_trade_no)}&notify=1">确认支付</a> <a id="pay-silent" href="/pay?o=${encodeURIComponent(biz.out_trade_no)}&notify=0">付款但不发通知</a>`);
  }
  if (req.method === 'GET' && url.pathname === '/pay') {
    const t = trades.get(url.searchParams.get('o'));
    if (!t) return send(404, 'no trade');
    t.paid = true;
    if (url.searchParams.get('notify') === '1') await sendNotify(t);
    res.writeHead(302, { location: t.params.return_url, connection: 'close' });
    return res.end();
  }
  if (req.method === 'GET' && url.pathname === '/renotify') { // 重放同一个通知
    const t = trades.get(url.searchParams.get('o'));
    await sendNotify(t);
    return send(200, JSON.stringify(t.lastNotify), 'application/json');
  }
  if (req.method === 'GET' && url.pathname === '/last') return send(200, JSON.stringify(last), 'application/json');
  if (req.method === 'GET' && url.pathname === '/trade') return send(200, JSON.stringify(trades.get(url.searchParams.get('o')) || null), 'application/json');

  if (req.method === 'POST' && url.pathname === '/gateway.do') {
    let raw = '';
    for await (const c of req) raw += c;
    const p = Object.fromEntries(new URLSearchParams(raw));
    if (!verifyApp(p)) return send(400, 'BAD_APP_SIGNATURE', 'text/plain');
    const biz = JSON.parse(p.biz_content);
    const t = trades.get(biz.out_trade_no);
    let inner;
    if (p.method === 'alipay.trade.query') {
      inner = !t ? { code: '40004', msg: 'Business Failed', sub_code: 'ACQ.TRADE_NOT_EXIST' }
        : { code: '10000', msg: 'Success', out_trade_no: biz.out_trade_no, trade_no: t.tradeNo, total_amount: t.biz.total_amount, trade_status: t.refunded ? 'TRADE_CLOSED' : t.paid ? 'TRADE_SUCCESS' : 'WAIT_BUYER_PAY', fund_bill_list: [{ amount: t.biz.total_amount, fund_channel: 'ALIPAYACCOUNT' }] };
    } else if (p.method === 'alipay.trade.refund') {
      if (!t || !t.paid) inner = { code: '40004', msg: 'Business Failed', sub_code: 'ACQ.TRADE_NOT_EXIST', sub_msg: '交易不存在' };
      else { t.refunded = true; t.refundAmount = biz.refund_amount; inner = { code: '10000', msg: 'Success', fund_change: 'Y', refund_fee: biz.refund_amount, out_trade_no: biz.out_trade_no }; }
    } else inner = { code: '40004', msg: 'unknown method' };
    const key = p.method.replace(/\./g, '_') + '_response';
    const innerJson = JSON.stringify(inner);
    return send(200, `{"${key}":${innerJson},"sign":"${signAli(innerJson)}"}`, 'application/json; charset=utf-8');
  }
  send(404, 'not found');
}
server.keepAliveTimeout = 0;
server.listen(PORT, '127.0.0.1', () => console.log(`mock alipay on ${PORT}`));
