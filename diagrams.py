"""Draw the Chapter Three design diagrams and Chapter Four result charts.

Output: artifacts/figs/*.png (200 dpi, white background).
Palette: navy #122a4d, orange #e67e22, green #1b6b3a, red #b3261e, grey #6b7280.
Layout is computed from content sizes; nothing is positioned by hand-tuned guesswork
where a measurement will do.
"""
import os, json
import matplotlib
matplotlib.use("Agg")
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Ellipse, Polygon, Circle

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "artifacts", "figs")
os.makedirs(OUT, exist_ok=True)

NAVY, ORANGE, GREEN, RED, GREY = "#122a4d", "#e67e22", "#1b6b3a", "#b3261e", "#6b7280"
LIGHT, WARM, MINT, PALE = "#e8f0fa", "#fdf1e3", "#eef7f0", "#f4f4f5"
plt.rcParams["font.family"] = "DejaVu Sans"


def canvas(w=12, h=8.6, xlim=(0, 100), ylim=(-4, 106)):
    fig, ax = plt.subplots(figsize=(w, h), dpi=200)
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.axis("off")
    fig.patch.set_facecolor("white")
    return fig, ax


def rbox(ax, x, y, w, h, text, fc="white", ec=NAVY, fs=9.5, bold=False,
         tc="#111827", lw=1.4, ls="-", zorder=3):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                boxstyle="round,pad=0.02,rounding_size=1.0",
                                linewidth=lw, edgecolor=ec, facecolor=fc,
                                ls=ls, zorder=zorder))
    if text:
        ax.text(x, y, text, ha="center", va="center", fontsize=fs, color=tc,
                fontweight="bold" if bold else "normal", zorder=zorder + 1,
                linespacing=1.5)


def line(ax, pts, color=NAVY, lw=1.3, ls="-", zorder=2):
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=lw, ls=ls,
            zorder=zorder, solid_capstyle="round")


def arrow(ax, p1, p2, text=None, color=NAVY, lw=1.3, fs=8, rad=0.0, ls="-",
          toff=(0, 2.0), style="-|>", zorder=4, tpos=0.5):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=13,
                                 color=color, lw=lw, shrinkA=1.2, shrinkB=1.2,
                                 connectionstyle=f"arc3,rad={rad}", linestyle=ls,
                                 zorder=zorder))
    if text:
        mx = p1[0] + (p2[0] - p1[0]) * tpos + toff[0]
        my = p1[1] + (p2[1] - p1[1]) * tpos + toff[1]
        ax.text(mx, my, text, fontsize=fs, ha="center", va="center", color=color,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.95),
                zorder=zorder + 1)


def diamond(ax, x, y, w, h, text, fs=8.8, fc="#fff4e6", ec=ORANGE):
    ax.add_patch(Polygon([(x, y + h / 2), (x + w / 2, y), (x, y - h / 2), (x - w / 2, y)],
                         closed=True, facecolor=fc, edgecolor=ec, lw=1.4, zorder=3))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, color="#111827",
            zorder=4, linespacing=1.4)


def oval(ax, x, y, w, h, text, fc=LIGHT, ec=NAVY, fs=9.2):
    ax.add_patch(Ellipse((x, y), w, h, facecolor=fc, edgecolor=ec, lw=1.4, zorder=3))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, color="#111827",
            fontweight="bold", zorder=4, linespacing=1.35)


def title(ax, text, fs=13):
    ax.text(50, 103, text, ha="center", va="top", fontsize=fs, color=NAVY,
            fontweight="bold")


