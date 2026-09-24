"""Copy the live CSV from the internal network share into this repo and push it.

Run this on a machine that has access to both the network share and git push
rights (e.g., on a schedule via sync_data.bat). Streamlit Community Cloud
redeploys automatically when the push lands, so the dashboard picks up the
new snapshot within a minute or two.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

SOURCE_PATH = r"\\azatshfs.intel.com\azatanalysis$\MAOATM\CDAT\zhaohua\CDAT_CW_Practice_data_his.csv"
REPO_DIR = Path(__file__).parent
DEST_PATH = REPO_DIR / "data" / "CDAT_CW_Practice_data_his.csv"


def refresh_local_snapshot(
    source_path: str | Path = SOURCE_PATH,
    destination_path: str | Path = DEST_PATH,
) -> tuple[bool, str]:
    """Copy the latest source CSV into the repo snapshot and report the outcome."""
    source = Path(source_path)
    destination = Path(destination_path)

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        try:
            df = pd.read_csv(destination)
            goal_col = (
                "monthly_practice_goal"
                if "monthly_practice_goal" in df.columns
                else "monthly practice goal"
                if "monthly practice goal" in df.columns
                else None
            )
            if (
                goal_col
                and "practice_lot_qty" in df.columns
                and "Complete_80_percent_tasks" not in df.columns
            ):
                df["Complete_80_percent_tasks"] = df["practice_lot_qty"] >= (df[goal_col] * 0.8)
                df.to_csv(destination, index=False)
        except Exception:
            pass
    except FileNotFoundError:
        return False, f"Source CSV not found: {source}"
    except OSError as exc:
        return False, f"Could not copy CSV from {source} to {destination}: {exc}"

    return True, f"Copied CSV from {source} to {destination}."


def run_git(*args: str) -> None:
    subprocess.run(["git", *args], cwd=REPO_DIR, check=True)


def main() -> None:
    ok, message = refresh_local_snapshot()
    if not ok:
        print(message, file=sys.stderr)
        sys.exit(1)

    run_git("add", str(DEST_PATH))
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=REPO_DIR
    )
    if result.returncode == 0:
        print("No data changes since last sync; nothing to push.")
        return

    run_git("commit", "-m", "Sync CW Practice data snapshot")
    run_git("push")
    print("Data snapshot synced and pushed.")


if __name__ == "__main__":
    main()
