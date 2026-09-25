#!/usr/bin/env python3
"""Unplotit.com chart digitizer generator.
Contact: unplotit.noreply@gmail.com

Given a time-series chart image plus axis calibration, this script:
  1. extracts monthly values by scanning the chart line's pixels,
  2. writes a CSV of the extracted data,
  3. writes an overlay PNG (chart + red dots) for accuracy checking,
  4. builds a self-contained Unplotit.com HTML page (drag-to-correct dots,
     capture peaks & troughs, daily/weekly/monthly/yearly resampling, CSV download).

Calibration (all in image pixels unless noted):
  --x0 --x1       left/right pixel bounds of the plot area (data region)
  --ymin --ymax   top/bottom pixel bounds usable for values
  --yscan         pixels with y < yscan are ignored when reading the line
                 (use to exclude a legend swatch sitting inside the plot)
  --slope --intercept   value = slope * y_pixel + intercept.
                 Derive from two y-axis grid labels:
                   slope = (v2 - v1) / (y2 - y1), intercept = v1 - slope * y1
  --d0 --d1       date range as YYYY-MM-DD (first/last month sampled)
  --name          chart title shown in the page header
  --prefix        filename prefix for outputs

Example:
  generate.py --image fred.png --x0 94 --x1 1298 --ymin 200 --ymax 612 --yscan 250 \
      --slope -0.04861 --intercept 24.477 --d0 1996-06-01 --d1 2026-08-01 \
      --name "Producer Price Index by Industry: Advertising Agencies (FRED)" \
      --prefix ppi_advertising_agencies_ --outdir ./ppi
"""
import argparse, base64, csv, os
from datetime import date

from PIL import Image, ImageDraw


def parse_args():
    p = argparse.ArgumentParser(description="Unplotit.com chart digitizer generator")
    p.add_argument("--image", required=True)
    p.add_argument("--x0", type=int, required=True)
    p.add_argument("--x1", type=int, required=True)
    p.add_argument("--ymin", type=int, required=True)
    p.add_argument("--ymax", type=int, required=True)
    p.add_argument("--yscan", type=int, required=True)
    p.add_argument("--slope", type=float, required=True)
    p.add_argument("--intercept", type=float, required=True)
    p.add_argument("--d0", required=True, help="YYYY-MM-DD")
    p.add_argument("--d1", required=True, help="YYYY-MM-DD")
    p.add_argument("--name", required=True)
    p.add_argument("--prefix", required=True)
    p.add_argument("--outdir", required=True)
    p.add_argument("--line-color", default="auto",
                   help="'auto' = any saturated line color; or hex RGB e.g. ff0000")
    return p.parse_args()


def months_between(d0, d1):
    return (d1.year - d0.year) * 12 + (d1.month - d0.month) + 1


