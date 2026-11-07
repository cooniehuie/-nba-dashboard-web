import hmac
import base64
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="NBA Model Center", page_icon="🏀", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
.block-container{padding-top:1.6rem;max-width:1600px}
[data-testid="stAppViewContainer"]{background:linear-gradient(160deg,#0f172a08,transparent 32%)}
[data-testid="stSidebar"]{background:#111827;color:#f9fafb}
/* Explicit text colors without overriding button/input text */
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,[data-testid="stSidebar"] [data-testid="stCaptionContainer"]{color:#f1f5f9}
[data-testid="stSidebar"] button{background:#f8fafc!important;color:#111827!important;border:1px solid #cbd5e1!important}
[data-testid="stSidebar"] button *{color:#111827!important}
[data-testid="stSidebar"] button:hover{background:#e2e8f0!important;color:#0f172a!important}
[data-testid="stSidebar"] [data-testid="stFileUploader"]{background:#f8fafc;border-radius:12px;padding:10px}
[data-testid="stSidebar"] [data-testid="stFileUploader"] *{color:#111827!important}
[data-testid="stSidebar"] [data-testid="stAlert"]{background:#e0f2fe!important;border-radius:10px}
[data-testid="stSidebar"] [data-testid="stAlert"] *{color:#0f172a!important}
[data-testid="stSidebar"] [data-testid="stRadio"] label{color:#f1f5f9!important}
[data-testid="stSidebar"] [data-testid="stRadio"] label *{color:#f1f5f9!important}
[data-testid="stDataFrame"]{border-radius:12px;overflow:hidden}
h1,h2,h3{letter-spacing:-.025em}
[data-testid="stMetric"]{border:1px solid #37415130;border-radius:14px;padding:12px 16px;background:#8080800b}
[data-testid="stSidebar"]{border-right:1px solid #80808030}
</style>""",unsafe_allow_html=True)
viewer_password=st.secrets.get("DASHBOARD_PASSWORD","")
admin_password=st.secrets.get("ADMIN_PASSWORD","")
if not viewer_password:
    st.error("DASHBOARD_PASSWORD is missing from Streamlit Secrets.")
    st.stop()
if admin_password and hmac.compare_digest(admin_password,viewer_password):
    st.error("ADMIN_PASSWORD must be different from DASHBOARD_PASSWORD.")
    st.stop()
if not st.session_state.get("authorized",False):
    st.title("🏀 NBA Model Center")
    st.caption("Private access · Daily NBA model projections")
    with st.form("login"):
        supplied=st.text_input("Password",type="password")
        if st.form_submit_button("Sign in",type="primary"):
            if admin_password and hmac.compare_digest(supplied,admin_password):
                st.session_state.authorized=True
                st.session_state.role="admin"
                st.rerun()
            elif hmac.compare_digest(supplied,viewer_password):
                st.session_state.authorized=True
                st.session_state.role="viewer"
                st.rerun()
            else:st.error("Incorrect password.")
    st.stop()
role=st.session_state.get("role","viewer")
is_admin=(role=="admin" and bool(admin_password))
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


def recent_hit_stats(row):
    side_col=lookup(pd.DataFrame(columns=row.index),"Model side")
    projection_col=lookup(pd.DataFrame(columns=row.index),"Model projection")
    if not side_col or not projection_col:return (0,0)
    side=str(row[side_col]).strip().lower()
    projection=number(row[projection_col])
    if projection is None or side not in ("over","under"):return (0,0)
    valid=[]
    for label in ("Last game","2 games ago","3 games ago"):
        col=lookup(pd.DataFrame(columns=row.index),label)
        if col:
            val=number(row[col])
            if val is not None:valid.append(val)
    hits=sum((v>projection if side=="over" else v<projection) for v in valid)
    return (hits,len(valid))

def historical_summary(df):
    if not (lookup(df,"Model side") and lookup(df,"Model projection")):return df
    result=df.copy()
    results=result.apply(recent_hit_stats,axis=1)
    result["Recent hits"]=results.map(lambda x:x[0])
    result["Games available"]=results.map(lambda x:x[1])
    result["Last 3 hit rate"]=results.map(lambda x:f"{x[0]}/{x[1]}" if x[1] else "N/A")
    return result

def storage_settings():
    token=st.secrets.get("GITHUB_STORAGE_TOKEN","")
    repo=st.secrets.get("GITHUB_STORAGE_REPO","")
    return token,str(repo).strip()

def github_file(path, data=None):
    token,repo=storage_settings()
    if not token or not repo:raise RuntimeError("Private storage is not configured.")
    if len(repo.split("/"))!=2:raise ValueError("GITHUB_STORAGE_REPO must be owner/repository.")
    url="https://api.github.com/repos/"+repo+"/contents/"+path
    headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"NBA-Model-Center"}
    def request(payload=None,method=None):
        raw=json.dumps(payload).encode() if payload is not None else None
        if raw:headers["Content-Type"]="application/json"
        req=urllib.request.Request(url,data=raw,headers=headers,method=method or ("PUT" if raw else "GET"))
        try:
            with urllib.request.urlopen(req,timeout=20) as response:return json.load(response)
        except urllib.error.HTTPError as err:
            if err.code==404:return None
            raise RuntimeError(f"Private storage request failed (HTTP {err.code}).") from None
    existing=request()
    if data is None:
        if not existing:return None
        return base64.b64decode(existing["content"])
    payload={"message":"Save NBA workbook "+datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),"content":base64.b64encode(data).decode()}
    if existing:payload["sha"]=existing["sha"]
    result=request(payload)
    if result is None:raise RuntimeError("Private storage file could not be saved.")
    return result

@st.cache_data(ttl=120,show_spinner=False)
def saved_workbook():
    return github_file("latest.xlsx")

with st.sidebar:
    st.title("🏀 NBA Model Center")
    st.caption("Your private model dashboard")
    st.caption("🔐 Administrator" if is_admin else "👁 Viewer access")
    if st.button("Sign out"):
        st.session_state.authorized=False
        st.session_state.pop("role",None)
        st.rerun()
    token,storage_repo=storage_settings()
    storage_ready=bool(token and storage_repo)
    uploaded=None
    if is_admin:
        if storage_ready:st.success("Private workbook storage configured")
        else:st.info("Private storage setup needed.")
        uploaded=st.file_uploader("Upload daily NBA workbook",type=["xlsx"],help="Upload and save a workbook to private storage.")
        if uploaded is not None and storage_ready:
            if st.button("💾 Save workbook permanently",type="primary",use_container_width=True):
                try:
                    data=uploaded.getvalue()
                    load_workbook(data)
                    github_file("latest.xlsx",data)
                    stamp=datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                    github_file("history/"+stamp+".xlsx",data)
                    saved_workbook.clear()
                    st.success("Saved! This workbook will load automatically on future visits.")
                except Exception as exc:st.error(f"Could not save workbook: {exc}")
        if storage_ready and st.button("↻ Reload saved workbook",use_container_width=True):
            saved_workbook.clear()
            st.rerun()
        st.caption("Uploads are saved to your separate private GitHub repository.")
    else:
        st.caption("Read-only access. Only the administrator can upload or replace projections.")
        if not admin_password:
            st.warning("Admin access is not enabled yet. Add ADMIN_PASSWORD in Streamlit Secrets.")
    st.divider()
    section=st.radio("Navigate",["Overview","Bankroll Builder","Favorite Props","All Player Props","Three-Point Projections","Individual Games"],label_visibility="visible")

source=uploaded.getvalue() if uploaded else None
if source is None and storage_ready:
    try:
        source=saved_workbook()
        if source:st.sidebar.caption("✓ Loaded saved workbook automatically")
    except Exception as exc:st.sidebar.warning(f"Saved workbook unavailable: {exc}")
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
        game_col=lookup(df,"Game")
        if game_col:
            available=sorted(df[game_col].dropna().astype(str).unique())
            if 1<len(available)<40:
                game_choice=st.selectbox("Matchup",["All games"]+available,key="game_"+name)
                if game_choice!="All games":df=df[df[game_col].astype(str)==game_choice]
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
    if allow_filters and lookup(df,"Model side") and lookup(df,"Model projection"):
        df=historical_summary(df)
        hit1,hit2=st.columns([1,3])
        only_three=hit1.checkbox("Show 3/3 recent hits",key="perfect_"+name,help="Three available games all on the model side of the projection.")
        if only_three:df=df[(df["Recent hits"]==3)&(df["Games available"]==3)]
        hit2.caption("Recent hit rate compares actual stats with the model projection; it is not a future win probability.")
    st.caption(f"{len(df):,} rows · {name}")
    priority=["Player","Market","Reference line","Model projection","Model side","Last game","2 games ago","3 games ago","Last 3 avg","Last 3 average","Last 3 hit rate"]
    if lookup(df,"Player") and lookup(df,"Model projection"):
        front=[lookup(df,k) for k in priority]
        front=[c for c in front if c is not None]
        df=df[front+[c for c in df.columns if c not in front]]
    # Convert values to display strings before passing them to Streamlit.
    # Streamlit's dataframe grid does not consistently honor Styler.format().
    df=df.replace({"None":pd.NA,"none":pd.NA,"N/A":pd.NA,"n/a":pd.NA})
    number_keys={"last game","2 games ago","3 games ago","last 3 avg","last 3 average","reference line","model projection","away model pts","home model pts","projected total","edge"}
    two_decimal={"last 3 avg","last 3 average","model projection","reference line","away model pts","home model pts","projected total","edge"}
    for c in df.columns:
        if str(c).lower() in number_keys:
            digits=2 if str(c).lower() in two_decimal else 0
            def fmt(v):
                n=number(v)
                if n is None:return "N/A"
                return f"{n:,.{digits}f}"
            df[c]=df[c].map(fmt)
        else:
            df[c]=df[c].map(lambda v:"N/A" if pd.isna(v) or str(v).strip().lower() in {"none","nan","n/a"} else v)
    for internal in ("Recent hits","Games available"):
        if internal in df.columns:df=df.drop(columns=[internal])
    # Size each column from its header and visible values, rather than using
    # Streamlit's broad small/medium/large presets. Preserve horizontal scrolling
    # only when the complete table genuinely exceeds the available viewport.
    config={}
    width_caps={
        "Player":(135,195),"Market":(90,110),
        "Reference line":(110,122),"Model projection":(120,136),
        "Model side":(90,100),"Last game":(85,96),
        "2 games ago":(96,108),"3 games ago":(96,108),
        "Last 3 avg":(90,102),"Last 3 average":(108,120),
        "Last 3 hit rate":(108,120),"Tipoff PST":(96,110),
        "Game":(160,260),
    }
    for heading in df.columns:
        minimum,maximum=width_caps.get(str(heading),(85,190))
        sample=df[heading].astype(str).head(150)
        longest=max([len(str(heading))]+sample.map(len).tolist(),default=len(str(heading)))
        pixels=max(minimum,min(maximum,int(longest*7.3+24)))
        config[heading]=st.column_config.TextColumn(str(heading),width=pixels)

    st.dataframe(df.style.apply(paint_row,axis=1),hide_index=True,use_container_width=True,height=min(680,max(230,39*(len(df)+1))),column_config=config)
    st.download_button("Download filtered CSV",df.to_csv(index=False).encode("utf-8"),file_name="nba_"+name.lower().replace(" ","_")+".csv",mime="text/csv",key="download_"+name)

if section=="Overview":
    st.title("Daily NBA Projections")
    st.caption("Model projections · Favorites · Safer lines · Recent player performance")
    a,b,c,d=st.columns(4)
    a.metric("Games",len(sheets[schedule]) if schedule else len(games))
    b.metric("Player props",len(sheets[allprops]) if allprops else "—")
    c.metric("Favorite props",len(sheets[favorites]) if favorites else "—")
    d.metric("Bankroll plays",len(sheets[bankroll]) if bankroll else "—")
    if allprops:
        candidates=historical_summary(sheets[allprops])
        if "Recent hits" in candidates:
            candidates=candidates[(candidates["Recent hits"]==3)&(candidates["Games available"]==3)]
            st.subheader("🔥 3-for-3 recent performance")
            st.caption("Historical matches to model projections, not guarantees or betting recommendations.")
            if len(candidates):
                wanted=[lookup(candidates,c) for c in ("Player","Game","Market","Model side","Model projection","Last 3 avg")]
                wanted=[c for c in wanted if c]
                st.dataframe(candidates[wanted].head(12),hide_index=True,use_container_width=True)
                st.caption(f"{len(candidates)} prop rows had 3 of 3 recent games on the model side.")
            else:st.info("No props with three available recent games and a 3/3 historical match.")
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
