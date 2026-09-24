"""unplotit core: extract a time-series from a chart image's pixels.

PIL-only. The algorithm mirrors ~/workspace/skills/unplotit/generate.py:
any saturated line colour is auto-detected (or match an explicit hex),
near-full-height columns in the line colour are treated as axes and
excluded, then each column's median line-pixel is converted to a value
via the caller-supplied axis calibration.
"""
import io
from datetime import date

from PIL import Image


def _parse_line_color(line_color):
    lc = line_color.lstrip("#").lower()
    if lc == "auto":
        return "auto", (0, 0, 0)
    return "color", (int(lc[0:2], 16), int(lc[2:4], 16), int(lc[4:6], 16))


def _months_between(d0, d1):
    return (d1.year - d0.year) * 12 + (d1.month - d0.month) + 1


def _add_months(d, k):
    m = d.month - 1 + k
    return date(d.year + m // 12, m % 12 + 1, 1)


def extract_monthly(image_bytes, *, x0, x1, yscan, ymax,
                    slope, intercept, d0, d1, line_color="auto"):
    """Scan the chart line and return [(iso_date, value), ...], monthly.

    Calibration:
      x0, x1      left/right pixel bounds of the plot area (data region)
      yscan, ymax pixel rows scanned for the line (rows above yscan are
                  ignored, e.g. to skip a legend swatch inside the plot)
      slope, intercept  value = slope * y_pixel + intercept. Derive from
                  two y-axis labels: slope = (v2 - v1) / (y2 - y1),
                  intercept = v1 - slope * y1
      d0, d1      'YYYY-MM-DD' first/last month sampled
      line_color  'auto' or hex RGB like 'ff0000'
    """
    mode, (lr, lg, lb) = _parse_line_color(line_color)
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    px = img.load()

    def is_line(x, y):
        r, g, b = px[x, y]
        if mode == "auto":
            mx = max(r, g, b)
            mn = min(r, g, b)
            return (mx - mn) > 70 and mx >= 60 and mn <= 215
        return (r - lr) ** 2 + (g - lg) ** 2 + (b - lb) ** 2 < 10000

    ncols = x1 - x0 + 1
    yrange = ymax - yscan + 1
    # Pass 1: axis columns (near-full-height runs of line-coloured pixels).
    dead = set()
    for xi in range(ncols):
        x = x0 + xi
        cnt = sum(1 for y in range(yscan, ymax + 1) if is_line(x, y))
        if cnt > 0.8 * yrange:
            dead.update(range(max(0, xi - 3), min(ncols, xi + 4)))
    # Pass 2: per-column median of line pixels.
    med = []
    for xi in range(ncols):
        if xi in dead:
            med.append(None)
            continue
        x = x0 + xi
        ys = [y for y in range(yscan, ymax + 1) if is_line(x, y)]
        ys.sort()
        med.append(ys[len(ys) // 2] if ys else None)
    # Fill gaps from neighbours (both directions).
    last = None
    for i in range(ncols):
        med[i] = med[i] if med[i] is not None else last
        last = med[i] if med[i] is not None else last
    last = None
    for i in range(ncols - 1, -1, -1):
        med[i] = med[i] if med[i] is not None else last
        last = med[i] if med[i] is not None else last

    start = date(*map(int, d0.split("-")))
    end = date(*map(int, d1.split("-")))
    n = _months_between(start, end)
    rows = []
    for i in range(n):
        x = round(x0 + i / max(n - 1, 1) * (x1 - x0))
        col = sorted(med[max(0, min(ncols - 1, x + k - x0))]
                     for k in range(-2, 3))
        col = [y for y in col if y is not None]
        y = col[len(col) // 2]
        rows.append((_add_months(start, i).isoformat(),
                     round(slope * y + intercept, 2)))
    return rows


def rows_to_csv(rows):
    return "date,value\n" + "\n".join(f"{d},{v:.2f}" for d, v in rows) + "\n"