def actor(ax, x, y, label, fs=9.5):
    ax.add_patch(Circle((x, y + 3.4), 1.6, facecolor="white", edgecolor=NAVY, lw=1.4, zorder=3))
    line(ax, [(x, y + 1.8), (x, y - 2.0)], lw=1.4, zorder=3)
    line(ax, [(x - 2.4, y + 0.6), (x + 2.4, y + 0.6)], lw=1.4, zorder=3)
    line(ax, [(x, y - 2.0), (x - 2.0, y - 5.4)], lw=1.4, zorder=3)
    line(ax, [(x, y - 2.0), (x + 2.0, y - 5.4)], lw=1.4, zorder=3)
    ax.text(x, y - 7.6, label, ha="center", va="center", fontsize=fs, color=NAVY, fontweight="bold")


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0.14, facecolor="white")
    plt.close(fig)
    print("wrote", path)


# ---------------------------------------------------------------- 1 use case
def fig_use_case():
    fig, ax = canvas(12, 9)
    title(ax, "Use case diagram — phishing detection and URL classification system")
    rbox(ax, 51, 53, 68, 84, "", fc="#fbfcfd", ec=NAVY, lw=1.6)
    ax.text(51, 92.5, "System boundary", ha="center", fontsize=8.6, color=GREY, style="italic")

    actor(ax, 8, 55, "User")
    actor(ax, 94, 26, "Administrator")

    # main use cases (left column)
    oval(ax, 33, 84, 26, 8.4, "Submit URL")
    oval(ax, 33, 56, 26, 8.4, "Classify URL")
    oval(ax, 33, 26, 26, 9.4, "View verdict\nand evidence")

    # included use cases (right column)
    for y, t in [(84, "Validate input"), (72, "Extract 16 features"),
                 (60, "Query trained model"), (44, "Log scan record")]:
        oval(ax, 71, y, 26, 8.0, t, fc=WARM, ec=ORANGE, fs=8.8)
    oval(ax, 71, 26, 24, 7.6, "Retrain model", fc=PALE, ec=GREY, fs=8.8)

    for y in (84, 56, 26):
        arrow(ax, (12, 55), (19.5, y), lw=1.1, rad=0.04)
    arrow(ax, (86, 26), (83.5, 26), lw=1.2)

    for y in (84, 72, 60, 44):
        arrow(ax, (46.5, 56), (57.5, y), color=ORANGE, lw=1.05, ls="--", style="-|>")
    arrow(ax, (33, 21.2), (33, 52), color=ORANGE, lw=1.05, ls="--", style="-|>",
          text="«extend»", fs=7.6, toff=(7.2, 0))

    ax.text(51, 5.5, "Solid arrows: actor interaction.   Dashed arrows: «include» and «extend» relationships.",
            ha="center", fontsize=8.8, color=GREY, style="italic")
    save(fig, "fig01_use_case.png")


# ---------------------------------------------------------------- 2 architecture
def fig_architecture():
    fig, ax = canvas(12, 8.4)
    title(ax, "Three-tier system architecture")
    tiers = [
        (86, 15, "PRESENTATION TIER\nReact single-page application · Tailwind CSS\nURL input · verdict panel · evidence chips · scan history", LIGHT, NAVY),
        (62, 18, "APPLICATION TIER — FastAPI service\n\nPOST /api/classify · input validation · feature extraction (16 features)\nmodel inference · contribution ranking · scan logging · GET /api/history", WARM, ORANGE),
        (37, 13, "MODEL TIER\nRandom Forest artefact · feature order · model metadata", MINT, GREEN),
        (14, 13, "DATA TIER\nSQLite · scan_record · model_version", PALE, GREY),
    ]
    for y, h, t, fc, ec in tiers:
        rbox(ax, 50, y, 84, h, t, fc=fc, ec=ec, fs=9.0)
    for y1, y2, lab in [(78.5, 71, "HTTPS / JSON"), (53, 43.5, "loads artefact at start-up"),
                        (30.5, 20.5, "writes verdict")]:
        ax.annotate("", xy=(50, y1), xytext=(50, y2),
                    arrowprops=dict(arrowstyle="<|-|>", color=NAVY, lw=1.3,
                                    mutation_scale=13))
        ax.text(60, (y1 + y2) / 2 + 0.4, lab, fontsize=8.4, color=NAVY, va="center")
    ax.text(50, 2.5, "No tier retrieves the submitted URL: the destination page is never requested by the server.",
            ha="center", fontsize=8.8, color=GREY, style="italic")
    save(fig, "fig02_architecture.png")


