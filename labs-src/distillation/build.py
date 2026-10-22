"""拼出蒸馏实验页：skill 模板的 head 与尾部脚本 + lab.body.html + core.js（计算核心）+ lab.js（界面）。
运行：python3 labs-src/distillation/build.py  → public/labs/distillation/index.html
改实验页请改这几个源文件再运行本脚本；run_lab.mjs 从生成的页面里抽出 core.js 那一段来跑。
"""
import pathlib
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
tpl = (ROOT / '.claude/skills/write-lesson/templates/lab.html').read_text(encoding='utf-8')
head = tpl[:tpl.index('<body>')].replace('__TITLE__', '蒸馏实验室')
tail = tpl[tpl.index('<script>/* 图形尺寸上限'):]
body = (HERE / 'lab.body.html').read_text(encoding='utf-8')
core = (HERE / 'core.js').read_text(encoding='utf-8')
ui = (HERE / 'lab.js').read_text(encoding='utf-8')
page = (head + '<body>\n' + body +
        '<script src="/vendor/katex/katex.min.js"></script>\n<script src="/vendor/katex/auto-render.min.js"></script>\n'
        "<script>\ntry{renderMathInElement(document.body,{delimiters:[{left:'\\\\[',right:'\\\\]',display:true},{left:'\\\\(',right:'\\\\)',display:false}],throwOnError:false});}catch(e){}\n</script>\n"
        '<script>\n' + core + '\n' + ui + '</script>\n' + tail)
out = ROOT / 'public/labs/distillation/index.html'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(page, encoding='utf-8')
print('ok', out, len(page))
