# -*- coding: utf-8 -*-
"""Generate SVG charts for the GitHub benchmark report (no external deps)."""
import os, re, html

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


def head(w, h, title, subtitle=""):
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">']
    s.append(f'<rect width="{w}" height="{h}" rx="12" fill="#ffffff"/>')
    s.append(f'<text x="24" y="34" font-family="{FONT}" font-size="19" font-weight="700" fill="{DARK}">{html.escape(title)}</text>')
    if subtitle:
        s.append(f'<text x="24" y="56" font-family="{FONT}" font-size="12.5" fill="{MUTED}">{html.escape(subtitle)}</text>')
    return s


def bar_chart(x0, y0, w, h, labels, values, colors, unit, title, max_v=None, fmt="{:.1f}"):
    """Vertical bar chart in a sub-region."""
    s = []
    s.append(f'<text x="{x0}" y="{y0 - 10}" font-family="{FONT}" font-size="13.5" font-weight="600" fill="{DARK}">{html.escape(title)}</text>')
    top = y0 + 10
    base = y0 + h
    mv = max_v if max_v else max(values) * 1.18
    # grid
    for i in range(5):
        gy = base - h * i / 4
        s.append(f'<line x1="{x0}" y1="{gy:.1f}" x2="{x0 + w}" y2="{gy:.1f}" stroke="#e2e8f0" stroke-width="1"/>')
    n = len(values)
    slot = w / n
    bw = slot * 0.5
    for i, (lab, v, c) in enumerate(zip(labels, values, colors)):
        cx = x0 + slot * (i + 0.5)
        bh = h * v / mv
        by = base - bh
        s.append(f'<rect x="{cx - bw/2:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="5" fill="{c}"/>')
        s.append(f'<text x="{cx:.1f}" y="{by - 7:.1f}" font-family="{FONT}" font-size="15" font-weight="700" fill="{DARK}" text-anchor="middle">{fmt.format(v)}</text>')
        s.append(f'<text x="{cx:.1f}" y="{base + 18:.1f}" font-family="{FONT}" font-size="12" fill="{MUTED}" text-anchor="middle">{html.escape(lab)}</text>')
    s.append(f'<text x="{x0 - 8}" y="{base + 4}" font-family="{FONT}" font-size="11" fill="{MUTED}" text-anchor="end">0</text>')
    s.append(f'<text x="{x0 + w}" y="{y0 - 10}" font-family="{FONT}" font-size="11.5" fill="{MUTED}" text-anchor="end">{html.escape(unit)}</text>')
    return s


# ---------------- Chart 1: speed duel ----------------
def chart_speed():
    W, H = 920, 400
    s = head(W, H, "Three-Way Speed Duel — RTX 5090 Laptop 24GB (llama.cpp b10889)",
             "Identical conditions: each model at its own max context, q8_0 KV, MTP n-max 3")
    labels = ["NVFP4-LOW", "IQ3_S", "UD-Q4_K_S"]
    gold_blue = [GOLD, BLUE, GRAY]
    s += bar_chart(60, 100, 370, 220, labels, [79.6, 64.4, 51.7], gold_blue, "tok/s", "Generation speed (256-token runs)")
    s += bar_chart(520, 100, 340, 220, labels, [9.7, 14.9, 19.9], gold_blue, "seconds (lower is better)", "15.6K-token prompt (prefill)")
    s.append(f'<text x="24" y="{H - 26}" font-family="{FONT}" font-size="12" fill="{MUTED}">'
             f'🏆 NVFP4-LOW leads both: +24% generation and −35% prefill latency vs IQ3_S; +54% / −51% vs UD-Q4_K_S.</text>')
    s.append(f'<text x="24" y="{H - 10}" font-family="{FONT}" font-size="11" fill="#94a3b8">'
             f'Speed varies ±10% with content-dependent MTP acceptance. Measured September 2026.</text>')
    s.append("</svg>")
    open(os.path.join(OUT, "chart1-speed-duel.svg"), "w", encoding="utf-8").write("\n".join(s))


