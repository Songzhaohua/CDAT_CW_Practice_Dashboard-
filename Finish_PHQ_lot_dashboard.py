import os

import pandas as pd
import streamlit as st


CSV_PATH = os.environ.get(
	"PHQ_CSV_PATH",
	r"\\azATSHFS.intel.com\azATAnalysis$\MAOATM\CDAT\zhaohua\Finish_PHQ_lot.csv",
)

st.set_page_config(page_title="Finish PHQ Lot Report", layout="wide")


@st.cache_data(ttl=300)
def load_data(path: str) -> pd.DataFrame:
	data = pd.read_csv(path, dtype={"LOT": "string", "AT_MRB1": "string"})
	data["QUANTITY"] = pd.to_numeric(data["QUANTITY"], errors="coerce").fillna(0)
	data["DAYS_AT_OPERATION"] = pd.to_numeric(
		data["DAYS_AT_OPERATION"], errors="coerce"
	)
	data["DATE_ENTERED_OPERATION"] = pd.to_datetime(
		data["DATE_ENTERED_OPERATION"], errors="coerce"
	)
	return data


st.title("Finish PHQ Lot Report")

with st.sidebar:
	st.header("Filters")
	if st.button("Refresh data", icon=":material/refresh:"):
		load_data.clear()
		st.rerun()

try:
	df = load_data(CSV_PATH)
except (OSError, pd.errors.ParserError, UnicodeError) as exc:
	st.error(f"Unable to read the PHQ lot CSV: {exc}")
	st.stop()

try:
	updated = pd.Timestamp.fromtimestamp(os.path.getmtime(CSV_PATH)).strftime(
		"%Y-%m-%d %H:%M"
	)
except OSError:
	updated = "unknown"
st.caption(f"Source updated: {updated} · {len(df):,} rows loaded")

with st.sidebar:
	groups = st.multiselect("Product group", sorted(df["PRODGROUP3"].dropna().unique()))
	owners = st.multiselect("Owner", sorted(df["OWNER"].dropna().unique()))
	hold_status = st.multiselect("On hold", sorted(df["ONHOLD"].dropna().unique()))
	phq_status = st.multiselect("At PHQ", sorted(df["AT_PHQ"].dropna().unique()))
	shippable_status = st.multiselect(
		"Shippable", sorted(df["AT_SHIPPABLE1"].dropna().unique())
	)

filtered = df.copy()
for column, selected in (
	("PRODGROUP3", groups),
	("OWNER", owners),
	("ONHOLD", hold_status),
	("AT_PHQ", phq_status),
	("AT_SHIPPABLE1", shippable_status),
):
	if selected:
		filtered = filtered[filtered[column].isin(selected)]

st.caption(f"Showing {len(filtered):,} of {len(df):,} lots")
shippable_lots = df[df["AT_SHIPPABLE1"].eq("Y")]
st.subheader(f"Shippable lots ({len(shippable_lots):,})")
st.html('<p style="color: #8b0000; font-size: 0.875rem; margin: 0">Click the lot number to view the lot location</p>')
if shippable_lots.empty:
	st.info("No shippable lots found.")
else:
	shippable_table = shippable_lots[
		["LOT", *[column for column in shippable_lots if column != "LOT"]]
	].to_html(index=False, escape=True)
	st.html(
		f"""
<div id="phq-shippable-lots">{shippable_table}</div>
<style>
#phq-shippable-lots {{ overflow-x: auto; max-height: 400px; overflow-y: auto; }}
#phq-shippable-lots table {{ border-collapse: collapse; width: 100%; font-size: 0.875rem; }}
#phq-shippable-lots th, #phq-shippable-lots td {{ border-bottom: 1px solid #ddd; padding: 8px; text-align: left; white-space: nowrap; }}
#phq-shippable-lots th {{ position: sticky; top: 0; background: white; }}
#phq-shippable-lots td:first-child a {{ color: #087c80; text-decoration: underline; }}
</style>
<script>
const lotTable = document.getElementById("phq-shippable-lots");

for (const cell of lotTable.querySelectorAll("tbody td:first-child")) {{
	const lot = cell.textContent.trim();
	if (lot) {{
		const link = document.createElement("a");
		link.href = `http://cd6veuinlb.cd.intel.com/ETravelerUI/home/${{encodeURIComponent(lot.toLowerCase())}}/consolidate`;
		link.textContent = lot;
		link.title = "Open in ETraveler";
		cell.replaceChildren(link);
	}}
}}
</script>
""",
		unsafe_allow_javascript=True,
	)

if filtered.empty:
	st.info("No lots match the selected filters.")
	st.stop()

lots, quantity, on_hold, aging = st.columns(4)
lots.metric("Lots", f"{filtered['LOT'].nunique():,}")
quantity.metric("Total quantity", f"{filtered['QUANTITY'].sum():,.0f}")
on_hold.metric("On hold", f"{filtered['ONHOLD'].eq('Y').sum():,}")
aging.metric("Over 2 days at operation", f"{filtered['DAYS_AT_OPERATION'].gt(2).sum():,}")

by_group, by_owner, detail = st.tabs(["Product groups", "Owners & aging", "Lot detail"])

with by_group:
	group_summary = (
		filtered.groupby("PRODGROUP3", dropna=False)
		.agg(lots=("LOT", "nunique"), quantity=("QUANTITY", "sum"))
		.sort_values("lots", ascending=False)
	)
	st.bar_chart(group_summary["lots"], x_label="Product group", y_label="Lot Qty")
	st.dataframe(group_summary, width="stretch")

with by_owner:
	owner_summary = (
		filtered.groupby("OWNER", dropna=False)
		.agg(
			lots=("LOT", "nunique"),
			quantity=("QUANTITY", "sum"),
			on_hold=("ONHOLD", lambda status: status.eq("Y").sum()),
			average_days=("DAYS_AT_OPERATION", "mean"),
		)
		.sort_values("lots", ascending=False)
	)
	st.bar_chart(owner_summary["lots"], x_label="Owner", y_label="Lot Qty")
	st.dataframe(owner_summary, width="stretch", column_config={
		"average_days": st.column_config.NumberColumn("Average days", format="%.1f"),
	})

with detail:
	st.download_button(
		"Download filtered CSV",
		filtered.to_csv(index=False).encode("utf-8-sig"),
		file_name="Finish_PHQ_lot_filtered.csv",
		mime="text/csv",
		icon=":material/download:",
	)
	st.dataframe(filtered, width="stretch", hide_index=True)
