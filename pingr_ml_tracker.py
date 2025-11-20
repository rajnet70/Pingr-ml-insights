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

    # -------------------------------------------------
    # 6. RSI RANGE ANALYSIS  (NEW SECTION YOU REQUESTED)
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

            # Strong / Very Strong / Extreme only
            if "alert_type" in df.columns:
                strong_rsi = rsi_data[
                    df["alert_type"].isin(["Strong", "Very Strong", "Extreme"])
                ]["rsi_15m"]

                if len(strong_rsi) > 0:
                    print("\nRSI values for STRONG category alerts:")
                    print(strong_rsi.describe())

            # Fake spikes (has rejections)
            if "rejected" in df.columns:
                fake_rsi = rsi_data[df["rejected"].notna()]["rsi_15m"]
                if len(fake_rsi) > 0:
                    print("\nRSI where FAKE spikes occurred (rejected signals):")
                    print(fake_rsi.describe())
        else:
            print("No usable RSI data found.")

    # -------------------------------------------------

    # -------------------------
    # 7. Save cleaned data
    # -------------------------
    df.to_csv("pingr_cleaned_data.csv", index=False)
    print("\n💾 Saved: pingr_cleaned_data.csv")

    print("\n🎉 Analysis Complete!")


if __name__ == "__main__":
    main()
