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
    df = pd.DataFrame(raw)

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["hour"] = df["timestamp"].dt.hour

    for col in ["rsi_15m", "signal_score", "heat_index"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["event_type"] = df["event_type"].fillna("generic")
    df["meta_gain"] = df["meta"].apply(lambda x: x.get("total_gain_percent") if isinstance(x, dict) else None)
    df["meta_reason"] = df["meta"].apply(lambda x: x.get("reason") if isinstance(x, dict) else None)

    alerts = df[df["alert_sent"] == True]

    print("📊 --- HIGH LEVEL SUMMARY ---")
    print("Total entries:", len(df))
    print("Total alerts sent:", len(alerts))

    # ============================================================
    # MOMENTUM CYCLES
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
                "start_score": row.get("signal_score"),
                "gain": None
            }

        if row["event_type"] == "momentum_end" and sym in active:
            active[sym]["gain"] = row.get("meta_gain")
            cycles.append(active[sym])
            del active[sym]

    cycles_df = pd.DataFrame(cycles).dropna(subset=["gain"])

    # ============================================================
    # 🧠 NEW REPORT 1: ALERT EFFECTIVENESS
    # ============================================================
    print("\n📊 ALERT EFFECTIVENESS")
    print("Alerts sent:", len(alerts))
    print("Momentum cycles:", len(cycles_df))
    print("Conversion rate:",
          round(len(cycles_df) / max(len(alerts), 1) * 100, 2), "%")

    # ============================================================
    # 📈 NEW REPORT 2: SCORE vs GAIN
    # ============================================================
    cycles_df["score_bucket"] = pd.cut(
        cycles_df["start_score"],
        bins=[0, 7, 9, 12, 20],
        labels=["low", "mid", "strong", "extreme"]
    )

    score_perf = cycles_df.groupby("score_bucket")["gain"].mean()

    print("\n📈 SCORE EFFECTIVENESS")
    print(score_perf)

    score_perf.to_csv("report_score_effectiveness.csv")

    # ============================================================
    # 🎯 NEW REPORT 3: IDEAL ENTRY ZONES
    # ============================================================
    cycles_df["rsi_bucket"] = pd.cut(
        cycles_df["start_rsi"],
        bins=[0, 45, 55, 65, 80],
        labels=["low", "warm", "ideal", "overheated"]
    )

    cycles_df["heat_bucket"] = pd.cut(
        cycles_df["start_heat"],
        bins=[0, 10, 20, 30, 100],
        labels=["low", "moderate", "high", "extreme"]
    )

    rsi_perf = cycles_df.groupby("rsi_bucket")["gain"].mean()
    heat_perf = cycles_df.groupby("heat_bucket")["gain"].mean()

    print("\n🎯 RSI PERFORMANCE")
    print(rsi_perf)

    print("\n🔥 HEAT PERFORMANCE")
    print(heat_perf)

    rsi_perf.to_csv("report_rsi_performance.csv")
    heat_perf.to_csv("report_heat_performance.csv")

    # ============================================================
    # 🧠 AUTO SESSION TUNING SUMMARY
    # ============================================================
    print("\n🧠 --- SESSION TUNING SUMMARY ---")

    best_rsi = rsi_perf.idxmax()
    best_heat = heat_perf.idxmax()
    best_score = score_perf.idxmax()

    print(f"✅ Best RSI zone: {best_rsi}")
    print(f"🔥 Best Heat zone: {best_heat}")
    print(f"🏆 Best Score range: {best_score}")

    print("\n⚙️ CONFIG SUGGESTIONS")
    if best_rsi == "ideal":
        print("- Keep RSI upper bound near ~65")
    if best_heat == "moderate":
        print("- Avoid extreme heat chasing (>30)")
    if best_score in ["strong", "extreme"]:
        print("- Consider raising min_score_alert")

    print("\n💾 Reports saved:")
    print(" - report_score_effectiveness.csv")
    print(" - report_rsi_performance.csv")
    print(" - report_heat_performance.csv")

    print("\n🎉 FULL ANALYSIS COMPLETE")


if __name__ == "__main__":
    main()
