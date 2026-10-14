// Resource 页条目。只放本人指定的内容，不要自行添加。
// 每条：title, note, links[]（按平台分列；没有该平台版本就不写）。
export type Link = { label: string; url: string; hint?: string };
export type Resource = { title: string; note: string; links: Link[] };

export const resources: Resource[] = [
  {
    title: 'FlClash',
    note: '开源跨平台代理客户端（Clash 内核）。下载页按版本列出所有安装包，按平台挑对应文件。',
    links: [
      { label: 'macOS', url: 'https://github.com/chen08209/FlClash/releases/latest', hint: 'Apple 芯片选 macos-arm64.dmg，Intel 选 macos-amd64.dmg' },
      { label: 'Windows', url: 'https://github.com/chen08209/FlClash/releases/latest', hint: '选 windows-amd64-setup.exe' },
      { label: 'Linux', url: 'https://github.com/chen08209/FlClash/releases/latest', hint: 'AppImage / .deb / .rpm 三选一' },
      { label: 'Android', url: 'https://github.com/chen08209/FlClash/releases/latest', hint: '多数手机选 android-arm64-v8a.apk' },
    ],
  },
  {
    title: 'Codex',
    note: 'OpenAI 的编程智能体。macOS 和 Windows 有桌面应用；Linux 用命令行版。',
    links: [
      { label: 'macOS', url: 'https://chatgpt.com/codex?app-landing-page=true', hint: '桌面应用' },
      { label: 'Windows', url: 'https://chatgpt.com/codex?app-landing-page=true', hint: '桌面应用' },
      { label: 'Linux', url: 'https://github.com/openai/codex', hint: '命令行：npm install -g @openai/codex' },
    ],
  },
  {
    title: 'Claude',
    note: 'Anthropic 的 Claude 桌面应用。Linux 版为 beta，支持 Ubuntu / Debian。',
    links: [
      { label: 'macOS', url: 'https://claude.ai/api/desktop/darwin/universal/dmg/latest/redirect', hint: '通用版 dmg' },
      { label: 'Windows', url: 'https://claude.ai/api/desktop/win32/x64/setup/latest/redirect', hint: 'x64；ARM 机器用 https://claude.ai/api/desktop/win32/arm64/setup/latest/redirect' },
      { label: 'Linux', url: 'https://code.claude.com/docs/en/desktop-linux', hint: 'beta，按文档安装' },
    ],
  },
  {
    title: 'door4ai.com',
    note: '我做的网站。',
    links: [{ label: '打开', url: 'https://door4ai.com' }],
  },
];
