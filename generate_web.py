#!/usr/bin/env python3
"""Generate interactive web dashboard for LLM model efficiency visualization."""

import json
import sys
from datetime import datetime
from pathlib import Path

CACHE_DIR = Path.home() / ".hermes" / "cache"
MODELS_CACHE = CACHE_DIR / "aa_models.json"
VERBOSITY_CACHE = CACHE_DIR / "aa_verbosity.json"
OUTPUT_FILE = Path(__file__).parent / "index.html"

REASONING_ONLY = True
MIN_CODING = 34

PROVIDER_COLORS = {
    "Google": "#34A853",
    "DeepSeek": "#003580",
    "Alibaba": "#FF8C00",
    "OpenAI": "#222222",
    "Anthropic": "#D2691E",
    "MiniMax": "#FF00FF",
    "xAI": "#7B2FBE",
    "Moonshot": "#5BC0EB",
    "Xiaomi": "#F4C430",
    "Meta": "#0668E1",
    "Z AI": "#1c7ff8",
    "NVIDIA": "#86b737",
    "#888888": "#AAAAAA",
}


def get_provider_color(creator_name, model_name):
    name_lower = model_name.lower()
    if "grok" in name_lower:
        return PROVIDER_COLORS["xAI"]
    if "mimo" in name_lower:
        return PROVIDER_COLORS["Xiaomi"]
    if "kimi" in name_lower:
        return PROVIDER_COLORS["Moonshot"]
    if creator_name == "Alibaba":
        return PROVIDER_COLORS["Alibaba"]
    return PROVIDER_COLORS.get(creator_name, "#AAAAAA")


def get_provider_label(creator_name, model_name):
    name_lower = model_name.lower()
    if "grok" in name_lower:
        return "xAI"
    if "mimo" in name_lower:
        return "Xiaomi"
    if "kimi" in name_lower:
        return "Moonshot"
    return creator_name


