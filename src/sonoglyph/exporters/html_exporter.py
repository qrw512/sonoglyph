"""HTML report exporter: minimalism, dark theme, modal with rich analytics."""

from __future__ import annotations

import base64
import html
import io
import json
from datetime import datetime
from pathlib import Path

from sonoglyph.schemas import AnalysisResult

# ---------- Design tokens ----------

_CSS = """
:root {
  --bg: #09090b;
  --panel: #131316;
  --panel-hover: #1a1a1e;
  --border: #26262b;
  --border-hover: #35353b;
  --text: #f4f4f5;
  --text-muted: #a1a1aa;
  --text-dim: #71717a;
  --accent: #a78bfa;
  --accent-soft: rgba(167, 139, 250, 0.12);
  --green: #4ade80;
  --yellow: #fbbf24;
  --red: #f87171;
  --blue: #60a5fa;
  --magenta: #c084fc;

  --r-sm: 8px;
  --r-md: 12px;
  --r-lg: 16px;
  --r-xl: 24px;

  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 24px 60px rgba(0, 0, 0, 0.6);
}

* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }

body {
  font-family: ui-sans-serif, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
  background: var(--bg); color: var(--text);
  font-size: 14px; line-height: 1.55;
  -webkit-font-smoothing: antialiased;
  min-height: 100vh;
}

.container { max-width: 1280px; margin: 0 auto; padding: 48px 32px 64px; }

/* ---------- Header ---------- */

.page-header { margin-bottom: 32px; }
.page-title {
  margin: 0 0 6px; font-size: 28px; font-weight: 600;
  letter-spacing: -0.02em;
}
.page-title .dot {
  display: inline-block; width: 8px; height: 8px;
  background: var(--accent); border-radius: 50%;
  margin-right: 12px; vertical-align: middle;
  box-shadow: 0 0 20px var(--accent);
}
.page-sub { color: var(--text-dim); font-size: 13px; }

/* ---------- Summary ---------- */

.summary {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px; margin-bottom: 28px;
}
.summary-item {
  background: var(--panel); border: 1px solid var(--border);
  border-radius: var(--r-lg); padding: 18px 20px;
  transition: border-color 0.15s, background 0.15s;
}
.summary-item:hover { border-color: var(--border-hover); }
.summary-label {
  color: var(--text-dim); font-size: 11px; font-weight: 500;
  text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px;
}
.summary-value {
  font-size: 24px; font-weight: 600; letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
}

/* ---------- Toolbar ---------- */

.toolbar { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.input, .select {
  background: var(--panel); color: var(--text);
  border: 1px solid var(--border); border-radius: var(--r-md);
  padding: 10px 14px; font-size: 14px; font-family: inherit;
  outline: none; transition: border-color 0.15s, box-shadow 0.15s;
}
.input:focus, .select:focus {
  border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft);
}
.input { flex: 1; min-width: 200px; }
.select { min-width: 180px; cursor: pointer; }

/* ---------- Table ---------- */

.table-wrap {
  background: var(--panel); border: 1px solid var(--border);
  border-radius: var(--r-lg); overflow: hidden;
}
table { width: 100%; border-collapse: collapse; }
th, td {
  padding: 14px 18px; text-align: left;
  border-bottom: 1px solid var(--border);
}
tr:last-child td { border-bottom: none; }
th {
  cursor: pointer; user-select: none;
  background: rgba(255, 255, 255, 0.015);
  color: var(--text-dim); font-weight: 500;
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em;
  transition: color 0.15s;
}
th:hover { color: var(--text); }
th.sort-asc::after { content: " ↑"; color: var(--accent); }
th.sort-desc::after { content: " ↓"; color: var(--accent); }
tr:hover td { background: var(--panel-hover); }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
td.mono {
  font-family: ui-monospace, "SF Mono", "Consolas", monospace;
  font-size: 12.5px;
}

/* ---------- Track button ---------- */

.track-btn {
  background: transparent; border: none; padding: 0;
  font: inherit; color: var(--accent); cursor: pointer;
  text-align: left; border-radius: 4px;
  transition: color 0.15s; font-weight: 500;
}
.track-btn:hover {
  color: var(--text); text-decoration: underline; text-underline-offset: 3px;
}

/* ---------- Mood badge ---------- */

.mood-badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 3px 10px; border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border);
  font-size: 12px; font-weight: 500;
}
.mood-badge::before {
  content: ""; width: 6px; height: 6px;
  border-radius: 50%; background: currentColor;
}
.mood-happy { color: var(--green); }
.mood-calm { color: var(--blue); }
.mood-sad { color: var(--text-muted); }
.mood-angry { color: var(--red); }
.mood-melancholic { color: var(--magenta); }
.mood-neutral { color: var(--yellow); }

/* ---------- Bar ---------- */

.bar-row {
  display: inline-flex; align-items: center; gap: 10px;
  font-variant-numeric: tabular-nums; font-size: 13px;
}
.bar {
  width: 60px; height: 6px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 3px; overflow: hidden;
}
.bar-fill {
  display: block; height: 100%; border-radius: 3px;
  transition: width 0.3s ease;
}

/* ---------- Modal ---------- */

.modal-backdrop {
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center;
  padding: 24px; z-index: 100;
  animation: fadeIn 0.15s ease;
}
.modal-backdrop[hidden] { display: none; }

@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

.modal {
  background: var(--panel); border: 1px solid var(--border);
  border-radius: var(--r-xl); box-shadow: var(--shadow-lg);
  width: 100%; max-width: 1020px; max-height: 92vh;
  display: flex; flex-direction: column; overflow: hidden;
  animation: modalIn 0.2s ease;
}

@keyframes modalIn {
  from { opacity: 0; transform: scale(0.97) translateY(8px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.modal-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 16px; padding: 24px 28px 16px;
  border-bottom: 1px solid var(--border);
}
.modal-title {
  margin: 0 0 4px; font-size: 20px; font-weight: 600;
  letter-spacing: -0.01em; word-break: break-word;
}
.modal-sub {
  color: var(--text-dim); font-size: 13px;
  font-variant-numeric: tabular-nums;
}
.modal-actions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }

.icon-btn {
  background: transparent; border: 1px solid var(--border);
  color: var(--text-muted); width: 36px; height: 36px;
  border-radius: var(--r-md); cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center;
  transition: all 0.15s; font-size: 16px; font-family: inherit;
}
.icon-btn:hover {
  background: var(--panel-hover); border-color: var(--border-hover);
  color: var(--text);
}

.modal-body { padding: 24px 28px 28px; overflow-y: auto; }

/* ---------- Visualization blocks ---------- */

.viz-block {
  margin-bottom: 24px;
  border-radius: var(--r-md);
  overflow: hidden;
  background: #0a0a0d;
  border: 1px solid var(--border);
}
.viz-block img { display: block; width: 100%; height: auto; }

.viz-title {
  font-size: 11px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--text-dim);
  padding: 14px 18px 8px;
}

.viz-empty {
  padding: 40px;
  text-align: center;
  color: var(--text-dim);
  font-size: 13px;
}

.viz-svg {
  display: block;
  width: 100%;
  padding: 12px 18px 18px;
}

/* ---------- Stats grid ---------- */

.stats-section { margin-bottom: 24px; }
.stats-section:last-child { margin-bottom: 0; }

.section-title {
  font-size: 11px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--text-dim); margin-bottom: 12px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 10px;
}

.stat {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  padding: 12px 14px;
}
.stat-label {
  color: var(--text-dim); font-size: 11px;
  margin-bottom: 4px; font-weight: 500;
}
.stat-value {
  font-size: 15px; font-weight: 500;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.01em;
}

.tag-list { display: flex; flex-wrap: wrap; gap: 6px; }
.tag {
  display: inline-block; padding: 3px 10px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 11.5px; font-weight: 500;
}

/* ---------- MFCC bars ---------- */

.mfcc-grid {
  display: grid;
  grid-template-columns: 40px 1fr 60px;
  gap: 6px 12px;
  align-items: center;
  font-variant-numeric: tabular-nums;
  font-size: 12.5px;
}
.mfcc-idx { color: var(--text-dim); font-size: 11px; }
.mfcc-bar-wrap {
  height: 8px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 4px;
  position: relative;
  overflow: hidden;
}
.mfcc-bar {
  position: absolute;
  top: 0; bottom: 0;
  border-radius: 4px;
}
.mfcc-val { text-align: right; font-family: ui-monospace, monospace; color: var(--text-muted); }

/* ---------- Mobile ---------- */

@media (max-width: 720px) {
  .container { padding: 24px 16px 48px; }
  .page-title { font-size: 22px; }
  th, td { padding: 10px 12px; font-size: 13px; }
  .modal-header, .modal-body { padding-left: 20px; padding-right: 20px; }
  .table-wrap { overflow-x: auto; }
  table { min-width: 640px; }
}
"""