# ---------------------------------------------------------------- 3 class diagram
def fig_class():
    fig, ax = canvas(12, 9.6)

    def cls(x, top, w, name, attrs, methods, fc="white", ec=NAVY):
        h = 4.6 + len(attrs) * 2.5 + 1.4 + len(methods) * 2.5 + 1.4
        bottom = top - h
        ax.add_patch(FancyBboxPatch((x - w / 2, bottom), w, h,
                                    boxstyle="round,pad=0.02,rounding_size=0.7",
                                    fc=fc, ec=ec, lw=1.4, zorder=3))
        ax.add_patch(plt.Rectangle((x - w / 2, top - 4.6), w, 4.6, fc=ec, ec=ec, zorder=4))
        ax.text(x, top - 2.3, name, ha="center", va="center", fontsize=9.2,
                color="white", fontweight="bold", zorder=5)
        ty = top - 6.6
        for a in attrs:
            ax.text(x - w / 2 + 1.4, ty, a, fontsize=8.0, color="#111827", zorder=5)
            ty -= 2.5
        div = ty + 0.9
        ax.plot([x - w / 2, x + w / 2], [div, div], color=ec, lw=1.0, zorder=5)
        ty = div - 1.9
        for m in methods:
            ax.text(x - w / 2 + 1.4, ty, m, fontsize=8.0, color=NAVY, style="italic", zorder=5)
            ty -= 2.5
        return bottom

    LEFT, RIGHT, W = 26, 72, 40
    cls(LEFT, 96, W, "URLSubmission",
        ["- raw: str", "- normalised: str", "- is_valid: bool"],
        ["+ validate() : bool", "+ normalise() : str"], fc=LIGHT)
    cls(RIGHT, 96, W, "FeatureExtractor",
        ["- brand_list: list", "- token_list: list"],
        ["+ extract(url) : dict", "- _host_features() : dict"], fc=WARM, ec=ORANGE)
    b2 = cls(LEFT, 62, W, "ModelPredictor",
             ["- model: RandomForest", "- feature_order: list"],
             ["+ predict(vec) : str", "+ probability(vec) : float", "+ contributions(vec) : list"],
             fc=MINT, ec=GREEN)
    cls(RIGHT, 62, W, "ScanResult",
        ["+ url: str", "+ verdict: str", "+ confidence: float", "+ evidence: list"],
        ["+ to_json() : dict"])
    cls(LEFT, 26, W, "ScanRecord",
        ["+ scan_id: int", "+ url: str", "+ created_at: datetime"], ["+ save() : None"])
    cls(RIGHT, 26, W, "ModelVersion",
        ["+ version: str", "+ accuracy: float"],
        ["+ load(path) : ModelPredictor", "+ metrics() : dict"])

    arrow(ax, (46, 88), (52, 88), text="1 → 1", fs=7.6, toff=(0, 2.2))
    arrow(ax, (72, 76), (44, 60.6), text="builds feature vector", fs=7.6, toff=(2, 2.6))
    arrow(ax, (46, 52), (52, 52), text="produces", fs=7.6, toff=(0, 2.2))
    arrow(ax, (26, 38), (26, 31), lw=1.2)
    arrow(ax, (72, 38), (72, 31), lw=1.2)
    arrow(ax, (46, 18), (52, 18), text="persists via", fs=7.6, toff=(0, 2.2), ls="--")
    ax.text(50, 6, "Method signatures are shown in italics; the ScanResult object is returned to the presentation tier.",
            ha="center", fontsize=8.6, color=GREY, style="italic")
    save(fig, "fig03_class.png")


