# -*- coding: utf-8 -*-
"""Round-2 SVG charts: context sweep, micro-tuning, build comparison, parameter scoreboard.
Pure hand-written SVG, no external deps. Output -> assets/ (relative to repo root)."""
import os, html

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
os.makedirs(OUT, exist_ok=True)

FONT = "-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
GOLD = "#d97706"
BLUE = "#2563eb"
GRAY = "#94a3b8"
DARK = "#0f172a"
MUTED = "#64748b"
GREEN = "#059669"
RED = "#dc2626"
LIGHT = "#f1f5f9"


def head(w, h, title, subtitle=""):
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">']
    s.append(f'<rect width="{w}" height="{h}" rx="12" fill="#ffffff"/>')
    s.append(f'<text x="24" y="34" font-family="{FONT}" font-size="19" font-weight="700" fill="{DARK}">{html.escape(title)}</text>')
    if subtitle:
        s.append(f'<text x="24" y="56" font-family="{FONT}" font-size="12.5" fill="{MUTED}">{html.escape(subtitle)}</text>')
    return s


def save(name, s):
    s.append('</svg>')
    p = os.path.join(OUT, name)
    open(p, "w", encoding="utf-8").write("\n".join(s))
    print("wrote", p)


# ---------------- Chart 5: context sweep ----------------
def chart_context_sweep():
    W, H = 940, 430
    s = head(W, H, "Vision Mode Context Sweep — 150K is the Sweet Spot",
             "Qwen3.8-27B NVFP4-LOW + Q8 vision + ckpt4 + MTP n-max 3 · RTX 5090 Laptop 24GB · 512-token runs")
    x0, y0, w, h = 70, 110, 800, 230
    labels = ["148K", "150K", "152K", "154K", "156K", "158K", "160K*", "192K*"]
    values = [80.4, 86.3, 63.6, 54.4, 49.2, 47.7, 37.2, 3.9]
    colors = [GOLD, GOLD, RED, RED, RED, RED, RED, RED]
    mv = 100.0
    base = y0 + h
    for i in range(6):
        gy = base - h * i / 5
        s.append(f'<line x1="{x0}" y1="{gy:.1f}" x2="{x0 + w}" y2="{gy:.1f}" stroke="#e2e8f0" stroke-width="1"/>')
        s.append(f'<text x="{x0 - 8}" y="{gy + 4:.1f}" font-family="{FONT}" font-size="11" fill="{MUTED}" text-anchor="end">{int(mv * i / 5)}</text>')
    n = len(values)
    slot = w / n
    bw = slot * 0.55
    for i, (lab, v, c) in enumerate(zip(labels, values, colors)):
        cx = x0 + slot * (i + 0.5)
        bh = h * v / mv
        by = base - bh
        s.append(f'<rect x="{cx - bw/2:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="5" fill="{c}"/>')
        s.append(f'<text x="{cx:.1f}" y="{by - 7:.1f}" font-family="{FONT}" font-size="14" font-weight="700" fill="{DARK}" text-anchor="middle">{v:.1f}</text>')
        s.append(f'<text x="{cx:.1f}" y="{base + 18:.1f}" font-family="{FONT}" font-size="12" fill="{MUTED}" text-anchor="middle">{lab}</text>')
    # reference line: text-mode 192K
    ry = base - h * 79.6 / mv
    s.append(f'<line x1="{x0}" y1="{ry:.1f}" x2="{x0 + w}" y2="{ry:.1f}" stroke="{BLUE}" stroke-width="1.5" stroke-dasharray="6,4"/>')
    s.append(f'<text x="{x0 + w - 4}" y="{ry - 6:.1f}" font-family="{FONT}" font-size="11.5" fill="{BLUE}" text-anchor="end">text-only mode reference: 79.6 tok/s</text>')
    s.append(f'<text x="{x0 + w}" y="{y0 - 12}" font-family="{FONT}" font-size="11.5" fill="{MUTED}" text-anchor="end">tok/s (generation)</text>')
    # annotations
    s.append(f'<text x="{x0 + slot * 1.5:.1f}" y="{y0 + 6}" font-family="{FONT}" font-size="12.5" font-weight="700" fill="{GOLD}" text-anchor="middle">← peak 86.3 (+36% vs 152K)</text>')
    s.append(f'<text x="24" y="{H - 22}" font-family="{FONT}" font-size="11.5" fill="{MUTED}">* 160K with ctx-checkpoints 4; 192K causes VRAM cliff (3.9). 150K ≈ text-only speed with full vision + long context.</text>')
    save("chart5-context-sweep.svg", s)


