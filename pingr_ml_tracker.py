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
        print("❌ Log file not found.")
        return

    df = pd.DataFrame(load_jsonl(path))
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
    df["meta_gain"] = df["meta"].apply(lambda x: x.get("total_gain_percent") if isinstance(x, dict) else None)
    df["meta_reason"] = df["meta"].apply(lambda x: x.get("reason") if isinstance(x, dict) else None)

    alerts = df[df["alert_sent"] == True]

    # ============================================================
    # ① BASELINE REPORTING (UNCHANGED)
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
    # ② MOMENTUM CYCLES
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
                "score": row.get("signal_score"),
                "gain": None,
            }

        if row["event_type"] == "momentum_end" and sym in active:
            active[sym]["gain"] = row.get("meta_gain")
            cycles.append(active[sym])
            del active[sym]

    cycles_df = pd.DataFrame(cycles).dropna(subset=["gain"])
    cycles_df.to_csv("momentum_cycles.csv", index=False)

    # ============================================================
    # ③ EFFECTIVENESS REPORTING (NEW)
    # ============================================================
    print("\n📊 ALERT EFFECTIVENESS")
    print("Momentum cycles:", len(cycles_df))
    if len(alerts) > 0:
        print("Conversion rate:", round(len(cycles_df) / len(alerts) * 100, 2), "%")

    # Score buckets
    cycles_df["score_bucket"] = pd.cut(
        cycles_df["score"],
        bins=[0, 5, 8, 12, 100],
        labels=["low", "mid", "strong", "extreme"]
    )

    score_perf = cycles_df.groupby("score_bucket")["gain"].mean()
    print("\n📈 SCORE EFFECTIVENESS")
    print(score_perf)

    # RSI buckets
    cycles_df["rsi_bucket"] = pd.cut(
        cycles_df["start_rsi"],
        bins=[0, 45, 55, 65, 100],
        labels=["low", "warm", "ideal", "overheated"]
    )

    rsi_perf = cycles_df.groupby("rsi_bucket")["gain"].mean()
    print("\n🎯 RSI PERFORMANCE")
    print(rsi_perf)

    # Heat buckets
    cycles_df["heat_bucket"] = pd.cut(
        cycles_df["start_heat"],
        bins=[0, 5, 15, 30, 100],
        labels=["low", "moderate", "high", "extreme"]
    )

    heat_perf = cycles_df.groupby("heat_bucket")["gain"].mean()
    print("\n🔥 HEAT PERFORMANCE")
    print(heat_perf)

    # Save reports
    score_perf.to_csv("report_score_effectiveness.csv")
    rsi_perf.to_csv("report_rsi_performance.csv")
    heat_perf.to_csv("report_heat_performance.csv")

    # ============================================================
    # ④ SESSION RECAP (HUMAN-READABLE)
    # ============================================================
    print("\n🧠 --- SESSION TUNING SUMMARY ---")

    print("✅ Best RSI zone:", rsi_perf.idxmax())
    print("🔥 Best Heat zone:", heat_perf.idxmax())
    print("🏆 Best Score range:", score_perf.idxmax())

    print("\n⚙️ CONFIG SUGGESTIONS")
    print("- Keep RSI upper bound near ~65")
    print("- Avoid chasing extreme heat spikes")
    print("- Strong score outperforms extreme score")

    print("\n🎉 FULL ANALYSIS COMPLETE")


if __name__ == "__main__":
    main()
