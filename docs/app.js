// Dashboard Lite - Full Multi-Stats Version (Debug Enabled)

async function loadCSV() {
    try {
        console.log("Fetching CSV from ./pingr_cleaned_data.csv …");

        const res = await fetch("./pingr_cleaned_data.csv", { cache: "no-store" });

        if (!res.ok) {
            document.getElementById("status").innerText =
                "❌ CSV missing. Run workflow.";
            return null;
        }

        const text = await res.text();
        console.log("CSV Loaded, first 200 chars:", text.slice(0, 200));

        return text.trim().split("\n").map(r => r.split(","));
    } catch (err) {
        console.error("CSV Load Error:", err);
        document.getElementById("status").innerText = "❌ Load error.";
        return null;
    }
}

function parseCSV(header, rows) {
    const items = [];
    rows.forEach((r) => {
        if (r.length !== header.length) return;
        let obj = {};
        header.forEach((h, i) => obj[h] = r[i]);
        items.push(obj);
    });
    return items;
}

async function buildDashboard() {
    document.getElementById("status").innerText = "Loading… (Debug ON)";

    const rows = await loadCSV();
    if (!rows) return;

    const header = rows[0];
    const data = parseCSV(header, rows.slice(1));

    console.log("Parsed dataset (first 5):", data.slice(0, 5));

    // Convert types
    data.forEach(d => {
        d.alert_sent = (d.alert_sent === "True" || d.alert_sent === "true");
        d.signal_score = parseFloat(d.signal_score) || 0;
        d.rsi_15m = parseFloat(d.rsi_15m) || null;
        d.heat_index = parseFloat(d.heat_index) || null;
    });

    const alerts = data.filter(d => d.alert_sent);
    console.log("Filtered alerts:", alerts);

    // -----------------------------
    // 1) TOP COINS
    // -----------------------------
    const scores = {};
    alerts.forEach(a => {
        if (!scores[a.symbol]) scores[a.symbol] = [];
        scores[a.symbol].push(a.signal_score);
    });

    const ranked = Object.entries(scores)
        .map(([sym, arr]) => ({
            sym,
            avg: arr.reduce((a, b) => a + b, 0) / arr.length
        }))
        .sort((a, b) => b.avg - a.avg)
        .slice(0, 10);

    document.getElementById("topCoins").innerHTML =
        ranked.map(r => `
            <div class="item">
                <span>${r.sym}</span>
                <strong>${r.avg.toFixed(2)}</strong>
            </div>
        `).join("");

    // -----------------------------
    // 2) SCORE DISTRIBUTION
    // -----------------------------
    const scoresOnly = data.map(d => d.signal_score);
    const min = Math.min(...scoresOnly);
    const max = Math.max(...scoresOnly);
    const avg = scoresOnly.reduce((a, b) => a + b, 0) / scoresOnly.length;

    document.getElementById("scoreStats").innerHTML = `
        <div class="stat-box">
            Min Score: <strong>${min}</strong><br>
            Max Score: <strong>${max}</strong><br>
            Average Score: <strong>${avg.toFixed(2)}</strong>
        </div>
    `;

    // -----------------------------
    // 3) RSI (alerts only)
    // -----------------------------
    const rsiVals = alerts.map(a => a.rsi_15m).filter(v => v !== null);
    const rsiAvg = rsiVals.reduce((a, b) => a + b, 0) / rsiVals.length;

    document.getElementById("rsiStats").innerHTML = `
        <div class="stat-box">
            Avg RSI: <strong>${rsiAvg.toFixed(2)}</strong><br>
            Min RSI: <strong>${Math.min(...rsiVals)}</strong><br>
            Max RSI: <strong>${Math.max(...rsiVals)}</strong>
        </div>
    `;

    // -----------------------------
    // 4) HEAT INDEX
    // -----------------------------
    const heats = data.map(d => d.heat_index).filter(v => v !== null);
    const heatAvg = heats.reduce((a, b) => a + b, 0) / heats.length;

    document.getElementById("heatStats").innerHTML = `
        <div class="stat-box">
            Avg Heat Index: <strong>${heatAvg.toFixed(2)}</strong><br>
            Max Heat: <strong>${Math.max(...heats)}</strong>
        </div>
    `;

    // -----------------------------
    // 5) MOMENTUM SUMMARY
    // -----------------------------
    const res = await fetch("./momentum_advanced_summary.json");
    let momentum = await res.json();

    document.getElementById("momentumSummary").innerHTML = `
        <div class="stat-box">
            Total Cycles: <strong>${momentum.total_cycles}</strong><br>
            Successes: <strong>${momentum.success_total}</strong><br>
            Failures: <strong>${momentum.failures}</strong><br>
            Still Active: <strong>${momentum.still_active}</strong>
        </div>
    `;

    document.getElementById("status").innerText = "Dashboard Loaded ✓";
}

buildDashboard();
