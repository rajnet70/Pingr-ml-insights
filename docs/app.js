// Dashboard Lite - Loads pingr_cleaned_data.csv from /docs and builds stats

async function loadCSV() {
    try {
        // Load from same folder (/docs)
        const res = await fetch("pingr_cleaned_data.csv", { cache: "no-store" });

        if (!res.ok) {
            document.getElementById("status").innerText = "❌ No data found. Run ML script first.";
            return null;
        }

        const text = await res.text();
        return text.trim().split("\n").map(r => r.split(","));
    } catch (err) {
        console.error("Failed to load CSV:", err);
        document.getElementById("status").innerText = "❌ Unable to load data.";
        return null;
    }
}

function parseCSV(header, rows) {
    const items = [];
    rows.forEach(r => {
        if (r.length !== header.length) return;
        let obj = {};
        header.forEach((h, i) => obj[h] = r[i]);
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

    data.forEach(d => {
        d.alert_sent = (d.alert_sent === "True" || d.alert_sent === "TRUE" || d.alert_sent === "true");
        d.signal_score = parseFloat(d.signal_score) || 0;
    });

    const alerts = data.filter(d => d.alert_sent);

    if (alerts.length === 0) {
        document.getElementById("topCoins").innerHTML = "<i>No alerts yet.</i>";
        document.getElementById("status").innerText = "Ready ✓";
        return;
    }

    const scores = {};
    alerts.forEach(a => {
        if (!scores[a.symbol]) scores[a.symbol] = [];
        scores[a.symbol].push(a.signal_score);
    });

    const ranked = Object.entries(scores)
        .map(([sym, arr]) => ({ sym, avg: arr.reduce((a,b)=>a+b,0)/arr.length }))
        .sort((a,b) => b.avg - a.avg)
        .slice(0, 10);

    const html = ranked.map(r => `
        <div class="item">
            <span>${r.sym}</span>
            <strong>${r.avg.toFixed(2)}</strong>
        </div>
    `).join("");

    document.getElementById("topCoins").innerHTML = html;
    document.getElementById("status").innerText = "Dashboard Loaded ✓";
}

buildDashboard();
