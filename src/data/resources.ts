// 资源库条目。每条：title, url, note（为什么值得看）。按 section 分组，顺序即展示顺序。
export const resources: { section: string; items: { title: string; url: string; note: string }[] }[] = [
  {
    section: 'LLM 推理与 KV Cache',
    items: [
      { title: 'KIVI: A Tuning-Free Asymmetric 2bit Quantization for KV Cache', url: 'https://arxiv.org/abs/2402.02750', note: 'K 按通道、V 按 token 分组量化的出处，本站第 1 讲实验 03 的依据。' },
      { title: 'KVQuant: Towards 10 Million Context Length LLM Inference', url: 'https://arxiv.org/abs/2401.18079', note: 'RoPE 前量化 K、离群值稀疏存储，把 KV 压到 3 bit 以下。' },
      { title: 'DeepSeek-V2 技术报告（MLA 章节）', url: 'https://arxiv.org/abs/2405.04434', note: 'Multi-head Latent Attention 的原始定义，低秩压缩 KV 的思路。' },
      { title: 'vLLM', url: 'https://github.com/vllm-project/vllm', note: 'PagedAttention 与 prefix caching 的参考实现，看推理引擎怎么管理 KV cache。' },
      { title: 'SGLang', url: 'https://github.com/sgl-project/sglang', note: 'RadixAttention：用前缀树在多请求之间共享 KV cache。' },
    ],
  },
  {
    section: '打基础',
    items: [
      { title: 'The Illustrated Transformer', url: 'https://jalammar.github.io/illustrated-transformer/', note: '最经典的 Transformer 图解，读完再看本站实验会更顺。' },
      { title: 'Andrej Karpathy — Neural Networks: Zero to Hero', url: 'https://karpathy.ai/zero-to-hero.html', note: '从反向传播手写到 GPT，全程写代码，不跳步。' },
    ],
  },
];
