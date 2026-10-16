// 课程「AI 从入门到精通」的分篇。按文章 frontmatter 的 order 划分：order < until 的归入该篇（按数组顺序取第一个满足的）。
// 新加一讲只要 order 落在对应区间就会自动归篇；要新开一篇，在这里加一项。
export const PARTS = [
  { key: 'basics', title: '基础篇', sub: '电脑、网络与开发工具', desc: 'AI 跑在什么上面、数据怎么在网上走、代码怎么管和怎么上线。', until: 4 },
  { key: 'models', title: '模型篇', sub: '大模型是怎么工作的', desc: '从 token 到注意力，再到推理时怎么省显存。', until: Infinity },
];
export const partOf = (order = 999) => PARTS.find((p) => order < p.until) ?? PARTS[PARTS.length - 1];
