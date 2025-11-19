#!/usr/bin/env python3

import json
import pandas as pd
from datetime import datetime
from pathlib import Path

LOG_FILE = "alert_log.jsonl"   # The file you will upload manually

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
    df["rsi_15m"] = pd.to_numeric(df.get("rsi_15m"), errors="coerce")
    df["signal_score"] = pd.to_numeric(df.get("signal_score"), errors="coerce")
    df["heat_index"] = pd.to_numeric(df.get("heat_index"), errors="coerce")

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

    # -------------------------
    # 6. Save cleaned data
    # -------------------------
    df.to_csv("pingr_cleaned_data.csv", index=False)
    print("\n💾 Saved: pingr_cleaned_data.csv")

    print("\n🎉 Analysis Complete!")

if __name__ == "__main__":
    main()
