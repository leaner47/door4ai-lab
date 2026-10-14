// Resource 页条目。只放本人指定的内容，不要自行添加。
// 每条：title, note, links[]。link.dl = 镜像 id（走 /dl/<id>，由本站 R2 镜像提供，仅登录用户可下）；link.url = 外部链接。
export type Link = { label: string; dl?: string; url?: string; hint?: string };
export type Resource = { title: string; note: string; links: Link[] };

export const resources: Resource[] = [
  {
    title: 'FlClash',
    note: '开源跨平台代理客户端（Clash 内核）。安装包由本站镜像，每天自动同步 GitHub 最新版本。',
    links: [
      { label: 'macOS · Apple 芯片', dl: 'flclash/macos-arm64' },
      { label: 'macOS · Intel', dl: 'flclash/macos-amd64' },
      { label: 'Windows', dl: 'flclash/windows' },
      { label: 'Linux · .deb', dl: 'flclash/linux-deb' },
      { label: 'Linux · AppImage', dl: 'flclash/linux-appimage' },
      { label: 'Android', dl: 'flclash/android' },
    ],
  },
  {
    title: 'Codex',
    note: 'OpenAI 的编程智能体。桌面版现已并入新版 ChatGPT 桌面应用，macOS 由本站镜像；Windows 只通过 Microsoft Store 分发；Linux 用命令行版。',
    links: [
      { label: 'macOS', dl: 'codex/macos' },
      { label: 'Windows', url: 'https://apps.microsoft.com/detail/9NT1R1C2HH7J', hint: 'Microsoft Store' },
      { label: 'Linux', url: 'https://github.com/openai/codex', hint: 'npm install -g @openai/codex' },
    ],
  },
  {
    title: 'Claude',
    note: 'Anthropic 的 Claude 桌面应用，由本站镜像官方最新版。Linux 版为 beta，支持 Ubuntu / Debian。',
    links: [
      { label: 'macOS', dl: 'claude/macos' },
      { label: 'Windows · x64', dl: 'claude/windows-x64' },
      { label: 'Windows · ARM64', dl: 'claude/windows-arm64' },
      { label: 'Linux · .deb (x64)', dl: 'claude/linux-amd64' },
      { label: 'Linux · .deb (ARM64)', dl: 'claude/linux-arm64' },
    ],
  },
  {
    title: 'door4ai.com',
    note: '我做的网站。',
    links: [{ label: '打开', url: 'https://door4ai.com' }],
  },
];