def add_months(d, k):
    m = d.month - 1 + k
    return date(d.year + m // 12, m % 12 + 1, 1)


def main():
    a = parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    img = Image.open(a.image).convert("RGB")
    W, H = img.size
    px = img.load()
    lc = a.line_color.lstrip("#")
    if lc == "auto":
        lmode = "auto"; LR = LG = LB = 0
    else:
        lmode = "color"; LR, LG, LB = int(lc[0:2], 16), int(lc[2:4], 16), int(lc[4:6], 16)

    def is_line(x, y):
        r, g, b = px[x, y]
        if lmode == "auto":
            mx = max(r, g, b); mn = min(r, g, b)
            return (mx - mn) > 70 and mx >= 60 and mn <= 215
        return (r - LR) ** 2 + (g - LG) ** 2 + (b - LB) ** 2 < 10000

    # Per-column median of line pixels (legend band excluded via yscan).
    # Columns that are nearly all line pixels are vertical axes/gridlines
    # drawn in the line colour: exclude them so they can't pollute the median.
    ncols = a.x1 - a.x0 + 1
    yrange = a.ymax - a.yscan + 1
    # First pass: find axis columns (nearly full-height runs of line-coloured pixels).
    axis_cols = set()
    for xi in range(ncols):
        x = a.x0 + xi
        cnt = sum(1 for y in range(a.yscan, a.ymax + 1) if is_line(x, y))
        if cnt > 0.8 * yrange:
            axis_cols.add(xi)
    # Exclude the axis column and a few neighbours each side (axis tick marks
    # live there and outnumber the data-line pixels); gaps fill from neighbours.
    dead = set()
    for xi in axis_cols:
        dead.update(range(max(0, xi - 3), min(ncols, xi + 4)))
    med = []
    for xi in range(ncols):
        if xi in dead:
            med.append(None)
            continue
        x = a.x0 + xi
        ys = [y for y in range(a.yscan, a.ymax + 1) if is_line(x, y)]
        ys.sort()
        med.append(ys[len(ys) // 2] if ys else None)
    # Fill gaps from neighbours.
    last = None
    for i in range(ncols):
        if med[i] is None:
            med[i] = last
        else:
            last = med[i]
    last = None
    for i in range(ncols - 1, -1, -1):
        if med[i] is None:
            med[i] = last
        else:
            last = med[i]

    def value_at(y):
        return round(a.slope * y + a.intercept, 2)

    d0 = date(*map(int, a.d0.split("-")))
    d1 = date(*map(int, a.d1.split("-")))
    n = months_between(d0, d1)
    rows = []
    for i in range(n):
        x = round(a.x0 + i / (n - 1) * (a.x1 - a.x0))
        col_ys = [med[max(0, min(ncols - 1, x + k - a.x0))] for k in range(-2, 3)]
        col_ys = sorted(y for y in col_ys if y is not None)
        y = col_ys[len(col_ys) // 2]
        rows.append((add_months(d0, i).isoformat(), value_at(y)))

    # --- Dot QA: verify every dot sits on the line, snap it if not ---------
    # Re-measure the line centre at each sample's exact x-column with a
    # speck/tick-rejecting estimator (largest 4px-connected cluster of line
    # pixels). The windowed median above can sit 2-4px off on steep segments
    # or beside axis tick marks. Dots >2.5px off are snapped to the measured
    # centre before anything is shown to the user. A few snaps are normal;
    # many (>5) signal a systematic problem (wrong line colour, bad yscan,
    # miscalibrated axes) that needs fixing before delivery.
    def line_center_at(xi):
        x = a.x0 + xi
        ys = [y for y in range(a.yscan, a.ymax + 1) if is_line(x, y)]
        if not ys:
            return None
        ys.sort()
        clusters, cur = [], [ys[0]]
        for y in ys[1:]:
            if y - cur[-1] <= 4:
                cur.append(y)
            else:
                clusters.append(cur)
                cur = [y]
        clusters.append(cur)
        big = max(clusters, key=len)
        return sum(big) / len(big)

    snapped = 0
    for i, (dstr, v) in enumerate(rows):
        xi = round(i / (n - 1) * (a.x1 - a.x0))
        if xi in dead:
            continue  # under an axis/tick column: not verifiable, keep sampled value
        c = line_center_at(xi)
        if c is None:
            continue
        if abs(c - (v - a.intercept) / a.slope) > 2.5:
            rows[i] = (dstr, value_at(c))
            snapped += 1
    print(f"dot QA: checked {n} dots, snapped {snapped} onto the line")
    if snapped > 5:
        print("WARNING: >5 dots were off the line - review calibration/line colour before delivering.")

    csv_path = os.path.join(a.outdir, f"{a.prefix}monthly.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "value"])
        w.writerows(rows)

    # Overlay PNG for accuracy checking.
    ov = img.copy()
    dr = ImageDraw.Draw(ov)
    for i, (_, v) in enumerate(rows):
        x = a.x0 + i / (n - 1) * (a.x1 - a.x0)
        y = (v - a.intercept) / a.slope
        dr.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(255, 45, 45), outline=(255, 255, 255))
    ov.save(os.path.join(a.outdir, f"{a.prefix}overlay.png"))

    # Self-contained HTML digitizer page.
    tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "template.html")).read()
    img_b64 = base64.b64encode(open(a.image, "rb").read()).decode()
    import json
    data_json = json.dumps([{"date": d, "value": v} for d, v in rows])
    d0y, d0m, d0d = d0.year, d0.month - 1, d0.day
    d1y, d1m = d1.year, d1.month - 1
    page = tpl
    for key, val in {
        "__IMG_B64__": img_b64,
        "__DATA_JSON__": data_json,
        "__SLOPE__": repr(a.slope),
        "__INTERCEPT__": repr(a.intercept),
        "__X0__": str(a.x0), "__X1__": str(a.x1),
        "__W__": str(W), "__H__": str(H),
        "__YMIN__": str(a.ymin), "__YMAX__": str(a.ymax),
        "__YSCAN__": str(a.yscan),
        "__D0Y__": str(d0y), "__D0M0__": str(d0m),
        "__D1Y__": str(d1y), "__D1M0__": str(d1m),
        "__Y0__": str(d0.year), "__Y1__": str(d1.year),
        "__CSV_PREFIX__": a.prefix,
        "__CHART_NAME__": a.name,
        "__LMODE__": lmode,
        "__LR__": str(LR), "__LG__": str(LG), "__LB__": str(LB),
    }.items():
        page = page.replace(key, val)
    html_path = os.path.join(a.outdir, f"{a.prefix}digitizer.html")
    open(html_path, "w").write(page)

    vals = [v for _, v in rows]
    print(f"months: {n}  min: {min(vals)}  max: {max(vals)}")
    print("wrote:", csv_path)
    print("wrote:", os.path.join(a.outdir, f"{a.prefix}overlay.png"))
    print("wrote:", html_path)


if __name__ == "__main__":
    main()
