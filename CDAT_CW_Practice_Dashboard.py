import os

import pandas as pd
import streamlit as st

from sync_data import SOURCE_PATH, refresh_local_snapshot

# Streamlit Community Cloud has no access to the internal Intel network share, so the
# default path is a snapshot committed to this repo (see sync_data.py). Set the
# CW_CSV_PATH env var to point at the live UNC share when running on-prem.
DEFAULT_CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "CDAT_CW_Practice_data_his.csv")
CSV_PATH = os.environ.get("CW_CSV_PATH", DEFAULT_CSV_PATH)

st.set_page_config(page_title="CW Practice Dashboard", page_icon="📊", layout="wide")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "month": "site_month",
        "monthly_practice_goal": "monthly practice goal",
        "complete_80_percent_tasks": "Complete_80_percent_tasks",
    }
    rename = {
        source: target
        for source, target in aliases.items()
        if source in df.columns and target not in df.columns
    }
    normalized = df.rename(columns=rename)
    if "Complete_80_percent_tasks" not in normalized.columns:
        normalized["Complete_80_percent_tasks"] = ""
    else:
        normalized["Complete_80_percent_tasks"] = normalized["Complete_80_percent_tasks"].fillna("")
    if "practice_shift_qty" not in normalized.columns:
        normalized["practice_shift_qty"] = 0
    return normalized


@st.cache_data(ttl=600)
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    return normalize_columns(df)


st.title("📊 CW Practice Data Dashboard")

def refresh_dashboard_data() -> None:
    """Pull the newest snapshot from the source share when available, then reload the cache."""
    if CSV_PATH == DEFAULT_CSV_PATH and os.path.exists(SOURCE_PATH):
        ok, message = refresh_local_snapshot(SOURCE_PATH, CSV_PATH)
        if not ok:
            st.warning(message)
            return
        st.success(message)

    load_data.clear()
    st.rerun()


with st.sidebar:
    st.header("Filters")
    if st.button("🔄 Refresh data"):
        refresh_dashboard_data()

try:
    df = load_data(CSV_PATH)
except FileNotFoundError:
    st.error(f"Could not find CSV file at:\n\n{CSV_PATH}")
    st.stop()
except OSError as e:
    st.error(f"Could not read CSV file (network path may be unavailable): {e}")
    st.stop()

try:
    data_updated = pd.Timestamp.fromtimestamp(os.path.getmtime(CSV_PATH)).strftime("%Y-%m-%d %H:%M")
except OSError:
    data_updated = "unknown"
page_loaded = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
st.caption(f"📅 Data last updated: **{data_updated}** · Page loaded: **{page_loaded}**")

with st.sidebar:
    site_months = st.multiselect("Site month", sorted(df["site_month"].unique()))
    modules = st.multiselect("Module", sorted(df["module"].dropna().unique()))
    teams = st.multiselect("Team", sorted(df["team"].unique()))
    supers = st.multiselect("Supervisor", sorted(df["super"].dropna().unique()))
    names = st.multiselect("Name", sorted(df["name"].dropna().unique()))
    operations = st.multiselect("Operation", sorted(df["operation"].dropna().unique()))

filtered = df.copy()
if site_months:
    filtered = filtered[filtered["site_month"].isin(site_months)]
if modules:
    filtered = filtered[filtered["module"].isin(modules)]
if teams:
    filtered = filtered[filtered["team"].isin(teams)]
if supers:
    filtered = filtered[filtered["super"].isin(supers)]
if names:
    filtered = filtered[filtered["name"].isin(names)]
if operations:
    filtered = filtered[filtered["operation"].isin(operations)]

st.caption(f"Showing **{len(filtered):,}** of {len(df):,} rows")

col1, col2, col3 = st.columns(3)
col1.metric("Distinct operation", f"{filtered['operation'].nunique():,}")
col2.metric("Total practice qty", f"{filtered['practice_lot_qty'].sum():,.0f}")
col3.metric("Distinct operators", f"{filtered['name'].nunique():,}")

tab_goal, tab_trend, tab_by_person, tab_by_module, tab_data = st.tabs(
    ["🎯 Goal comparison", "📈 Trend", "🧑 By operator", "🏭 By module", "📄 Raw data"]
)

with tab_trend:
    by_site_month = (
        filtered.groupby("site_month")["practice_lot_qty"]
        .sum()
        .sort_index()
    )
    if by_site_month.empty:
        st.info("No data for the selected filters.")
    else:
        st.bar_chart(by_site_month)

with tab_by_person:
    by_name = (
        filtered.groupby("name")
        .agg(
            practice_qty=("practice_lot_qty", "sum"),
            goal=("monthly practice goal", "sum"),
            lots=("name", "count"),
        )
        .sort_values("practice_qty", ascending=False)
        .head(30)
    )
    if by_name.empty:
        st.info("No data for the selected filters.")
    else:
        st.bar_chart(by_name["practice_qty"])
        st.dataframe(by_name, use_container_width=True)