_JS = r"""
const DATA = JSON.parse(document.getElementById('track-data').textContent);
const backdrop = document.getElementById('modal-backdrop');
const tbody = document.querySelector('#results tbody');

/* ---------- helpers ---------- */

function fmtDuration(sec) {
  const s = Math.round(sec);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

function barRow(value, color) {
  if (value === null || value === undefined) return '—';
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return `<span class="bar-row">
    <span class="bar"><span class="bar-fill" style="width:${pct.toFixed(1)}%;background:${color}"></span></span>
    <span>${value.toFixed(2)}</span>
  </span>`;
}

function stat(label, value) {
  return `<div class="stat"><div class="stat-label">${label}</div><div class="stat-value">${value}</div></div>`;
}

function mean(arr) { return arr.reduce((a, b) => a + b, 0) / arr.length; }

function median(arr) {
  const s = [...arr].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

function std(arr, m) {
  if (m === undefined) m = mean(arr);
  return Math.sqrt(arr.reduce((a, b) => a + (b - m) * (b - m), 0) / arr.length);
}

/* ---------- beat visualization ---------- */

function beatStats(beats) {
  if (!beats || beats.length < 2) return null;
  const intervals = [];
  for (let i = 1; i < beats.length; i++) intervals.push(beats[i] - beats[i - 1]);
  const m = mean(intervals);
  const s = std(intervals, m);
  return {
    count: intervals.length,
    mean: m,
    median: median(intervals),
    std: s,
    min: Math.min(...intervals),
    max: Math.max(...intervals),
    cv: m > 0 ? s / m : 0,
    bpmFromMean: m > 0 ? 60 / m : 0,
  };
}

function beatTimeline(beats, duration) {
  if (!beats || beats.length === 0) return '';
  const W = 1000, H = 50, padX = 0, padY = 4;
  const span = duration - 0;
  const scale = (W - 2 * padX) / span;
  const lines = beats.map(t => {
    const x = padX + t * scale;
    return `<line x1="${x.toFixed(2)}" y1="${padY}" x2="${x.toFixed(2)}" y2="${H - padY}" stroke="var(--accent)" stroke-width="1" opacity="0.65"/>`;
  }).join('');
  return `
    <svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" preserveAspectRatio="none" class="viz-svg" style="padding:0">
      <rect x="0" y="0" width="${W}" height="${H}" fill="#0a0a0d"/>
      ${lines}
    </svg>
  `;
}

function beatHistogram(beats) {
  if (!beats || beats.length < 3) return '';
  const intervals = [];
  for (let i = 1; i < beats.length; i++) intervals.push(beats[i] - beats[i - 1]);

  const min = Math.min(...intervals);
  const max = Math.max(...intervals);
  const nBins = 24;
  const binWidth = (max - min) / nBins || 1;
  const bins = new Array(nBins).fill(0);
  intervals.forEach(v => {
    const b = Math.min(nBins - 1, Math.floor((v - min) / binWidth));
    bins[b]++;
  });
  const maxCount = Math.max(...bins, 1);

  const W = 1000, H = 80, padY = 8;
  const barW = (W - 20) / nBins;
  const bars = bins.map((count, i) => {
    const h = (count / maxCount) * (H - 2 * padY);
    const x = 10 + i * barW;
    const y = H - padY - h;
    return `<rect x="${x.toFixed(2)}" y="${y.toFixed(2)}" width="${(barW - 1).toFixed(2)}" height="${h.toFixed(2)}" fill="var(--accent)" opacity="0.75" rx="2"/>`;
  }).join('');

  return `
    <svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" preserveAspectRatio="none" class="viz-svg" style="padding:0">
      <rect x="0" y="0" width="${W}" height="${H}" fill="#0a0a0d"/>
      ${bars}
    </svg>
  `;
}

/* ---------- MFCC chart ---------- */

function mfccChart(mfcc) {
  if (!mfcc || mfcc.length === 0) return '';
  const maxAbs = Math.max(...mfcc.map(Math.abs), 1);
  const rows = mfcc.map((v, i) => {
    const pct = (Math.abs(v) / maxAbs) * 50;
    const isNeg = v < 0;
    const left = isNeg ? (50 - pct) : 50;
    const width = pct;
    const color = isNeg ? 'var(--red)' : 'var(--blue)';
    return `
      <div class="mfcc-idx">#${i}</div>
      <div class="mfcc-bar-wrap">
        <div class="mfcc-bar" style="left:${left.toFixed(2)}%;width:${width.toFixed(2)}%;background:${color}"></div>
      </div>
      <div class="mfcc-val">${v.toFixed(2)}</div>
    `;
  }).join('');

  return `
    <div class="stats-section">
      <div class="section-title">MFCC (mel-frequency cepstral coefficients)</div>
      <div class="mfcc-grid">${rows}</div>
    </div>
  `;
}

/* ---------- Sections ---------- */

function buildRhythmSection(r) {
  if (!r.tempo) return '';
  const beats = r.tempo.beat_positions || [];
  const bs = beatStats(beats);

  let html = `<div class="stats-section"><div class="section-title">Rhythm</div><div class="stats-grid">`;
  html += stat('BPM', r.tempo.bpm.toFixed(2));
  html += stat('Beats detected', r.tempo.beat_count);
  html += stat('Tempo confidence', r.tempo.confidence.toFixed(3));
  if (bs) {
    html += stat('Mean interval', (bs.mean * 1000).toFixed(1) + ' ms');
    html += stat('Median interval', (bs.median * 1000).toFixed(1) + ' ms');
    html += stat('Std deviation', (bs.std * 1000).toFixed(1) + ' ms');
    html += stat('Min interval', (bs.min * 1000).toFixed(1) + ' ms');
    html += stat('Max interval', (bs.max * 1000).toFixed(1) + ' ms');
    html += stat('CV (stability)', bs.cv.toFixed(4));
    html += stat('BPM from intervals', bs.bpmFromMean.toFixed(2));
  }
  html += `</div></div>`;

  if (bs) {
    html += `<div class="viz-block">
      <div class="viz-title">Beat interval distribution</div>
      ${beatHistogram(beats)}
    </div>`;
    html += `<div class="viz-block">
      <div class="viz-title">Beat positions over time</div>
      ${beatTimeline(beats, r.metadata.duration_sec)}
    </div>`;
  }

  return html;
}

function buildKeySection(r) {
  if (!r.key) return '';
  let html = `<div class="stats-section"><div class="section-title">Key</div><div class="stats-grid">`;
  html += stat('Key', r.key.name);
  html += stat('Tonic', r.key.tonic);
  html += stat('Mode', r.key.mode);
  html += stat('Confidence', r.key.confidence.toFixed(3));
  html += `</div></div>`;
  return html;
}

function buildMoodSection(r) {
  const m = r.mood;
  if (!m) return '';
  const tags = (m.tags || []).map(t => `<span class="tag">#${t}</span>`).join('');

  let html = `<div class="stats-section"><div class="section-title">Mood · ${m.label}</div><div class="stats-grid">`;
  html += stat('Valence', barRow(m.valence, 'var(--green)'));
  html += stat('Arousal', barRow(m.arousal, 'var(--red)'));
  if (m.arousal_rhythmic !== null && m.arousal_rhythmic !== undefined) {
    html += stat('Rhythmic arousal', barRow(m.arousal_rhythmic, 'var(--red)'));
  }
  if (m.arousal_harmonic !== null && m.arousal_harmonic !== undefined) {
    html += stat('Harmonic arousal', barRow(m.arousal_harmonic, 'var(--blue)'));
  }
  if (m.spectral_flatness !== null && m.spectral_flatness !== undefined) {
    html += stat('Spectral flatness', `<span style="font-family:ui-monospace,monospace">${m.spectral_flatness.toFixed(5)}</span>`);
  }
  html += stat('Backend', `<span style="color:var(--text-muted)">${m.backend}</span>`);
  html += `</div>`;
  if (tags) html += `<div class="tag-list" style="margin-top:12px">${tags}</div>`;
  html += `</div>`;
  return html;
}

function buildSpectralSection(r) {
  const s = r.spectral;
  if (!s) return '';
  let html = `<div class="stats-section"><div class="section-title">Spectral</div><div class="stats-grid">`;
  html += stat('Centroid mean', s.centroid_mean.toFixed(1) + ' Hz');
  html += stat('Centroid σ', s.centroid_std.toFixed(1) + ' Hz');
  html += stat('Rolloff mean', s.rolloff_mean.toFixed(1) + ' Hz');
  html += stat('Zero-crossing rate', s.zcr_mean.toFixed(5));
  html += `</div></div>`;

  if (s.mfcc_mean && s.mfcc_mean.length) {
    html += mfccChart(s.mfcc_mean);
  }
  return html;
}

function buildEnergySection(r) {
  const e = r.energy;
  if (!e) return '';
  let html = `<div class="stats-section"><div class="section-title">Energy</div><div class="stats-grid">`;
  html += stat('RMS mean', e.rms_mean.toFixed(5));
  html += stat('RMS σ', e.rms_std.toFixed(5));
  html += stat('Dynamic range', e.dynamic_range_db.toFixed(2) + ' dB');
  html += `</div></div>`;
  return html;
}

function buildStats(r) {
  return (
    buildRhythmSection(r) +
    buildKeySection(r) +
    buildMoodSection(r) +
    buildSpectralSection(r) +
    buildEnergySection(r)
  );
}

/* ---------- Modal ---------- */

function openModal(idx) {
  const t = DATA[idx];
  if (!t) return;
  const r = t.result;

  document.getElementById('modal-title').textContent = t.filename;
  const subParts = [
    fmtDuration(r.metadata.duration_sec),
    `${r.metadata.sample_rate} Hz`,
    `${r.metadata.channels}ch`,
    r.metadata.format.toUpperCase(),
  ];
  document.getElementById('modal-sub').textContent = subParts.join(' · ');

  // Waveform + spectrogram composite image
  const imgWrap = document.getElementById('modal-plot-wrap');
  const emptyWrap = document.getElementById('modal-plot-empty');
  const img = document.getElementById('modal-plot');
  if (t.plot) {
    img.src = 'data:image/png;base64,' + t.plot;
    imgWrap.style.display = '';
    emptyWrap.style.display = 'none';
  } else {
    imgWrap.style.display = 'none';
    emptyWrap.style.display = '';
  }

  document.getElementById('modal-stats').innerHTML = buildStats(r);
  document.getElementById('modal-open-file').href = t.file_uri || '#';

  backdrop.hidden = false;
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  backdrop.hidden = true;
  document.body.style.overflow = '';
}

/* ---------- Events ---------- */

tbody.addEventListener('click', (e) => {
  const btn = e.target.closest('.track-btn');
  if (!btn) return;
  const tr = btn.closest('tr');
  if (!tr) return;
  openModal(parseInt(tr.dataset.trackId, 10));
});

backdrop.addEventListener('click', (e) => {
  if (e.target === backdrop) closeModal();
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !backdrop.hidden) closeModal();
});
document.getElementById('modal-close-btn').addEventListener('click', closeModal);

// Filters
const filterInput = document.getElementById('filter');
const moodSelect = document.getElementById('mood-filter');

function applyFilters() {
  const q = filterInput.value.toLowerCase().trim();
  const mood = moodSelect.value.toLowerCase();
  tbody.querySelectorAll('tr').forEach(tr => {
    const text = tr.textContent.toLowerCase();
    const trMood = (tr.dataset.mood || '').toLowerCase();
    const matchText = !q || text.includes(q);
    const matchMood = !mood || trMood === mood;
    tr.style.display = (matchText && matchMood) ? '' : 'none';
  });
}
filterInput.addEventListener('input', applyFilters);
moodSelect.addEventListener('change', applyFilters);

// Sorting
document.querySelectorAll('th[data-sort]').forEach(th => {
  th.addEventListener('click', () => {
    const col = parseInt(th.dataset.sort, 10);
    const type = th.dataset.type || 'str';
    const asc = !th.classList.contains('sort-asc');

    document.querySelectorAll('th[data-sort]').forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
    th.classList.add(asc ? 'sort-asc' : 'sort-desc');

    const rows = Array.from(tbody.querySelectorAll('tr'));
    rows.sort((a, b) => {
      const av = a.cells[col].dataset.value ?? a.cells[col].textContent.trim();
      const bv = b.cells[col].dataset.value ?? b.cells[col].textContent.trim();
      if (type === 'num') {
        const an = parseFloat(av) || 0;
        const bn = parseFloat(bv) || 0;
        return asc ? an - bn : bn - an;
      }
      return asc ? av.localeCompare(bv) : bv.localeCompare(av);
    });
    rows.forEach(r => tbody.appendChild(r));
  });
});
"""

