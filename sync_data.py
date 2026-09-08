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

SOURCE_PATH = r"\\azatshfs.intel.com\azatanalysis$\MAOATM\CDAT\zhaohua\CDAT_CW_Practice_data_his.csv"
REPO_DIR = Path(__file__).parent
DEST_PATH = REPO_DIR / "data" / "CDAT_CW_Practice_data_his.csv"


def run_git(*args: str) -> None:
    subprocess.run(["git", *args], cwd=REPO_DIR, check=True)


def main() -> None:
    DEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copyfile(SOURCE_PATH, DEST_PATH)
    except OSError as e:
        print(f"Could not read source CSV from network share: {e}", file=sys.stderr)
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
