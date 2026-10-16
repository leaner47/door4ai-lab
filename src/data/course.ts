// 课程「AI 从入门到精通」的分篇。按文章 frontmatter 的 order 划分：order < until 的归入该篇（按数组顺序取第一个满足的）。
// 新加一讲只要 order 落在对应区间就会自动归篇；要新开一篇，在这里加一项。页面上每篇只显示篇名（本人要求不加副标题/说明）。
export const PARTS = [
  { key: 'basics', title: '基础篇', until: 4 },
  { key: 'models', title: '模型篇', until: Infinity },
];
export const partOf = (order = 999) => PARTS.find((p) => order < p.until) ?? PARTS[PARTS.length - 1];
