// Dashboard Lite - DEBUG MODE ENABLED (FINAL WORKING VERSION)

async function loadCSV() {
    try {
        console.log("Fetching CSV from: ./pingr_cleaned_data.csv (inside /docs)");

        // CSV lives in /docs, same folder as app.js
        const res = await fetch("./pingr_cleaned_data.csv", { cache: "no-store" });

        if (!res.ok) {
            document.getElementById("status").innerText =
                "❌ CSV not found in /docs. Run ML workflow.";
            return null;
        }

        const text = await res.text();
        console.log("Raw CSV text loaded:", text.slice(0, 300));

        return text.trim().split("\n").map(r => r.split(","));
    } catch (err) {
        console.error("❌ CSV load error:", err);
        document.getElementById("status").innerText = "❌ Unable to load CSV.";
        return null;
    }
}

function parseCSV(header, rows) {
    console.log("CSV Header:", header);

    const items = [];

    rows.forEach((r, idx) => {
        if (r.length !== header.length) {
            console.warn("⚠️ Row length mismatch at line", idx + 2, r);
            return;
        }
        let obj = {};
        header.forEach((h, i) => obj[h] = r[i]);
        items.push(obj);
    });

    console.log("Parsed items count:", items.length);
    return items;
}

async function buildDashboard() {
    document.getElementById("status").innerText = "Loading... (Debug ON)";

    const rows = await loadCSV();
    if (!rows) return;

    const header = rows[0];
    const data = parseCSV(header, rows.slice(1));

    console.log("Full parsed dataset:", data.slice(0, 5));

    // Convert types
    data.forEach(d => {
        d.alert_sent = (d.alert_sent === "True" || d.alert_sent === "true");
        d.signal_score = parseFloat(d.signal_score) || 0;
    });

    const alerts = data.filter(d => d.alert_sent);

    console.log("Filtered alerts:", alerts);

    if (alerts.length === 0) {
        document.getElementById("topCoins").innerHTML =
            "<i>No alerts found in dataset.</i>";
        document.getElementById("status").innerText =
            "Loaded ✓ (but no alerts)";
        return;
    }

    // Group by symbol
    const scores = {};
    alerts.forEach(a => {
        if (!scores[a.symbol]) scores[a.symbol] = [];
        scores[a.symbol].push(a.signal_score);
    });

    console.log("Grouped score object:", scores);

    const ranked = Object.entries(scores)
        .map(([sym, arr]) => ({
            sym,
            avg: arr.reduce((a, b) => a + b, 0) / arr.length
        }))
        .sort((a, b) => b.avg - a.avg)
        .slice(0, 10);

    console.log("Top coins ranked:", ranked);

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