_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sonoglyph · __TITLE__</title>
<style>__CSS__</style>
</head>
<body>
<div class="container">

  <header class="page-header">
    <h1 class="page-title"><span class="dot"></span>Sonoglyph report</h1>
    <div class="page-sub">Generated __GEN_TIME__ · __TOTAL__ tracks</div>
  </header>

  <div class="summary">
    <div class="summary-item"><div class="summary-label">Tracks</div><div class="summary-value">__TOTAL__</div></div>
    <div class="summary-item"><div class="summary-label">Average BPM</div><div class="summary-value">__AVG_BPM__</div></div>
    <div class="summary-item"><div class="summary-label">Moods</div><div class="summary-value">__NUM_MOODS__</div></div>
  </div>

  <div class="toolbar">
    <input id="filter" class="input" type="text" placeholder="Search by name, key, tag...">
    <select id="mood-filter" class="select">
      <option value="">All moods</option>
      __MOOD_OPTIONS__
    </select>
  </div>

  <div class="table-wrap">
    <table id="results">
      <thead>
        <tr>
          <th data-sort="0" data-type="str">Track</th>
          <th data-sort="1" data-type="num">BPM</th>
          <th data-sort="2" data-type="str">Key</th>
          <th data-sort="3" data-type="str">Mood</th>
          <th data-sort="4" data-type="num">V / A</th>
        </tr>
      </thead>
      <tbody>