with tab_by_module:
    by_module = (
        filtered.groupby("module")["practice_lot_qty"].sum().sort_values(ascending=False)
    )
    if by_module.empty:
        st.info("No data for the selected filters.")
    else:
        st.bar_chart(by_module)

with tab_goal:
    summary = (
        filtered.groupby(["name", "site_month", "module", "operation"])
        .agg(
            team=("team", "first"),
            super=("super", "first"),
            practiced_qty=("practice_lot_qty", "first"),
            **{
                "monthly practice goal": ("monthly practice goal", "max"),
                "Complete_80_percent_tasks": (
                    "Complete_80_percent_tasks",
                    lambda s: s.dropna().iloc[0] if not s.dropna().empty else "",
                ),
            },
        )
        .reset_index()
    )
    summary = summary[
        [
            "site_month",
            "module",
            "name",
            "team",
            "super",
            "operation",
            "practiced_qty",
            "monthly practice goal",
            "Complete_80_percent_tasks",
        ]
    ]
    if summary.empty:
        st.info("No data for the selected filters.")
    else:
        summary["attainment_%"] = (
            summary["practiced_qty"]
            / summary["monthly practice goal"].replace(0, pd.NA)
            * 100
        ).round(1)
        summary["gap_to_goal"] = (
            summary["monthly practice goal"] - summary["practiced_qty"]
        )
        summary["met_goal"] = summary["practiced_qty"] >= summary["monthly practice goal"]
        summary = summary.sort_values("attainment_%", ascending=True).reset_index(drop=True)

        goal_status = st.radio(
            "Goal status",
            ["All", "Met goal", "Not met goal"],
            horizontal=True,
            key="goal_status_filter",
        )
        if goal_status == "Met goal":
            summary = summary[summary["met_goal"]]
        elif goal_status == "Not met goal":
            summary = summary[~summary["met_goal"]]

        display_summary = (
            summary.drop(columns=["met_goal"])
            .rename(columns=lambda c: c if c.startswith("Complete_") else c[:1].upper() + c[1:])
        )

        col_a, col_b = st.columns(2)
        col_a.metric("Operator/month/module/operation combos", f"{len(summary):,}")
        col_b.metric("Met goal", f"{summary['met_goal'].sum():,} / {len(summary):,}")

        if summary.empty:
            st.info("No rows match the selected goal status filter.")
        else:
            st.markdown(
                "[Justification for missing goal operators](https://content.sseprod.intel.com/sites/CD/CDATwebshare/IonReport/Cross_training/CW_practice_data.aspx)"
            )

            def highlight_goal(row):
                val = str(row.get("Complete_80_percent_tasks", "")).strip().upper()
                color = "background-color: #c6efce" if val in ("Y", "YES", "TRUE", "1") else "background-color: #ffc7ce"
                return [color] * len(row)

            st.caption("Click a value in the Practiced_qty column to see its lot details below.")
            event = st.dataframe(
                display_summary.style.apply(highlight_goal, axis=1)
                .format(
                    {
                        "Practiced_qty": "{:,.0f}",
                        "Attainment_%": "{:.1f}%",
                        "Gap_to_goal": "{:,.0f}",
                    }
                ),
                use_container_width=True,
                height=500,
                on_select="rerun",
                selection_mode="single-cell",
            )
            st.download_button(
                "Download goal comparison as CSV",
                data=display_summary.to_csv(index=False).encode("utf-8"),
                file_name="goal_comparison_summary.csv",
                mime="text/csv",
                key="download_goal_summary",
            )

            selected_cells = event.selection.cells if event and event.selection else []
            if selected_cells:
                row_idx, col_name = selected_cells[0]
                if col_name == "Practiced_qty":
                    sel = summary.iloc[row_idx]
                    detail = filtered[
                        (filtered["name"] == sel["name"])
                        & (filtered["site_month"] == sel["site_month"])
                        & (filtered["module"] == sel["module"])
                        & (filtered["operation"] == sel["operation"])
                    ]
                    st.subheader(
                        f"Lot details — {sel['name']} · {sel['site_month']} · {sel['module']} · operation {sel['operation']}"
                    )
                    st.dataframe(detail, use_container_width=True)
                    st.download_button(
                        "Download lot details as CSV",
                        data=detail.to_csv(index=False).encode("utf-8"),
                        file_name="lot_details.csv",
                        mime="text/csv",
                        key="download_lot_details",
                    )

with tab_data:
    raw_data = filtered.drop(columns=["practice_shift_qty"], errors="ignore")
    st.dataframe(raw_data, use_container_width=True, height=500)
    st.download_button(
        "Download filtered data as CSV",
        data=raw_data.to_csv(index=False).encode("utf-8"),
        file_name="filtered_practice_data.csv",
        mime="text/csv",
    )
