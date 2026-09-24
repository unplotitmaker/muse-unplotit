# aiagent.unplotit

Chart-image → CSV extraction, built for AI agents.

## What this is

When a user asks an AI assistant for time-series data and no downloadable source
exists — but a chart of the data does — the assistant can extract digitized
estimates straight from the chart image. That's what this repo provides, three ways:

| Directory | What | Who it's for |
|---|---|---|
| `mcp/` | MCP server (`extract_chart`, `calibration_guide` tools) | Any MCP-capable assistant (Claude, Muse, …) |
| `skill/` | Drop-in skill (Python extractor + correction-page generator) | Muse agents |
| `web/` | Single-file browser tool (upload/paste chart → calibrate → CSV) | Agents with browser access; fallback UI |

Values returned are **digitized estimates, not official data**. Always say so.

## The trigger pattern

1. User asks for time-series data.
2. No raw/downloadable source exists, but a chart/graph of the data does.
3. Agent finds the chart and **asks the user** whether they want digitized
   estimates extracted from it ("unplotit" + chart also triggers this directly).
4. On yes: calibrate axes, extract, verify against an overlay, hand over CSV.

## Using the MCP server

```bash
cd mcp
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python server.py        # MCP over stdio
```

Connect it in your MCP client (Claude Desktop `claude_desktop_config.json` etc.):

```json
{ "mcpServers": { "aiagent-unplotit":
  { "command": "/abs/path/mcp/.venv/bin/python",
    "args": ["/abs/path/mcp/server.py"] } } }
```

`extract_chart` needs axis calibration: plot-area pixel bounds, scan band,
`value = slope * y_pixel + intercept` from two y-axis labels, and the date range.
Call `calibration_guide` first — it teaches the calling agent to derive these
from the image itself. See `mcp/README.md` (original notes) for details.

## Using the skill (Muse)

Copy `skill/` into your Muse skills directory as `unplotit/`. The skill
calibrates from the image, runs `generate.py` to extract monthly CSV + overlay
PNG + a self-contained drag-to-correct HTML page, and hands the page to the user.

## Accuracy

Measured against NASA GISTEMP: r=0.94, residual MAE 0.10 °C after baseline
offset correction. Near-vertical line segments can vary ~0.5–0.8 chart units.
Always overlay-verify before delivering numbers.

## Policy

This tool is for AI agents extracting data on a user's behalf. It is not
operated as a human-facing chart-upload service.

## License

MIT — see `LICENSE`.