# ---------------- Chart 2: capacity ----------------
def chart_capacity():
    W, H = 920, 420
    s = head(W, H, "Context Capacity by KV Quantization",
             "Measured launch + inference ceiling (24 GB VRAM, single model, no offload)")
    models = ["NVFP4-LOW", "IQ3_S", "UD-Q4_K_S"]
    f16 = [96, 136, 96]
    q8 = [200, 212, 200]
    x0, y0, w, h = 70, 105, 790, 230
    base = y0 + h
    mv = 240
    s.append(f'<text x="{x0}" y="{y0 - 20}" font-family="{FONT}" font-size="13.5" font-weight="600" fill="{DARK}">Max context length (thousands of tokens)</text>')
    for i in range(6):
        gy = base - h * i / 5
        s.append(f'<line x1="{x0}" y1="{gy:.1f}" x2="{x0 + w}" y2="{gy:.1f}" stroke="#e2e8f0" stroke-width="1"/>')
        s.append(f'<text x="{x0 - 10}" y="{gy + 4:.1f}" font-family="{FONT}" font-size="11" fill="{MUTED}" text-anchor="end">{int(mv * i / 5)}K</text>')
    slot = w / len(models)
    bw = slot * 0.22
    for i, m in enumerate(models):
        cx = x0 + slot * (i + 0.5)
        for j, (v, c, lab) in enumerate([(f16[i], GRAY, "F16 KV"), (q8[i], GREEN, "q8_0 KV")]):
            bx = cx + (j - 1) * (bw + 6) + 3
            bh = h * v / mv
            s.append(f'<rect x="{bx:.1f}" y="{base - bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="5" fill="{c}"/>')
            s.append(f'<text x="{bx + bw/2:.1f}" y="{base - bh - 7:.1f}" font-family="{FONT}" font-size="13" font-weight="700" fill="{DARK}" text-anchor="middle">{v}K</text>')
            if i == 0:
                s.append(f'<text x="{bx + bw/2:.1f}" y="{base + 16:.1f}" font-family="{FONT}" font-size="11" fill="{MUTED}" text-anchor="middle">{lab}</text>')
        s.append(f'<text x="{cx:.1f}" y="{base + 40:.1f}" font-family="{FONT}" font-size="12.5" font-weight="600" fill="{DARK}" text-anchor="middle">{html.escape(m)}</text>')
    s.append(f'<text x="24" y="{H - 30}" font-family="{FONT}" font-size="12" fill="{MUTED}">'
             f'q8_0 KV costs nothing in speed (measured) and lifts capacity +48%~+108%: 🔑 the single most effective lever.</text>')
    s.append(f'<text x="24" y="{H - 13}" font-family="{FONT}" font-size="11" fill="{RED}">'
             f'⚠️ q4_0-class KV reaches the full 262K but makes long prompts ~28× slower (kernel fallback) — do not use.</text>')
    s.append("</svg>")
    open(os.path.join(OUT, "chart2-context-capacity.svg"), "w", encoding="utf-8").write("\n".join(s))


# ---------------- Chart 3: thermal ----------------
def chart_thermal():
    # parse raw data
    pts = []
    src = os.path.join(os.path.dirname(OUT), "data", "thermal-stress-12min-100rounds.txt")
    if os.path.exists(src):
        for line in open(src, encoding="utf-8"):
            m = re.search(r"\[(\d+)m(\d+)s\].*?([\d.]+) tok/s.*?GPU:\s*(\d+),\s*([\d.]+) W,\s*(\d+) MHz", line)
            if m:
                t = int(m.group(1)) * 60 + int(m.group(2))
                pts.append((t, float(m.group(3)), int(m.group(4)), float(m.group(5)), int(m.group(6))))
    if not pts:
        pts = [(0, 78.7, 55, 132.1, 1830), (120, 73.3, 72, 146.3, 1777), (459, 73.7, 75, 145.5, 1725), (725, 83.7, 77, 145.4, 1740)]
    W, H = 920, 420
    s = head(W, H, "12-Minute Thermal Stress Test — 100 Rounds, No Speed Decay",
             "Continuous 512-token generation · NVFP4-LOW @152K · laptop RTX 5090 (≈145 W ceiling)")
    x0, y0, w, h = 70, 100, 700, 230
    base = y0 + h
    tmax = max(p[0] for p in pts) or 1
    vmin, vmax = 40, 100
    tmin, tmaxc = 40, 90
    for i in range(7):
        gy = base - h * i / 6
        s.append(f'<line x1="{x0}" y1="{gy:.1f}" x2="{x0 + w}" y2="{gy:.1f}" stroke="#e2e8f0" stroke-width="1"/>')
        s.append(f'<text x="{x0 - 8}" y="{gy + 4:.1f}" font-family="{FONT}" font-size="11" fill="{BLUE}" text-anchor="end">{int(vmin + (vmax - vmin) * i / 6)}</text>')
        s.append(f'<text x="{x0 + w + 8}" y="{gy + 4:.1f}" font-family="{FONT}" font-size="11" fill="{RED}">{int(tmin + (tmaxc - tmin) * i / 6)}°</text>')
    for mm in range(0, 13, 3):
        gx = x0 + w * (mm * 60) / tmax
        s.append(f'<line x1="{gx:.1f}" y1="{base}" x2="{gx:.1f}" y2="{base + 5}" stroke="{MUTED}"/>')
        s.append(f'<text x="{gx:.1f}" y="{base + 19:.1f}" font-family="{FONT}" font-size="11" fill="{MUTED}" text-anchor="middle">{mm} min</text>')
    def px(p):
        return (x0 + w * p[0] / tmax, base - h * (p[1] - vmin) / (vmax - vmin), base - h * (p[2] - tmin) / (tmaxc - tmin))
    s.append(f'<path d="' + " ".join(("M" if i == 0 else "L") + f"{px(p)[0]:.1f},{px(p)[1]:.1f}" for i, p in enumerate(pts)) + f'" fill="none" stroke="{BLUE}" stroke-width="2" opacity="0.9"/>')
    s.append(f'<path d="' + " ".join(("M" if i == 0 else "L") + f"{px(p)[0]:.1f},{px(p)[2]:.1f}" for i, p in enumerate(pts)) + f'" fill="none" stroke="{RED}" stroke-width="2" opacity="0.9"/>')
    fp = px(pts[0]); lp = px(pts[-1])
    s.append(f'<circle cx="{fp[0]:.1f}" cy="{fp[1]:.1f}" r="4" fill="{BLUE}"/><circle cx="{lp[0]:.1f}" cy="{lp[1]:.1f}" r="4" fill="{BLUE}"/>')
    s.append(f'<circle cx="{fp[0]:.1f}" cy="{fp[2]:.1f}" r="4" fill="{RED}"/><circle cx="{lp[0]:.1f}" cy="{lp[2]:.1f}" r="4" fill="{RED}"/>')
    s.append(f'<text x="{lp[0]-10:.1f}" y="{lp[1]-14:.1f}" font-family="{FONT}" font-size="12" font-weight="700" fill="{BLUE}" text-anchor="end">tok/s</text>')
    s.append(f'<text x="{lp[0]-10:.1f}" y="{lp[2]+20:.1f}" font-family="{FONT}" font-size="12" font-weight="700" fill="{RED}" text-anchor="end">GPU temp</text>')
    s.append(f'<rect x="{x0 + w + 40}" y="{y0}" width="150" height="86" rx="8" fill="#f8fafc" stroke="#e2e8f0"/>')
    s.append(f'<text x="{x0 + w + 52}" y="{y0 + 22}" font-family="{FONT}" font-size="11.5" fill="{MUTED}">First round</text>')
    s.append(f'<text x="{x0 + w + 52}" y="{y0 + 40}" font-family="{FONT}" font-size="14" font-weight="700" fill="{DARK}">78.7 tok/s · 55°C</text>')
    s.append(f'<text x="{x0 + w + 52}" y="{y0 + 60}" font-family="{FONT}" font-size="11.5" fill="{MUTED}">Last round (#100)</text>')
    s.append(f'<text x="{x0 + w + 52}" y="{y0 + 78}" font-family="{FONT}" font-size="14" font-weight="700" fill="{GREEN}">83.7 tok/s · 77°C</text>')
    s.append(f'<text x="24" y="{H - 24}" font-family="{FONT}" font-size="12" fill="{MUTED}">'
             f'Temperature plateaus at 77°C; SM clock dips only −5%. Sustained agent workloads are thermally safe on this laptop.</text>')
    s.append("</svg>")
    open(os.path.join(OUT, "chart3-thermal-stress.svg"), "w", encoding="utf-8").write("\n".join(s))