__ROWS__
      </tbody>
    </table>
  </div>

</div>

<!-- Modal -->
<div class="modal-backdrop" id="modal-backdrop" hidden>
  <div class="modal" role="dialog" aria-modal="true">
    <header class="modal-header">
      <div>
        <h2 class="modal-title" id="modal-title">—</h2>
        <div class="modal-sub" id="modal-sub">—</div>
      </div>
      <div class="modal-actions">
        <a id="modal-open-file" class="icon-btn" href="#" title="Open audio file" target="_blank" rel="noopener">↗</a>
        <button id="modal-close-btn" class="icon-btn" aria-label="Close">✕</button>
      </div>
    </header>
    <div class="modal-body">
      <div class="viz-block" id="modal-plot-wrap">
        <div class="viz-title">Waveform with beats · Mel spectrogram</div>
        <img id="modal-plot" alt="Waveform and spectrogram">
      </div>
      <div class="viz-block viz-empty" id="modal-plot-empty" style="display:none">
        Plot unavailable — install <code>matplotlib</code> and regenerate the report.
      </div>
      <div id="modal-stats"></div>
    </div>
  </div>
</div>

<script id="track-data" type="application/json">__DATA_JSON__</script>
<script>__JS__</script>
</body>
</html>
"""


# ---------- Composite plot generation ----------

def _make_analysis_plot_b64(
    path: Path,
    beat_positions: list[float] | None,
    sr: int = 22050,
) -> str | None:
    """Generate waveform+beats and mel-spectrogram as one PNG.

    Returns base64-encoded PNG, or None if matplotlib is unavailable.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # noqa: F401
        import numpy as np
        import librosa
        import librosa.display
    except ImportError:
        return None

    try:
        from sonoglyph.cache import DEFAULT_CACHE_DIR, file_hash

        h = file_hash(path)
        # Include beat count in cache key so changes to beat detection invalidate the plot
        n_beats = len(beat_positions) if beat_positions else 0
        cache_png = (
            DEFAULT_CACHE_DIR / "plots" / h[:2] / f"{h}-b{n_beats}.png"
        )
        if cache_png.exists():
            return base64.b64encode(cache_png.read_bytes()).decode("ascii")

        y, sr_native = librosa.load(str(path), sr=sr, mono=True)
        duration = len(y) / sr_native

        fig, (ax_wave, ax_spec) = plt.subplots(
            2, 1,
            figsize=(12, 5.6),
            dpi=85,
            gridspec_kw={"height_ratios": [1, 2.2], "hspace": 0.15},
        )
        fig.patch.set_facecolor("#0a0a0d")

        # --- Waveform + beats ---
        ax_wave.set_facecolor("#0a0a0d")
        times = np.linspace(0, duration, len(y))
        ax_wave.plot(times, y, color="#a78bfa", linewidth=0.35)
        if beat_positions:
            for bt in beat_positions:
                if 0 <= bt <= duration:
                    ax_wave.axvline(bt, color="#f4f4f5", linewidth=0.35, alpha=0.45)

        ax_wave.set_xlim(0, duration)
        ax_wave.set_ylim(-1.05, 1.05)
        ax_wave.set_xticks([])
        ax_wave.set_yticks([])
        for s in ax_wave.spines.values():
            s.set_color("#26262b")
        ax_wave.set_title(
            "waveform · beat markers",
            color="#71717a", fontsize=9, loc="left", pad=4,
        )

        # --- Mel spectrogram ---
        ax_spec.set_facecolor("#0a0a0d")
        S = librosa.feature.melspectrogram(
            y=y, sr=sr_native, n_mels=128, fmax=8000
        )
        S_db = librosa.power_to_db(S, ref=np.max)
        librosa.display.specshow(
            S_db,
            sr=sr_native,
            x_axis="time",
            y_axis="mel",
            fmax=8000,
            ax=ax_spec,
            cmap="magma",
        )
        ax_spec.set_xlabel("time (s)", color="#71717a", fontsize=9)
        ax_spec.set_ylabel("mel", color="#71717a", fontsize=9)
        ax_spec.tick_params(colors="#71717a", labelsize=8)
        for s in ax_spec.spines.values():
            s.set_color("#26262b")

        buf = io.BytesIO()
        plt.savefig(
            buf, format="png",
            facecolor=fig.get_facecolor(),
            bbox_inches="tight", pad_inches=0.15,
        )
        plt.close(fig)
        buf.seek(0)
        png_bytes = buf.read()

        cache_png.parent.mkdir(parents=True, exist_ok=True)
        cache_png.write_bytes(png_bytes)

        return base64.b64encode(png_bytes).decode("ascii")
    except Exception:  # noqa: BLE001
        return None


