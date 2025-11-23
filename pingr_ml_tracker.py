#!/usr/bin/env python3

import json
import pandas as pd
from datetime import datetime
from pathlib import Path

LOG_FILE = "alert_log.jsonl"   # The file you upload manually

def load_jsonl(path):
    data = []
    with open(path, "r") as f:
        for line in f:
            try:
                data.append(json.loads(line))
            except:
                pass
    return data


def main():
    print("🔍 Pingr ML Tracker Starting...\n")

    # -------------------------
    # 1. Load Log File
    # -------------------------
    path = Path(LOG_FILE)
    if not path.exists():
        print(f"❌ ERROR: {LOG_FILE} not found in repo.")
        return

    print(f"📁 Reading: {LOG_FILE}")
    raw = load_jsonl(path)

    if not raw:
        print("⚠️ Log file is empty or unreadable.")
        return

    df = pd.DataFrame(raw)
    print(f"📦 Loaded {len(df)} rows\n")

    # -------------------------
    # 2. Clean Data
    # -------------------------
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["hour"] = df["timestamp"].dt.hour

    numeric_cols = ["rsi_15m", "signal_score", "heat_index"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    print("✅ Data cleaned\n")

    # -------------------------
    # 3. Summary
    # -------------------------
    print("📊 --- HIGH LEVEL SUMMARY ---\n")
    print("Total entries:", len(df))

    alerts = df[df["alert_sent"] == True]
    print("Total alerts sent:", len(alerts))

    # -------------------------
    # 4. Score Distribution
    # -------------------------
    print("\n🧮 --- SCORE DISTRIBUTION ---")
    print(df["signal_score"].describe())

    # -------------------------
    # 5. Average 15m RSI on Alerts
    # -------------------------
    print("\n📉 --- RSI Stats for Alerts ---")
    if len(alerts) > 0:
        print("Mean RSI(15m):", alerts["rsi_15m"].mean())
    else:
        print("No alerts found.")

    # -------------------------------------------------
    # 6. RSI RANGE ANALYSIS
    # -------------------------------------------------
    print("\n🔵 --- RSI RANGE ANALYSIS ---\n")

    if "rsi_15m" in df.columns:
        rsi_data = df[df["rsi_15m"].notna()]

        if len(rsi_data) > 0:
            print("RSI range of ALL data:")
            print(rsi_data["rsi_15m"].describe())

            # Alerts only
            alert_rsi = rsi_data[rsi_data["alert_sent"] == True]["rsi_15m"]
            if len(alert_rsi) > 0:
                print("\nRSI where alerts actually triggered:")
                print(alert_rsi.describe())

            # Fake spikes (rejected)
            if "rejected" in df.columns:
                fake_rsi = rsi_data[df["rejected"].notna()]["rsi_15m"]
                if len(fake_rsi) > 0:
                    print("\nRSI where FAKE spikes occurred (rejected signals):")
                    print(fake_rsi.describe())

    # -------------------------------------------------
    # 7. NEW — Heat Index Distribution
    # -------------------------------------------------
    print("\n🔥 --- HEAT INDEX DISTRIBUTION ---")
    if "heat_index" in df.columns:
        print(df["heat_index"].describe())

    # -------------------------------------------------
    # 8. NEW — Top Coins by Average Score
    # -------------------------------------------------
    print("\n🏆 --- TOP PERFORMING COINS (Avg Score) ---")
    if "signal_score" in df.columns:
        top = df.groupby("symbol")["signal_score"].mean().sort_values(ascending=False).head(15)
        print(top)

    # -------------------------------------------------
    # 9. NEW — Weakest Coins by Score
    # -------------------------------------------------
    print("\n🐢 --- LOWEST PERFORMING COINS (Avg Score) ---")
    worst = df.groupby("symbol")["signal_score"].mean().sort_values().head(10)
    print(worst)

    # -------------------------------------------------
    # 10. NEW — MACD Alignment Breakdown
    # -------------------------------------------------
    print("\n📈 --- MACD ALIGNMENT BREAKDOWN ---")
    try:
        macd_counts = df["context"].apply(
            lambda x: x.get("macd_alignment") if isinstance(x, dict) else None
        ).value_counts()
        print(macd_counts)
    except:
        print("MACD context not available.")

    # -------------------------------------------------
    # 11. NEW — Rejection Reason Frequency
    # -------------------------------------------------
    print("\n⛔ --- REJECTION REASONS ---")
    if "rejected" in df.columns:
        reasons = df["rejected"].dropna().explode().value_counts().head(15)
        print(reasons)

    # -------------------------------------------------
    # 12. NEW — Alert Frequency by Hour (for timing optimization)
    # -------------------------------------------------
    print("\n⏰ --- ALERTS BY HOUR OF DAY ---")
    if len(alerts) > 0:
        hourly = alerts.groupby("hour").size()
        print(hourly)

    # -------------------------------------------------
    # 13. Save cleaned data
    # -------------------------------------------------
    df.to_csv("pingr_cleaned_data.csv", index=False)
    print("\n💾 Saved: pingr_cleaned_data.csv")

    print("\n🎉 Analysis Complete!")


if __name__ == "__main__":
    main()