def load_cache(path):
    if not path.exists():
        print(f"ERROR: Cache not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def load_verbosity():
    if not VERBOSITY_CACHE.exists():
        return {}
    data = load_cache(VERBOSITY_CACHE)
    return {m["slug"]: m for m in data.get("models", []) if m.get("slug")}


def process_models():
    api_data = load_cache(MODELS_CACHE)
    verbosity = load_verbosity()
    models = api_data.get("models", [])

    processed = []
    for m in models:
        name = m.get("name", "")
        slug = m.get("slug", "")
        creator = m.get("model_creator", {}).get("name", "Unknown")
        evals = m.get("evaluations", {})
        pricing = m.get("pricing", {})

        intelligence = evals.get("artificial_analysis_intelligence_index")
        coding = evals.get("artificial_analysis_coding_index")
        speed = m.get("median_output_tokens_per_second", 0) or 0
        price_in = pricing.get("price_1m_input_tokens", 0) or 0
        price_out = pricing.get("price_1m_output_tokens", 0) or 0

        if not all([intelligence, coding, price_in, price_out]):
            continue
        if coding < MIN_CODING:
            continue
        if REASONING_ONLY and "Non-reasoning" in name:
            continue

        verb = verbosity.get(slug, {})
        output_tokens = verb.get("output_tokens", 0)
        if output_tokens < 1_000_000:
            continue

        processed.append({
            "name": name,
            "slug": slug,
            "creator": creator,
            "intelligence": float(intelligence),
            "coding": float(coding),
            "speed": float(speed),
            "price_in": float(price_in),
            "price_out": float(price_out),
            "output_tokens": int(output_tokens),
        })

    if not processed:
        print("ERROR: No models after filtering", file=sys.stderr)
        sys.exit(1)

    min_output = min(m["output_tokens"] for m in processed)
    for m in processed:
        m["cost"] = m["price_in"] * 0.3 + m["price_out"] * 0.7
        m["verbosity_penalty"] = m["output_tokens"] / min_output
        output_m = m["output_tokens"] / 1_000_000  # millions — same unit as pricing
        m["efficiency_coding"] = m["coding"] / (m["cost"] * output_m)
        m["efficiency_intelligence"] = m["intelligence"] / (m["cost"] * output_m)
        m["color"] = get_provider_color(m["creator"], m["name"])
        m["provider"] = get_provider_label(m["creator"], m["name"])

    return processed


def generate_html(models):
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    js_data = json.dumps([{
        "name": m["name"],
        "provider": m["provider"],
        "intelligence": m["intelligence"],
        "coding": m["coding"],
        "efficiency_coding": m["efficiency_coding"],
        "efficiency_intelligence": m["efficiency_intelligence"],
        "speed": m["speed"],
        "price_in": m["price_in"],
        "price_out": m["price_out"],
        "cost": m["cost"],
        "verbosity_penalty": m["verbosity_penalty"],
        "output_tokens": m["output_tokens"],
        "color": m["color"],
    } for m in models])

    # Build HTML with string concatenation to avoid f-string brace escaping
    parts = []
    parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Model Efficiency Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.1.0/dist/chartjs-plugin-annotation.min.js"></script>
<style>
:root {
    --bg: #1a1a2e;
    --surface: #16213e;
    --text: #e0e0e0;
    --text-muted: #888;
    --border: #333;
    --accent: #0f3460;
    --grid: rgba(255,255,255,0.08);
}
.light {
    --bg: #f5f5f5;
    --surface: #ffffff;
    --text: #333;
    --text-muted: #777;
    --border: #ddd;
    --accent: #e3f2fd;
    --grid: rgba(0,0,0,0.08);
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
}
.container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
}
header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    flex-wrap: wrap;
    gap: 10px;
}
h1 {
    font-size: 1.4rem;
    font-weight: 600;
}
.controls {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: center;
    background: var(--surface);
    padding: 12px 16px;
    border-radius: 10px;
    border: 1px solid var(--border);
    margin-bottom: 16px;
}
.control-group {
    display: flex;
    align-items: center;
    gap: 6px;
}
.control-group label {
    font-size: 0.8rem;
    color: var(--text-muted);
    white-space: nowrap;
}
.toggle {
    position: relative;
    width: 44px;
    height: 24px;
    background: var(--border);
    border-radius: 12px;
    cursor: pointer;
    transition: background 0.2s;
}
.toggle.active {
    background: #0f3460;
}
.toggle::after {
    content: '';
    position: absolute;
    top: 3px;
    left: 3px;
    width: 18px;
    height: 18px;
    background: white;
    border-radius: 50%;
    transition: transform 0.2s;
}
.toggle.active::after {
    transform: translateX(20px);
}
.toggle-label {
    font-size: 0.8rem;
    font-weight: 500;
    min-width: 50px;
}
.chart-container {
    background: var(--surface);
    border-radius: 12px;
    border: 1px solid var(--border);
    padding: 20px;
    position: relative;
    height: 600px;
}
.chart-container canvas {
    width: 100% !important;
    height: 100% !important;
}
.footer {
    text-align: center;
    padding: 16px;
    color: var(--text-muted);
    font-size: 0.75rem;
}
.footer a {
    color: var(--text-muted);
}
</style>
</head>
<body class="light">
<div class="container">
    <header>
        <h1>AI Model Efficiency Dashboard</h1>
        <span style="font-size:0.8rem; color:var(--text-muted)">""" + str(len(models)) + """ models · Data from <a href="https://artificialanalysis.ai/" target="_blank">Artificial Analysis</a></span>
    </header>

    <div class="controls">
        <div class="control-group">
            <label>Y-axis:</label>
            <span class="toggle-label" id="yAxisLabel">Coding</span>
            <div class="toggle active" id="yAxisToggle" onclick="toggleYAxis()"></div>
        </div>

        <div class="control-group">
            <label>Scale:</label>
            <span class="toggle-label" id="scaleLabel">Log</span>
            <div class="toggle active" id="scaleToggle" onclick="toggleScale()"></div>
        </div>

        <div class="control-group">
            <label>Theme:</label>
            <span class="toggle-label" id="themeLabel">Light</span>
            <div class="toggle" id="themeToggle" onclick="toggleTheme()"></div>
        </div>

        <div class="control-group">
            <label>Min Intelligence:</label>
            <input type="range" id="minSlider" min="0" max="80" value="34"
                   oninput="updateMin(this.value)" style="width:100px;">
            <span id="minValue" style="font-size:0.8rem; min-width:25px;">34</span>
        </div>

        <div class="control-group">
            <label>Pareto Line:</label>
            <div class="toggle active" id="paretoToggle" onclick="togglePareto()"></div>
        </div>

        <div class="control-group">
            <label>Pareto Frontier:</label>
            <div class="toggle active" id="frontierToggle" onclick="toggleFrontier()"></div>
        </div>

        <div class="control-group">
            <label>Grid Lines:</label>
            <div class="toggle active" id="gridToggle" onclick="toggleGrid()"></div>
        </div>
    </div>

    <div class="chart-container">
        <canvas id="scatterChart"></canvas>
    </div>

    <div class="footer">
        Efficiency = Coding Index / (Cost x Output Tokens)<br>
        Cost = Input x 0.3 + Output x 0.7 · Output Tokens = millions from Intelligence Index benchmark<br>
        Data: <a href="https://artificialanalysis.ai/" target="_blank">artificialanalysis.ai</a> · Generated by model-efficiency · """ + generated_at + """<br>
        Suggestions: <a href="mailto:hermeselbecario@gmail.com">hermeselbecario@gmail.com</a>
    </div>