# ---------- Helpers ----------

def _fmt_bar(value: float | None, color: str) -> str:
    if value is None:
        return '<span style="color:var(--text-dim)">—</span>'
    pct = max(0.0, min(1.0, value)) * 100
    return (
        f'<span class="bar-row">'
        f'<span class="bar"><span class="bar-fill" '
        f'style="width:{pct:.1f}%;background:{color}"></span></span>'
        f'<span>{value:.2f}</span>'
        f'</span>'
    )


def _mood_class(label: str) -> str:
    return f"mood-{label.lower()}" if label else ""


def _row(idx: int, r: AnalysisResult) -> str:
    """One compact table row."""
    name = html.escape(Path(r.metadata.path).name)
    path = html.escape(r.metadata.path)

    bpm = f"{r.tempo.bpm:.1f}" if r.tempo else "—"
    key = html.escape(r.key.name) if r.key else "—"

    if r.mood:
        mood_html = (
            f'<span class="mood-badge {_mood_class(r.mood.label)}">'
            f'{html.escape(r.mood.label)}</span>'
        )
    else:
        mood_html = '<span style="color:var(--text-dim)">—</span>'

    v = _fmt_bar(r.mood.valence if r.mood else None, "var(--green)")
    a = _fmt_bar(r.mood.arousal if r.mood else None, "var(--red)")
    va = f"{v}<br>{a}"

    return (
        f'<tr data-track-id="{idx}" '
        f'data-mood="{html.escape(r.mood.label) if r.mood else ""}">'
        f'<td><button class="track-btn" title="{path}">{name}</button></td>'
        f'<td class="num" data-value="{r.tempo.bpm if r.tempo else 0}">{bpm}</td>'
        f'<td class="mono">{key}</td>'
        f'<td>{mood_html}</td>'
        f'<td class="num" data-value="{r.mood.arousal if r.mood else 0}">{va}</td>'
        f'</tr>'
    )