# ---------------- Chart 6: micro tuning ----------------
def chart_micro():
    W, H = 940, 430
    s = head(W, H, "Micro-Tuning on the 150K Sweet Spot — Default Wins",
             "Community-recommended flags tested on this machine: none helped (-ub 1024 hurt by 16%)")
    labels = ["Default", "-ub 1024", "-t 8", "-ub 1024 -t 8"]
    dec = [86.2, 72.6, 77.9, 62.1]
    pre = [1899, 1687, 2051, 1504]
    # left: decode
    x0, y0, w, h = 70, 110, 380, 230
    base = y0 + h
    mv = 100.0
    for i in range(5):
        gy = base - h * i / 4
        s.append(f'<line x1="{x0}" y1="{gy:.1f}" x2="{x0 + w}" y2="{gy:.1f}" stroke="#e2e8f0" stroke-width="1"/>')
        s.append(f'<text x="{x0 - 8}" y="{gy + 4:.1f}" font-family="{FONT}" font-size="11" fill="{MUTED}" text-anchor="end">{int(mv * i / 4)}</text>')
    slot = w / len(dec)
    bw = slot * 0.5
    for i, (lab, v) in enumerate(zip(labels, dec)):
        cx = x0 + slot * (i + 0.5)
        bh = h * v / mv
        by = base - bh
        c = GREEN if i == 0 else RED
        s.append(f'<rect x="{cx - bw/2:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="5" fill="{c}"/>')
        s.append(f'<text x="{cx:.1f}" y="{by - 7:.1f}" font-family="{FONT}" font-size="14" font-weight="700" fill="{DARK}" text-anchor="middle">{v:.1f}</text>')
        s.append(f'<text x="{cx:.1f}" y="{base + 18:.1f}" font-family="{FONT}" font-size="11.5" fill="{MUTED}" text-anchor="middle">{html.escape(lab)}</text>')
    s.append(f'<text x="{x0 + w/2}" y="{y0 - 12}" font-family="{FONT}" font-size="13.5" font-weight="600" fill="{DARK}" text-anchor="middle">Decode (tok/s)</text>')
    # right: prefill
    x1 = 540
    base2 = y0 + h
    mv2 = 2400.0
    for i in range(5):
        gy = base2 - h * i / 4
        s.append(f'<line x1="{x1}" y1="{gy:.1f}" x2="{x1 + w}" y2="{gy:.1f}" stroke="#e2e8f0" stroke-width="1"/>')
        s.append(f'<text x="{x1 - 8}" y="{gy + 4:.1f}" font-family="{FONT}" font-size="11" fill="{MUTED}" text-anchor="end">{int(mv2 * i / 4)}</text>')
    for i, (lab, v) in enumerate(zip(labels, pre)):
        cx = x1 + slot * (i + 0.5)
        bh = h * v / mv2
        by = base2 - bh
        c = GREEN if i == 0 else (BLUE if i == 2 else RED)
        s.append(f'<rect x="{cx - bw/2:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="5" fill="{c}"/>')
        s.append(f'<text x="{cx:.1f}" y="{by - 7:.1f}" font-family="{FONT}" font-size="14" font-weight="700" fill="{DARK}" text-anchor="middle">{v}</text>')
        s.append(f'<text x="{cx:.1f}" y="{base2 + 18:.1f}" font-family="{FONT}" font-size="11.5" fill="{MUTED}" text-anchor="middle">{html.escape(lab)}</text>')
    s.append(f'<text x="{x1 + w/2}" y="{y0 - 12}" font-family="{FONT}" font-size="13.5" font-weight="600" fill="{DARK}" text-anchor="middle">Prefill (tok/s, 4800-token prompt)</text>')
    s.append(f'<text x="24" y="{H - 22}" font-family="{FONT}" font-size="11.5" fill="{MUTED}">-t 8 trades 10% decode for 8% prefill (net loss). -ub 1024 hurts both — another "community data does not transfer" case.</text>')
    save("chart6-micro-tuning.svg", s)


