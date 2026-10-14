// 镜像源定义。每个 target 有稳定 id（app/platform），resolve() 返回当前最新文件的 url / filename / version / sha256。
export type Resolved = { url: string; filename: string; version: string; sha256?: string | null };
export type Target = { id: string; app: string; platform: string; label: string; resolve: () => Promise<Resolved> };

const UA = 'door4ai-lab-mirror/1.0 (+https://lab.door4ai.com)';
const H = { 'User-Agent': UA, Accept: '*/*' };

// ---------- FlClash: GitHub latest release ----------
// GitHub API 匿名配额很小（按出口 IP 计），同一轮同步里多个 target 共用一次结果，并用 Cache API 存 10 分钟。
let releaseMemo: Promise<any> | null = null;
async function flclashRelease(): Promise<any> {
  if (releaseMemo) return releaseMemo;
  releaseMemo = (async () => {
    const api = 'https://api.github.com/repos/chen08209/FlClash/releases/latest';
    const cacheKey = new Request('https://lab.door4ai.com/__cache/flclash-latest.json');
    const cache = (caches as any).default as Cache;
    const hit = await cache.match(cacheKey);
    if (hit) return hit.json();
    const r = await fetch(api, { headers: { ...H, Accept: 'application/vnd.github+json' } });
    if (!r.ok) {
      releaseMemo = null;
      throw new Error(`github ${r.status}`);
    }
    const data = await r.json();
    await cache.put(cacheKey, new Response(JSON.stringify(data), { headers: { 'content-type': 'application/json', 'cache-control': 'public, max-age=600' } }));
    return data;
  })();
  return releaseMemo;
}
// 不依赖 API 的版本解析：/releases/latest 会 302 到 /releases/tag/vX.Y.Z，资源文件名有固定规律。
let tagMemo: Promise<string> | null = null;
async function flclashLatestTag(): Promise<string> {
  if (tagMemo) return tagMemo;
  tagMemo = (async () => {
    const r = await fetch('https://github.com/chen08209/FlClash/releases/latest', { method: 'GET', redirect: 'manual', headers: H });
    try { await r.body?.cancel(); } catch {}
    const loc = r.headers.get('location') || '';
    const m = /\/releases\/tag\/(v[\d.]+)/.exec(loc);
    if (!m) { tagMemo = null; throw new Error(`cannot resolve latest tag (${r.status})`); }
    return m[1];
  })();
  return tagMemo;
}
function flclash(platform: string, label: string, suffix: string, re: RegExp): Target {
  return {
    id: `flclash/${platform}`, app: 'flclash', platform, label,
    async resolve() {
      const tag = await flclashLatestTag();
      const ver = tag.replace(/^v/, '');
      const filename = `FlClash-${ver}-${suffix}`;
      const url = `https://github.com/chen08209/FlClash/releases/download/${tag}/${filename}`;
      // 校验值来自 API 的 digest 字段；API 配额用尽时跳过，不影响镜像
      let sha256: string | null = null;
      try {
        const rel = await flclashRelease();
        const a = (rel.assets as any[]).find((x) => re.test(x.name));
        if (a && typeof a.digest === 'string' && a.digest.startsWith('sha256:')) sha256 = a.digest.slice(7);
      } catch {}
      return { url, filename, version: tag, sha256 };
    },
  };
}

