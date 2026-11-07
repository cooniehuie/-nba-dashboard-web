import hmac
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="NBA Model Center", page_icon="🏀", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
.block-container{padding-top:1.7rem;max-width:1500px}
h1,h2,h3{letter-spacing:-.025em}
[data-testid="stMetric"]{border:1px solid #37415130;border-radius:14px;padding:12px 16px;background:#8080800b}
[data-testid="stSidebar"]{border-right:1px solid #80808030}
</style>""",unsafe_allow_html=True)
password=st.secrets.get("DASHBOARD_PASSWORD","")
if not password:
    st.error("Dashboard password is not configured. Add DASHBOARD_PASSWORD to the app's Streamlit Secrets.")
    st.stop()
if not st.session_state.get("authorized",False):
    st.title("🏀 NBA Model Center")
    st.caption("Private access · Daily NBA model projections")
    with st.form("login"):
        supplied=st.text_input("Password",type="password")
        if st.form_submit_button("Sign in",type="primary"):
            if hmac.compare_digest(supplied,password):
                st.session_state.authorized=True
                st.rerun()
            else: st.error("Incorrect password.")
    st.stop()

@st.cache_data(show_spinner=False)
def load_workbook(contents):
    from io import BytesIO
    excel=pd.ExcelFile(BytesIO(contents))
    return {name:pd.read_excel(excel,sheet_name=name,header=None,dtype=object) for name in excel.sheet_names}

def clean_sheet(raw):
    if raw.empty:return pd.DataFrame()
    keywords=("player","tipoff","market","reference line","model projection","our play","safer line","play","away","home")
    best=(-1,0)
    for idx in range(min(15,len(raw))):
        cells=[str(v).strip().lower() for v in raw.iloc[idx].values if pd.notna(v)]
        score=sum(any(k==c or k in c for k in keywords) for c in cells)
        if score>best[0]:best=(score,idx)
    start=best[1]
    frame=raw.iloc[start+1:].copy()
    headers=[str(v).strip() if pd.notna(v) else f"Column {i+1}" for i,v in enumerate(raw.iloc[start])]
    frame.columns=headers
    frame=frame.dropna(how="all")
    frame=frame.loc[:,~frame.columns.str.match(r"^Column \d+$") | frame.notna().any(axis=0).values]
    frame=frame.reset_index(drop=True)
    frame=frame.replace({"None":pd.NA,"none":pd.NA,"N/A":pd.NA,"n/a":pd.NA})
    return frame

def lookup(frame,*names):
    for n in names:
        for col in frame.columns:
            if str(col).strip().lower()==n.lower():return col
    return None

def number(v):
    try:
        if pd.isna(v):return None
        return float(v)
    except (TypeError,ValueError):return None

def paint_row(row):
    styles=[""]*len(row)
    side_col=lookup(pd.DataFrame(columns=row.index),"Model side")
    proj_col=lookup(pd.DataFrame(columns=row.index),"Model projection")
    side=str(row[side_col]).strip().lower() if side_col else ""
    proj=number(row[proj_col]) if proj_col else None
    historical={"last game","2 games ago","3 games ago","last 3 avg","last 3 average"}
    for i,c in enumerate(row.index):
        key=str(c).lower()
        v=row[c]
        if key=="model side":
            if "over" in str(v).lower():styles[i]="color:#16a34a;font-weight:700"
            elif "under" in str(v).lower():styles[i]="color:#dc2626;font-weight:700"
        elif key=="safer line":
            styles[i]="color:#16a34a;font-weight:700"
        elif key in historical and proj is not None and ("over" in side or "under" in side):
            n=number(v)
            if n is None:continue
            if n==proj:continue
            win=(n>proj and "over" in side) or (n<proj and "under" in side)
            styles[i]="color:#16a34a;font-weight:700" if win else "color:#dc2626;font-weight:700"
    return styles

with st.sidebar:
    st.title("🏀 NBA Model Center")
    st.caption("Your private model dashboard")
    if st.button("Sign out"):
        st.session_state.authorized=False
        st.rerun()
    uploaded=st.file_uploader("Upload daily NBA workbook",type=["xlsx"],help="Excel files are read for this browser session only.")
    st.caption("Upload a new workbook each day. Files are not committed to GitHub.")
    st.divider()
    section=st.radio("Navigate",["Overview","Bankroll Builder","Favorite Props","All Player Props","Three-Point Projections","Individual Games"],label_visibility="visible")

source=uploaded.getvalue() if uploaded else None
if source is None:
    default=Path("sample_nba_workbook.xlsx")
    if default.exists():source=default.read_bytes()
if source is None:
    st.title("🏀 NBA Model Center")
    st.info("Upload your NBA projections Excel workbook using the sidebar to load the dashboard.")
    st.stop()
try:raw_sheets=load_workbook(source)
except Exception as exc:
    st.error(f"Could not read Excel workbook: {exc}")
    st.stop()
sheets={name:clean_sheet(df) for name,df in raw_sheets.items()}
names=list(sheets)
def find_sheet(*terms):
    return next((n for n in names if any(t.lower() in n.lower() for t in terms)),None)
schedule=find_sheet("game schedule","game summary")
bankroll=find_sheet("bankroll")
favorites=find_sheet("favorite")
allprops=find_sheet("all player props")
threes=find_sheet("three-point","three point","3-point")
excluded={x for x in [schedule,bankroll,favorites,allprops,threes] if x}
games=[n for n in names if n not in excluded]

def show_table(name, allow_filters=True):
    if not name:
        st.info("This section is not present in the uploaded workbook.")
        return
    df=sheets[name].copy()
    if df.empty:
        st.warning("No rows found in this section.")
        return
    if allow_filters:
        c1,c2,c3=st.columns([2,1,1])
        search=c1.text_input("Search players or props",key="search_"+name)
        if search:
            df=df[df.astype(str).apply(lambda col:col.str.contains(search,case=False,regex=False,na=False)).any(axis=1)]
        market=lookup(df,"Market","Stat")
        side=lookup(df,"Model side")
        if market:
            opts=sorted(df[market].dropna().astype(str).unique())
            if len(opts)<=80:
                selected=c2.multiselect("Market",opts,key="market_"+name)
                if selected:df=df[df[market].astype(str).isin(selected)]
        if side:
            opts=sorted(df[side].dropna().astype(str).unique())
            selected=c3.multiselect("Model side",opts,key="side_"+name)
            if selected:df=df[df[side].astype(str).isin(selected)]
    st.caption(f"{len(df):,} rows · {name}")
    priority=["Player","Reference line","Model projection","Model side","Last game","2 games ago","3 games ago","Last 3 avg","Last 3 average"]
    if lookup(df,"Player") and lookup(df,"Model projection"):
        front=[lookup(df,k) for k in priority]
        front=[c for c in front if c is not None]
        df=df[front+[c for c in df.columns if c not in front]]
    df=df.replace({"None":pd.NA,"none":pd.NA,"N/A":pd.NA,"n/a":pd.NA})
    numeric_columns=[]
    for c in df.columns:
        if str(c).lower() in {"last game","2 games ago","3 games ago","last 3 avg","last 3 average","reference line","model projection","away model pts","home model pts","projected total","edge"}:
            df[c]=pd.to_numeric(df[c],errors="coerce")
            numeric_columns.append(c)
    styler=df.style.apply(paint_row,axis=1).format(na_rep="N/A")
    for c in numeric_columns:
        digits=2 if str(c).lower() in {"last 3 avg","last 3 average","model projection","reference line","away model pts","home model pts","projected total","edge"} else 0
        styler=styler.format({c:("{:,.%df}"%digits)},na_rep="N/A")
    config={c:st.column_config.NumberColumn(c,width="small") for c in numeric_columns}
    if "Player" in df.columns:config["Player"]=st.column_config.TextColumn("Player",width="medium")
    if "Game" in df.columns:config["Game"]=st.column_config.TextColumn("Game",width="large")
    st.dataframe(styler,hide_index=True,use_container_width=True,height=min(680,max(230,39*(len(df)+1))),column_config=config)
    st.download_button("Download filtered CSV",df.to_csv(index=False).encode("utf-8"),file_name="nba_"+name.lower().replace(" ","_")+".csv",mime="text/csv",key="download_"+name)

if section=="Overview":
    st.title("Daily NBA Projections")
    st.caption("Model projections · Favorites · Safer lines · Recent player performance")
    a,b,c,d=st.columns(4)
    a.metric("Games",len(sheets[schedule]) if schedule else len(games))
    b.metric("Player props",len(sheets[allprops]) if allprops else "—")
    c.metric("Favorite props",len(sheets[favorites]) if favorites else "—")
    d.metric("Bankroll plays",len(sheets[bankroll]) if bankroll else "—")
    st.subheader("Today's games")
    if schedule:show_table(schedule,False)
    else:st.info("No game schedule sheet found.")
    st.subheader("Favorite props")
    if favorites:show_table(favorites,False)
    st.subheader("Bankroll builder")
    if bankroll:show_table(bankroll,False)
elif section=="Individual Games":
    st.title("Individual Game Projections")
    if games:
        selected=st.selectbox("Choose matchup",games)
        show_table(selected)
    else:st.info("No individual game tabs found.")
else:
    chosen={"Bankroll Builder":bankroll,"Favorite Props":favorites,"All Player Props":allprops,"Three-Point Projections":threes}.get(section)
    st.title(section)
    show_table(chosen)
