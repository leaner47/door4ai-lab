// 用实验页同源的 o200k 分词器（public/labs/tokenizer-llm/tiktoken.js）数 token。
// 输入：stdin 一个字符串数组的 JSON；输出：每个字符串的 token 数。toy.py 调用它。
import fs from 'fs'; import path from 'path'; import { fileURLToPath } from 'url';
const here = path.dirname(fileURLToPath(import.meta.url));
globalThis.window = globalThis; globalThis.dispatchEvent = () => {}; globalThis.Event = class {};
(0, eval)(fs.readFileSync(path.join(here, '../../public/labs/tokenizer-llm/tiktoken.js'), 'utf8'));
const xs = JSON.parse(fs.readFileSync(0, 'utf8'));
console.log(JSON.stringify(xs.map((s) => window.TK.o200k.encode(s).length)));
