// DASHBOARD LITE – FULL VERSION (Top Coins + Score + RSI + Heat + Momentum)

async function loadCSV() {
    try {
        console.log("Fetching CSV from /docs...");
        const res = await fetch("./pingr_cleaned_data.csv", { cache: "no-store" });

        if (!res.ok) {
            document.getElementById("status").innerText =
                "❌ CSV not found. Run ML workflow.";
            return null;
        }

        const text = await res.text();
        return text.trim().split("\n").map(r => r.split(","));
    } catch (err) {
        console.error("❌ CSV load error:", err);
        document.getElementById("status").innerText = "❌ Unable to load CSV.";
        return null;
    }
}

function parseCSV(header, rows) {
    const items = [];
    rows.forEach((r, i) => {
        if (r.length !== header.length) return;
        let obj = {};
        header.forEach((h, j) => obj[h] = r[j]);
        items.push(obj);
    });
    return items;
}

async function buildDashboard() {

    document.getElementById("status").innerText = "Loading...";

    const rows = await loadCSV();
    if (!rows) return;

    const header = rows[0];
    const data = parseCSV(header, rows.slice(1));

    // Convert types
    data.forEach(d => {
        d.alert_sent = (d.alert_sent === "True" || d.alert_sent === "true");
        d.signal_score = parseFloat(d.signal_score) || 0;
        d.rsi_15m = parseFloat(d.rsi_15m) || null;
        d.heat_index = parseFloat(d.heat_index) || null;
    });

    // Filter alerts only
    const alerts = data.filter(d => d.alert_sent);

    // ---------------------------
    // 1) Top Coins
    // ---------------------------
    const scores = {};
    alerts.forEach(a => {
        if (!scores[a.symbol]) scores[a.symbol] = [];
        scores[a.symbol].push(a.signal_score);
    });

    const ranked = Object.entries(scores)
        .map(([sym, arr]) => ({ sym, avg: arr.reduce((a, b) => a + b, 0) / arr.length }))
        .sort((a, b) => b.avg - a.avg)
        .slice(0, 10);

    document.getElementById("topCoins").innerHTML = ranked
        .map(r => `<div class="item"><span>${r.sym}</span><strong>${r.avg.toFixed(2)}</strong></div>`)
        .join("");

    // ---------------------------
    // 2) Score Distribution
    // ---------------------------
    const allScores = alerts.map(a => a.signal_score);
    const avgScore = (allScores.reduce((a, b) => a + b, 0) / allScores.length).toFixed(2);
    const maxScore = Math.max(...allScores).toFixed(2);
    const minScore = Math.min(...allScores).toFixed(2);

    document.getElementById("scoreStats").innerHTML = `
        <div class="stat-box">
            <b>Avg Score:</b> ${avgScore}<br>
            <b>High:</b> ${maxScore} &nbsp; <b>Low:</b> ${minScore}
        </div>
    `;

    // ---------------------------
    // 3) RSI Stats
    // ---------------------------
    const alertRSI = alerts.map(a => a.rsi_15m).filter(x => x !== null);
    const avgRSI = (alertRSI.reduce((a, b) => a + b, 0) / alertRSI.length).toFixed(2);

    document.getElementById("rsiStats").innerHTML = `
        <div class="stat-box">
            <b>Avg RSI(15m):</b> ${avgRSI}<br>
            <b>Min:</b> ${Math.min(...alertRSI).toFixed(2)} &nbsp;
            <b>Max:</b> ${Math.max(...alertRSI).toFixed(2)}
        </div>
    `;

    // ---------------------------
    // 4) Heat Index Stats
    // ---------------------------
    const heatVals = alerts.map(a => a.heat_index).filter(x => x !== null);

    document.getElementById("heatStats").innerHTML = `
        <div class="stat-box">
            <b>Avg Heat:</b> ${(heatVals.reduce((a,b)=>a+b,0)/heatVals.length).toFixed(2)}<br>
            <b>Min:</b> ${Math.min(...heatVals).toFixed(2)} &nbsp;
            <b>Max:</b> ${Math.max(...heatVals).toFixed(2)}
        </div>
    `;

    // ---------------------------
    // 5) Momentum Summary (simple)
    // ---------------------------
    const momentumFile = await fetch("./momentum_advanced_summary.json").then(r => r.json());

    document.getElementById("momentumSummary").innerHTML = `
        <div class="stat-box">
            <b>Total Cycles:</b> ${momentumFile.total_cycles}<br>
            <b>Successes:</b> ${momentumFile.success_total}<br>
            <b>Failures:</b> ${momentumFile.failures}<br>
            <b>Still Active:</b> ${momentumFile.still_active}
        </div>
    `;

    document.getElementById("status").innerText = "Dashboard Loaded ✓";
}

buildDashboard();
