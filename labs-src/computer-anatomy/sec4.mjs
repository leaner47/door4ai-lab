import { fig4, f4Live } from "./fig4.mjs";
const F = fig4();
export function html() {
  return `
<p>假设你写了个网站，在自己电脑上跑得好好的，放到服务器上却报错：Python 版本不对、少装了某个库、配置文件路径不一样……这就是程序员最常说的那句「<b>在我电脑上明明能跑</b>」。</p>
<p><b>Docker</b> 的办法跟海运一模一样。几十年前，码头上的货物大大小小、形状各异，每条船都要人工一件件码放；后来有了<em>标准集装箱</em>：不管里面装的是钢琴还是香蕉，外面都是同样尺寸的铁箱，吊车、货船、卡车都能直接搬。Docker 把<b>软件 + 它需要的全部东西</b>（运行环境、依赖库、配置）打包成一个标准「箱子」，叫做<b>容器</b>（container）。</p>
<div class="grid">
  <div class="tile"><div class="w">镜像 image</div><div class="t">箱子的「模具」</div><div class="d">一个只读的打包文件，存在镜像仓库（如 Docker Hub）。码头上那堆箱子就是它。</div></div>
  <div class="tile"><div class="w">容器 container</div><div class="t">正在运行的箱子</div><div class="d">用镜像启动出来的实例。同一个镜像可以启动很多个容器。</div></div>
  <div class="tile"><div class="w">内核 kernel</div><div class="t">共用的甲板</div><div class="d">操作系统最核心的部分。所有容器共用宿主机这一个内核，所以又轻又快。</div></div>
</div>
<div class="controls">
  <button class="btn" id="f4-run">＋ 装一个箱子（docker run）</button>
  <button class="btn" id="f4-stop">－ 卸一个箱子（docker stop）</button>
</div>
${F.body}
<div class="apps" id="f4-list" aria-live="polite"></div>
<h3>为什么不直接用虚拟机？</h3>
<p>虚拟机（VM）也能隔离软件，但它是在你的电脑里再<em>模拟出一整台电脑</em>，每台都要装一套完整的操作系统——相当于每运一个箱子都要再造一条小船。容器只带应用自己需要的东西，内核共用，所以：</p>
<div class="race">
  <span>容器</span><span class="bar"><i id="f4-ct"></i></span><span class="v" id="f4-ct-v">—</span>
  <span>虚拟机</span><span class="bar"><i id="f4-vm"></i></span><span class="v" id="f4-vm-v">—</span>
</div>
<p class="small">上面是「额外开销」的内存粗估：每个容器约几十 MB（只多出应用本身），每台虚拟机约 2 GB（一整套操作系统）。启动时间也差很多：容器通常 1 秒内，虚拟机常要几十秒。代价是隔离没有虚拟机彻底——容器之间共用一个内核。</p>
<div class="note"><b>注意看：</b>吊车从不关心箱子里装的是什么，它只认箱子的外形。Docker 也一样：只要装了 Docker，任何电脑、任何云服务器都能用同一条命令把同一个箱子跑起来，环境一模一样。</div>`;
}
export const LIVE = f4Live(F.P, F.S);
