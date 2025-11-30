#!/usr/bin/env python3

import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np

LOG_FILE = "alert_log.jsonl"   # Upload this before analysis
OUTPUT_DIR = Path("docs")      # <-- NEW: all output goes into /docs
OUTPUT_DIR.mkdir(exist_ok=True)


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


def main():
    print("🔍 Pingr ML Tracker Starting...\n")

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

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["hour"] = df["timestamp"].dt.hour

    numeric_cols = ["rsi_15m", "signal_score", "heat_index"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["event_type"] = df["event_type"].fillna("generic")
    df["meta_reason"] = df["meta"].apply(lambda x: x.get("reason") if isinstance(x, dict) else None)
    df["meta_gain"] = df["meta"].apply(lambda x: x.get("total_gain_percent") if isinstance(x, dict) else None)
    df["meta_drop"] = df["meta"].apply(lambda x: x.get("drop_percent") if isinstance(x, dict) else None)

    print("✅ Data cleaned\n")

    alerts = df[df["alert_sent"] == True]

    print("📊 --- HIGH LEVEL SUMMARY ---\n")
    print("Total entries:", len(df))
    print("Total alerts sent:", len(alerts))


    # ==================================================
    # MOMENTUM ENGINE
    # ==================================================
    print("\n⚡ Generating advanced momentum analysis...\n")

    cycles = []
    active = {}

    for _, row in df.sort_values("timestamp").iterrows():
        sym = row["symbol"]
        ts = row["timestamp"]

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

        if row["event_type"] == "momentum_end" and sym in active:
            active[sym]["end"] = ts
            active[sym]["end_reason"] = row.get("meta_reason")
            active[sym]["gain"] = row.get("meta_gain")
            cycles.append(active[sym])
            del active[sym]

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

        # SAVE ALL FILES INSIDE /docs/
        (OUTPUT_DIR / "momentum_cycles.csv").write_text(cycles_df.to_csv(index=False))

        symbol_stats = cycles_df.groupby("symbol").agg({
            "success_gain": "sum",
            "success_structural": "sum",
            "failure": "sum",
            "gain": "mean",
            "duration_min": "mean"
        })
        symbol_stats.to_csv(OUTPUT_DIR / "momentum_per_symbol.csv")

        df["momentum_hour"] = df["timestamp"].dt.hour
        hour_perf = cycles_df.merge(df[["symbol", "hour"]], on="symbol", how="left").groupby("hour")["success_gain"].mean()
        hour_perf.to_csv(OUTPUT_DIR / "momentum_by_hour.csv")

        def rsi_bucket(x):
            if x is None: return None
            if x < 40: return "oversold"
            if 40 <= x < 55: return "ideal"
            if 55 <= x < 70: return "heated"
            return "overbought"

        cycles_df["rsi_bucket"] = cycles_df["start_rsi"].apply(rsi_bucket)
        cycles_df.groupby("rsi_bucket")["success_gain"].mean().to_csv(OUTPUT_DIR / "momentum_rsi_buckets.csv")


        try:
            heat_bins = pd.qcut(cycles_df["start_heat"], q=4, duplicates="drop")
            heat_stats = cycles_df.groupby(heat_bins)["success_gain"].mean()
            heat_stats.to_csv(OUTPUT_DIR / "momentum_heat_impact.csv")
        except:
            pass

        macd_stats = cycles_df.groupby("start_macd")["success_gain"].mean()
        macd_stats.to_csv(OUTPUT_DIR / "momentum_macd_stats.csv")

        summary = {
            "total_cycles": len(cycles_df),
            "success_total": int(cycles_df["success_gain"].sum() + cycles_df["success_structural"].sum()),
            "failures": int(cycles_df["failure"].sum()),
            "still_active": int(sum(cycles_df["end_reason"] == "still_active")),
            "gain_distribution": cycles_df["gain"].describe().fillna(0).to_dict(),
        }
        with open(OUTPUT_DIR / "momentum_advanced_summary.json", "w") as f:
            json.dump(summary, f, indent=2)

    # SAVE MAIN CSV → docs/
    df.to_csv(OUTPUT_DIR / "pingr_cleaned_data.csv", index=False)

    print("\n🎉 Analysis Complete — saved to /docs/!\n")


if __name__ == "__main__":
    main()
