import argparse
import json
import os
import sys

# Add backend to path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.adapters.fastf1_replay_builder import extract_snapshots

def main():
    parser = argparse.ArgumentParser(description="Build NDJSON replay file from FastF1")
    parser.add_argument("--year", type=int, default=2024, help="F1 Season Year")
    parser.add_argument("--gp", type=str, default="Australia", help="Grand Prix name")
    parser.add_argument("--session", type=str, default="R", help="Session identifier (e.g., R for Race)")
    parser.add_argument("--session-id", type=str, default="replay_aus_2024_r", help="Session ID to embed in snapshots")
    parser.add_argument("--out", type=str, default="data/replay/aus_2024_r.ndjson", help="Output NDJSON path")

    args = parser.parse_args()

    print(f"Fetching FastF1 data for {args.year} {args.gp} {args.session}...")
    try:
        snapshots = extract_snapshots(args.year, args.gp, args.session, args.session_id)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return

    print(f"Generated {len(snapshots)} coarse snapshots. Writing to {args.out}...")
    
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    
    with open(args.out, "w") as f:
        for snap in snapshots:
            # model_dump_json serializes Pydantic models to JSON strings
            f.write(snap.model_dump_json(exclude_none=False) + "\n")
            
    print("Done!")

if __name__ == "__main__":
    main()
