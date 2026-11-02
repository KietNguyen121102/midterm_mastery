#!/usr/bin/env python3
"""Build a 16:9 PDF of the midterm talk.

    python3 experiments/make_slides_pdf.py
    # writes PRESENTATION.pdf
"""
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "PRESENTATION.pdf"
FIG = ROOT / "results" / "aws" / "figures"

# 16:9 at 1920x1080 pt-equivalent: 13.333 x 7.5 in
W, H = 960, 540
NAVY = HexColor("#1e3a5f")
BLUE = HexColor("#2b6cb0")
INK = HexColor("#1a202c")
MUTED = HexColor("#4a5568")
LINE = HexColor("#cbd5e0")
BG = HexColor("#f7fafc")
HEAD = HexColor("#eef2f6")
NOTE = HexColor("#718096")


def page(c: canvas.Canvas) -> None:
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.rect(0, H - 6, W, 6, fill=1, stroke=0)
    c.setFillColor(LINE)
    c.rect(0, 0, W, 4, fill=1, stroke=0)


def kicker(c: canvas.Canvas, text: str) -> None:
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, H - 36, text.upper())


def title(c: canvas.Canvas, text: str, y: float = H - 72, size: int = 22) -> float:
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", size)
    for line in wrap(text, 70 if size >= 20 else 78):
        c.drawString(40, y, line)
        y -= size + 4
    return y


def body(c: canvas.Canvas, text: str, x: float, y: float, width_chars: int = 52, size: int = 11) -> float:
    c.setFillColor(MUTED)
    c.setFont("Helvetica", size)
    for line in wrap(text, width_chars):
        c.drawString(x, y, line)
        y -= size + 4
    return y


def bullets(c: canvas.Canvas, items: list[str], x: float, y: float, width_chars: int = 48) -> float:
    c.setFont("Helvetica", 11)
    for item in items:
        c.setFillColor(BLUE)
        c.circle(x + 3, y + 3, 2.2, fill=1, stroke=0)
        c.setFillColor(MUTED)
        lines = wrap(item, width_chars)
        c.drawString(x + 12, y, lines[0])
        y -= 15
        for extra in lines[1:]:
            c.drawString(x + 12, y, extra)
            y -= 15
        y -= 4
    return y


def wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = word if not cur else f"{cur} {word}"
        if len(trial) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [""]


def footer(c: canvas.Canvas, n: int, total: int, note: str) -> None:
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    c.line(40, 28, W - 40, 28)
    c.setFillColor(NOTE)
    c.setFont("Helvetica", 8)
    c.drawString(40, 14, note)
    c.drawRightString(W - 40, 14, f"{n} / {total}")


def figure(c: canvas.Canvas, path: Path, x: float, y: float, w: float, h: float) -> None:
    c.setStrokeColor(LINE)
    c.setFillColor(white)
    c.setLineWidth(0.8)
    c.roundRect(x - 4, y - 4, w + 8, h + 8, 4, fill=1, stroke=1)
    c.drawImage(ImageReader(str(path)), x, y, width=w, height=h, preserveAspectRatio=True, anchor="c", mask="auto")


