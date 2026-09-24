#!/usr/bin/env python3
"""unplotit MCP server (experimental).

Contact: unplotit.noreply@gmail.com

Exposes chart-to-CSV extraction as tools any MCP-capable AI assistant
(Muse, Claude Desktop, etc.) can call mid-conversation:

    user:  "get me the data behind this chart"
    agent: extract_chart(image_base64=..., x0=..., ...) -> CSV

Run locally over stdio:  python server.py
"""
import base64

from mcp.server.fastmcp import FastMCP

from core import extract_monthly, rows_to_csv

mcp = FastMCP("unplotit")


@mcp.tool()
def extract_chart(image_base64: str, x0: int, x1: int, yscan: int, ymax: int,
                  slope: float, intercept: float, d0: str, d1: str,
                  line_color: str = "auto") -> str:
    """Extract monthly time-series data from a chart image and return it as CSV.

    The image is scanned pixel-by-pixel for the chart line, so this works on
    screenshots and photos of charts where no underlying data file exists.

    Calibration (call calibration_guide first if unsure how to derive these):
      image_base64: PNG/JPEG chart image, base64-encoded
      x0, x1:       left/right pixel bounds of the plot area (the data region)
      yscan, ymax:  pixel rows scanned for the line; rows above yscan are
                    ignored (use to skip a legend swatch inside the plot)
      slope, intercept: value = slope * y_pixel + intercept, derived from two
                    y-axis labels: slope = (v2 - v1) / (y2 - y1),
                    intercept = v1 - slope * y1
      d0, d1:       'YYYY-MM-DD' of the first/last month sampled
      line_color:   'auto' (any saturated line colour) or hex RGB e.g. 'ff0000'

    Returns CSV text with 'date,value' header, one row per month.
    Values are digitized estimates, not official data.
    """
    raw = base64.b64decode(image_base64)
    rows = extract_monthly(raw, x0=x0, x1=x1, yscan=yscan, ymax=ymax,
                           slope=slope, intercept=intercept,
                           d0=d0, d1=d1, line_color=line_color)
    return rows_to_csv(rows)


@mcp.tool()
def calibration_guide() -> str:
    """How to derive the calibration numbers extract_chart needs from a chart image.

    Call this before extract_chart if you are unsure how to measure x0, x1,
    yscan, ymax, slope or intercept.
    """
    return """\
CALIBRATING A CHART FOR extract_chart (all pixel coords: x right, y DOWN from top-left)

1. x0, x1 — the plot area's left and right edges: the x-range where the data
   line actually lives (inside the axes, not including y-axis labels).

2. yscan, ymax — the vertical scan band. ymax = the pixel row of the lowest
   usable plot point (near the x-axis). yscan = a row BELOW any legend colour
   swatch or title sitting inside the plot, but ABOVE the data line's highest
   point. When in doubt: yscan = just under the legend, ymax = just above the
   x-axis labels.

3. slope, intercept — pick TWO y-axis grid labels with known values and pixel
   rows, e.g. label A: value v1 at pixel row y1; label B: value v2 at row y2.
   slope = (v2 - v1) / (y2 - y1)        (negative: y grows downward)
   intercept = v1 - slope * y1
   Check: value = slope * y_pixel + intercept should reproduce both labels.

4. d0, d1 — 'YYYY-MM-DD' for the first and last month the x-axis covers.
   Sampling is monthly; one CSV row per month between d0 and d1 inclusive.

5. line_color — 'auto' works for any saturated line (blue, red, green...).
   Pass an explicit hex like 'ff0000' only if auto picks up the wrong line.

TIP: you can read pixel coordinates from any image viewer/editor, or ask the
user for the two y-axis labels and the plot bounds if you cannot see the image.
"""


if __name__ == "__main__":
    mcp.run()
