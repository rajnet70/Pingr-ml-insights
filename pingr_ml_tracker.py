#!/usr/bin/env python3

import json
import pandas as pd
from pathlib import Path

LOG_FILE = "alert_log.jsonl"
OUTPUT_DIR = Path("docs")
OUTPUT_DIR.mkdir(exist_ok=True)


def load_jsonl(path):
    rows = []
    with open(path, "r") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except:
                pass
    return rows


def safe_get(d, *keys):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def main():
    print("🔍 Pingr ML Tracker Starting...\n")

    raw = load_jsonl(LOG_FILE)
    df = pd.DataFrame(raw)

    print(f"📦 Loaded {len(df)} rows\n")

    # Convert columns before ANY looping or iteration
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["hour"] = df["timestamp"].dt.hour
    df["alert_sent"] = df["alert_sent"].astype(bool)

    for col in ["rsi_15m", "signal_score", "heat_index"]:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["event_type"] = df["event_type"].fillna("generic")

    df["meta_reason"] = df["meta"].apply(
        lambda x: x.get("reason") if isinstance(x, dict) else None
    )
    df["meta_gain"] = df["meta"].apply(
        lambda x: x.get("total_gain_percent") if isinstance(x, dict) else None
    )

    print("Total alerts sent in DF:", df["alert_sent"].sum())

    # SAVE CLEAN CSV **BEFORE** any loops that destroy type integrity
    df.to_csv(OUTPUT_DIR / "pingr_cleaned_data.csv", index=False)
    print("✔ Saved clean CSV to docs/pingr_cleaned_data.csv\n")

    # -------- MOMENTUM ENGINE (SEPARATE, SAFE) --------
    cycles = []
    active = {}

    for row in df.sort_values("timestamp").itertuples():
        sym = row.symbol

        if row.alert_sent:
            active[sym] = {
                "symbol": sym,
                "start": row.timestamp,
                "start_rsi": row.rsi_15m,
                "start_heat": row.heat_index,
                "start_macd": safe_get(row._asdict(), "context", "macd_alignment"),
                "end": None,
                "end_reason": None,
                "gain": None,
            }

        if row.event_type == "momentum_end" and sym in active:
            active[sym]["end"] = row.timestamp
            active[sym]["end_reason"] = row.meta_reason
            active[sym]["gain"] = row.meta_gain
            cycles.append(active[sym])
            del active[sym]

    # Save momentum results
    cycles_df = pd.DataFrame(cycles)
    cycles_df.to_csv(OUTPUT_DIR / "momentum_cycles.csv", index=False)

    print("🎉 Analysis Complete — saved to /docs/!\n")


if __name__ == "__main__":
    main()