</div>

<script>
const MODELS = """ + js_data + """;

let state = {
    yAxis: 'coding',
    scale: 'logarithmic',
    theme: 'light',
    minIntelligence: 34,
    showPareto: true,
    showFrontier: true,
    showGrid: true,
};

function percentile(arr, p) {
    const sorted = [...arr].sort((a, b) => a - b);
    const idx = Math.ceil(p * sorted.length / 100) - 1;
    return sorted[Math.max(0, idx)];
}

function getVisibleModels() {
    return MODELS.filter(m => m.intelligence >= state.minIntelligence);
}

function getEff(m) {
    return state.yAxis === 'intelligence' ? m.efficiency_intelligence : m.efficiency_coding;
}

function computeParetoLine(models) {
    if (models.length < 2) return null;
    const yAxisKey = state.yAxis;
    let maxIdx = models[0], maxEff = models[0];
    for (const m of models) {
        if (m[yAxisKey] > maxIdx[yAxisKey]) maxIdx = m;
        if (getEff(m) > getEff(maxEff)) maxEff = m;
    }
    return [
        { x: getEff(maxEff), y: maxEff[yAxisKey], meta: maxEff },
        { x: getEff(maxIdx), y: maxIdx[yAxisKey], meta: maxIdx },
    ];
}

function computeFrontier(models) {
    if (models.length < 2) return [];
    const yAxisKey = state.yAxis;
    const sorted = [...models].sort((a, b) => getEff(b) - getEff(a));
    const frontier = [];
    let maxY = -Infinity;
    for (const m of sorted) {
        const yVal = m[yAxisKey];
        if (yVal > maxY) {
            maxY = yVal;
            frontier.push({ x: getEff(m), y: yVal, meta: m });
        }
    }
    return frontier.sort((a, b) => a.x - b.x);
}

