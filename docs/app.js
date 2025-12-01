// Pingr Dashboard Lite — FINAL DEBUG VERSION
// This version ALWAYS loads data from /docs/pingr_cleaned_data.csv

async function loadCSV() {
    try {
        console.log("Fetching CSV → /docs/pingr_cleaned_data.csv");

        const res = await fetch("./pingr_cleaned_data.csv", { cache: "no-store" });

        if (!res.ok) {
            document.getElementById("status").innerText = "❌ CSV missing in /docs.";
            return null;
        }

        const text = await res.text();
        console.log("CSV Loaded (first 200 chars):", text.slice(0, 200));

        return text.trim().split("\n").map(row => row.split(","));
    } catch (err) {
        console.error("CSV load error:", err);
        document.getElementById("status").innerText = "❌ Failed to load CSV.";
        return null;
    }
}

function parseCSV(header, rows) {
    console.log("CSV Header Parsed:", header);

    const items = [];
    rows.forEach((row, i) => {
        if (row.length !== header.length) {
            console.warn("⚠️ Row mismatch at line", i + 2, row);
            return;
        }
        let obj = {};
        header.forEach((h, idx) => (obj[h] = row[idx]));
        items.push(obj);
    });

    console.log("Parsed", items.length, "rows.");
    return items;
}

function showStat(id, label, value) {
    document.getElementById(id).innerHTML += `
        <div class="stat-box">
            <strong>${label}:</strong> ${value}
        </div>
    `;
}

async function buildDashboard() {
    document.getElementById("status").innerText = "Loading Dashboard…";

    const rows = await loadCSV();
    if (!rows) return;

    const header = rows[0];
    const data = parseCSV(header, rows.slice(1));

    // Type fixes
    data.forEach(d => {
        d.alert_sent = (d.alert_sent === "True" || d.alert_sent === "true");
        d.signal_score = parseFloat(d.signal_score) || 0;
        d.rsi_15m = parseFloat(d.rsi_15m) || null;
        d.heat_index = parseFloat(d.heat_index) || null;
    });

    console.log("Data sample:", data.slice(0, 5));

    const alerts = data.filter(d => d.alert_sent);
    console.log("Alerts:", alerts);

    if (alerts.length === 0) {
        document.getElementById("topCoins").innerHTML = "<i>No alerts found.</i>";
        document.getElementById("status").innerText = "Loaded ✓ (no alerts)";
        return;
    }

    document.getElementById("status").innerText = "Loaded ✓";

    // ---------------------------------
    // 1) TOP COINS
    // ---------------------------------
    const scoreMap = {};
    alerts.forEach(a => {
        if (!scoreMap[a.symbol]) scoreMap[a.symbol] = [];
        scoreMap[a.symbol].push(a.signal_score);
    });

    const ranked = Object.entries(scoreMap)
        .map(([sym, arr]) => ({
            sym,
            avg: arr.reduce((a, b) => a + b, 0) / arr.length
        }))
        .sort((a, b) => b.avg - a.avg)
        .slice(0, 10);

    document.getElementById("topCoins").innerHTML = ranked
        .map(r => `
        <div class="item">
            <span>${r.sym}</span>
            <strong>${r.avg.toFixed(2)}</strong>
        </div>
    `)
        .join("");

    // ---------------------------------
    // 2) Score Distribution
    // ---------------------------------
    const scores = alerts.map(a => a.signal_score);
    showStat("scoreStats", "Mean Score", (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(2));
    showStat("scoreStats", "Max Score", Math.max(...scores));
    showStat("scoreStats", "Min Score", Math.min(...scores));

    // ---------------------------------
    // 3) RSI Stats
    // ---------------------------------
    const rsi = alerts.map(a => a.rsi_15m).filter(v => v !== null);
    if (rsi.length > 0) {
        showStat("rsiStats", "RSI Avg", (rsi.reduce((a, b) => a + b, 0) / rsi.length).toFixed(2));
        showStat("rsiStats", "RSI Min", Math.min(...rsi));
        showStat("rsiStats", "RSI Max", Math.max(...rsi));
    }

    // ---------------------------------
    // 4) Heat Index
    // ---------------------------------
    const heat = alerts.map(a => a.heat_index).filter(v => v !== null);
    if (heat.length > 0) {
        showStat("heatStats", "Heat Avg", (heat.reduce((a, b) => a + b, 0) / heat.length).toFixed(2));
        showStat("heatStats", "Heat Min", Math.min(...heat));
        showStat("heatStats", "Heat Max", Math.max(...heat));
    }

    // ---------------------------------
    // 5) Momentum Summary (from CSV)
    // ---------------------------------
    showStat("momentumSummary", "Total Alerts", alerts.length);
    showStat("momentumSummary", "Unique Coins", Object.keys(scoreMap).length);
}

buildDashboard();
