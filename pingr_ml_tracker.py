#!/usr/bin/env python3

import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np

LOG_FILE = "alert_log.jsonl"   # Upload this before analysis


# ----------------------------------------------------
# Helpers
# ----------------------------------------------------
def load_jsonl(path):
    data = []
    with open(path, "r") as f:
        for line in f:
            try: data.append(json.loads(line))
            except: pass
    return data


def safe_get(d, *keys):
    """Safely extract nested dict fields."""
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

    # -------------------------
    # 1. Load Log File
    # -------------------------
    path = Path(LOG_FILE)
    if not path.exists():
        print(f"❌ ERROR: {LOG_FILE} not found.")
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

    # Extract momentum fields
    df["event_type"] = df["event_type"].fillna("generic")
    df["meta_reason"] = df["meta"].apply(lambda x: x.get("reason") if isinstance(x, dict) else None)
    df["meta_gain"] = df["meta"].apply(lambda x: x.get("total_gain_percent") if isinstance(x, dict) else None)
    df["meta_drop"] = df["meta"].apply(lambda x: x.get("drop_percent") if isinstance(x, dict) else None)

    print("✅ Data cleaned\n")

    # ============================================================
    # ORIGINAL REPORTING (unchanged)
    # ============================================================
    print("📊 --- HIGH LEVEL SUMMARY ---\n")
    print("Total entries:", len(df))

    alerts = df[df["alert_sent"] == True]
    print("Total alerts sent:", len(alerts))

    print("\n🧮 --- SCORE DISTRIBUTION ---")
    print(df["signal_score"].describe())

    print("\n📉 --- RSI Stats for Alerts ---")
    if len(alerts) > 0:
        print("Mean RSI(15m):", alerts["rsi_15m"].mean())

    print("\n🔵 --- RSI RANGE ANALYSIS ---")
    rsi_data = df[df["rsi_15m"].notna()]
    if len(rsi_data) > 0:
        print(rsi_data["rsi_15m"].describe())
        alert_rsi = rsi_data[rsi_data["alert_sent"] == True]["rsi_15m"]
        if len(alert_rsi) > 0:
            print("\nRSI where alerts triggered:")
            print(alert_rsi.describe())
        if "rejected" in df.columns:
            fake_rsi = rsi_data[df["rejected"].notna()]["rsi_15m"]
            if len(fake_rsi) > 0:
                print("\nRSI of rejected spikes:")
                print(fake_rsi.describe())

    print("\n🔥 --- HEAT INDEX DISTRIBUTION ---")
    print(df["heat_index"].describe())

    print("\n🏆 --- TOP PERFORMING COINS ---")
    print(df.groupby("symbol")["signal_score"].mean().sort_values(ascending=False).head(15))

    print("\n🐢 --- LOWEST PERFORMING COINS ---")
    print(df.groupby("symbol")["signal_score"].mean().sort_values().head(10))

    print("\n📈 --- MACD ALIGNMENT BREAKDOWN ---")
    try:
        macd_counts = df["context"].apply(
            lambda x: x.get("macd_alignment") if isinstance(x, dict) else None
        ).value_counts()
        print(macd_counts)
    except:
        print("MACD context unavailable.")

    print("\n⛔ --- REJECTION REASONS ---")
    if "rejected" in df.columns:
        print(df["rejected"].dropna().explode().value_counts().head(15))

    print("\n⏰ --- ALERTS BY HOUR OF DAY ---")
    if len(alerts) > 0:
        print(alerts.groupby("hour").size())


    # ============================================================
    # ADVANCED MOMENTUM ANALYSIS
    # ============================================================
    print("\n⚡ Generating advanced momentum analysis...\n")

    cycles = []
    active = {}

    for _, row in df.sort_values("timestamp").iterrows():
        sym = row["symbol"]
        ts = row["timestamp"]

        # Start cycle when alert_sent == True
        if row.get("alert_sent"):
            active[sym] = {
                "symbol": sym,
                "start": ts,
                "start_rsi": row.get("rsi_15m"),
                "start_heat": row.get("heat_index"),
                "start_macd": safe_get(row, "context", "macd_alignment"),
                "end": None,
                "end_reason": None,
                "gain": None,
            }

        # End cycle when momentum_end
        if row["event_type"] == "momentum_end" and sym in active:
            active[sym]["end"] = ts
            active[sym]["end_reason"] = row.get("meta_reason")
            active[sym]["gain"] = row.get("meta_gain")
            cycles.append(active[sym])
            del active[sym]

    # Remaining open cycles
    for sym, c in active.items():
        c["end"] = None
        c["end_reason"] = "still_active"
        cycles.append(c)

    cycles_df = pd.DataFrame(cycles)

    if cycles_df.empty:
        print("⚠️ No momentum cycles detected.")
    else:
        cycles_df["duration_min"] = cycles_df.apply(
            lambda r: (r["end"] - r["start"]).total_seconds() / 60 if pd.notna(r["end"]) else None,
            axis=1
        )

        cycles_df["success_gain"] = cycles_df["gain"].apply(lambda g: g >= 1.2 if g is not None else False)
        cycles_df["success_structural"] = cycles_df["end_reason"].apply(lambda r: r in [None, "still_active"])
        cycles_df["failure"] = cycles_df["end_reason"].apply(lambda r: r in ["rsi_weakening", "price_drop_stop", "timeout"])

        cycles_df.to_csv("momentum_cycles.csv", index=False)

        print("📈 Momentum Cycles:", len(cycles_df))
        print("✔ Success (gain/structural):", int(cycles_df["success_gain"].sum() + cycles_df["success_structural"].sum()))
        print("❌ Failures:", int(cycles_df["failure"].sum()))
        print("⏳ Still active:", int(sum(cycles_df["end_reason"] == "still_active")))

        print("\n📉 Gain Distribution:")
        print(cycles_df["gain"].describe())

        # Symbol stats
        symbol_stats = cycles_df.groupby("symbol").agg({
            "success_gain": "sum",
            "success_structural": "sum",
            "failure": "sum",
            "gain": "mean",
            "duration_min": "mean"
        })
        symbol_stats.to_csv("momentum_per_symbol.csv")

        # Hour stats
        df["momentum_hour"] = df["timestamp"].dt.hour
        hour_perf = cycles_df.merge(df[["symbol", "hour"]], on="symbol", how="left").groupby("hour")["success_gain"].mean()
        hour_perf.to_csv("momentum_by_hour.csv")

        # RSI Bucket
        def rsi_bucket(x):
            if x is None: return None
            if x < 40: return "oversold"
            if 40 <= x < 55: return "ideal"
            if 55 <= x < 70: return "heated"
            return "overbought"

        cycles_df["rsi_bucket"] = cycles_df["start_rsi"].apply(rsi_bucket)
        cycles_df.groupby("rsi_bucket")["success_gain"].mean().to_csv("momentum_rsi_buckets.csv")

        # SAFE HEAT IMPACT (fixed)
        try:
            heat_bins = pd.qcut(cycles_df["start_heat"], q=4, duplicates="drop")
            heat_stats = cycles_df.groupby(heat_bins)["success_gain"].mean()
            heat_stats.to_csv("momentum_heat_impact.csv")
        except Exception as e:
            print(f"⚠️ Heat impact skipped: {e}")

        # MACD
        macd_stats = cycles_df.groupby("start_macd")["success_gain"].mean()
        macd_stats.to_csv("momentum_macd_stats.csv")

        # Summary JSON
        summary = {
            "total_cycles": len(cycles_df),
            "success_total": int(cycles_df["success_gain"].sum() + cycles_df["success_structural"].sum()),
            "failures": int(cycles_df["failure"].sum()),
            "still_active": int(sum(cycles_df["end_reason"] == "still_active")),
            "gain_distribution": cycles_df["gain"].describe().fillna(0).to_dict(),
        }
        with open("momentum_advanced_summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        print("\n💾 Advanced data saved:")
        print("   - momentum_cycles.csv")
        print("   - momentum_per_symbol.csv")
        print("   - momentum_by_hour.csv")
        print("   - momentum_rsi_buckets.csv")
        print("   - momentum_heat_impact.csv")
        print("   - momentum_macd_stats.csv")
        print("   - momentum_advanced_summary.json")

    # Save master dataset
    df.to_csv("pingr_cleaned_data.csv", index=False)
    print("\n🎉 Analysis Complete!")


if __name__ == "__main__":
    main()