function computeGridLines(models) {
    if (models.length < 2) return {};
    const yAxisKey = state.yAxis;
    const lineColor = state.theme === 'dark' ? 'rgba(255,255,255,0.3)' : 'rgba(0,0,0,0.3)';
    let maxEffModel = models[0], maxIdxModel = models[0];
    for (const m of models) {
        if (getEff(m) > getEff(maxEffModel)) maxEffModel = m;
        if (m[yAxisKey] > maxIdxModel[yAxisKey]) maxIdxModel = m;
    }
    return {
        vertical: {
            type: 'line',
            xMin: getEff(maxIdxModel),
            xMax: getEff(maxIdxModel),
            borderColor: lineColor,
            borderWidth: 1,
            borderDash: [6, 4],
            label: {
                display: true,
                content: maxIdxModel.name.split(' ')[0],
                position: 'start',
                font: { size: 10 },
            },
        },
        horizontal: {
            type: 'line',
            yMin: maxEffModel[yAxisKey],
            yMax: maxEffModel[yAxisKey],
            borderColor: lineColor,
            borderWidth: 1,
            borderDash: [6, 4],
            label: {
                display: true,
                content: maxEffModel.name.split(' ')[0],
                position: 'end',
                font: { size: 10 },
            },
        },
    };
}

const ctx = document.getElementById('scatterChart').getContext('2d');
let chart = null;

function buildDatasets() {
    const visible = getVisibleModels();
    const groups = {};
    for (const m of visible) {
        if (!groups[m.provider]) groups[m.provider] = [];
        groups[m.provider].push(m);
    }

    const datasets = Object.entries(groups).map(([provider, models]) => ({
        label: provider,
        data: models.map(m => ({
            x: getEff(m),
            y: state.yAxis === 'intelligence' ? m.intelligence : m.coding,
            meta: m,
        })),
        backgroundColor: models[0].color + 'CC',
        borderColor: models[0].color,
        borderWidth: 1,
        pointRadius: 8,
        pointHoverRadius: 12,
        pointHoverBorderWidth: 3,
        pointHoverBorderColor: '#fff',
        pointBorderWidth: 2,
    }));

    if (state.showPareto) {
        const line = computeParetoLine(visible);
        if (line) {
            datasets.push({
                label: 'Pareto Line',
                data: line,
                type: 'line',
                borderColor: '#ff6b6b',
                borderWidth: 2,
                borderDash: [8, 4],
                pointRadius: 6,
                pointStyle: 'circle',
                pointBackgroundColor: '#ff6b6b',
                fill: false,
                order: -1,
            });
        }
    }

    if (state.showFrontier) {
        const frontier = computeFrontier(visible);
        if (frontier.length > 1) {
            datasets.push({
                label: 'Pareto Frontier',
                data: frontier,
                type: 'line',
                borderColor: '#ffd93d',
                borderWidth: 2,
                borderDash: [4, 2],
                pointRadius: 4,
                pointBackgroundColor: '#ffd93d',
                fill: false,
                order: -1,
            });
        }
    }

    return datasets;
}

function buildAnnotations() {
    if (!state.showGrid) return {};
    const visible = getVisibleModels();
    const lines = computeGridLines(visible);
    return { annotations: lines };
}

function getThemeColors() {
    const isDark = state.theme === 'dark';
    return {
        gridColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
        textColor: isDark ? '#e0e0e0' : '#333',
        tooltipBg: isDark ? '#16213e' : '#ffffff',
        tooltipBorder: isDark ? '#333' : '#ddd',
        tooltipText: isDark ? '#e0e0e0' : '#333',
    };
}