# ---------------------------------------------------------------- 4 activity
def fig_activity():
    fig, ax = canvas(11, 10, ylim=(-6, 106))
    title(ax, "Activity diagram — classifying a submitted URL")
    oval(ax, 50, 92, 14, 5.6, "start")
    rbox(ax, 50, 82, 46, 7.2, "User enters a URL", fc=LIGHT)
    rbox(ax, 50, 71, 46, 7.2, "System validates the input", fc=LIGHT)
    diamond(ax, 50, 58, 27, 11, "valid URL?")
    rbox(ax, 85, 58, 26, 7.4, "Show validation\nmessage", fc="#fdecea", ec=RED, fs=8.4)
    oval(ax, 85, 48, 12, 5.4, "end", fc="#fdecea", ec=RED, fs=8.6)
    rbox(ax, 50, 45, 52, 7.4, "Extract 16 lexical and structural features", fc=WARM, ec=ORANGE)
    rbox(ax, 50, 33, 48, 7.2, "Query trained model (Random Forest)", fc=MINT, ec=GREEN)
    diamond(ax, 50, 20, 27, 11, "model reached?")
    rbox(ax, 85, 20, 26, 7.4, "Show error,\nno verdict", fc="#fdecea", ec=RED, fs=8.4)
    oval(ax, 85, 10, 12, 5.4, "end", fc="#fdecea", ec=RED, fs=8.6)
    rbox(ax, 50, 9, 46, 7.2, "Return verdict, confidence, evidence")
    oval(ax, 50, -1, 14, 5.6, "end")

    arrow(ax, (50, 89.2), (50, 85.6))
    arrow(ax, (50, 78.4), (50, 74.6))
    arrow(ax, (50, 67.4), (50, 63.6))
    arrow(ax, (63.5, 58), (72, 58), text="no", fs=8, toff=(0, 2.0))
    arrow(ax, (85, 54.3), (85, 50.8))
    arrow(ax, (50, 52.5), (50, 48.8), text="yes", fs=8, toff=(3.6, 0))
    arrow(ax, (50, 41.3), (50, 36.7))
    arrow(ax, (50, 29.4), (50, 25.6))
    arrow(ax, (63.5, 20), (72, 20), text="no", fs=8, toff=(0, 2.0))
    arrow(ax, (85, 16.3), (85, 12.8))
    arrow(ax, (50, 14.5), (50, 12.7), text="yes", fs=8, toff=(3.6, 0))
    arrow(ax, (50, 5.4), (50, 1.9))
    save(fig, "fig04_activity.png")


# ---------------------------------------------------------------- 5 sequence
def fig_sequence():
    fig, ax = canvas(12, 8.8)
    title(ax, "Sequence diagram — a successful classification request")
    actors = [(11, "User"), (30, "React UI"), (50, "FastAPI (API)"),
              (70, "FeatureExtractor"), (90, "ModelPredictor")]
    for x, name in actors:
        rbox(ax, x, 88, 17.5, 6.4, name, fc=LIGHT, fs=8.8, bold=True)
        line(ax, [(x, 84.7), (x, 6)], color=GREY, lw=1.0, ls=(0, (4, 3)))

    steps = [(11, 30, 79, "enters a URL, submits", "-", False),
             (30, 50, 71, "POST /api/classify { url }", "-", False),
             (50, 70, 63, "extract(url)", "-", False),
             (70, 50, 55, "dict of 16 features", "--", False),
             (50, 90, 47, "predict(features)", "-", False),
             (90, 50, 39, "verdict, probability, top features", "--", False),
             (50, 50, 31, "write scan_record", "-", True),
             (50, 30, 22, "200 OK  { verdict, confidence, evidence }", "--", False),
             (30, 11, 14, "render verdict panel and evidence", "-", False)]
    for a, b, y, label, ls, is_self in steps:
        if is_self:
            x0, x1 = a + 0.0, a + 7.0
            line(ax, [(x0, y + 2.4), (x1, y + 2.4)], lw=1.2)
            line(ax, [(x1, y + 2.4), (x1, y - 0.2)], lw=1.2)
            arrow(ax, (x1, y - 0.2), (x0 + 0.4, y - 0.2), lw=1.2)
            ax.text(x1 + 1.2, y + 1.1, label, fontsize=8.2, color=NAVY, va="center")
        else:
            arrow(ax, (a, y), (b, y), text=label, fs=8.2, style="-|>", lw=1.2, ls=ls,
                  toff=(0, 2.1))
    ax.text(50, 1.5, "Dashed arrows are return messages.", ha="center",
            fontsize=8.6, color=GREY, style="italic")
    save(fig, "fig05_sequence.png")


