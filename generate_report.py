"""Generate a static HTML report from the CW Practice data.

Writes an .html file to a shared network location so others can open it
directly in a browser (no web server / firewall access needed). Run
manually or on a schedule (see start_report.bat).
"""
import pandas as pd

CSV_PATH = r"\\azatshfs.intel.com\azatanalysis$\MAOATM\CDAT\zhaohua\CDAT_CW_Practice_data_his.csv"
OUTPUT_PATH = r"\\azatshfs.intel.com\azatanalysis$\MAOATM\CDAT\zhaohua\CDAT_CW_Practice_Report.html"


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "month": "site_month",
        "monthly_practice_goal": "monthly practice goal",
    }
    rename = {
        source: target
        for source, target in aliases.items()
        if source in df.columns and target not in df.columns
    }
    return df.rename(columns=rename)


def build_goal_summary(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby(["name", "site_month", "module", "operation"])
        .agg(
            team=("team", "first"),
            super=("super", "first"),
            practiced_qty=("practice_lot_qty", "sum"),
            **{"monthly practice goal": ("monthly practice goal", "max")},
        )
        .reset_index()
    )
    summary = summary[
        ["site_month", "module", "name", "team", "super", "operation", "practiced_qty", "monthly practice goal"]
    ]
    summary["attainment_%"] = (
        summary["practiced_qty"] / summary["monthly practice goal"].replace(0, pd.NA) * 100
    ).round(1)
    summary["gap_to_goal"] = summary["monthly practice goal"] - summary["practiced_qty"]
    summary["met_goal"] = summary["practiced_qty"] >= summary["monthly practice goal"]
    return summary.sort_values("attainment_%", ascending=True).reset_index(drop=True)


def highlight_goal(row: pd.Series) -> list[str]:
    color = "background-color: #c6efce" if row["met_goal"] else "background-color: #ffc7ce"
    return [color] * len(row)


def main() -> None:
    df = normalize_columns(pd.read_csv(CSV_PATH))

    goal_summary = build_goal_summary(df)
    by_site_month = df.groupby("site_month")["practice_lot_qty"].sum().sort_index()
    by_module = df.groupby("module")["practice_lot_qty"].sum().sort_values(ascending=False)
    by_name = (
        df.groupby("name")
        .agg(practice_qty=("practice_lot_qty", "sum"), lots=("name", "count"))
        .sort_values("practice_qty", ascending=False)
    )

    goal_html = goal_summary.style.apply(highlight_goal, axis=1).format({"attainment_%": "{:.1f}%"}).to_html()
    generated_at = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>CW Practice Data Report</title>
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; }}
h1 {{ font-size: 22px; }}
h2 {{ font-size: 18px; margin-top: 32px; }}
table {{ border-collapse: collapse; font-size: 13px; }}
th, td {{ border: 1px solid #ddd; padding: 4px 8px; }}
th {{ background-color: #f2f2f2; }}
.caption {{ color: #666; font-size: 12px; }}
</style>
</head>
<body>
<h1>CW Practice Data Report</h1>
<p class="caption">Generated {generated_at}</p>

<h2>Goal comparison</h2>
{goal_html}

<h2>Trend by site month (practice lot qty)</h2>
{by_site_month.to_frame("practice_lot_qty").to_html()}

<h2>By operator</h2>
{by_name.to_html()}

<h2>By module</h2>
{by_module.to_frame("practice_lot_qty").to_html()}
</body>
</html>
"""
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Report written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