function createChart() {
    const theme = getThemeColors();
    const yAxisLabel = state.yAxis === 'intelligence' ? 'Intelligence Index' : 'Coding Index';

    chart = new Chart(ctx, {
        type: 'scatter',
        data: { datasets: buildDatasets() },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            scales: {
                x: {
                    type: state.scale === 'logarithmic' ? 'logarithmic' : 'linear',
                    title: {
                        display: true,
                        text: 'Efficiency (Coding / Cost x Output Tokens)',
                        color: theme.textColor,
                    },
                    grid: {
                        color: state.showGrid ? theme.gridColor : 'transparent',
                    },
                    ticks: { color: theme.textColor },
                    ...(state.scale === 'linear' ? (() => {
                        const effs = getVisibleModels().map(m => getEff(m));
                        const p98 = percentile(effs, 98);
                        const margin = p98 * 0.20;
                        return { max: p98 + margin };
                    })() : {}),
                },
                y: {
                    title: {
                        display: true,
                        text: yAxisLabel,
                        color: theme.textColor,
                    },
                    grid: {
                        color: state.showGrid ? theme.gridColor : 'transparent',
                    },
                    ticks: { color: theme.textColor },
                },
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: theme.textColor,
                        usePointStyle: true,
                        padding: 16,
                    },
                },
                annotation: buildAnnotations(),
                tooltip: {
                    enabled: true,
                    backgroundColor: theme.tooltipBg,
                    borderColor: theme.tooltipBorder,
                    borderWidth: 1,
                    titleColor: theme.tooltipText,
                    bodyColor: theme.tooltipText,
                    padding: 12,
                    cornerRadius: 8,
                    displayColors: true,
                    callbacks: {
                        title: function(items) {
                            if (!items.length) return '';
                            const m = items[0].raw.meta;
                            return m ? m.name + ' (' + m.provider + ')' : '';
                        },
                        label: function(item) {
                            if (item.dataset.type === 'line') return '';
                            const m = item.raw.meta;
                            if (!m) return '';
                            return [
                                'Intelligence: ' + m.intelligence.toFixed(1),
                                'Coding: ' + m.coding.toFixed(1),
                                'Efficiency: ' + getEff(m).toFixed(2),
                                'Speed: ' + m.speed.toFixed(0) + ' tok/s',
                                'Cost: $' + m.price_in.toFixed(2) + ' / $' + m.price_out.toFixed(2) + ' per 1M',
                                'Verbosity: ' + (m.output_tokens / 1000000).toFixed(1) + 'M tokens',
                            ];
                        },
                    },
                },
            },
        },
    });
}

function updateChart() {
    if (chart) {
        chart.destroy();
        chart = null;
    }
    const canvas = document.getElementById('scatterChart');
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    createChart();
}

function toggleYAxis() {
    state.yAxis = state.yAxis === 'intelligence' ? 'coding' : 'intelligence';
    document.getElementById('yAxisLabel').textContent =
        state.yAxis === 'intelligence' ? 'Intelligence' : 'Coding';
    document.getElementById('yAxisToggle').classList.toggle('active');
    updateChart();
}

function toggleScale() {
    state.scale = state.scale === 'linear' ? 'logarithmic' : 'linear';
    document.getElementById('scaleLabel').textContent =
        state.scale === 'linear' ? 'Linear' : 'Log';
    document.getElementById('scaleToggle').classList.toggle('active');
    updateChart();
}

function toggleTheme() {
    state.theme = state.theme === 'dark' ? 'light' : 'dark';
    document.body.classList.toggle('light');
    document.getElementById('themeLabel').textContent =
        state.theme === 'dark' ? 'Dark' : 'Light';
    document.getElementById('themeToggle').classList.toggle('active');
    updateChart();
}

function updateMin(val) {
    state.minIntelligence = parseInt(val);
    document.getElementById('minValue').textContent = val;
    updateChart();
}

function togglePareto() {
    state.showPareto = !state.showPareto;
    document.getElementById('paretoToggle').classList.toggle('active');
    updateChart();
}

function toggleFrontier() {
    state.showFrontier = !state.showFrontier;
    document.getElementById('frontierToggle').classList.toggle('active');
    updateChart();
}

function toggleGrid() {
    state.showGrid = !state.showGrid;
    document.getElementById('gridToggle').classList.toggle('active');
    updateChart();
}

createChart();
</script>
</body>
</html>""")

    return "".join(parts)


if __name__ == "__main__":
    models = process_models()
    print(f"Processed {len(models)} models")

    html = generate_html(models)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"Generated: {OUTPUT_FILE}")
    print(f"File size: {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")