def slide_setup(c: canvas.Canvas) -> None:
    page(c)
    kicker(c, "CS6650 midterm  ·  AWS us-west-2  ·  file-transfer-playservice")
    title(c, "Three experiments on a lossy UDP file service", size=24)
    body(c, "Client → ALB → gateway (HTTP, MAX_INFLIGHT=4) → NLB → backend (UDP, WORKERS=8) → S3.  64-byte chunks, 4 MiB cap.", 40, H - 108, 110, 11)

    headers = ["", "1. File size", "2. Send loss", "3. Load / scale"]
    rows = [
        ["HW tool", "HW4 sweep", "HW4 sweep", "HW5/6 Locust + watch"],
        ["Fixed", "SEND_LOSS=0, retries 5/5", "64 KiB (1024 chunks)", "64 KiB, 25 users, 8 min"],
        ["Vary", "4 KiB → 4 MiB", "SEND_LOSS 0 then 10", "concurrency; two scaler metrics"],
    ]
    col_w = [90, 230, 250, 270]
    x0, y0, row_h = 40, H - 160, 28
    x = x0
    c.setFillColor(HEAD)
    c.rect(x0, y0 - row_h + 8, sum(col_w), row_h, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    for i, h in enumerate(headers):
        c.drawString(x + 8, y0 - 10, h)
        x += col_w[i]
    c.setFont("Helvetica", 9)
    for r, row in enumerate(rows):
        y = y0 - (r + 2) * row_h + 8
        if r % 2 == 1:
            c.setFillColor(HexColor("#f1f5f9"))
            c.rect(x0, y - 6, sum(col_w), row_h, fill=1, stroke=0)
        x = x0
        for i, cell in enumerate(row):
            c.setFillColor(INK if i == 0 else MUTED)
            c.setFont("Helvetica-Bold" if i == 0 else "Helvetica", 9)
            c.drawString(x + 8, y + 4, cell)
            x += col_w[i]
    c.setStrokeColor(LINE)
    c.rect(x0, y0 - 4 * row_h + 8, sum(col_w), 4 * row_h, fill=0, stroke=1)

    body(c, "Gateway scales on ALBRequestCountPerTarget = 40.  Backend scales on CPU = 40%.  Min 2 / max 4 tasks each.", 40, 56, 110, 10)
    footer(c, 1, 5, "Defaults kept: 5 OPEN, 5 RETY, 2 s quiet timeout.")
    c.showPage()


def slide_size(c: canvas.Canvas) -> None:
    page(c)
    kicker(c, "Experiment 1  ·  file size on AWS")
    y = title(c, "On the NLB path, size kills success, not just latency", size=18)
    figure(c, FIG / "size.png", 28, 58, 580, 350)
    bullets(c, [
        "4 KiB (64 chunks): 4/5 ok, ~4 s",
        "64 KiB (1024): 4/5 ok, ~9 s",
        "256 KiB (4096): 1/5 ok",
        "1 MiB and 4 MiB: 0/5 and 0/2",
        "Localhost: every size finished in 2.0–2.3 s. The 2 s quiet timeout is the floor.",
        "AWS blasts chunks through a UDP NLB. Tail-drops leave missing ranges; RETY bursts overflow the 32-deep worker queue.",
    ], 610, H - 120, 42)
    footer(c, 2, 5, "HW4-style sweep. SEND_LOSS=0. Extra seconds are retry rounds, not send time.")
    c.showPage()


def slide_loss(c: canvas.Canvas) -> None:
    page(c)
    kicker(c, "Experiment 2  ·  send loss")
    title(c, "AWS is already lossy. +10% send loss makes 64 KiB slower, not much rarer.", size=16)
    figure(c, FIG / "loss.png", 28, 70, 560, 330)
    bullets(c, [
        "64 KiB @ 0%: 80% ok, median 8.9 s",
        "64 KiB @ 10%: 75% ok, median 11.2 s",
        "4 KiB @ 10%: 8/8 ok, 4.3–6.4 s",
        "Locally, 10% finished every 64 KiB file (10–12 s) and 20% collapsed to 1/8 at exactly 12 s.",
        "On AWS, 1024-chunk files already sit near the 5-round budget. Small files still have slack.",
    ], 600, H - 120, 44)
    footer(c, 3, 5, "Backend logs: Overloaded: dropped incoming datagram, plus consecutive missing-chunk ranges.")
    c.showPage()


def slide_load(c: canvas.Canvas) -> None:
    page(c)
    kicker(c, "Experiment 3  ·  Locust + two scalers")
    title(c, "Gateway scaled 2 → 4. Backend never moved.", size=18)
    figure(c, FIG / "load.png", 28, 58, 580, 350)
    bullets(c, [
        "25 users, 8 min, 64 KiB: 1764 req, 51% fail",
        "789 × 503 busy, 105 × 504 timeout",
        "Gateway desired 4 at 18:54, healthy 4 at 18:55",
        "Backend stayed at 2. CPU avg 22–39% (target 40). One task hit 76% max; target tracking uses the average.",
        "ALB can scale on requests/target. NLB cannot, so the backend only watches CPU.",
    ], 620, H - 118, 40)
    footer(c, 4, 5, "HW6 Locust FastHttpUser + watch of both services.")
    c.showPage()


def slide_takeaways(c: canvas.Canvas) -> None:
    page(c)
    kicker(c, "What the service actually is")
    title(c, "Three limits, confirmed on AWS", size=22)
    items = [
        ("1. Burst + 2 s completion",
         "Localhost hides it — everything is ~2 s. On AWS, 256 KiB+ transfers mostly 504 because a blast of 64-byte datagrams is dropped and five RETY rounds cannot catch up."),
        ("2. Retry turns into overload",
         "Missing ranges become RETY floods. The backend drops them once 32 jobs are queued. Extra SEND_LOSS mainly adds more 2 s quiet-timeout rounds."),
        ("3. The two scalers do not agree",
         "The gateway feels request pile-up and scales. The backend, busy enough to 504 files, still averages under 40% CPU and stays at min=2."),
    ]
    y = H - 130
    for head, text in items:
        c.setFillColor(NAVY)
        c.roundRect(40, y - 52, W - 80, 78, 6, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(56, y + 6, head)
        c.setFont("Helvetica", 11)
        ty = y - 12
        for line in wrap(text, 108):
            c.drawString(56, ty, line)
            ty -= 14
        y -= 96
    footer(c, 5, 5, "Talk ~4:30. Tear down when finished: scripts/destroy.sh --yes")
    c.showPage()


def main() -> None:
    for name in ("size.png", "loss.png", "load.png"):
        if not (FIG / name).exists():
            raise SystemExit(f"missing figure {FIG / name}")
    c = canvas.Canvas(str(OUT), pagesize=(W, H))
    c.setTitle("File-transfer service — three experiments")
    c.setAuthor("CS6650 midterm")
    slide_setup(c)
    slide_size(c)
    slide_loss(c)
    slide_load(c)
    slide_takeaways(c)
    c.save()
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
