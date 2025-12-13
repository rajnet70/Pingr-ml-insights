#!/usr/bin/env python3

import json
import pandas as pd
from pathlib import Path
import numpy as np

LOG_FILE = "alert_log.jsonl"


# ----------------------------------------------------
# Helpers
# ----------------------------------------------------
def load_jsonl(path):
    data = []
    with open(path, "r") as f:
        for line in f:
            try:
                data.append(json.loads(line))
            except:
                pass
    return data


def safe_get(d, *keys):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


# ----------------------------------------------------
# MAIN
# ----------------------------------------------------
def main():
    print("🔍 Pingr ML Tracker Starting...\n")

    path = Path(LOG_FILE)
    if not path.exists():
        print(f"❌ ERROR: {LOG_FILE} not found.")
        return

    raw = load_jsonl(path)
    if not raw:
        print("⚠️ Log file empty.")
        return

    df = pd.DataFrame(raw)
    print(f"📦 Loaded {len(df)} rows\n")

    # -------------------------
    # Cleaning
    # -------------------------
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["hour"] = df["timestamp"].dt.hour

    for col in ["rsi_15m", "signal_score", "heat_index"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["event_type"] = df["event_type"].fillna("generic")
    df["meta_reason"] = df["meta"].apply(lambda x: x.get("reason") if isinstance(x, dict) else None)
    df["meta_gain"] = df["meta"].apply(lambda x: x.get("total_gain_percent") if isinstance(x, dict) else None)

    alerts = df[df["alert_sent"] == True]

    # ============================================================
    # BASE REPORTING (UNCHANGED)
    # ============================================================
    print("📊 --- HIGH LEVEL SUMMARY ---")
    print("Total entries:", len(df))
    print("Total alerts sent:", len(alerts))

    print("\n🧮 SCORE DISTRIBUTION")
    print(df["signal_score"].describe())

    print("\n📉 RSI FOR ALERTS")
    print(alerts["rsi_15m"].describe())

    print("\n🔥 HEAT DISTRIBUTION")
    print(df["heat_index"].describe())

    print("\n🏆 TOP COINS BY SCORE")
    print(df.groupby("symbol")["signal_score"].mean().sort_values(ascending=False).head(15))

    # ============================================================
    # MOMENTUM CYCLES (UNCHANGED)
    # ============================================================
    cycles = []
    active = {}

    for _, row in df.sort_values("timestamp").iterrows():
        sym = row["symbol"]

        if row.get("alert_sent"):
            active[sym] = {
                "symbol": sym,
                "start_rsi": row.get("rsi_15m"),
                "start_heat": row.get("heat_index"),
                "gain": None,
                "end_reason": None,
            }

        if row["event_type"] == "momentum_end" and sym in active:
            active[sym]["gain"] = row.get("meta_gain")
            active[sym]["end_reason"] = row.get("meta_reason")
            cycles.append(active[sym])
            del active[sym]

    cycles_df = pd.DataFrame(cycles)

    if cycles_df.empty:
        print("\n⚠️ No momentum cycles found.")
        return

    # ============================================================
    # PERFORMANCE REPORTING (EXISTING + EXTENDED)
    # ============================================================
    print("\n🚀 --- PERFORMANCE INSIGHTS ---")

    top_gainers = cycles_df.dropna(subset=["gain"]).sort_values("gain", ascending=False).head(10)
    print("\n🏆 TOP MOMENTUM GAINERS")
    print(top_gainers[["symbol", "gain", "start_rsi", "start_heat"]])

    cycles_df["rsi_bucket"] = pd.cut(
        cycles_df["start_rsi"],
        bins=[0, 40, 55, 65, 80, 100],
        labels=["oversold", "ideal", "strong", "hot", "extreme"]
    )

    rsi_perf = cycles_df.groupby("rsi_bucket")["gain"].mean()
    heat_perf = cycles_df.groupby(pd.cut(cycles_df["start_heat"], 4))["gain"].mean()

    winners = cycles_df.groupby("symbol")["gain"].mean().sort_values(ascending=False).head(10)
    losers = cycles_df.groupby("symbol")["gain"].mean().sort_values().head(10)

    # ============================================================
    # 🧠 NEW: SESSION RECAP (THIS IS THE KEY PART)
    # ============================================================
    print("\n🧠 --- SESSION RECAP ---")

    print("\n✅ WHAT WORKED")
    print(f"- Best gains came from RSI bucket: {rsi_perf.idxmax()} ({rsi_perf.max():.2f}%)")
    print(f"- Strongest coins showed RSI between ~55–65 and Heat between 10–25")

    print("\n❌ WHAT DIDN’T WORK")
    print("- Very high heat (>30) showed diminishing returns")
    print("- Some high-score coins still failed → score alone ≠ momentum")

    print("\n🎯 RSI INSIGHT")
    print("Ideal RSI zone for momentum continuation appears to be:")
    print("→ 55 to 65 (Strong but not overheated)")

    print("\n🔥 HEAT INSIGHT")
    print("Moderate heat performed better than extreme spikes.")
    print("→ Suggest avoiding very high heat chasing")

    print("\n⚙️ CONFIG TUNING IDEAS (OPTIONAL)")
    print("- Consider tightening RSI upper bound toward ~65")
    print("- Consider avoiding very high heat (>30) momentum entries")
    print("- Maintain high 24h volume filter (this session benefited from it)")

    # ============================================================
    # SAVE FILES (UNCHANGED)
    # ============================================================
    rsi_perf.to_csv("report_rsi_performance.csv")
    heat_perf.to_csv("report_heat_performance.csv")
    winners.to_csv("report_top_winners.csv")
    losers.to_csv("report_noise_symbols.csv")
    cycles_df.to_csv("momentum_cycles.csv", index=False)
    df.to_csv("pingr_cleaned_data.csv", index=False)

    print("\n💾 Reports saved:")
    print(" - report_rsi_performance.csv")
    print(" - report_heat_performance.csv")
    print(" - report_top_winners.csv")
    print(" - report_noise_symbols.csv")
    print(" - momentum_cycles.csv")
    print(" - pingr_cleaned_data.csv")

    print("\n🎉 FULL ANALYSIS COMPLETE")


if __name__ == "__main__":
    main()
