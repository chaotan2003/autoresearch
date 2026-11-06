#!/usr/bin/env python3
"""Render the autoresearch data-flow diagram (one image, PNG + SVG)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "Noto Sans CJK JP", "WenQuanYi Micro Hei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

W, H = 22.0, 8.6
fig, ax = plt.subplots(figsize=(W, H), dpi=150)
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

C = dict(
    gemini=("#dbeafe", "#2563eb"), codex=("#ffedd5", "#ea580c"),
    dsh=("#dcfce7", "#16a34a"), human=("#fef9c3", "#ca8a04"),
    art=("#f8fafc", "#475569"), gate=("#fee2e2", "#dc2626"),
)
INK = "#1e293b"; MUTED = "#64748b"

def box(cx, cy, w, h, text, kind, fs=9.5, bold_first=True):
    fc, ec = C[kind]
    ax.add_patch(FancyBboxPatch((cx - w/2, cy - h/2), w, h,
                 boxstyle="round,pad=0.015,rounding_size=0.08",
                 facecolor=fc, edgecolor=ec, linewidth=1.3, zorder=3))
    lines = text.split("\n")
    if bold_first and len(lines) > 1:
        ax.text(cx, cy + 0.13, lines[0], ha="center", va="center", fontsize=fs,
                fontweight="bold", color=INK, zorder=4)
        ax.text(cx, cy - 0.17, "\n".join(lines[1:]), ha="center", va="center",
                fontsize=fs - 1.6, color=MUTED, zorder=4, linespacing=1.45)
    else:
        ax.text(cx, cy, text, ha="center", va="center", fontsize=fs,
                color=INK, zorder=4, linespacing=1.45)

def arrow(p0, p1, color=INK, style="-|>", lw=1.7, ls="-", rad=0.0, z=2):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle=style, mutation_scale=16,
                 linewidth=lw, linestyle=ls, color=color, zorder=z,
                 connectionstyle=f"arc3,rad={rad}", shrinkA=2, shrinkB=2))

# ---------- geometry ----------
xs = [1.15 + i * 2.54 for i in range(8)]
BW, BH = 1.62, 0.95
Y_AXIS, Y_BADGE, Y_FILE = 4.90, 6.15, 3.35
GATE_A, GATE_B = (xs[3] + xs[4]) / 2, (xs[5] + xs[6]) / 2

stages = [
    ("S1  找文献 + 选 baseline", "agy 搜+写 · DSH 核", "paper_search.md\nbaseline_selection.md", "dsh"),
    ("S2  提 10 个 idea", "agy 写（新会话）", "ideas.md", "gemini"),
    ("S3  idea 打分排序", "Codex 独立评审", "idea_cards.md\nidea_ranking.md", "codex"),
    ("S4  查新 + 方法提案", "agy + Codex + DSH", "method_proposal.md", "gemini"),
    ("S5  复现 baseline", "DSH 跑 · 你看结果", "baseline_report.md\nbaseline_logs/", "dsh"),
    ("S6  写研究合同", "DSH 起草 · 你审", "research_contract_v1.md\nsha256 冻结", "human"),
    ("S7  实现方法", "DSH 写 · Codex 审", "method/ · tests/\nimplementation_report.md", "dsh"),
    ("S8  跑实验 + 分析", "DSH 跑 · Codex 挑刺", "experiment_results/\nexperiment_analysis.md\nresearch_decision.md", "dsh"),
]

# ---------- title ----------
ax.text(0.55, 8.25, "AUTORESEARCH 数据流 —— 以 DSH 为主控", fontsize=17, fontweight="bold", color=INK)
ax.text(0.55, 7.86, "阶段之间只传文件路径，不共享聊天记录；每个 AI 调用都是新会话/新进程。产物落在 research/，状态落在 .autoresearch/。",
        fontsize=9.5, color=MUTED)

# ---------- input ----------
box(xs[0], 6.98, 2.05, 0.52, "你的研究目标", "human", fs=10)
arrow((xs[0], 6.70), (xs[0], 6.39), color=C["human"][1])

# ---------- stages ----------
for i, (title, actor, files, kind) in enumerate(stages):
    x = xs[i]
    box(x, Y_BADGE, BW, 0.42, actor, kind, fs=8.2)
    box(x, Y_AXIS, BW, BH, title, "art", fs=9.2)
    arrow((x, Y_AXIS - BH/2), (x, Y_FILE + 1.15/2), color=MUTED, lw=1.2, ls=(0, (2, 2)))
    box(x, Y_FILE, BW, 1.15, files, "art", fs=8.0, bold_first=False)
    ax.text(x, Y_FILE - 0.72, f"#{i+1}", fontsize=7.5, color=MUTED, ha="center")

# ---------- flow arrows ----------
for i in range(7):
    x0, x1 = xs[i] + BW/2, xs[i+1] - BW/2
    arrow((x0, Y_AXIS), (x1, Y_AXIS))

# ---------- gates ----------
for gx, label in ((GATE_A, "★ Gate A｜你批准方法"), (GATE_B, "★ Gate B｜你冻结合同")):
    ax.plot([gx, gx], [2.95, 6.55], color=C["gate"][1], lw=2.6, ls=(0, (4, 3)), zorder=6)
    box(gx, 6.98, 2.42, 0.52, label, "gate", fs=9.5, bold_first=False)
    ax.text(gx, 2.72, "停：等你", fontsize=8.5, color=C["gate"][1], ha="center", fontweight="bold")


# ---------- decision ----------
DX = 21.0
box(DX, Y_AXIS, 1.72, BH, "你判\nContinue / Revise / Kill", "gate", fs=9.2, bold_first=False)
arrow((xs[7] + BW/2, Y_AXIS), (DX - 0.9, Y_AXIS))
box(DX, 6.98, 1.35, 0.52, "结束", "human", fs=9.5)
arrow((DX, Y_AXIS + BH/2), (DX, 6.70), color=C["human"][1])

# three outcomes as a plain text block (less clutter than three arrows)
for k, line in enumerate(("Continue → 重跑 S8", "Revise → 回 S4 开 v2", "Kill → 结束")):
    ax.text(DX, 4.02 - k * 0.36, line, fontsize=8.6, color=C["gate"][1], ha="center", va="center")

# Revise: back to S4
ax.plot([DX + 0.86, DX + 0.86], [Y_AXIS - BH/2, 1.98], color=C["gate"][1], lw=1.8, ls=(0, (5, 3)), zorder=1)
ax.plot([DX + 0.86, xs[3]], [1.98, 1.98], color=C["gate"][1], lw=1.8, ls=(0, (5, 3)), zorder=1)
arrow((xs[3], 1.98), (xs[3], Y_FILE - 1.15/2), color=C["gate"][1], lw=1.8, ls=(0, (5, 3)))
ax.text(xs[3] + 0.35, 2.14, "Revise：合同升 v2 → 回 S4 重做（旧合同留档只读）",
        fontsize=8.8, color=C["gate"][1], ha="left")

# ---------- state bar ----------
ax.add_patch(FancyBboxPatch((0.55, 1.08), W - 1.1, 0.46,
             boxstyle="round,pad=0.012,rounding_size=0.06",
             facecolor="#eef2ff", edgecolor="#6366f1", linewidth=1.1, zorder=3))
ax.text(0.75, 1.31, "全局状态（每步读 → 做事 → 写）：", fontsize=8.6, color="#3730a3",
        fontweight="bold", va="center")
ax.text(6.1, 1.31, ".autoresearch/state.json  ·  gates.jsonl（每次拍板）  ·  traces/（每次 agent 调用原文，可审计）",
        fontsize=8.6, color="#3730a3", va="center")

# ---------- legend ----------
lx = 0.75
for label, kind in (("agy 参与（Gemini 模型）", "gemini"), ("Codex 参与", "codex"),
                    ("DSH 自己做", "dsh"), ("你要出场", "human"),
                    ("产物文件", "art"), ("闸门 / 决策", "gate")):
    fc, ec = C[kind]
    ax.add_patch(FancyBboxPatch((lx, 0.30), 0.26, 0.24, boxstyle="round,pad=0.01,rounding_size=0.04",
                 facecolor=fc, edgecolor=ec, linewidth=1.2))
    ax.text(lx + 0.36, 0.42, label, fontsize=8.6, va="center", color=INK)
    lx += 0.36 + len(label) * 0.155 + 0.28

fig.canvas.draw()
r = fig.canvas.get_renderer()
tb = [(t, t.get_window_extent(r)) for t in ax.texts if t.get_text().strip()]
bad = 0
for i in range(len(tb)):
    for j in range(i + 1, len(tb)):
        a, b = tb[i][1], tb[j][1]
        if a.overlaps(b):
            ov = (min(a.x1, b.x1) - max(a.x0, b.x0)) * (min(a.y1, b.y1) - max(a.y0, b.y0))
            if ov > 0.15 * min(a.width * a.height, b.width * b.height):
                bad += 1
                print("TEXT OVERLAP:", repr(tb[i][0].get_text()[:24]), "<->", repr(tb[j][0].get_text()[:24]))
print("texts:", len(tb), "overlaps:", bad)

# every text inside its box / canvas
from matplotlib.patches import FancyBboxPatch as FBP
boxes = [p for p in ax.patches if isinstance(p, FBP)]
inv = ax.transData
x0f, y0f = ax.transData.transform((0, 0)); x1f, y1f = ax.transData.transform((W, H))
problems = 0
for t, bb in tb:
    if bb.x0 < x0f - 1 or bb.y0 < y0f - 1 or bb.x1 > x1f + 1 or bb.y1 > y1f + 1:
        problems += 1; print("OUT OF CANVAS:", repr(t.get_text()[:30]))
cx = (t.get_window_extent(r).x0 + t.get_window_extent(r).x1) / 2
cy = (t.get_window_extent(r).y0 + t.get_window_extent(r).y1) / 2
for p in boxes:
    pb = p.get_window_extent(r)
    if pb.x0 <= cx <= pb.x1 and pb.y0 <= cy <= pb.y1:
        if bb.x0 < pb.x0 - 1 or bb.x1 > pb.x1 + 1 or bb.y0 < pb.y0 - 1 or bb.y1 > pb.y1 + 1:
            problems += 1
            print("TEXT OVERFLOWS BOX:", repr(t.get_text()[:40]))
        break
print("containment problems:", problems)

import os
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "autoresearch-dataflow")
fig.savefig(out + ".png", bbox_inches="tight", pad_inches=0.12, facecolor="white")
fig.savefig(out + ".svg", bbox_inches="tight", pad_inches=0.12, facecolor="white")
print("wrote", out + ".png/.svg")