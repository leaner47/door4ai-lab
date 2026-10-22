"""拼出实验页：skill 模板的样式与尾部脚本 + lab.body.html + lab.script.js → public/labs/vectors-softmax/index.html
运行：python3 labs-src/vectors-softmax/build.py
"""
import pathlib, re
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
tpl = (ROOT / '.claude/skills/write-lesson/templates/lab.html').read_text(encoding='utf-8')
head = tpl[:tpl.index('<body>')]
fit = tpl[tpl.index('<script>/* 图形尺寸上限'):tpl.index('</body>')]
EXTRA = """.mat{display:inline-grid;grid-template-columns:repeat(2,64px);gap:4px;padding:2px 8px;border-left:2px solid var(--fg);border-right:2px solid var(--fg);border-radius:4px}
.vec{display:inline-grid;grid-template-columns:64px;gap:4px;padding:2px 8px;border-left:2px solid var(--fg);border-right:2px solid var(--fg);border-radius:4px}
.mat input,.vec input,input.num{font:inherit;font-size:15px;width:64px;box-sizing:border-box;padding:3px 6px;border:1px solid var(--line);border-radius:4px;background:var(--bg);color:var(--fg);text-align:right}
input.num{width:96px}
.duo{display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:center}
@media (max-width:760px){.duo{grid-template-columns:1fr}}
.verdict{font-size:16px;margin:10px 0 0}
.okc{color:var(--ok);font-weight:700;margin-right:6px}
.bad{color:var(--warn);font-weight:700;margin-right:6px}
td .bad{margin:0}
#sl4 .ctrl input{width:120px}
th.num{text-align:right}
.figw{max-width:760px;margin-inline:auto}
.figw.narrow{max-width:520px}
"""
head = head.replace('<title>__TITLE__</title>', '<title>数学实验室</title>').replace('</style>', EXTRA + '</style>')
body = (HERE / 'lab.body.html').read_text(encoding='utf-8')
js = (HERE / 'lab.script.js').read_text(encoding='utf-8')
html = (head + '<body>\n<!-- 本页由 labs-src/vectors-softmax/build.py 生成：改 lab.body.html / lab.script.js 后重跑 -->\n' + body +
        '<script src="/vendor/katex/katex.min.js"></script>\n<script src="/vendor/katex/auto-render.min.js"></script>\n<script>\n' + js + '</script>\n' + fit + '</body>\n</html>\n')
assert '__' not in re.sub(r'<script>.*?</script>', '', html, flags=re.S).replace('__proto__', ''), 'template placeholder left'
out = ROOT / 'public/labs/vectors-softmax/index.html'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(html, encoding='utf-8')
print('ok', len(html))