# ---------------- Chart 4: funnel ----------------
def chart_funnel():
    W, H = 920, 320
    s = head(W, H, "Selection Funnel — 53 Community Variants to 1 Winner",
             "Hard constraints → paper review → unified benchmarking → deep duel")
    stages = [
        ("53", "quantization variants\n(surveyed across 8 families)"),
        ("15", "structurally qualified\n(size / MTP / non-experimental)"),
        ("4", "benchmarked finalists\n(IQ3_S · NVFP4-MH · NVFP4-LOW · UD-Q4_K_S)"),
        ("3", "deep duel\n(speed + capacity + quality)"),
        ("1", "winner\nNVFP4-MTP-LOW"),
    ]
    x0, y0, w = 60, 100, 800
    maxw = 470
    ws = [maxw, maxw * 0.72, maxw * 0.55, maxw * 0.42, maxw * 0.30]
    for i, ((num, desc), bw) in enumerate(zip(stages, ws)):
        yy = y0 + i * 40
        col = GOLD if i == len(stages) - 1 else BLUE
        op = 1.0 if i >= 3 else 0.82
        s.append(f'<rect x="{x0 + (maxw - bw)/2:.1f}" y="{yy}" width="{bw:.1f}" height="30" rx="6" fill="{col}" opacity="{op}"/>')
        s.append(f'<text x="{x0 + maxw/2:.1f}" y="{yy + 21}" font-family="{FONT}" font-size="14" font-weight="700" fill="#ffffff" text-anchor="middle">{num}</text>')
        for k, line in enumerate(desc.split("\n")):
            s.append(f'<text x="{x0 + maxw + 26}" y="{yy + 13 + k*15}" font-family="{FONT}" font-size="12" fill="{MUTED if i < 4 else DARK}">{html.escape(line)}</text>')
    s.append("</svg>")
    open(os.path.join(OUT, "chart4-selection-funnel.svg"), "w", encoding="utf-8").write("\n".join(s))


chart_speed()
chart_capacity()
chart_thermal()
chart_funnel()
print("charts written to", OUT)
for f in sorted(os.listdir(OUT)):
    print(" ", f, os.path.getsize(os.path.join(OUT, f)), "bytes")
