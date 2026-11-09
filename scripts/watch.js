// Watch the video on the current page (TikTok, YouTube, Facebook...) and measure its style.
// Run with the browser's JavaScript tool on the video's page, as `await <this file's text>`.
// Streams like a normal viewer: no download, no login, no bot-check workarounds.
// Returns style.json (same keys and 0-255 scales as analyze.py) and draws a contact sheet over the page;
// take a screenshot right after to see it. Run again with SHEET_ONLY = true to redraw just the sheet.
(async () => {
  const SHEET_ONLY = false;
  const v = [...document.querySelectorAll('video')].sort((a, b) => b.clientWidth * b.clientHeight - a.clientWidth * a.clientHeight)[0];
  if (!v || !v.duration || !isFinite(v.duration)) return JSON.stringify({ error: 'no playable video on this page yet: press play once, then run again' });
  v.pause(); v.muted = true;
  const seek = t => new Promise(r => { const f = () => { v.removeEventListener('seeked', f); r(); }; v.addEventListener('seeked', f); v.currentTime = Math.min(t, v.duration - 0.05); });
  const canvas = (w, h) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return [c, c.getContext('2d', { willReadFrequently: true })]; };
  const VW = v.videoWidth, VH = v.videoHeight;
  try { canvas(1, 1)[1].drawImage(v, 0, 0, 1, 1); canvas(1, 1)[1].getImageData(0, 0, 1, 1); } catch (e) { return JSON.stringify({ error: 'site blocks reading frames: ask the user for the video file instead' }); }

  // content box: skip black letterbox bars (common in reposts and screen recordings)
  const [b, bx] = canvas(36, 64), rows = new Float32Array(64), cols = new Float32Array(36);
  for (const f of [0.1, 0.3, 0.5, 0.7, 0.9]) {
    await seek(v.duration * f); bx.drawImage(v, 0, 0, 36, 64); const d = bx.getImageData(0, 0, 36, 64).data;
    for (let y = 0; y < 64; y++) for (let x = 0; x < 36; x++) { const i = (y * 36 + x) * 4, l = (d[i] + d[i + 1] + d[i + 2]) / 3 / 5; rows[y] += l / 36; cols[x] += l / 64; }
  }
  let t0 = 0, t1 = 63, l0 = 0, l1 = 35;
  while (t0 < 63 && rows[t0] < 12) t0++; while (t1 > t0 && rows[t1] < 12) t1--;
  while (l0 < 35 && cols[l0] < 12) l0++; while (l1 > l0 && cols[l1] < 12) l1--;
  const box = { x: Math.round(l0 / 36 * VW), y: Math.round(t0 / 64 * VH), w: Math.round((l1 - l0 + 1) / 36 * VW), h: Math.round((t1 - t0 + 1) / 64 * VH) };

  // contact sheet: 16 frames of the content box, left to right, top to bottom
  const times = [...Array(16)].map((_, i) => +(v.duration * (i + 0.5) / 16).toFixed(2));
  const tw = 200, th = Math.round(200 * box.h / box.w), [sc, sx] = canvas(tw * 4, th * 4); sx.font = 'bold 13px sans-serif';
  for (let i = 0; i < 16; i++) {
    await seek(times[i]); const X = (i % 4) * tw, Y = Math.floor(i / 4) * th;
    sx.drawImage(v, box.x, box.y, box.w, box.h, X, Y, tw, th); sx.fillStyle = '#000'; sx.fillRect(X, Y, 44, 16); sx.fillStyle = '#ff0'; sx.fillText(times[i] + 's', X + 2, Y + 12);
  }
  document.getElementById('__3be_sheet')?.remove();
  sc.id = '__3be_sheet';
  const scale = Math.min(1, (innerWidth * 0.95) / sc.width, (innerHeight * 0.95) / sc.height);
  sc.style.cssText = `position:fixed;left:0;top:0;z-index:2147483647;pointer-events:none;transform-origin:0 0;transform:scale(${scale})`;
  document.documentElement.appendChild(sc);
  if (SHEET_ONLY) return JSON.stringify({ contact_sheet: { times_s: times } });

  // scan: brightness-histogram change per step + colour, in ffmpeg signalstats units (limited-range 8-bit YUV).
  // Histogram, not pixel difference: handheld gym footage moves every pixel but keeps its histogram; a cut changes it.
  const step = v.duration <= 90 ? 0.1 : 0.2, W = 64, H = Math.max(8, Math.round(64 * box.h / box.w)), [c, x] = canvas(W, H);
  let prev = null, Y = 0, S = 0, U = 0, V = 0, n = 0; const diffs = [];
  for (let t = 0; t < v.duration; t += step) {
    await seek(t); x.drawImage(v, box.x, box.y, box.w, box.h, 0, 0, W, H); const d = x.getImageData(0, 0, W, H).data, h = new Float32Array(16);
    for (let i = 0; i < d.length; i += 4) {
      const r = d[i], gg = d[i + 1], bb = d[i + 2], y = 0.299 * r + 0.587 * gg + 0.114 * bb;
      const u = (-0.169 * r - 0.331 * gg + 0.5 * bb) * 224 / 255, w = (0.5 * r - 0.419 * gg - 0.081 * bb) * 224 / 255;
      h[Math.min(15, y >> 4)]++; Y += 16 + y * 219 / 255; S += Math.hypot(u, w); U += u; V += w; n++;
    }
    let diff = 0; if (prev) { for (let k = 0; k < 16; k++) diff += Math.abs(h[k] - prev[k]); diff /= 2 * W * H; }
    prev = h; diffs.push([+t.toFixed(2), diff]);
  }
  // a cut: histogram change above 0.15 that is a local peak; changes within 0.4 s are one cut (keep the biggest)
  const peaks = diffs.filter((z, i) => i > 0 && z[1] > 0.15 && z[1] >= diffs[i - 1][1] && z[1] >= (diffs[i + 1] || [0, 0])[1]);
  const kept = [];
  for (const p of peaks) { const last = kept[kept.length - 1]; if (last && p[0] - last[0] <= 0.4) { if (p[1] > last[1]) kept[kept.length - 1] = p; } else kept.push(p); }
  const cuts = kept.map(p => p[0]);

  const dur = +v.duration.toFixed(3), bounds = [0, ...cuts, dur], shots = bounds.slice(1).map((e, i) => +(e - bounds[i]).toFixed(3));
  const mean = a => a.reduce((s, z) => s + z, 0) / a.length, med = a => { const s = [...a].sort((p, q) => p - q), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
  const third = dur / 3, byThird = [0, 1, 2].map(k => { const p = shots.filter((s, i) => bounds[i] < (k + 1) * third && bounds[i] + s > k * third); return p.length ? +mean(p).toFixed(3) : null; });
  const bucket = r => r < 0.66 ? '9:16' : r < 0.9 ? '3:4' : r < 1.12 ? '1:1' : r < 1.5 ? '4:3' : '16:9';
  const aspect = bucket(box.w / box.h), frameAspect = bucket(VW / VH);
  const warmth = +((V - U) / n).toFixed(1);
  return JSON.stringify({
    schema: 1, source: location.href.split('?')[0], measured_by: 'browser',
    title: document.title,
    format: { duration_s: dur, width: VW, height: VH, aspect: frameAspect, content_box: box, content_aspect: aspect, letterboxed: box.w < VW * 0.95 || box.h < VH * 0.95 },
    pacing: {
      shot_count: shots.length, cuts_per_min: +(cuts.length / dur * 60).toFixed(2), avg_shot_s: +mean(shots).toFixed(3), median_shot_s: +med(shots).toFixed(3),
      min_shot_s: Math.min(...shots), max_shot_s: Math.max(...shots), first_cut_s: cuts[0] ?? null, avg_shot_by_third_s: byThird,
      transitions: { hard: cuts.length, animated: 0 }, cuts_s: cuts, shots_s: shots,
    },
    color: { brightness_0_255: +(Y / n).toFixed(1), saturation_0_255: +(S / n).toFixed(1), warmth, tint: warmth > 4 ? 'warm' : warmth < -4 ? 'cool' : 'neutral' },
    audio: null, music: null, speech: null,
    contact_sheet: { file: null, shown_on_page: true, grid: '4x4', times_s: times },
    visual_notes: null,
    not_measured: ['loudness, music beats and speech (browser watch reads frames only)', 'slow fades/slides (only sudden cuts)'],
  });
})()