# ---------- Public API ----------

def to_html(
    results: list[AnalysisResult],
    out: str | Path,
    include_spectrograms: bool = True,
) -> Path:
    """Generate a self-contained HTML report with a rich modal.

    Args:
        results: analysis results.
        out: path to write the HTML file.
        include_spectrograms: when True, embed composite waveform+spectrogram
            plots (requires matplotlib; silently skipped if unavailable).

    Returns:
        Absolute path to the written file.
    """
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)

    total = len(results)
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    tracks_with_tempo = [r for r in results if r.tempo]
    avg_bpm = (
        sum(r.tempo.bpm for r in tracks_with_tempo) / len(tracks_with_tempo)
        if tracks_with_tempo
        else 0.0
    )

    moods: dict[str, int] = {}
    for r in results:
        if r.mood:
            moods[r.mood.label] = moods.get(r.mood.label, 0) + 1

    mood_options = "".join(
        f'<option value="{html.escape(m)}">{html.escape(m)} ({c})</option>'
        for m, c in sorted(moods.items(), key=lambda kv: -kv[1])
    )

    # ---- Per-track payload for the modal ----
    track_data = []
    for i, r in enumerate(results):
        plot_b64: str | None = None
        if include_spectrograms:
            p = Path(r.metadata.path)
            if p.exists():
                beats = r.tempo.beat_positions if r.tempo else None
                plot_b64 = _make_analysis_plot_b64(p, beats)

        file_uri = ""
        try:
            p = Path(r.metadata.path)
            if p.exists():
                file_uri = p.as_uri()
        except (ValueError, OSError):
            pass

        track_data.append(
            {
                "idx": i,
                "filename": Path(r.metadata.path).name,
                "file_uri": file_uri,
                "plot": plot_b64,
                "result": r.model_dump(mode="json"),
            }
        )

    data_json = json.dumps(track_data, ensure_ascii=False).replace("</", "<\\/")

    rows_html = "\n".join(_row(i, r) for i, r in enumerate(results))

    html_doc = (
        _TEMPLATE
        .replace("__CSS__", _CSS)
        .replace("__JS__", _JS)
        .replace("__TITLE__", f"{total} tracks")
        .replace("__GEN_TIME__", gen_time)
        .replace("__TOTAL__", str(total))
        .replace("__AVG_BPM__", f"{avg_bpm:.0f}")
        .replace("__NUM_MOODS__", str(len(moods)))
        .replace("__MOOD_OPTIONS__", mood_options)
        .replace("__ROWS__", rows_html)
        .replace("__DATA_JSON__", data_json)
    )

    out.write_text(html_doc, encoding="utf-8")
    return out.resolve()
