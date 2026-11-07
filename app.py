import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="NBA Model Center",page_icon="🏀",layout="wide")
st.title("🏀 NBA Model Center")
password=st.secrets.get("DASHBOARD_PASSWORD","")
if not password:
    st.error("Dashboard password is not configured. Add DASHBOARD_PASSWORD in Streamlit app secrets.")
    st.stop()
if not st.session_state.get("authorized",False):
    with st.form("login"):
        supplied=st.text_input("Dashboard password",type="password")
        if st.form_submit_button("Sign in"):
            import hmac
            if hmac.compare_digest(supplied,password):
                st.session_state.authorized=True
                st.rerun()
            else: st.error("Incorrect password")
    st.stop()
with st.sidebar:
    st.success("Signed in")
    if st.button("Sign out"):
        st.session_state.authorized=False
        st.rerun()
    upload=st.file_uploader("Upload daily NBA workbook",type=["xlsx"])
    st.caption("Uploads update only your current session.")
source=upload if upload else Path("sample_nba_workbook.xlsx")
if not upload and not source.exists():
    st.info("Upload your NBA projections Excel workbook in the sidebar to begin.")
    st.stop()
try:
    book=pd.ExcelFile(source)
except Exception as e:
    st.error(f"Could not open workbook: {e}")
    st.stop()
sheets=book.sheet_names
st.caption("Daily projections • Bankroll Builder • Favorite Props • Historical performance")
chosen=st.selectbox("Dashboard section",sheets)
df=pd.read_excel(book,sheet_name=chosen)
df=df.dropna(how="all")
if df.empty:
    st.warning("No data found in this worksheet.")
    st.stop()
search=st.text_input("Search players or props",placeholder="e.g. Nikola Jokic")
if search:
    mask=df.astype(str).apply(lambda c:c.str.contains(search,case=False,regex=False,na=False)).any(axis=1)
    df=df[mask]
filters=st.columns(2)
for col, label in zip(filters,["Model Side","Stat"]):
    matching=next((c for c in df.columns if str(c).strip().lower()==label.lower()),None)
    if matching:
        options=sorted(df[matching].dropna().astype(str).unique())
        if 0<len(options)<100:
            selection=col.multiselect(label,options)
            if selection: df=df[df[matching].astype(str).isin(selection)]
st.metric("Visible rows",len(df))
def shade(v):
    if isinstance(v,str):
        if v.lower()=="over":return "color: #15803d; font-weight: bold"
        if v.lower()=="under":return "color: #dc2626; font-weight: bold"
    return ""
historical=["Last Game","2 Games Ago","3 Games Ago","Last 3 Average","Last game","2 games ago","3 games ago","Last 3 avg"]
side=next((c for c in df.columns if str(c).lower()=="model side"),None)
projection=next((c for c in df.columns if str(c).lower()=="model projection"),None)
def color_history(row):
    styles=[""]*len(row)
    if side is None or projection is None:return styles
    try: p=float(row[projection])
    except (ValueError,TypeError):return styles
    direction=str(row[side]).lower()
    for i,c in enumerate(row.index):
        if str(c) not in historical:continue
        try: n=float(row[c])
        except (ValueError,TypeError):continue
        if n==p:continue
        good=(n>p and "over" in direction) or (n<p and "under" in direction)
        styles[i]="color: #15803d; font-weight: bold" if good else "color: #dc2626; font-weight: bold"
    return styles
styled=df.style.map(shade).apply(color_history,axis=1)
st.dataframe(styled,use_container_width=True,hide_index=True,height=640)
st.download_button("Download filtered rows",df.to_csv(index=False),file_name="nba_props_filtered.csv",mime="text/csv")
