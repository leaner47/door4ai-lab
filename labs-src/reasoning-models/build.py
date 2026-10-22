"""拼出实验页：skill 模板的 <head>、样式和尾部脚本 + lab.body.html + lab.js
运行：python3 labs-src/reasoning-models/build.py → public/labs/reasoning-models/index.html
"""
import pathlib, re
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
tpl = (ROOT / '.claude/skills/write-lesson/templates/lab.html').read_text(encoding='utf-8')
head = tpl[:tpl.index('<body>') + len('<body>')]
head = head.replace('__TITLE__', '推理模型实验室')
EXTRA = """.legend{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:14px;color:var(--muted);margin-top:8px}
.legend i{display:inline-block;width:14px;height:4px;border-radius:2px;vertical-align:middle;margin-right:6px}
.grid4{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px 16px;margin-bottom:14px}
.grid4 label{display:flex;flex-direction:column;gap:4px;font-size:13px;color:var(--muted)}
.grid4 input{font:inherit;font-size:16px;color:var(--fg);background:var(--bg);border:1px solid var(--line);border-radius:4px;padding:5px 8px;width:100%;box-sizing:border-box;font-variant-numeric:tabular-nums}
.sum{color:var(--fg)}
"""
head = head.replace('</style>', EXTRA + '</style>')
tail = tpl[tpl.index('<script src="/vendor/katex/katex.min.js">'):]
# 模板里的示范脚本（draw1 那段）换成本讲的脚本；保留 KaTeX 渲染与「图形尺寸上限」
m = re.search(r'<script>\n/\* 公式：.*?</script>\n', tail, re.S)
render = "<script>\ntry{renderMathInElement(document.body,{delimiters:[{left:'\\\\[',right:'\\\\]',display:true},{left:'\\\\(',right:'\\\\)',display:false}],throwOnError:false});}catch(e){}\n" + (HERE / 'lab.js').read_text(encoding='utf-8') + '</script>\n'
tail = tail[:m.start()] + render + tail[m.end():]
body = (HERE / 'lab.body.html').read_text(encoding='utf-8')
out = ROOT / 'public/labs/reasoning-models/index.html'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(head + '\n' + body + tail, encoding='utf-8')
print('wrote', out, len(out.read_text(encoding='utf-8')))
