"""拼实验页：skill 模板的头尾 + lab.body.html → public/labs/distributed-training/index.html
运行：python3 labs-src/distributed-training/build_lab.py（改实验页改 lab.body.html 后重跑）"""
import pathlib
HERE = pathlib.Path(__file__).resolve().parent; ROOT = HERE.parent.parent
tpl = (ROOT / '.claude/skills/write-lesson/templates/lab.html').read_text(encoding='utf-8')
head = tpl[:tpl.index('<body>') + len('<body>')].replace('__TITLE__', '分布式训练实验室')
tail = tpl[tpl.index('<script>/* 图形尺寸上限'):]
out = ROOT / 'public/labs/distributed-training/index.html'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(head + '\n' + (HERE / 'lab.body.html').read_text(encoding='utf-8') + tail, encoding='utf-8')
print('ok', out)