# ---------------- Chart 7: build comparison (MTP bug) ----------------
def chart_builds():
    W, H = 940, 420
    s = head(W, H, "Build Comparison — The MTP Prefill Bug",
             "Same model, same server arguments; only the toolchain differs (prefill, 4800-token prompt)")
    x0, y0, w, h = 70, 110, 800, 220
    labels = ["Self-built\n+ MTP", "Self-built\nno MTP", "Official b10917\n+ MTP", "Official b10889\n+ MTP"]
    values = [32.7, 1867.5, 1344.9, 1482.0]
    colors = [RED, GREEN, BLUE, BLUE]
    mv = 2100.0
    base = y0 + h
    for i in range(5):
        gy = base - h * i / 4
        s.append(f'<line x1="{x0}" y1="{gy:.1f}" x2="{x0 + w}" y2="{gy:.1f}" stroke="#e2e8f0" stroke-width="1"/>')
        s.append(f'<text x="{x0 - 8}" y="{gy + 4:.1f}" font-family="{FONT}" font-size="11" fill="{MUTED}" text-anchor="end">{int(mv * i / 4)}</text>')
    slot = w / len(values)
    bw = slot * 0.5
    for i, (lab, v, c) in enumerate(zip(labels, values, colors)):
        cx = x0 + slot * (i + 0.5)
        bh = h * v / mv
        by = base - bh
        s.append(f'<rect x="{cx - bw/2:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="5" fill="{c}"/>')
        s.append(f'<text x="{cx:.1f}" y="{by - 7:.1f}" font-family="{FONT}" font-size="14" font-weight="700" fill="{DARK}" text-anchor="middle">{v:.1f}</text>')
        for j, line in enumerate(lab.split("\n")):
            s.append(f'<text x="{cx:.1f}" y="{base + 18 + j*14:.1f}" font-family="{FONT}" font-size="11.5" fill="{MUTED}" text-anchor="middle">{html.escape(line)}</text>')
    s.append(f'<text x="{x0 + w}" y="{y0 - 12}" font-family="{FONT}" font-size="11.5" fill="{MUTED}" text-anchor="end">tok/s (prefill)</text>')
    s.append(f'<text x="{x0 + slot*0.5:.1f}" y="{y0 + 6}" font-family="{FONT}" font-size="12" font-weight="700" fill="{RED}" text-anchor="middle">57× slower</text>')
    s.append(f'<text x="24" y="{H - 40}" font-family="{FONT}" font-size="11.5" fill="{MUTED}">Root cause: MSVC + CUDA 12.8 self-compilation. Official builds (Clang + CUDA 13.x) unaffected.</text>')
    s.append(f'<text x="24" y="{H - 22}" font-family="{FONT}" font-size="11.5" fill="{MUTED}">Reported upstream: github.com/ggml-org/llama.cpp/issues/28790</text>')
    save("chart7-build-comparison.svg", s)


# ---------------- Chart 8: parameter scoreboard ----------------
def chart_scoreboard():
    W, H = 940, 480
    s = head(W, H, "Parameter Scoreboard — What Actually Helps",
             "Every optimization tested on this machine, ranked by measured effect")
    # (label, effect %, note)
    rows = [
        ("q8_0 KV vs q4_0 KV  (long input)", 2700, "+27× faster; q4_0 falls off a cliff", GREEN),
        ("--ctx-checkpoints 4  (160K)", 79, "+79% at 160K (20.8 → 37.2)", GREEN),
        ("150K context (vs 152K)", 36, "+36%: the sweet spot discovery", GREEN),
        ("MTP n-max 3 (vs 8)", 523, "n-max 8 collapses draft acceptance", GREEN),
        ("Q8 vision quant (VRAM)", 32, "-32% mmproj size, same quality", GREEN),
        ("-t 8 (thread count)", -10, "trades 10% decode for 8% prefill", RED),
        ("-ub 1024 (community rec.)", -16, "hurts both decode and prefill here", RED),
        ("iMatrix mixed quant", -27, "quality tied, 27% slower, 48K less ctx", RED),
        ("--spec-default (n-gram)", -39, "45.8 vs 74.6 tok/s", RED),
        ("Self-built (MSVC) + MTP", -98, "prefill collapsed 57× (bug #28790)", RED),
    ]
    x0 = 360
    w = 460
    y = 100
    rh = 32
    # zero axis at x0
    mv = 100.0  # % scale for pos; negatives use log-ish cap at -100
    s.append(f'<line x1="{x0}" y1="{y}" x2="{x0}" y2="{y + rh * len(rows)}" stroke="{MUTED}" stroke-width="1"/>')
    for i, (label, v, note, c) in enumerate(rows):
        yy = y + i * rh
        s.append(f'<text x="{x0 - 12}" y="{yy + 18}" font-family="{FONT}" font-size="12" fill="{DARK}" text-anchor="end">{html.escape(label)}</text>')
        if v > 100:  # cap wide bars
            vv = 100
            txt = note
        else:
            vv = v
            txt = f"{v:+d}%"
        bw = abs(vv) / 100 * (w * 0.42)
        bx = x0 + 4 if v > 0 else x0 - 4 - bw
        s.append(f'<rect x="{bx:.1f}" y="{yy + 6}" width="{bw:.1f}" height="20" rx="4" fill="{c}"/>')
        s.append(f'<text x="{(bx + bw + 6) if v > 0 else (bx - 6):.1f}" y="{yy + 21}" font-family="{FONT}" font-size="11.5" fill="{DARK}" text-anchor="{"start" if v > 0 else "end"}">{html.escape(txt)}</text>')
    s.append(f'<text x="{x0}" y="{y - 12}" font-family="{FONT}" font-size="12" font-weight="600" fill="{MUTED}" text-anchor="middle">← negative ｜ positive →</text>')
    s.append(f'<text x="24" y="{H - 22}" font-family="{FONT}" font-size="11.5" fill="{MUTED}">Green = measured improvement kept in the final recipe. Red = rejected after testing (regardless of popularity).</text>')
    save("chart8-parameter-scoreboard.svg", s)


chart_context_sweep()
chart_micro()
chart_builds()
chart_scoreboard()
print("done")
