// Dashboard Lite - Dark Mode Engine
// Loads pingr_cleaned_data.csv (latest ML output) and builds stats

async function loadCSV() {
    try {
        const res = await fetch("../pingr_cleaned_data.csv");
        const text = await res.text();
        const rows = text.split("\n").map(r => r.split(","));
        return rows;
    } catch (err) {
        console.error("Failed to load CSV:", err);
        document.getElementById("status").innerText = "❌ Unable to load data.";
    }
}

// Simple CSV → JSON converter
function parseCSV(header, rows) {
    return rows.map(r => {
        let obj = {};
        header.forEach((h, i) => obj[h] = r[i]);
        return obj;
    });
}

async function buildDashboard() {
    document.getElementById("status").innerText = "Loading...";

    const rows = await loadCSV();
    if (!rows) return;

    const header = rows[0];
    const data = parseCSV(header, rows.slice(1));

    // Filter alerts sent
    const alerts = data.filter(d => d.alert_sent === "True");

    // Top coins
    const scores = {};
    alerts.forEach(a => {
        const sym = a.symbol;
        const s = parseFloat(a.signal_score) || 0;
        if (!scores[sym]) scores[sym] = [];
        scores[sym].push(s);
    });

    const ranked = Object.entries(scores)
        .map(([sym, arr]) => ({ sym, avg: arr.reduce((a,b)=>a+b,0)/arr.length }))
        .sort((a,b) => b.avg - a.avg)
        .slice(0, 10);

    // Inject into HTML
    const html = ranked.map(r => `
        <div class="item">
            <span>${r.sym}</span>
            <strong>${r.avg.toFixed(2)}</strong>
        </div>
    `).join("");

    document.getElementById("topCoins").innerHTML = html;
    document.getElementById("status").innerText = "Data Loaded ✓";
}

buildDashboard();