# ---------------------------------------------------------------- 6 flowchart
def fig_flowchart():
    fig, ax = canvas(11, 10, ylim=(-4, 106))
    title(ax, "Flowchart of the URL classification algorithm")
    oval(ax, 50, 93, 16, 5.4, "START")
    rbox(ax, 50, 83, 52, 6.8, "Read url string", fc=LIGHT)
    diamond(ax, 50, 71, 30, 10.5, "empty or\nunparseable?", fs=8.4)
    rbox(ax, 85, 71, 24, 7.0, "Return error\n(FR2)", fc="#fdecea", ec=RED, fs=8.4)
    rbox(ax, 50, 59, 52, 6.8, "Parse scheme, host, path, query", fc=LIGHT)
    rbox(ax, 50, 47.5, 62, 7.6, "Compute 16 features: lengths, depth, tokens,\ndigits, hyphens, TLD, encoding, brand", fc=WARM, ec=ORANGE, fs=8.4)
    rbox(ax, 50, 36, 52, 6.8, "Build vector in the fixed feature order", fc=WARM, ec=ORANGE)
    rbox(ax, 50, 25.5, 52, 6.8, "model.predict_proba(vector)", fc=MINT, ec=GREEN)
    diamond(ax, 50, 13.5, 30, 10.5, "p(phishing)\n≥ 0.5?", fs=8.4)
    rbox(ax, 85, 13.5, 24, 7.0, "Verdict =\nPHISHING", fc="#fdecea", ec=RED, fs=8.4)
    rbox(ax, 15, 13.5, 24, 7.0, "Verdict =\nLEGITIMATE", fc=MINT, ec=GREEN, fs=8.4)
    oval(ax, 50, 1, 24, 5.6, "Return result")

    arrow(ax, (50, 90.2), (50, 86.4))
    arrow(ax, (50, 79.6), (50, 76.3))
    arrow(ax, (65, 71), (73, 71), text="yes", fs=8, toff=(0, 2.0))
    arrow(ax, (50, 65.7), (50, 62.4), text="no", fs=8, toff=(3.4, 0))
    arrow(ax, (50, 55.6), (50, 51.4))
    arrow(ax, (50, 43.7), (50, 39.4))
    arrow(ax, (50, 32.6), (50, 28.9))
    arrow(ax, (50, 22.1), (50, 18.8))
    arrow(ax, (65, 13.5), (73, 13.5), text="yes", fs=8, toff=(0, 2.0))
    arrow(ax, (35, 13.5), (27, 13.5), text="no", fs=8, toff=(0, 2.0))
    arrow(ax, (85, 10), (85, 5.2)); arrow(ax, (85, 5.2), (62.5, 2.4))
    arrow(ax, (15, 10), (15, 5.2)); arrow(ax, (15, 5.2), (37.5, 2.4))
    save(fig, "fig06_flowchart.png")


