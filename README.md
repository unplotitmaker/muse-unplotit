# aiagent.unplotit

Chart-image → CSV extraction, built for **Muse**.

## What this is

When a user asks Muse for time-series data and no downloadable source exists —
but a chart of the data does — Muse extracts digitized estimates straight from
the chart image. This repo holds the code that makes that work.

| Directory | What | Status |
|---|---|---|
| `skill/` | Drop-in Muse skill (Python extractor + correction-page generator) | **Supported** — used in production with Muse |
| `web/` | Single-file browser tool (upload/paste chart → calibrate → CSV) | Supported fallback |
| `mcp/` | MCP server (`extract_chart`, `calibration_guide` tools) | **Experimental** — protocol handshake tested only; not validated inside any non-Muse assistant. Other-assistant support is planned later. |

Values returned are **digitized estimates, not official data**. Always say so.

## The trigger pattern (Muse)

1. User asks for time-series data.
2. No raw/downloadable source exists, but a chart/graph of the data does.
3. Muse finds the chart and **asks the user** whether they want digitized
   estimates extracted from it ("unplotit" + chart also triggers this directly).
4. On yes: calibrate axes, extract, verify against an overlay, hand over CSV.

## Using the skill (Muse)

Copy `skill/` into the Muse skills directory as `unplotit/`. The skill
calibrates from the image, runs `generate.py` to extract monthly CSV + overlay
PNG + a self-contained drag-to-correct HTML page, and hands the page to the user
for verification.

## Using the web tool

Open `web/aiagent.html` in any browser (works from `file://`, no server needed):
paste or drop a chart image, calibrate the plot rectangle and axes, verify the
overlay, correct dots by dragging, resample, export CSV.

## MCP server (experimental)

```bash
cd mcp
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python server.py        # MCP over stdio
```

`extract_chart` needs axis calibration: plot-area pixel bounds, scan band,
`value = slope * y_pixel + intercept` from two y-axis labels, and the date range.
Call `calibration_guide` first — it teaches the calling agent to derive these
from the image itself. Not yet tested end-to-end with non-Muse assistants.

## Accuracy

Measured against NASA GISTEMP: r=0.94, residual MAE 0.10 °C after baseline
offset correction. Near-vertical line segments can vary ~0.5–0.8 chart units.
Always overlay-verify before delivering numbers.

## Policy

This tool runs inside the user's AI assistant, extracting data on their behalf.
It is not operated as a human-facing chart-upload service.

## License

MIT — see `LICENSE`.
