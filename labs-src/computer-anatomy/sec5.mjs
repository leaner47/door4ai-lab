import { fig5, F5_LIVE } from "./fig5.mjs";
const rows = [
  ["给谁用", "很多人、很多程序同时通过网络访问", "通常就你一个人坐在前面用"],
  ["开机时间", "7×24 小时不关机，一年停机以分钟计", "用完就关，或者睡眠"],
  ["长什么样", "扁平的盒子插在机柜里（1U ≈ 4.4 cm 高），没有屏幕、键盘", "机箱 / 笔记本，配显示器、键盘、鼠标"],
  ["怎么操作", "远程登录（SSH 命令行、网页后台）；带独立管理芯片，死机了也能远程重启", "直接看屏幕、点鼠标"],
  ["可靠性", "双电源、ECC 纠错内存、硬盘阵列：坏一个零件不影响运行，可在开机状态下换", "坏了就停，送修"],
  ["规模", "常见 2 颗 CPU、几十到上百个核心，内存几百 GB 到数 TB，可插 8 张 GPU", "1 颗 CPU、8～24 核，内存 16～128 GB，一张显卡"],
  ["系统", "多为 Linux，没有桌面", "Windows / macOS，图形界面"],
  ["住在哪", "机房：恒温、防尘、双路供电、风扇很吵", "家里、办公室，要求安静"],
];
export function html() {
  return `
<p>很多人以为服务器是某种神秘的超级机器。其实<b>服务器也是电脑</b>：同样有 CPU、内存、硬盘，很多甚至用的是同一类芯片。区别在于它的<em>工作方式</em>——服务器的任务是「<b>一直开着，替很多人干活</b>」：你刷的网页、用的 App、和你聊天的 AI，背后都是机房里成排的服务器在响应。</p>
<div class="controls"><span class="seg" role="group" aria-label="高亮">
  <button data-f5="server" aria-pressed="true">服务器</button><button data-f5="pc" aria-pressed="false">个人电脑</button></span></div>
${fig5()}
<div class="tablewrap"><table class="cmp">
<thead><tr><th></th><th data-col="server">服务器</th><th data-col="pc">个人电脑</th></tr></thead>
<tbody>${rows.map(([a, b, c]) => `<tr><th>${a}</th><td data-col="server">${b}</td><td data-col="pc">${c}</td></tr>`).join("")}</tbody></table></div>
<div class="note"><b>串起来看：</b>一台 AI 服务器 = 机柜里的一个大盒子，里面是 2 颗 CPU（主厨）、8 张 GPU（每张带自己的显存，即帮厨和他们的操作台）、几 TB 内存；上面跑着 Linux，各种服务用 Docker 容器装好，一个箱子一个应用。你在网页上和 AI 聊天，请求就是顺着网线到了这样一台机器上。</div>
<p class="small">「云服务器」也是这样的物理机器，只不过一台被切成很多份（虚拟机或容器）租给不同的人，你按小时付费、远程登录使用。</p>`;
}
export const LIVE = F5_LIVE;