# ---------------------------------------------------------------- 7 ERD
def fig_erd():
    fig, ax = canvas(12, 6.4)

    def entity(cx, top, w, name, fields):
        h = 4.8 + len(fields) * 3.0 + 1.6
        bottom = top - h
        ax.add_patch(FancyBboxPatch((cx - w / 2, bottom), w, h,
                                    boxstyle="round,pad=0.02,rounding_size=0.7",
                                    fc="white", ec=NAVY, lw=1.5, zorder=3))
        ax.add_patch(plt.Rectangle((cx - w / 2, top - 4.8), w, 4.8, fc=NAVY, ec=NAVY, zorder=4))
        ax.text(cx, top - 2.4, name, ha="center", va="center", color="white",
                fontsize=9.8, fontweight="bold", zorder=5)
        ty = top - 7.6
        for tag, fname, ftype in fields:
            color = ORANGE if tag == "PK" else (NAVY if tag == "FK" else "#111827")
            ax.text(cx - w / 2 + 1.5, ty, tag, fontsize=7.8, color=color, zorder=5,
                    fontweight="bold" if tag else "normal")
            ax.text(cx - w / 2 + 6.0, ty, fname, fontsize=8.2, color=color, zorder=5,
                    fontweight="bold" if tag == "PK" else "normal")
            ax.text(cx + w / 2 - 1.5, ty, ftype, fontsize=8.2, color=GREY, zorder=5,
                    ha="right")
            ty -= 3.0
        return bottom, top

    lw_ = 36
    b1, t1 = entity(20, 90, lw_, "MODEL_VERSION", [
        ("PK", "model_id", "INTEGER"),
        ("", "version", "VARCHAR(32)"),
        ("", "algorithm", "VARCHAR(32)"),
        ("", "trained_on", "DATE"),
        ("", "accuracy", "REAL"),
        ("", "artefact_path", "VARCHAR(255)"),
        ("", "n_features", "INTEGER"),
    ])
    b2, t2 = entity(74, 90, lw_, "SCAN_RECORD", [
        ("PK", "scan_id", "INTEGER"),
        ("", "url", "TEXT"),
        ("", "verdict", "VARCHAR(16)"),
        ("", "confidence", "REAL"),
        ("FK", "model_id", "INTEGER"),
        ("", "created_at", "TIMESTAMP"),
    ])

    # relationship: 1 ---- N across the gap between the boxes
    ym = 74
    line(ax, [(38, ym), (56, ym)], lw=1.6)
    ax.text(40.5, ym + 2.4, "1", fontsize=11, color=NAVY, fontweight="bold", ha="center")
    ax.text(50.5, ym + 2.4, "N", fontsize=11, color=NAVY, fontweight="bold", ha="center")
    for dy in (-1.9, 0, 1.9):
        line(ax, [(56, ym), (52.6, ym + dy)], lw=1.4)
    ax.text(47, ym - 3.4, "accounts for", fontsize=8.2, color=GREY, ha="center")

    ax.text(50, 50, "One model version accounts for many scans; each scan is produced by exactly one model version.\n"
                    "PK = primary key    FK = foreign key", ha="center", fontsize=9,
            color=GREY, style="italic", linespacing=1.9)
    save(fig, "fig07_erd.png")


# ---------------------------------------------------------------- 8 pipeline
def fig_pipeline():
    fig, ax = canvas(12, 7.6, ylim=(-6, 106))
    title(ax, "Machine learning pipeline — CRISP-DM stages as implemented")
    stages = [("1. Load dataset\n235,795 rows", LIGHT), ("2. Clean\nremove 425 duplicates", LIGHT),
              ("3. Recode labels\nphishing = 1", LIGHT), ("4. Extract features\n16 per URL", WARM),
              ("5. Stratified split\n80 / 20", WARM), ("6. Train\nRF and LR", MINT),
              ("7. Evaluate\n5 metrics + CM", MINT), ("8. Select and\nserialise", PALE)]
    W, H = 21.5, 17
    row1 = [12.5, 37, 61.5, 86]
    row2 = [86, 61.5, 37, 12.5]
    for (t, c), x in zip(stages[:4], row1):
        rbox(ax, x, 82, W, H, t, fc=c, fs=8.4)
    for (t, c), x in zip(stages[4:], row2):
        rbox(ax, x, 55, W, H, t, fc=c, fs=8.4)
    for i in range(3):
        arrow(ax, (row1[i] + W / 2, 82), (row1[i + 1] - W / 2, 82), lw=1.2)
        arrow(ax, (row2[i] - W / 2, 55), (row2[i + 1] + W / 2, 55), lw=1.2)
    arrow(ax, (86, 73.4), (86, 63.6), lw=1.2)

    rbox(ax, 49, 27, 52, 15, "artefacts written\nmodel_rf.joblib · model_lr.joblib · metrics.json\nconfusion matrices · feature importances",
         fc="#fbfcfd", ec=GREY, fs=8.4)
    line(ax, [(12.5, 46.4), (12.5, 27), (14, 27)], lw=1.2)
    arrow(ax, (14, 27), (22.6, 27), lw=1.2)
    ax.text(50, 6, "The split is fixed at random_state = 42, so every figure in Chapter Four is reproducible.",
            ha="center", fontsize=9, color=GREY, style="italic")
    save(fig, "fig08_pipeline.png")