// ---------- Claude: official "latest" redirect endpoints ----------
async function followRedirects(url: string): Promise<{ finalUrl: string; headers: Headers }> {
  let u = url;
  for (let i = 0; i < 6; i++) {
    // 有的端点不接受 HEAD（claude.ai 返回 405），所以用 GET 并在拿到头之后立刻取消正文
    const r = await fetch(u, { method: 'GET', redirect: 'manual', headers: H });
    try { await r.body?.cancel(); } catch {}
    if (r.status >= 300 && r.status < 400 && r.headers.get('location')) {
      u = new URL(r.headers.get('location')!, u).toString();
      continue;
    }
    if (!r.ok) throw new Error(`${r.status} at ${u}`);
    return { finalUrl: u, headers: r.headers };
  }
  throw new Error('too many redirects');
}
function claudeRedirect(platform: string, label: string, url: string, fallbackName: string): Target {
  return {
    id: `claude/${platform}`, app: 'claude', platform, label,
    async resolve() {
      const { finalUrl, headers } = await followRedirects(url);
      const cd = headers.get('content-disposition') || '';
      const m = /filename\*?=(?:UTF-8'')?"?([^";]+)/i.exec(cd);
      const fromUrl = decodeURIComponent(new URL(finalUrl).pathname.split('/').pop() || '');
      const filename = (m && m[1]) || fromUrl || fallbackName;
      const ver = /(\d+\.\d+\.\d+)/.exec(filename + ' ' + finalUrl);
      const version = ver ? ver[1] : (headers.get('etag') || headers.get('last-modified') || 'unknown').replace(/[^\w.-]/g, '');
      return { url: finalUrl, filename, version, sha256: null };
    },
  };
}
// Claude Linux: parse the apt Packages index
function claudeDeb(arch: 'amd64' | 'arm64'): Target {
  return {
    id: `claude/linux-${arch}`, app: 'claude', platform: `linux-${arch}`, label: `Linux .deb (${arch})`,
    async resolve() {
      const base = 'https://downloads.claude.ai/claude-desktop/apt/stable/';
      const r = await fetch(`${base}dists/stable/main/binary-${arch}/Packages`, { headers: H });
      if (!r.ok) throw new Error(`apt index ${r.status}`);
      const stanzas = (await r.text()).split(/\n\n+/).filter((s) => /^Package: claude-desktop/m.test(s));
      const parsed = stanzas.map((s) => {
        const g = (k: string) => (new RegExp(`^${k}: (.+)$`, 'm').exec(s) || [])[1];
        return { version: g('Version'), file: g('Filename'), sha256: g('SHA256') };
      }).filter((x) => x.version && x.file);
      parsed.sort((a, b) => a.version.localeCompare(b.version, undefined, { numeric: true }));
      const best = parsed[parsed.length - 1];
      if (!best) throw new Error('no deb found');
      return { url: base + best.file, filename: best.file.split('/').pop()!, version: best.version, sha256: best.sha256 || null };
    },
  };
}

// ---------- Codex (now shipped as the new ChatGPT desktop app) ----------
function codexMac(): Target {
  return {
    id: 'codex/macos', app: 'codex', platform: 'macos', label: 'macOS',
    async resolve() {
      const url = 'https://persistent.oaistatic.com/codex-app-prod/ChatGPT.dmg';
      const { headers } = await followRedirects(url);
      const version = (headers.get('etag') || headers.get('last-modified') || 'unknown').replace(/[^\w.-]/g, '');
      return { url, filename: 'ChatGPT.dmg', version, sha256: null };
    },
  };
}

export const TARGETS: Target[] = [
  flclash('macos-arm64', 'macOS · Apple 芯片', 'macos-arm64.dmg', /macos-arm64\.dmg$/),
  flclash('macos-amd64', 'macOS · Intel', 'macos-amd64.dmg', /macos-amd64\.dmg$/),
  flclash('windows', 'Windows', 'windows-amd64-setup.exe', /windows-amd64-setup\.exe$/),
  flclash('linux-deb', 'Linux · .deb', 'linux-amd64.deb', /linux-amd64\.deb$/),
  flclash('linux-appimage', 'Linux · AppImage', 'linux-amd64.AppImage', /linux-amd64\.AppImage$/),
  flclash('android', 'Android', 'android-arm64-v8a.apk', /android-arm64-v8a\.apk$/),
  claudeRedirect('macos', 'macOS', 'https://claude.ai/api/desktop/darwin/universal/dmg/latest/redirect', 'Claude.dmg'),
  claudeRedirect('windows-x64', 'Windows · x64', 'https://claude.ai/api/desktop/win32/x64/setup/latest/redirect', 'Claude-Setup-x64.exe'),
  claudeRedirect('windows-arm64', 'Windows · ARM64', 'https://claude.ai/api/desktop/win32/arm64/setup/latest/redirect', 'Claude-Setup-arm64.exe'),
  claudeDeb('amd64'),
  claudeDeb('arm64'),
  codexMac(),
];
export const byId = (id: string) => TARGETS.find((t) => t.id === id);
