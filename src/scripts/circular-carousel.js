// Circular carousel in the spirit of React Bits <https://reactbits.dev/components/circular-carousel>:
// tiles on a 3D cylinder, drag to spin with momentum, snap to the nearest tile, idle drift,
// click a side tile to bring it to the front (click on the front tile falls through to its link).
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const norm = (a) => ((a % 360) + 540) % 360 - 180; // → (-180, 180]

export function initCarousel(root) {
  if (root.dataset.ccInit) return; root.dataset.ccInit = '1';
  const ring = root.querySelector('.ccar__ring');
  const tiles = [...ring.children];
  const n = tiles.length;
  const cardW = +(root.dataset.cardW || 150);
  const gap = +(root.dataset.gap || 36);
  const tiltX = +(root.dataset.tilt || -6);
  const drift = +(root.dataset.drift || 5); // deg/s when idle
  const depthFade = +(root.dataset.fade || 0.55);
  const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
  // Few tiles would make a tiny ring, so lay them out as if the ring had at least `minSlots` tiles:
  // the tiles then form a wide arc in front of the viewer and the ring rotation is clamped to that arc.
  const minSlots = +(root.dataset.minSlots || 8);
  const m = Math.max(n, minSlots);
  const step = 360 / m;
  const arc = n < m; // arc mode: angle clamped to [-(n-1)*step, 0]
  const minA = arc ? -(n - 1) * step : -Infinity, maxA = arc ? 0 : Infinity;
  const R = n > 1 ? (cardW + gap) / (2 * Math.sin(Math.PI / m)) : 0;
  root.style.setProperty('--cc-r', R + 'px');
  tiles.forEach((t, i) => { t.style.setProperty('--cc-a', i * step + 'deg'); t.dataset.index = i; });

  const st = { angle: 0, v: 0, target: null, press: null, hoverUntil: 0, raf: 0, last: performance.now(), visible: true };
  const clampA = (a) => clamp(a, minA, maxA);
  const front = () => arc ? clamp(Math.round(-st.angle / step), 0, n - 1) : ((Math.round(-st.angle / step) % n) + n) % n;

  const render = () => {
    ring.style.transform = `translateZ(${-R}px) rotateX(${tiltX}deg) rotateY(${st.angle}deg)`;
    const f = front();
    tiles.forEach((t, i) => {
      const a = norm(i * step + st.angle); // 0 = facing viewer
      const c = Math.cos((a * Math.PI) / 180); // 1 front … -1 back
      const k = (c + 1) / 2;
      t.style.opacity = String(n > 2 ? 0.15 + 0.85 * Math.pow(k, 1 / (1 - depthFade + 0.0001) * 0.6) : 1);
      t.style.filter = n > 2 ? `brightness(${0.55 + 0.45 * k})` : '';
      t.style.zIndex = String(Math.round(100 + c * 50));
      t.classList.toggle('is-front', i === f);
      t.style.pointerEvents = c < -0.2 ? 'none' : '';
    });
    root.dataset.front = String(f); root.dataset.angle = st.angle.toFixed(1);
  };

  const tick = (now) => {
    st.raf = 0;
    const dt = Math.min(0.05, (now - st.last) / 1000); st.last = now;
    if (st.press) { /* dragging: angle set directly */ }
    else if (Math.abs(st.v) > 2) { st.angle = clampA(st.angle + st.v * dt); if (arc && (st.angle === minA || st.angle === maxA)) st.v = 0; st.v *= Math.pow(0.08, dt); if (Math.abs(st.v) <= 2) st.target = clampA(Math.round(st.angle / step) * step); }
    else if (st.target != null) {
      const d = st.target - st.angle;
      if (Math.abs(d) < 0.05) { st.angle = st.target; st.target = null; }
      else st.angle += d * Math.min(1, 10 * dt);
    } else if (!reduce && drift && !arc && now > st.hoverUntil && st.visible) {
      st.angle += drift * dt; // idle drift (full rings only); snap again when the user comes back
    }
    render();
    const idle = st.target == null && Math.abs(st.v) <= 2 && !st.press && (reduce || !drift || arc || now < st.hoverUntil || !st.visible);
    if (!idle) st.raf = requestAnimationFrame(tick);
  };
  const wake = () => { if (!st.raf) { st.last = performance.now(); st.raf = requestAnimationFrame(tick); } };
  const pause = (ms) => { st.hoverUntil = performance.now() + ms; wake(); };
  const snap = () => { st.target = clampA(Math.round(st.angle / step) * step); wake(); };
  const goTo = (i) => { if (arc) { st.target = -i * step; } else { const cur = -st.angle / step; let k = Math.round(cur); const d = norm((i - k) * step) / step; st.target = -(k + d) * step; } st.v = 0; wake(); };

  // drag
  root.addEventListener('pointerdown', (e) => {
    if (e.button !== 0) return;
    st.press = { id: e.pointerId, x: e.clientX, angle: st.angle, moved: false, samples: [{ t: performance.now(), a: st.angle }] };
    st.v = 0; st.target = null; pause(4000);
  });
  root.addEventListener('pointermove', (e) => {
    const p = st.press; if (!p || e.pointerId !== p.id) return;
    const dx = e.clientX - p.x;
    if (!p.moved && Math.abs(dx) > 6) { p.moved = true; root.setPointerCapture?.(p.id); root.classList.add('is-dragging'); }
    if (!p.moved) return;
    st.angle = clampA(p.angle + (dx / Math.max(R, cardW)) * (180 / Math.PI) * 0.9);
    p.samples.push({ t: performance.now(), a: st.angle }); if (p.samples.length > 6) p.samples.shift();
    render();
  });
  const release = (e) => {
    const p = st.press; if (!p || (e && e.pointerId !== p.id)) return;
    st.press = null; root.classList.remove('is-dragging');
    if (p.moved) {
      const s0 = p.samples[0], s1 = p.samples[p.samples.length - 1];
      const dt = Math.max(0.016, (s1.t - s0.t) / 1000);
      st.v = clamp((s1.a - s0.a) / dt, -900, 900);
      if (Math.abs(st.v) <= 2) snap();
      root.dataset.suppress = '1'; setTimeout(() => delete root.dataset.suppress, 0);
    }
    pause(4000); wake();
  };
  root.addEventListener('pointerup', release); root.addEventListener('pointercancel', release);
  // click: side tile → bring to front, front tile → let the link work
  root.addEventListener('click', (e) => {
    if (root.dataset.suppress) { e.preventDefault(); e.stopPropagation(); return; }
    const tile = e.target.closest('.ccar__tile'); if (!tile) return;
    const i = +tile.dataset.index;
    if (i !== front()) { e.preventDefault(); e.stopPropagation(); goTo(i); pause(4000); }
  }, true);
  // hover pauses drift and snaps to the nearest tile
  root.addEventListener('pointerenter', () => { pause(1e9); snap(); });
  root.addEventListener('pointerleave', () => { if (!st.press) { st.hoverUntil = performance.now() + 2500; snap(); } });
  // wheel (horizontal) spins
  root.addEventListener('wheel', (e) => { if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) { e.preventDefault(); st.angle = clampA(st.angle - e.deltaX * 0.3); st.target = null; pause(2000); clearTimeout(st.wt); st.wt = setTimeout(snap, 150); render(); } }, { passive: false });
  // keyboard
  root.tabIndex = 0;
  root.addEventListener('keydown', (e) => { if (e.key === 'ArrowLeft') { goTo(arc ? Math.max(0, front() - 1) : (front() - 1 + n) % n); pause(4000); } if (e.key === 'ArrowRight') { goTo(arc ? Math.min(n - 1, front() + 1) : (front() + 1) % n); pause(4000); } });
  new IntersectionObserver((es) => { st.visible = es.some((x) => x.isIntersecting); if (st.visible) wake(); }).observe(root);

  if (arc) { st.angle = -Math.floor((n - 1) / 2) * step; }
  render(); wake();
}
export function initCarousels() { document.querySelectorAll('.ccar').forEach(initCarousel); }
