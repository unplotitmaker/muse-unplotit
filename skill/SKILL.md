# Unplotit

Digitize a chart/graph image into CSV data when no raw data is available. Use this skill when the user shares (or points to) a chart image and wants the underlying numbers extracted, corrected, or resampled.

## What it produces

For one chart image, `generate.py` builds:
1. **`<prefix>monthly.csv`** — monthly values extracted from the chart line's pixels.
2. **`<prefix>overlay.png`** — the original chart with red dots on every extracted point, for visual accuracy checking.
3. **`<prefix>digitizer.html`** — a self-contained Unplotit.com page: the chart with draggable dots (vertical drag corrects a value, dots turn orange), a **Capture peaks & troughs** button that snaps the nearest dot to each local high/low found by pixel scan, **Daily/Weekly/Monthly/Yearly** resampling buttons, and one-click corrected-CSV download. No server needed; open the file in any browser.

## Workflow

1. **Get the chart image.** The user uploads it (chat attachment). Save it where the script can read it.
2. **Calibrate by inspecting the image** (read it with the image viewer):
   - `x0, x1`: left/right pixel bounds of the plot's data region.
   - `ymin, ymax`: top/bottom pixel bounds of the data region.
   - `yscan`: ignore pixels above this y (use it to exclude a legend swatch or title sitting inside the plot area; the true line must never go above it — verify against the line's highest tip).
   - `slope, intercept` from two y-axis grid labels: `slope = (v2-v1)/(y2-y1)`, `intercept = v1 - slope*y1`. Note: y grows downward, so slope is negative when up means larger.
   - `d0, d1`: first/last month on the x-axis (`YYYY-MM-DD`, day `01`).
   - Sanity-check calibration against 2–3 known points before trusting the output.
3. **Run `generate.py`** with those parameters plus `--name` and `--prefix`.
4. **Verify with the overlay PNG**: open it, check dots sit on the line, especially at peaks, troughs, and steep segments. Sharp tips narrower than a month get under-read by monthly sampling — the page's **Capture peaks & troughs** button fixes those (it refines tip values from unsmoothed pixels).
5. **Hand the user the HTML page** so they can drag-correct any dot and download the corrected CSV.

## Accuracy

State measured accuracy, never asserted accuracy. The overlay is the check. Measured 2026-09-24 on a wild rainbow line chart (NASA GISS global temperature, realclimate.org): extracted monthly series vs the underlying GISTEMP dataset's 12-month running mean gives Pearson r=0.94 and residual MAE 0.10°C after removing a +0.26°C baseline offset (the 2017 chart predates current GISTEMP revisions). Known limits:
- Monthly sampling under-reads spikes narrower than one month (use peak capture).
- Steep segments: a dot's x-position may sit on a flank; dragging corrects it.
- If the user wants a scored accuracy number, compare against a manual transcription of a sample of points.

## Notes

- Line detection defaults to `auto`: any saturated line colour on a light or dark background (handles blue, red, rainbow-gradient lines; black/gray gridlines and text are excluded). Override with `--line-color <hex>` (e.g. `ff0000`) if a saturated gridline or area fill confuses it.
- A vertical axis or gridline drawn in the line colour is auto-detected and excluded (plus a 3px margin for its tick marks); those columns gap-fill from neighbours.
- Assumes a time-series chart with a linear date axis. Log axes or categorical axes need custom handling — say so rather than fudging it.
- Validated 2026-09-24 on four wild charts: FRED-style PPI (blue/white), NASA GISS temperature (rainbow/white), S&P 500 1950–2013 (steel-blue/white grid), S&P 500 price/revenue 1995–2020 (light-blue/dark background, right-hand y-axis).
- Do not switch the user to a different digitizer without their approval.