# ---------------------------------------------------------------- 9 class balance
def fig_class_balance(metrics):
    fig, ax = plt.subplots(figsize=(7.6, 4.0), dpi=200)
    vals = [metrics["dataset"]["legitimate"], metrics["dataset"]["phishing"]]
    bars = ax.barh(["Legitimate", "Phishing"], vals, color=[NAVY, ORANGE], height=0.5)
    for b, v in zip(bars, vals):
        ax.text(v + 2500, b.get_y() + b.get_height() / 2,
                f"{v:,}  ({v / sum(vals) * 100:.1f}%)", va="center", fontsize=10)
    ax.set_xlim(0, max(vals) * 1.32)
    ax.set_xlabel("URLs in the cleaned dataset (235,370 total)", fontsize=10)
    ax.set_title("Class distribution of the PhiUSIIL dataset after preprocessing",
                 fontsize=11, color=NAVY, fontweight="bold", pad=12)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=10)
    fig.tight_layout()
    save(fig, "fig09_class_balance.png")


# ---------------------------------------------------------------- 10 importances
def fig_importance(path):
    import pandas as pd
    df = pd.read_csv(path).sort_values("rf_importance")
    fig, ax = plt.subplots(figsize=(8.4, 5.6), dpi=200)
    ax.barh(df["feature"], df["rf_importance"], color=ORANGE, height=0.6)
    for i, v in enumerate(df["rf_importance"]):
        ax.text(v + 0.002, i, f"{v:.3f}", va="center", fontsize=8.5)
    ax.set_xlabel("Mean decrease in impurity", fontsize=10)
    ax.set_title("Feature importance of the deployed Random Forest model",
                 fontsize=11, color=NAVY, fontweight="bold", pad=12)
    ax.set_xlim(0, df["rf_importance"].max() * 1.2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=9)
    fig.tight_layout()
    save(fig, "fig10_feature_importance.png")


# ---------------------------------------------------------------- 11 metrics
def fig_metrics(metrics):
    import numpy as np
    r = metrics["results"]
    keys = ["accuracy", "precision", "recall", "f1"]
    labels = ["Accuracy", "Precision", "Recall", "F1-score"]
    rf = [r["random_forest"][k] * 100 for k in keys]
    lr = [r["logistic_regression"][k] * 100 for k in keys]
    x = np.arange(len(labels)); w = 0.36
    fig, ax = plt.subplots(figsize=(8.4, 4.6), dpi=200)
    for off, vals, lab, col in [(-w / 2, rf, "Random Forest", NAVY), (w / 2, lr, "Logistic Regression", ORANGE)]:
        b = ax.bar(x + off, vals, w, label=lab, color=col)
        for bar in b:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                    f"{bar.get_height():.2f}", ha="center", fontsize=8.4)
    ax.set_xticks(x, labels, fontsize=10)
    ax.set_ylim(95, 100.7)
    ax.set_ylabel("Score (%)", fontsize=10)
    ax.set_title("Held-out test performance of both models (n = 47,074)",
                 fontsize=11, color=NAVY, fontweight="bold", pad=34)
    ax.legend(frameon=False, fontsize=9.5, ncol=2, loc="lower center",
              bbox_to_anchor=(0.5, 1.005))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    save(fig, "fig11_metrics.png")


# ---------------------------------------------------------------- 12 generalisation
def fig_generalisation(gen):
    import numpy as np
    m = gen["models"]
    labels = ["Phishing\ncaught", "Legitimate\ncleared", "Overall\naccuracy"]
    rf = [m["random_forest"]["recall"] * 100, m["random_forest"]["tn"] / 500 * 100,
          m["random_forest"]["accuracy"] * 100]
    lr = [m["logistic_regression"]["recall"] * 100, m["logistic_regression"]["tn"] / 500 * 100,
          m["logistic_regression"]["accuracy"] * 100]
    x = np.arange(len(labels)); w = 0.36
    fig, ax = plt.subplots(figsize=(8.4, 4.6), dpi=200)
    for off, vals, lab, col in [(-w / 2, rf, "Random Forest", NAVY), (w / 2, lr, "Logistic Regression", ORANGE)]:
        b = ax.bar(x + off, vals, w, label=lab, color=col)
        for bar in b:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.6,
                    f"{bar.get_height():.1f}%", ha="center", fontsize=8.6)
    ax.set_xticks(x, labels, fontsize=10)
    ax.set_ylim(0, 108)
    ax.set_ylabel("Percentage (%)", fontsize=10)
    ax.set_title("Generalisation test on 1,000 unseen URLs (bare domains only)",
                 fontsize=11, color=NAVY, fontweight="bold", pad=34)
    ax.legend(frameon=False, fontsize=9.5, ncol=2, loc="lower center",
              bbox_to_anchor=(0.5, 1.005))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    save(fig, "fig12_generalisation.png")


# ---------------------------------------------------------------- 13 confusion matrices
def fig_confusion(metrics):
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("pg", ["#ffffff", "#8fa8c8", NAVY])
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.3), dpi=200)
    for ax, key, title in [(axes[0], "random_forest", "Random Forest"),
                           (axes[1], "logistic_regression", "Logistic Regression")]:
        r = metrics["results"][key]
        m = np.array([[r["tn"], r["fp"]], [r["fn"], r["tp"]]])
        ax.imshow(m, cmap=cmap)
        for i in range(2):
            for j in range(2):
                ax.text(j, i, f"{m[i, j]:,}", ha="center", va="center", fontsize=13,
                        color="white" if m[i, j] > m.max() / 2 else "#111827",
                        fontweight="bold")
        ax.set_xticks([0, 1], ["Legitimate", "Phishing"], fontsize=9.5)
        ax.set_yticks([0, 1], ["Legitimate", "Phishing"], fontsize=9.5)
        ax.set_xlabel("Predicted class", fontsize=9.5)
        ax.set_ylabel("Actual class", fontsize=9.5)
        ax.set_title(title, fontsize=10.5, color=NAVY, fontweight="bold")
    fig.suptitle("Confusion matrices on the 47,074 held-out URLs", fontsize=11.5,
                 color=NAVY, fontweight="bold", y=0.99)
    fig.tight_layout()
    save(fig, "fig13_confusion.png")


if __name__ == "__main__":
    metrics = json.load(open(os.path.join(HERE, "artifacts", "metrics.json")))
    gen = json.load(open(os.path.join(HERE, "artifacts", "generalisation.json")))
    fig_use_case(); fig_architecture(); fig_class(); fig_activity()
    fig_sequence(); fig_flowchart(); fig_erd(); fig_pipeline()
    fig_class_balance(metrics)
    fig_importance(os.path.join(HERE, "artifacts", "feature_importance.csv"))
    fig_metrics(metrics); fig_generalisation(gen); fig_confusion(metrics)
    print("all diagrams written to", OUT)