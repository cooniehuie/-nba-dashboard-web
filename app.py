import hmac
import base64
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Huie's Degen Center", page_icon="🏀", layout="wide", initial_sidebar_state="auto")
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
@media(max-width:700px){
 .block-container{padding:0.75rem 0.65rem 3rem!important}
 h1{font-size:1.65rem!important;line-height:1.2!important}
 h2{font-size:1.35rem!important}
 h3{font-size:1.12rem!important}
 [data-testid="stMetric"]{padding:8px!important;min-width:0!important}
 [data-testid="stMetricLabel"]{font-size:.77rem!important}
 [data-testid="stMetricValue"]{font-size:1.25rem!important}
 [data-testid="stHorizontalBlock"]{gap:.45rem!important;flex-wrap:wrap!important}
 [data-testid="column"]{min-width:145px!important;flex:1 1 45%!important}
 [data-testid="stDataFrame"]{max-width:100%;overflow:auto}
 [data-testid="stDataFrame"] canvas{touch-action:pan-x pan-y}
 .mobile-only-cards{display:block!important}
 .mobile-hide-table{display:none!important}
}
.mobile-only-cards{display:block}
.mobile-prop-card{padding:12px 14px;margin:8px 0;border:1px solid #9ca3af55;border-radius:12px;background:#8080800a;overflow-wrap:anywhere}
.mobile-prop-title{font-size:1rem;font-weight:700;margin-bottom:5px}
.mobile-prop-detail{font-size:.87rem;line-height:1.6}
.mobile-prop-detail b{font-weight:650}
/* Responsive bankroll live tracker: desktop grid and mobile cards swap automatically. */
.st-key-bankroll_live_mobile_ui,.st-key-embedded_bankroll_mobile_ui{display:none}
.bk-live-game{font-size:.91rem;font-weight:750;padding:13px 3px 6px;line-height:1.35}
.bk-live-game small{display:block;font-weight:450;font-size:.77rem;opacity:.75;margin-top:2px}
.bk-live-card{border:1px solid #9ca3af55;border-left:4px solid #9ca3af;border-radius:13px;background:var(--secondary-background-color,#f3f4f6);padding:13px 14px;margin:8px 0 12px;overflow-wrap:anywhere}
.bk-live-card.live{border-left-color:#eab308}.bk-live-card.hit{border-left-color:#16a34a}.bk-live-card.miss{border-left-color:#dc2626}
.bk-live-head{display:flex;justify-content:space-between;gap:8px;align-items:flex-start}
.bk-live-name{font-size:1.08rem;font-weight:800;line-height:1.3;min-width:0}
.bk-live-status{font-size:.74rem;font-weight:750;border:1px solid #94a3b855;border-radius:99px;padding:3px 8px;white-space:nowrap}
.bk-live-line{font-size:1rem;font-weight:750;margin-top:9px}
.bk-live-model{font-size:.78rem;opacity:.76;margin:4px 0 9px}
.bk-live-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin:11px 0}
.bk-live-stat{padding:8px 5px;text-align:center;border-radius:9px;background:#94a3b81b}
.bk-live-stat span{display:block;font-size:.69rem;opacity:.8;margin-bottom:3px}
.bk-live-stat b{display:block;font-size:1.3rem;line-height:1.25;font-variant-numeric:tabular-nums}
.bk-live-progress{height:8px;border-radius:9px;background:#94a3b84a;overflow:hidden;margin:6px 0}
.bk-live-progress-fill{height:100%;border-radius:9px;background:#eab308}
.bk-live-card.hit .bk-live-progress-fill{background:#16a34a}
.bk-live-note{font-size:.76rem;opacity:.8;margin-top:7px}
@media(max-width:700px){
 .st-key-bankroll_live_desktop_grid,.st-key-embedded_bankroll_desktop_grid{display:none!important}
 .st-key-bankroll_live_mobile_ui,.st-key-embedded_bankroll_mobile_ui{display:block!important}
}

/* Responsive app navigation and data views; all desktop widgets remain unchanged. */
.mobile-site-head{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:12px 14px;border-radius:15px;background:#112440;color:#fff;margin:4px 0 16px}
.mobile-site-head b{font-size:14px}.mobile-site-head small{display:block;font-size:10px;color:#cad9ec;margin-top:2px}
.mobile-site-head .mobile-live-dot{font-size:10px;background:#17493f;color:#99edbe;border-radius:24px;padding:6px 9px;white-space:nowrap}
.mobile-data-card{background:var(--secondary-background-color,#fff);border:1px solid #94a3b855;border-radius:13px;padding:13px;margin:9px 0;overflow-wrap:anywhere}
.mobile-data-top{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}
.mobile-data-title{font-size:1.05rem;line-height:1.3;font-weight:800;min-width:0}
.mobile-data-badge{font-size:.7rem;font-weight:700;border:1px solid #94a3b866;border-radius:30px;padding:4px 8px;max-width:48%;text-align:right}
.mobile-data-context{font-size:.78rem;opacity:.76;margin:6px 0}
.mobile-data-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin:11px 0 7px}
.mobile-data-field{background:#94a3b81b;padding:9px 10px;border-radius:9px;min-width:0}
.mobile-data-field small{display:block;font-size:.65rem;opacity:.75;letter-spacing:.2px;text-transform:uppercase}
.mobile-data-field strong{display:block;font-size:1.02rem;line-height:1.35;margin-top:3px;overflow-wrap:anywhere}
.mobile-data-more{font-size:.8rem;opacity:.85;margin-top:8px}
.mobile-data-more summary{cursor:pointer;padding:6px 0;font-weight:750}
.mobile-data-more dl{margin:4px 0}
.mobile-data-more dt{font-size:.71rem;opacity:.7;margin-top:9px}
.mobile-data-more dd{font-size:.84rem;font-weight:650;margin:1px 0}
.st-key-mobile_top_header,.st-key-mobile_bottom_nav,[class*="st-key-mobile_data_"]{display:none!important}
@media(max-width:768px){
 html,body{overflow-x:hidden!important}
 [data-testid="stAppViewContainer"]{overflow-x:hidden!important}
 [data-testid="stMainBlockContainer"],.block-container{padding:.65rem .7rem calc(6.2rem + env(safe-area-inset-bottom))!important;max-width:100%!important}
 [data-testid="stHeader"]{background:transparent!important}
 h1{font-size:1.5rem!important}h2{font-size:1.22rem!important}h3{font-size:1.07rem!important}
 [data-testid="stHorizontalBlock"]{gap:.45rem!important;flex-wrap:wrap!important}
 [data-testid="column"]{min-width:0!important;flex:1 1 calc(50% - 8px)!important}
 [data-testid="stMetric"]{padding:10px!important}
 [data-testid="stMetricLabel"]{font-size:.75rem!important}
 [data-testid="stMetricValue"]{font-size:1.28rem!important;overflow-wrap:anywhere}
 [data-testid="stTabs"] button{font-size:.8rem!important;white-space:nowrap!important}
 [data-testid="stSidebar"]{width:min(88vw,330px)!important}
 .st-key-mobile_top_header,[class*="st-key-mobile_data_"]{display:block!important}
 [class*="st-key-desktop_data_"]{display:none!important}
 .st-key-mobile_bottom_nav{
  display:block!important;position:fixed!important;z-index:999;left:0;right:0;bottom:0;
  background:var(--background-color,#fff);border-top:1px solid #94a3b855;
  box-shadow:0 -5px 20px #00000015;padding:7px 7px calc(7px + env(safe-area-inset-bottom))!important}
 .st-key-mobile_bottom_nav [data-testid="stHorizontalBlock"]{display:flex!important;flex-wrap:nowrap!important;gap:4px!important}
 .st-key-mobile_bottom_nav [data-testid="column"]{min-width:0!important;flex:1 1 20%!important}
 .st-key-mobile_bottom_nav button{width:100%!important;min-height:43px!important;padding:4px 2px!important;border-radius:10px!important;font-size:.67rem!important;line-height:1.2!important;white-space:normal!important;overflow-wrap:anywhere!important}
 .bk-hero{padding:16px 14px!important;border-radius:15px!important}
 .bk-big{font-size:46px!important}.bk-grid{grid-template-columns:1fr!important;gap:12px!important}
 .bk-chart{overflow-x:auto;gap:5px!important}.bk-bar-wrap{min-width:30px!important}
 .bk-stat strong{font-size:21px!important}
}
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
    st.title("🏀 Huie's Degen Center")
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


# Historical daily totals from the user’s prior ChatGPT tracker. These are chat-reported, not independently box-score verified.
BANKROLL_HISTORY = [
    {"Date":"2026-10-27","Wins":16,"Losses":4,"Excluded":0,"Status":"Chat-reported"},
    {"Date":"2026-10-28","Wins":13,"Losses":5,"Excluded":2,"Status":"Chat-reported"},
    {"Date":"2026-10-29","Wins":9,"Losses":3,"Excluded":3,"Status":"Chat-reported"},
    {"Date":"2026-10-30","Wins":15,"Losses":1,"Excluded":4,"Status":"Chat-reported"},
    {"Date":"2026-10-31","Wins":12,"Losses":6,"Excluded":2,"Status":"Chat-reported"},
    {"Date":"2026-11-01","Wins":14,"Losses":3,"Excluded":3,"Status":"Chat-reported"},
    {"Date":"2026-11-02","Wins":15,"Losses":4,"Excluded":1,"Status":"Chat-reported"},
    {"Date":"2026-11-04","Wins":16,"Losses":4,"Excluded":0,"Status":"Chat-reported"},
    {"Date":"2026-11-05","Wins":14,"Losses":5,"Excluded":0,"Status":"Chat-reported"},
    {"Date":"2026-11-06","Wins":14,"Losses":4,"Excluded":2,"Status":"Chat-reported · 2 DNP"},
]
# Source: user's November 5 screenshot; actuals checked against NBA box scores.
# Keep each original safer-line selection distinct, even when a player appears multiple times.
NOV5_PICKS = [
    ("Tristan da Silva","Threes",2,4),
    ("De'Anthony Melton","Threes",1,0),
    ("Desmond Bane","Threes",2,3),
    ("Tristan da Silva","Points",8,18),
    ("Anthony Black","Threes",1,1),
    ("Desmond Bane","Points",16,15),
    ("De'Anthony Melton","Rebounds",3,6),
    ("Oso Ighodaro","Assists",2,1),
    ("Franz Wagner","Rebounds",5,8),
    ("Stephen Curry","Points",23,29),
    ("Franz Wagner","Assists",5,15),
    ("Stephen Curry","Threes",3,6),
    ("Wendell Carter Jr.","Rebounds",7,13),
    ("Collin Gillespie","Assists",3,2),
    ("Brandin Podziemski","Assists",3,3),
    ("Franz Wagner","Points",19,15),
    ("Anthony Black","Points",10,10),
    ("Anthony Black","Assists",3,6),
    ("Yaxel Lendeborg","Assists",3,6),
]
# November 6 safer lines transcribed from the user-provided Sam's Models screenshot.
# Actual stats intentionally unfilled until independently verified.
NOV6_PICKS = [
    ("Cam Spencer","Rebounds",2),
    ("Cam Spencer","Threes",1),
    ("Grayson Allen","Threes",2),
    ("Sidy Cissoko","Rebounds",2),
    ("Cedric Coward","Rebounds",6),
    ("Toumani Camara","Threes",2),
    ("Jarrett Allen","Rebounds",6),
    ("Cam Spencer","Assists",4),
    ("Jaden McDaniels","Assists",2),
    ("Jalen Johnson","Rebounds",8),
    ("Darius Acuff Jr.","Assists",4),
    ("Zach LaVine","Points",15),
    ("Evan Mobley","Threes",1),
    ("Alex Caruso","Rebounds",3),
    ("Rudy Gobert","Rebounds",10),
    ("Nickeil Alexander-Walker","Threes",2),
    ("Deni Avdija","Assists",5),
    ("Robert Williams III","Rebounds",4),
    ("Ty Jerome","Points",17),
    ("Ace Bailey","Rebounds",4),
]
def bankroll_history_frame():
    frame=pd.DataFrame(BANKROLL_HISTORY)
    frame["Graded"]=frame["Wins"]+frame["Losses"]
    frame["Hit rate"]=frame.apply(lambda r:100*r["Wins"]/r["Graded"] if r["Graded"] else 0,axis=1)
    return frame

def performance_graph(frame):
    frame=frame[frame["Graded"]>0]
    wins=int(frame["Wins"].sum())
    losses=int(frame["Losses"].sum())
    excluded=int(frame["Excluded"].sum())
    graded=wins+losses
    pct=100*wins/graded if graded else 0
    # HTML/CSS visualization avoids a chart library and adapts to screen width.
    bars=[]
    for _,r in frame.iterrows():
        day=pd.to_datetime(r["Date"]).strftime("%b %-d") if hasattr(pd.to_datetime(r["Date"]),"strftime") else r["Date"]
        rate=float(r["Hit rate"])
        bars.append(f'<div class="bk-bar-wrap"><div class="bk-bar-track"><div class="bk-bar" style="height:{rate:.1f}%"></div></div><span>{day}</span><b>{rate:.1f}%</b></div>')
    st.markdown("""<style>
    .bk-hero{border-radius:22px;padding:26px 30px;background:linear-gradient(125deg,#0f172a,#172554 62%,#0e7490);color:#fff;box-shadow:0 16px 35px #0f172a20;margin:14px 0 22px}
    .bk-kicker{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#93c5fd;font-weight:700}
    .bk-grid{display:grid;grid-template-columns:1.2fr 1fr;gap:24px;align-items:center}
    .bk-big{font-size:clamp(48px,6vw,82px);font-weight:850;line-height:1.12;letter-spacing:-.05em}
    .bk-muted{color:#cbd5e1;font-size:13px}
    .bk-stats{display:flex;gap:20px;flex-wrap:wrap;margin-top:18px}
    .bk-stat strong{display:block;font-size:25px;color:#fff}
    .bk-stat span{font-size:12px;color:#cbd5e1}
    .bk-track{height:12px;border-radius:30px;background:#fb7185;overflow:hidden;margin:16px 0 7px}
    .bk-fill{height:100%;background:linear-gradient(90deg,#34d399,#a7f3d0);border-radius:30px}
    .bk-chart{display:flex;align-items:end;gap:7px;height:170px;padding-top:12px}
    .bk-bar-wrap{flex:1;min-width:0;text-align:center;display:flex;flex-direction:column;align-items:center;gap:5px;height:100%}
    .bk-bar-track{width:100%;height:118px;display:flex;align-items:end;border-radius:7px;background:#ffffff14;overflow:hidden}
    .bk-bar{width:100%;border-radius:6px 6px 0 0;background:linear-gradient(#67e8f9,#34d399)}
    .bk-bar-wrap span{font-size:10px;color:#cbd5e1;white-space:nowrap}
    .bk-bar-wrap b{font-size:10px;color:white}
    @media(max-width:750px){.bk-grid{grid-template-columns:1fr}.bk-hero{padding:20px}.bk-chart{height:160px}}
    </style>""",unsafe_allow_html=True)
    st.markdown(f"""<div class="bk-hero">
      <div class="bk-kicker">🏀 GREEN SAFER-LINE PERFORMANCE · HISTORICAL</div>
      <div class="bk-grid">
        <div><div class="bk-big">{pct:.1f}%</div><div class="bk-muted">Overall hit rate · {graded} graded selections</div>
          <div class="bk-track"><div class="bk-fill" style="width:{pct:.2f}%"></div></div>
          <div class="bk-stats"><div class="bk-stat"><strong>{wins}</strong><span>WINS</span></div>
          <div class="bk-stat"><strong>{losses}</strong><span>LOSSES</span></div>
          <div class="bk-stat"><strong>{excluded}</strong><span>EXCLUDED</span></div></div>
        </div>
        <div><div class="bk-muted">DAILY HIT RATE</div><div class="bk-chart">{''.join(bars)}</div></div>
      </div>
    </div>""",unsafe_allow_html=True)


def mobile_cards(frame,preferred=None,max_rows=150):
    """Phone cards that keep each player's model, line and stats together."""
    import html
    if frame is None or frame.empty:
        st.caption("No rows to display.")
        return
    cols=list(frame.columns)
    title_col=next((c for c in ("Player","Combo","Game","Date","Market","Bet") if c in cols),cols[0])
    context=[c for c in ("Game","Matchup","Market","Stat","Game time","Tipoff PST","Clock / Status") if c in cols and c!=title_col]
    status=next((c for c in ("Live status","Leg progress","Result","Outcome","Status","Model side") if c in cols),None)
    priorities=preferred or ["Safer line","Our play","Model projection","Reference line","Actual","Needed","Target","Wager","Potential profit","Reached","Hit rate","Progress"]
    priorities=[c for c in priorities if c in cols and c not in [title_col,status] + context]
    def safe(v):
        try:
            if pd.isna(v):return "—"
        except (TypeError,ValueError):
            pass
        val=str(v).strip()
        return html.escape(val) if val and val.lower() not in ("nan","none","<na>") else "—"
    pieces=[]
    for _,row in frame.head(max_rows).iterrows():
        ctx=" · ".join(safe(row[c]) for c in context if safe(row[c])!="—")
        badge=safe(row[status]) if status else ""
        pieces.append('<article class="mobile-data-card"><div class="mobile-data-top"><div class="mobile-data-title">'+safe(row[title_col])+'</div>')
        if badge and badge!="—":pieces.append('<span class="mobile-data-badge">'+badge+'</span>')
        pieces.append('</div>')
        if ctx:pieces.append('<div class="mobile-data-context">'+ctx+'</div>')
        fields=priorities[:4] or [c for c in cols if c not in [title_col,status]+context][:4]
        pieces.append('<div class="mobile-data-grid">')
        for c in fields:
            pieces.append('<div class="mobile-data-field"><small>'+html.escape(str(c))+'</small><strong>'+safe(row[c])+'</strong></div>')
        pieces.append('</div>')
        if "Progress" in fields:
            frac=number(row["Progress"])
            if frac is not None:
                frac=max(0,min(1,frac))
                pieces.append('<div class="bk-live-progress"><div class="bk-live-progress-fill" style="width:'+str(round(frac*100))+'%"></div></div>')
        extras=[c for c in cols if c not in [title_col,status]+context+fields and not str(c).startswith("_")]
        if extras:
            pieces.append('<details class="mobile-data-more"><summary>More details</summary><dl>')
            for c in extras:
                pieces.append('<dt>'+html.escape(str(c))+'</dt><dd>'+safe(row[c])+'</dd>')
            pieces.append('</dl></details>')
        pieces.append('</article>')
    st.markdown("".join(pieces),unsafe_allow_html=True)
    if len(frame)>max_rows:
        st.caption("Showing first "+str(max_rows)+" of "+str(len(frame))+" rows. Search or filter to narrow the list.")

def responsive_dataframe(frame,key,preferred=None,max_rows=150,desktop_frame=None,**kwargs):
    """Retain Streamlit desktop dataframes; show matching native cards on phones."""
    with st.container(key="desktop_data_"+key):
        st.dataframe(desktop_frame if desktop_frame is not None else frame,**kwargs)
    with st.container(key="mobile_data_"+key):
        mobile_cards(frame,preferred=preferred,max_rows=max_rows)


def show_bankroll_performance():
    st.title("📈 Bankroll Performance")
    st.caption("Green safer-line picks · October 27–November 6, 2026 · Daily totals from prior ChatGPT tracker; not independently verified")
    history=bankroll_history_frame()
    dates=history["Date"].tolist()
    selected=st.multiselect("Filter by date",dates,default=dates,key="bankroll_history_dates")
    visible=history[history["Date"].isin(selected)]
    if visible.empty:
        st.info("Select at least one date to view performance.")
        return
    performance_graph(visible)
    st.subheader("Daily results")
    display=visible[["Date","Wins","Losses","Excluded","Graded","Hit rate","Status"]].copy()
    display["Hit rate"]=display["Hit rate"].map(lambda x:f"{x:.1f}%")
    st.dataframe(display,hide_index=True,use_container_width=True)
    st.download_button("Download historical results CSV",display.to_csv(index=False),file_name="bankroll_performance_history.csv",mime="text/csv")
    st.subheader("Player-by-player results")
    chosen_date=st.selectbox("Select a date to see individual safer-line results",dates,index=len(dates)-1,key="bankroll_drilldown_date",format_func=lambda d:pd.to_datetime(d).strftime("%b %d, %Y"))
    individual={
        "2026-11-05":[
            {"Player":p,"Market":market,"Safer line":f"{line}+ {market.lower()}","Actual":actual,
             "Result":"Hit" if actual>=line else "Loss",
             "Source":"https://www.basketball-reference.com/boxscores/202611050PHO.html" if p in {"Tristan da Silva","Desmond Bane","Anthony Black","Oso Ighodaro","Franz Wagner","Wendell Carter Jr.","Collin Gillespie"} else "https://www.nba.com/game/mia-vs-gsw-0022600188/box-score"}
            for p,market,line,actual in NOV5_PICKS
        ],
    }
    if chosen_date=="2026-11-06":
        st.info("November 6: prior chat reports 14 hits, 4 misses and 2 DNPs (77.8% of 18 graded picks). The complete player-by-player actual stats were not available from that chat summary; only the explicitly documented result below is shown.")
        pending=pd.DataFrame([{"Player":p,"Market":m,"Safer line":f"{line}+ {m.lower()}","Actual":0 if p=="Grayson Allen" and m=="Threes" else "Not documented","Result":"Loss" if p=="Grayson Allen" and m=="Threes" else "Chat total only"} for p,m,line in NOV6_PICKS])
        st.dataframe(pending,hide_index=True,use_container_width=True)
        st.download_button("Download November 6 selections",pending.to_csv(index=False),file_name="bankroll_nov6_picks.csv",mime="text/csv")
        return
    detail=pd.DataFrame(individual.get(chosen_date,[]))
    if detail.empty:
        st.warning("This date is awaiting verification against original safer-line selections and final NBA box scores. The daily totals are chat-reported, but individual player stats are not documented for this date.")
    else:
        wins=detail[detail["Result"]=="Hit"]
        losses=detail[detail["Result"]=="Loss"]
        tab_all,tab_hits,tab_losses=st.tabs([f"All recorded ({len(detail)})",f"✅ Hits ({len(wins)})",f"❌ Misses ({len(losses)})"])
        for tab,subset in ((tab_all,detail),(tab_hits,wins),(tab_losses,losses)):
            with tab:
                if subset.empty:st.caption("No individually documented selections in this category yet.")
                else:st.dataframe(subset,hide_index=True,use_container_width=True)
        total=history.loc[history["Date"]==chosen_date].iloc[0]
        missing=int(total["Graded"])-len(detail)
        if missing>0:st.info(f"{len(detail)} of {int(total['Graded'])} graded selections have player-level details. {missing} individual results are still missing; the daily totals remain unchanged.")
        st.download_button("Download this date's documented player results",detail.to_csv(index=False),file_name="bankroll_players_"+chosen_date+".csv",mime="text/csv",key="player_detail_csv")
    st.caption("November 5 has a player-by-player breakdown. November 6 has chat-reported totals and one documented player result. Other dates have chat-reported totals only.")



MODEL_FIELDS=["Date","Player","Market","Reference line","Model projection","Model side","Actual","Odds","Stake","Status"]
@st.cache_data(ttl=120,show_spinner=False)
def model_log():
    try:
        blob=github_file("model_results.csv")
        return pd.read_csv(__import__("io").BytesIO(blob)).fillna("") if blob else pd.DataFrame(columns=MODEL_FIELDS)
    except Exception:
        return pd.DataFrame(columns=MODEL_FIELDS)

def model_grades(raw):
    d=raw.copy()
    for c in MODEL_FIELDS:
        if c not in d:d[c]=""
    for c in ["Reference line","Model projection","Actual","Odds","Stake"]:
        d[c]=pd.to_numeric(d[c],errors="coerce")
    d["Outcome"]="Ungraded"
    ready=d["Status"].astype(str).str.lower().isin(["final","verified"]) & d["Actual"].notna() & d["Reference line"].notna()
    over=d["Model side"].astype(str).str.lower()=="over"
    under=d["Model side"].astype(str).str.lower()=="under"
    d.loc[ready & (over|under),"Outcome"]="Loss"
    d.loc[ready & ((over & (d["Actual"]>d["Reference line"]))|(under & (d["Actual"]<d["Reference line"]))),"Outcome"]="Win"
    d.loc[ready & (over|under) & (d["Actual"]==d["Reference line"]),"Outcome"]="Push"
    priced=d["Outcome"].isin(["Win","Loss","Push"]) & (d["Stake"]>0) & ((d["Odds"]>=100)|(d["Odds"]<=-100))
    d["Net profit"]=float("nan")
    w=priced & (d["Outcome"]=="Win")
    d.loc[w,"Net profit"]=d.loc[w,"Stake"]*d.loc[w,"Odds"].map(lambda o:o/100 if o>0 else 100/abs(o))
    l=priced & (d["Outcome"]=="Loss")
    d.loc[l,"Net profit"]=-d.loc[l,"Stake"]
    d.loc[priced & (d["Outcome"]=="Push"),"Net profit"]=0.0
    d["ROI stake"]=d["Stake"].where(priced,0)
    return d

def show_model_accuracy():
    st.title("🎯 Model Accuracy & ROI")
    st.caption("Model Over/Under decisions are graded against the sportsbook reference line, not the model projection. Missing actuals and DNPs are excluded.")
    if is_admin:
        with st.expander("Admin · Import final results or enter a result"):
            st.download_button("Download CSV template",pd.DataFrame(columns=MODEL_FIELDS).to_csv(index=False),file_name="model_results_template.csv",mime="text/csv")
            uploaded_results=st.file_uploader("Import model results CSV",type="csv",key="outcome_import")
            if uploaded_results is not None:
                try:
                    candidate=pd.read_csv(uploaded_results,dtype=str).fillna("")
                    missing=set(["Date","Player","Market","Reference line","Model side","Actual","Status"])-set(candidate.columns)
                    if missing:st.error("Missing fields: "+", ".join(sorted(missing)))
                    else:
                        st.dataframe(candidate.head(10),hide_index=True)
                        if st.button("Replace saved model results with this CSV",type="primary"):
                            github_file("model_results.csv",candidate.reindex(columns=MODEL_FIELDS,fill_value="").to_csv(index=False).encode())
                            model_log.clear()
                            st.rerun()
                except Exception as e:st.error("CSV could not be imported: "+str(e))
            with st.form("add_outcome"):
                a,b,c=st.columns(3)
                date=a.date_input("Date",key="outcome_date")
                player=b.text_input("Player",key="outcome_player")
                market=c.selectbox("Market",["Points","Rebounds","Assists","Threes"],key="outcome_market")
                a,b,c=st.columns(3)
                ref=a.number_input("Reference line",min_value=0.0,step=0.5)
                proj=b.number_input("Model projection",min_value=0.0,step=0.5)
                side=c.selectbox("Model side",["Over","Under"])
                a,b,c=st.columns(3)
                actual=a.number_input("Actual",min_value=0.0,step=1.0)
                status=b.selectbox("Status",["Final","Pending","DNP"])
                odds=c.number_input("American odds (0 if unknown)",value=0,step=5)
                stake=st.number_input("Wager amount (0 if none)",min_value=0.0,value=0.0,step=5.0)
                submit=st.form_submit_button("Save result")
            if submit:
                if not player.strip():st.error("Player name is required.")
                elif not storage_ready:st.error("Private storage is not configured.")
                else:
                    old=model_log()
                    entry={"Date":str(date),"Player":player.strip(),"Market":market,"Reference line":ref,"Model projection":proj,"Model side":side,"Actual":actual,"Odds":odds if odds else "","Stake":stake if stake else "","Status":status}
                    combined=pd.concat([old,pd.DataFrame([entry])],ignore_index=True)
                    github_file("model_results.csv",combined.reindex(columns=MODEL_FIELDS,fill_value="").to_csv(index=False).encode())
                    model_log.clear()
                    st.rerun()
    raw=model_log()
    if raw.empty:
        st.info("No final model results have been saved. Daily projection workbooks do not contain verified final game outcomes. Import or enter completed games to enable the tracker.")
        return
    d=model_grades(raw)
    markets=sorted(d["Market"].astype(str).unique())
    selected=st.multiselect("Markets",markets,default=markets,key="accuracy_market")
    d=d[d["Market"].isin(selected)]
    graded=d[d["Outcome"].isin(["Win","Loss","Push"])]
    decided=graded[graded["Outcome"].isin(["Win","Loss"])]
    wins=int((decided["Outcome"]=="Win").sum())
    paid=graded[graded["ROI stake"]>0]
    investment=float(paid["ROI stake"].sum())
    profit=float(paid["Net profit"].sum()) if len(paid) else 0.0
    a,b,c,e=st.columns(4)
    a.metric("Model win rate",str(round(100*wins/len(decided),1))+"%" if len(decided) else "N/A")
    b.metric("Decisions graded",len(decided))
    c.metric("Net profit",("$"+format(profit,",.2f")) if investment else "N/A")
    e.metric("ROI",str(round(100*profit/investment,1))+"%" if investment else "N/A")
    st.caption(str(len(d)-len(graded))+" ungraded · "+str(int((graded["Outcome"]=="Push").sum()))+" pushes · "+str(len(paid))+" bets with valid odds and stake. ROI excludes bets without odds/stake.")
    if len(decided):
        st.subheader("Accuracy by market")
        group=decided.groupby("Market")["Outcome"].agg(Total="size",Wins=lambda x:(x=="Win").sum()).reset_index()
        group["Hit rate"]=100*group["Wins"]/group["Total"]
        st.dataframe(group,hide_index=True,use_container_width=True)
    st.subheader("Projection vs. actual")
    chart=d[d["Model projection"].notna() & d["Actual"].notna() & d["Outcome"].isin(["Win","Loss","Push"])].copy()
    if chart.empty:st.info("No completed projection/actual pairs yet.")
    else:
        import altair as alt
        maxval=max(float(chart["Actual"].max()),float(chart["Model projection"].max()),1)
        dots=alt.Chart(chart).mark_circle(size=85).encode(x=alt.X("Model projection:Q",scale=alt.Scale(domain=[0,maxval])),y=alt.Y("Actual:Q",scale=alt.Scale(domain=[0,maxval])),color="Market:N",tooltip=["Date","Player","Market","Model projection","Actual","Outcome"])
        diagonal=alt.Chart(pd.DataFrame({"x":[0,maxval],"y":[0,maxval]})).mark_line(strokeDash=[5,5],color="#94a3b8").encode(x="x:Q",y="y:Q")
        st.altair_chart(diagonal+dots,use_container_width=True)
    st.subheader("Saved outcome history")
    st.dataframe(d,hide_index=True,use_container_width=True)
    st.download_button("Export model outcomes",d.to_csv(index=False),file_name="model_outcomes.csv",mime="text/csv")


def live_name(value):
    import re,unicodedata
    normalized=unicodedata.normalize("NFKD",str(value)).encode("ascii","ignore").decode().lower()
    return re.sub("[^a-z0-9]","",normalized)

@st.cache_data(ttl=30,show_spinner=False)
def espn_stats(day):
    root="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/"
    def fetch(endpoint):
        req=urllib.request.Request(root+endpoint,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
        with urllib.request.urlopen(req,timeout=12) as resp:return json.load(resp)
    events=fetch("scoreboard?dates="+day.replace("-","")).get("events",[])
    rows=[]
    for event in events:
        eid=event.get("id")
        if not eid:continue
        try:summary=fetch("summary?event="+str(eid))
        except Exception:continue
        status=event.get("status",{}).get("type",{})
        for team in summary.get("boxscore",{}).get("players",[]):
            for category in team.get("statistics",[]):
                labels=category.get("labels",[])
                for athlete in category.get("athletes",[]):
                    if athlete.get("didNotPlay") or athlete.get("inactive"):continue
                    stats=dict(zip(labels,athlete.get("stats",[])))
                    def stat(k):
                        try:return float(stats[k])
                        except (ValueError,TypeError,KeyError):return None
                    threes=None
                    for k in ["3PT","3PM-A","3FG"]:
                        if k in stats:
                            try:threes=float(str(stats[k]).split("-")[0])
                            except ValueError:pass
                            break
                    name=athlete.get("athlete",{}).get("displayName","")
                    for market,actual in [("Points",stat("PTS")),("Rebounds",stat("REB")),("Assists",stat("AST")),("Threes",threes)]:
                        if actual is not None:rows.append({"Key":live_name(name)+"|"+market.lower(),"Actual":actual,"Matchup":event.get("shortName",""),"Game status":status.get("shortDetail",""),"Game state":status.get("state",""),"Player source":name})
    return pd.DataFrame(rows),len(events)

def show_bankroll_live_tracker(embedded=False):
    from datetime import date
    from zoneinfo import ZoneInfo
    import re
    if not embedded:st.title("🔴 Bankroll Live Tracking")
    else:st.subheader("🔴 Bankroll Live Tracker")
    st.caption("Bankroll Builder workbook props · ESPN NBA box scores · auto-refresh every 30 seconds while open.")
    if not bankroll:
        st.warning("No Bankroll Builder sheet is available in the loaded workbook.")
        return
    frame=sheets[bankroll].copy()
    playercol=lookup(frame,"Player")
    marketcol=lookup(frame,"Market","Stat")
    linecol=lookup(frame,"Safer line")
    gamecol=lookup(frame,"Game")
    sidecol=lookup(frame,"Model side")
    modelcol=lookup(frame,"Model projection","Reference line")
    if not all([playercol,linecol]):
        st.warning("The bankroll workbook needs Player and Safer line columns for tracking.")
        return
    prefix="embedded_bankroll" if embedded else "bankroll_live"
    game_date=st.date_input("Game date (match your uploaded workbook)",value=datetime.now(ZoneInfo("America/Los_Angeles")).date(),key=prefix+"_date")
    st.caption("Check the selected date: player-name matching alone cannot prove a prop belongs to a particular game.")
    @st.fragment(run_every="30s")
    def render_bankroll_live():
        if st.button("↻ Refresh now",key=prefix+"_refresh"):
            espn_nba_boxscores.clear()
        try:
            games,players=espn_nba_boxscores(game_date.strftime("%Y%m%d"))
        except Exception as exc:
            st.warning("ESPN box scores unavailable. No picks have been graded or saved.")
            with st.expander("Connection details"):st.code(str(exc))
            return
        st.caption(str(len(games))+" NBA games found · Last checked "+datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%I:%M:%S %p PT"))
        if not games:
            st.info("No NBA games found for this date.")
            return
        if any(g.get("boxscore_error") for g in games):
            st.warning("Some game box scores could not be loaded. Missing stats are not counted as losses.")
        def safer_market(value):
            v=str(value).lower()
            for token,market in [("assist","Assists"),("rebound","Rebounds"),("three","Threes"),("3pt","Threes"),("3-pointer","Threes"),("point","Points")]:
                if token in v:return market
            return ""
        def teams_from_matchup(value):
            # Compare the two teams rather than exact ESPN display punctuation/order.
            return set(re.findall(r"[A-Z]{2,4}",str(value).upper()))
        game_by_id={str(g["id"]):g for g in games}
        # ESPN scoreboard competition team abbreviations are more reliable than
        # shortName punctuation; accept either home/away ordering.
        import urllib.request
        team_pairs={}
        try:
            request=urllib.request.Request("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates="+game_date.strftime("%Y%m%d"),headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(request,timeout=12) as response:
                board=json.load(response)
            for event in board.get("events",[]):
                competitors=(event.get("competitions") or [{}])[0].get("competitors",[])
                team_pairs[str(event.get("id"))]={c.get("team",{}).get("abbreviation","").upper() for c in competitors}
        except Exception:
            pass
        rows=[]
        for _,pick in frame.iterrows():
            player_name=str(pick[playercol])
            market=str(pick[marketcol]).strip().title() if marketcol else safer_market(pick[linecol])
            if market not in ("Points","Rebounds","Assists","Threes"):
                market=safer_market(pick[linecol])
            workbook_game=str(pick[gamecol]) if gamecol else ""
            expected_teams=teams_from_matchup(workbook_game)
            candidate=match_espn_player(player_name,players)
            game=candidate["game"] if candidate else None
            actual=candidate["stats"].get(market) if candidate else None
            if candidate and expected_teams:
                live_teams=team_pairs.get(str(game["id"]),set())
                if live_teams and live_teams!=expected_teams:
                    candidate=None
                    game=None
                    actual=None
            target_match=re.search(r"\d+(?:\.\d+)?",str(pick[linecol]))
            target=float(target_match.group()) if target_match else None
            under="under" in str(pick[linecol]).lower()
            if actual is None or target is None:
                result="⚪ Unverified"
            elif game["state"]=="post":
                result="🟢 Hit" if (actual<target if under else actual>=target) else "🔴 Miss"
            elif game["state"]=="in":
                result=("🟡 Under in progress" if under else ("🟢 Target reached" if actual>=target else "🟡 In progress"))
            else:
                result="⚪ Not started / unverified"
            needed=max(0,target-actual) if actual is not None and target is not None and not under else None
            # A scoreboard matchup can provide a game time/status even when the player
            # is absent from the box score. It does NOT provide an actual or grade.
            display_game=game
            if display_game is None and expected_teams:
                display_game=next((g for g in games
                                   if team_pairs.get(str(g["id"]))==expected_teams),None)
            raw_model=pick[modelcol] if modelcol else None
            model_label=str(raw_model) if raw_model is not None and pd.notna(raw_model) else ""
            row={"Player":player_name,"Game":workbook_game,"Market":market,
                 "Model line":model_label,"Safer line":str(pick[linecol]),
                 "Actual":actual,"Needed":needed,
                 "Live status":result,
                 "Game status":display_game["detail"] if display_game else "Unavailable",
                 "_tipoff":display_game.get("start_utc","") if display_game else "9999"}
            rows.append(row)
        output=pd.DataFrame(rows)
        counts=output["Live status"].value_counts()
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Bankroll props",len(output))
        c2.metric("Reached / hit",sum(v for k,v in counts.items() if "Target reached" in k or k=="🟢 Hit"))
        c3.metric("Final misses",int(counts.get("🔴 Miss",0)))
        c4.metric("Unverified",sum(v for k,v in counts.items() if "Unverified" in k))
        output=output.sort_values(["_tipoff","Game","Player"],kind="stable")
        # On a phone, the full-width table disappears automatically. The card UI
        # keeps the player, model projection, safer line, actual and status together.
        with st.container(key=prefix+"_desktop_grid"):
            st.dataframe(output.drop(columns=["_tipoff"]),hide_index=True,use_container_width=True)
        with st.container(key=prefix+"_mobile_ui"):
            import html
            choice=st.radio("Player filter",["Active","All","Live","Hit","Miss","Unverified"],
                            horizontal=True,key=prefix+"_mobile_filter",
                            help="Active hides unverified stats; All includes a collapsed unverified list.")
            def unverified_status(status):
                return "Unverified" in status or "Not started" in status
            def card_group(data):
                if data.empty:
                    st.caption("No player props in this filter.")
                    return
                chunks=[]
                # Grouping by actual game start time, then matchup, preserves tipoff order.
                for (start,matchup),group in data.groupby(["_tipoff","Game"],sort=False,dropna=False):
                    start_label=""
                    if start and start!="9999":
                        try:
                            start_label=datetime.fromisoformat(str(start).replace("Z","+00:00")).astimezone(
                                ZoneInfo("America/Los_Angeles")).strftime("%-I:%M %p PT")
                        except (ValueError,TypeError):
                            pass
                    game_label=str(matchup) if matchup and str(matchup)!="nan" else "Matchup unavailable"
                    game_status=group.iloc[0]["Game status"]
                    chunks.append('<div class="bk-live-game">'+html.escape(game_label)+
                                  '<small>'+html.escape(start_label or "Tipoff unavailable")+
                                  ' · '+html.escape(str(game_status))+'</small></div>')
                    for _,r in group.iterrows():
                        state=str(r["Live status"])
                        kind=("hit" if "🟢" in state else "miss" if "🔴" in state
                              else "live" if "🟡" in state else "unverified")
                        actual=r["Actual"]
                        has_actual=pd.notna(actual)
                        actual_text=(format(float(actual),"g") if has_actual else "—")
                        needed=r["Needed"]
                        needed_text=(format(float(needed),"g") if pd.notna(needed) else "—")
                        line=str(r["Safer line"])
                        match=re.search(r"\d+(?:\.\d+)?",line)
                        threshold=float(match.group()) if match else None
                        under="under" in line.lower()
                        pct=(min(100,max(0,float(actual)/threshold*100))
                             if has_actual and threshold and threshold>0 and not under else 0)
                        status_text=state.split(" ",1)[-1]
                        model_info=('<div class="bk-live-model">Model projection: <b>'+
                                    html.escape(str(r["Model line"]))+'</b></div>'
                                    if str(r["Model line"]).strip() else "")
                        bar=('<div class="bk-live-progress"><div class="bk-live-progress-fill" style="width:'+
                             f'{pct:.0f}%"></div></div>' if threshold and not under and has_actual else "")
                        note=("Under line · monitor until final" if under and has_actual else
                              f'{pct:.0f}% of target · Provisional until final' if has_actual and threshold else
                              "Awaiting verified player stats")
                        chunks.append('<div class="bk-live-card '+kind+'">'+
                            '<div class="bk-live-head"><span class="bk-live-name">'+
                            html.escape(str(r["Player"]))+'</span><span class="bk-live-status">'+
                            html.escape(status_text)+'</span></div>'+
                            '<div class="bk-live-line">🎯 '+html.escape(line)+'</div>'+model_info+
                            '<div class="bk-live-stats">'+
                            '<div class="bk-live-stat"><span>ACTUAL</span><b>'+actual_text+'</b></div>'+
                            '<div class="bk-live-stat"><span>TARGET</span><b>'+
                            (format(threshold,"g") if threshold is not None else "—")+'</b></div>'+
                            '<div class="bk-live-stat"><span>NEEDED</span><b>'+needed_text+'</b></div>'+
                            '</div>'+bar+
                            '<div class="bk-live-note">'+html.escape(note)+'</div></div>')
                st.markdown("".join(chunks),unsafe_allow_html=True)
            unknown=output["Live status"].map(unverified_status)
            if choice=="Active":
                selected=output[~unknown]
            elif choice=="Live":
                selected=output[output["Live status"].str.contains("In progress|Target reached|Under in progress",case=False,regex=True)]
            elif choice=="Hit":
                selected=output[output["Live status"].str.contains("Hit|Target reached",case=False,regex=True)]
            elif choice=="Miss":
                selected=output[output["Live status"].str.contains("Miss",case=False,regex=False)]
            elif choice=="Unverified":
                selected=output[unknown]
            else:
                selected=output[~unknown]
            card_group(selected)
            if choice in ("Active","All") and unknown.any():
                with st.expander("⚪ Unverified / awaiting stats ("+str(int(unknown.sum()))+")",expanded=False):
                    card_group(output[unknown])
        st.caption("Uses the same ESPN player stats as My Bets. In-progress targets are provisional; missing players and missing box scores are never treated as losses.")
    render_bankroll_live()


def show_live_tracker():
    st.title("🔴 Live Prop Tracker")
    st.caption("ESPN box-score feed · manually refreshed · approximately 2-minute cache · not guaranteed real-time")
    from zoneinfo import ZoneInfo
    pacific=ZoneInfo("America/Los_Angeles")
    day=st.date_input("NBA game date (must match the workbook)",value=datetime.now(pacific).date(),key="live_date")
    st.warning("The currently uploaded workbook may be from another date. Select the matching game date; player-name matches alone do not verify a matchup.")
    choice=st.radio("Prop source",["Bankroll safer lines","Model reference lines"],horizontal=True)
    sheet=bankroll if choice=="Bankroll safer lines" else allprops
    if not sheet:
        st.info("The selected sheet is not available in the workbook.")
        return
    props=sheets[sheet].copy()
    playercol=lookup(props,"Player")
    marketcol=lookup(props,"Market")
    linecol=lookup(props,"Safer line") if choice=="Bankroll safer lines" else lookup(props,"Reference line")
    sidecol=lookup(props,"Model side")
    if not playercol or not marketcol or not linecol:
        st.warning("Required Player, Market or target line columns are missing.")
        return
    if st.button("↻ Refresh NBA box scores",type="primary",key="refresh_boxscores"):
        espn_stats.clear()
    try:stats,games_count=espn_stats(str(day))
    except Exception as exc:
        st.error("ESPN stats could not be retrieved. Saved data is unchanged.")
        st.caption(type(exc).__name__)
        return
    st.caption(str(games_count)+" games returned · Checked "+datetime.now(pacific).strftime("%I:%M %p PT"))
    if stats.empty:
        st.info("No player statistics are available from the feed for this date.")
        return
    props["Key"]=props[playercol].map(live_name)+"|"+props[marketcol].astype(str).str.lower().str.strip()
    # Do not assign ambiguous duplicate player/market records.
    duplicates=set(stats.loc[stats["Key"].duplicated(keep=False),"Key"])
    stats=stats[~stats["Key"].isin(duplicates)].drop_duplicates("Key")
    joined=props.merge(stats,on="Key",how="left")
    def outcome(row):
        actual=number(row.get("Actual"))
        threshold=number(row.get(linecol))
        if threshold is None and choice=="Bankroll safer lines":
            import re
            match=re.search(r"\d+(?:\.\d+)?",str(row.get(linecol,"")))
            if match:threshold=float(match.group())
        if actual is None or threshold is None:return "Unverified"
        final=str(row.get("Game state","")).lower()=="post"
        if choice=="Bankroll safer lines":
            if final:return "Hit" if actual>=threshold else "Miss"
            return "Target reached (in progress)" if actual>=threshold else "In progress"
        direction=str(row.get(sidecol,"")).strip().lower() if sidecol else ""
        if direction not in ["over","under"]:return "Unverified"
        if not final:return "In progress (not graded)"
        if actual==threshold:return "Push"
        return "Hit" if ((direction=="over" and actual>threshold) or (direction=="under" and actual<threshold)) else "Miss"
    joined["Live result"]=joined.apply(outcome,axis=1)
    cols=[playercol,marketcol,linecol,"Actual","Live result","Matchup","Game status"]
    if choice!="Bankroll safer lines" and sidecol:cols.insert(3,sidecol)
    st.dataframe(joined[[c for c in cols if c in joined.columns]],hide_index=True,use_container_width=True)
    st.caption("Missing players, ambiguous names, incomplete box scores and games still in progress are not counted as final losses. Results are not automatically saved to the historical model accuracy log.")


PERSONAL_BETS=[
("3-leg B",289,32.4,[("C. Johnson","Threes",1),("J. Murray","Threes",3),("A. Nembhard","Threes",2)]),
("3-leg A",1264,6.6,[("J. Murray","Threes",4),("A. Nembhard","Threes",3),("O. Toppin","Threes",2)]),
("7-leg B",1117,7.6,[("J. Murray","Threes",2),("A. Nembhard","Assists",6),("A. Nembhard","Points",15),("A. Nesmith","Points",10),("O. Toppin","Points",10),("J. Murray","Rebounds",4),("O. Toppin","Rebounds",4)]),
("7-leg A",483,39.4,[("J. Murray","Threes",2),("A. Nembhard","Threes",1),("A. Nembhard","Assists",4),("P. Siakam","Assists",2),("A. Nembhard","Points",10),("P. Siakam","Points",15),("P. Siakam","Rebounds",4)]),
("9-leg",1113,7.8,[("A. Nembhard","Assists",6),("C. Braun","Points",10),("J. Murray","Points",20),("N. Jokic","Points",20),("A. Nesmith","Points",10),("P. Siakam","Points",15),("A. Gordon","Rebounds",4),("J. Murray","Rebounds",4),("N. Jokic","Rebounds",8)])
]
ROBINHOOD_NOV7_BETS=[
("9-leg",1113,7.8,101.96,15.15,[["A. Nembhard","Assists",6],["C. Braun","Points",10],["J. Murray","Points",20],["N. Jokić","Points",20],["A. Nesmith","Points",10],["P. Siakam","Points",15],["A. Gordon","Rebounds",4],["J. Murray","Rebounds",4],["N. Jokić","Rebounds",8]]),
("5-leg",1281,6.5,99.98,16.72,[["N. Alexander-Walker","Threes",3],["J. Murray","Threes",3],["J. Smith Jr.","Threes",2],["T. Silva","Threes",3],["T. Camara","Threes",3]]),
("7-leg A",483,39.4,199.97,9.67,[["J. Murray","Threes",2],["A. Nembhard","Threes",1],["A. Nembhard","Assists",4],["P. Siakam","Assists",2],["A. Nembhard","Points",10],["P. Siakam","Points",15],["P. Siakam","Rebounds",4]]),
("3-leg C",276,34.2,99.92,5.53,[["N. Alexander-Walker","Threes",3],["T. Silva","Threes",2],["T. Camara","Threes",2]]),
("7-leg B",1117,7.6,100,15.11,[["J. Murray","Threes",2],["A. Nembhard","Assists",6],["A. Nembhard","Points",15],["A. Nesmith","Points",10],["O. Toppin","Points",10],["J. Murray","Rebounds",4],["O. Toppin","Rebounds",4]]),
("4-leg A",800,11,99.92,11.92,[["L. Dort","Threes",2],["N. Alexander-Walker","Threes",4],["O. Okongwu","Threes",1],["M. Porter Jr.","Threes",3]]),
("3-leg A",1264,6.6,99.97,16.55,[["J. Murray","Threes",4],["A. Nembhard","Threes",3],["O. Toppin","Threes",2]]),
("3-leg B",289,32.4,99.42,5.78,[["C. Johnson","Threes",1],["J. Murray","Threes",3],["A. Nembhard","Threes",2]]),
("4-leg B",293,32.1,99.92,5.87,[["A. Nembhard","Assists",6],["R. Sheppard","Assists",2],["A. Nembhard","Points",10],["O. Okongwu","Rebounds",6]]),
("4-leg C",255,37.2,99.96,5.1,[["C. McCollum","Assists",2],["D. Daniels","Assists",4],["F. Wagner","Assists",6],["D. Avdija","Assists",4]]),
("3-leg D",314,29.8,99.86,6.29,[["N. Alexander-Walker","Threes",3],["E. Mobley","Threes",1],["S. Gilgeous-Alexander","Threes",2]]),
("3-leg E",272,34.7,99.83,5.45,[["J. Smith Jr.","Threes",2],["T. Silva","Threes",2],["T. Camara","Threes",2]]),
("6-leg",835,10.5,99.96,12.29,[["N. Alexander-Walker","Threes",3],["J. Smith Jr.","Threes",2],["E. Mobley","Threes",1],["T. Silva","Threes",2],["T. Camara","Threes",2],["S. Gilgeous-Alexander","Threes",2]]),
("3-leg F",1851,4.2,99.99,22.25,[["A. Sengun","Assists",8],["D. Green","Assists",8],["D. Avdija","Assists",8]]),
("3-leg G",385,24,99.77,7.37,[["A. Sengun","Assists",6],["D. Green","Assists",6],["D. Avdija","Assists",6]]),
("3-leg H",286,32.9,99.82,5.73,[["O. Toppin","Points",10],["J. Smith Jr.","Points",10],["T. Silva","Points",10]])
]

@st.cache_data(ttl=120,show_spinner=False)
def saved_bet_statuses():
    try:
        blob=github_file("personal_bets_status.csv")
        return pd.read_csv(__import__("io").BytesIO(blob),dtype=str).fillna("") if blob else pd.DataFrame(columns=["Bet","Status","Net P/L"])
    except Exception:
        return pd.DataFrame(columns=["Bet","Status","Net P/L"])


@st.cache_data(ttl=120,show_spinner=False)
def imported_bet_rows():
    try:
        raw=github_file("personal_bets_imports.json")
        data=json.loads(raw.decode("utf-8")) if raw else []
        return data if isinstance(data,list) else []
    except Exception:
        return []

def parse_robinhood_positions(text):
    import re
    # Supports copied desktop position lists with contract description followed by
    # "289 Yes @ 32.4¢". Wrapped descriptions are joined before parsing.
    text=text.replace("\u00a0"," ").replace("￠","¢")
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    found=[]
    pattern=re.compile(r"^([\d,]+)\s+Yes\s*@\s*([\d.]+)\s*(?:¢|cents?)",re.I)
    leg_pattern=re.compile(r"^(.+?)\s+(\d+)\+\s*(Threes|Points|Assists|Rebounds)\s*$",re.I)
    buffer=[]
    for line in lines:
        m=pattern.match(line)
        if m:
            description=" ".join(buffer).strip()
            # Strip header/UI artifacts when present; only validated prop tokens survive.
            parts=[x.strip() for x in description.split(",")]
            legs=[]
            for part in parts:
                lm=leg_pattern.match(part)
                if lm:
                    legs.append([lm.group(1).strip(),lm.group(3).title(),int(lm.group(2))])
            if legs:
                qty=int(m.group(1).replace(",",""))
                price=float(m.group(2))
                if qty>0 and 0<price<=100:
                    found.append({"qty":qty,"cents":price,"legs":legs,"raw":description})
            buffer=[]
        elif not line.lower().startswith(("your positions","close ","getting price")):
            buffer.append(line)
    return found

def show_bulk_bet_import():
    with st.expander("📋 Bulk import Robinhood positions",expanded=False):
        st.caption("Copy the entire Your Positions list from Robinhood desktop and paste it below. Review parsed legs before saving. Nothing is submitted to Robinhood.")
        import_date=st.date_input("Game date for imported positions",value=datetime.now().date(),key="bulk_bet_date")
        pasted=st.text_area("Paste positions",height=180,placeholder="J. Murray 2+ Threes, A. Nembhard 6+ Assists\n1,117 Yes @ 7.6¢",key="bulk_bets_text")
        parsed=parse_robinhood_positions(pasted) if pasted.strip() else []
        if pasted.strip():
            if not parsed:st.warning("No complete positions recognized. Include each description and its quantity / Yes @ price line.")
            else:
                st.success(str(len(parsed))+" positions recognized. Check all legs and prices before saving.")
                for i,item in enumerate(parsed,1):
                    st.markdown("**Position "+str(i)+" · "+str(item["qty"])+" Yes @ "+str(item["cents"])+"¢ · "+str(len(item["legs"]))+" recognized legs**")
                    st.dataframe(pd.DataFrame(item["legs"],columns=["Player","Market","Target"]),hide_index=True,use_container_width=True)
                st.warning("If any legs are missing or truncated, do not save; fix the pasted text first.")
                if st.button("Save reviewed positions to private storage",key="save_bulk_bets",type="primary"):
                    if not storage_ready:st.error("Private GitHub storage is not configured.")
                    else:
                        current=imported_bet_rows()
                        added=0
                        for item in parsed:
                            row={"date":str(import_date),"qty":item["qty"],"cents":item["cents"],"legs":item["legs"]}
                            if row not in current:
                                current.append(row)
                                added+=1
                        try:
                            github_file("personal_bets_imports.json",json.dumps(current,ensure_ascii=False,indent=2).encode("utf-8"))
                            imported_bet_rows.clear()
                            st.success(str(added)+" new positions saved; "+str(len(parsed)-added)+" duplicates skipped.")
                            st.rerun()
                        except Exception as exc:st.error("Unable to save positions: "+str(exc))


@st.cache_data(ttl=30,show_spinner=False)
def espn_nba_boxscores(date_string):
    import unicodedata
    def fetch(url):
        req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; HuieDashboard/1.0)","Accept":"application/json"})
        with urllib.request.urlopen(req,timeout=12) as response:
            return json.load(response)
    scoreboard=fetch("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates="+date_string)
    events=scoreboard.get("events",[])
    players=[]
    games=[]
    for event in events:
        eid=event.get("id")
        comp=(event.get("competitions") or [{}])[0]
        status=event.get("status",{})
        game={"id":eid,"name":event.get("shortName",event.get("name","Game")),
              "start_utc":event.get("date",""),
              "state":status.get("type",{}).get("state","unknown"),
              "detail":status.get("type",{}).get("shortDetail",status.get("type",{}).get("detail",""))}
        games.append(game)
        try:
            summary=fetch("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event="+str(eid))
            for team in summary.get("boxscore",{}).get("players",[]):
                for group in team.get("statistics",[]):
                    labels=[str(x).upper() for x in group.get("labels",[])]
                    keys=[str(x).lower() for x in group.get("keys",[])]
                    for athlete in group.get("athletes",[]):
                        if athlete.get("didNotPlay") or athlete.get("inactive"):continue
                        stats=athlete.get("stats",[])
                        def stat(names):
                            for key in names:
                                if key in keys:return stats[keys.index(key)] if keys.index(key)<len(stats) else None
                                if key.upper() in labels:return stats[labels.index(key.upper())] if labels.index(key.upper())<len(stats) else None
                            return None
                        def number(v):
                            try:return int(float(str(v).replace(",","")))
                            except (TypeError,ValueError):return None
                        threes=stat(["3pt","3pm","3-pt"])
                        if threes is not None and "-" in str(threes):
                            threes=str(threes).split("-")[0]
                        values={"Points":number(stat(["pts","points"])),
                                "Rebounds":number(stat(["reb","rebs","rebounds"])),
                                "Assists":number(stat(["ast","assists"])),
                                "Threes":number(threes)}
                        athlete_info=athlete.get("athlete",{})
                        players.append({"name":athlete_info.get("displayName",athlete_info.get("fullName","")),
                                        "team":team.get("team",{}).get("abbreviation",""),
                                        "game":game, "stats":values})
        except Exception:
            game["boxscore_error"]=True
    return games,players

def match_espn_player(short_name,players):
    import unicodedata
    def norm(value):
        return "".join(ch for ch in unicodedata.normalize("NFKD",str(value).lower()) if ch.isalnum() or ch.isspace()).strip()
    parts=norm(short_name).split()
    if len(parts)<2:return None
    initial=parts[0][0]
    surname=" ".join(parts[1:])
    matches=[]
    for player in players:
        full=norm(player["name"]).split()
        if len(full)>1 and full[0].startswith(initial) and (" ".join(full[1:])==surname or full[-1]==parts[-1]):
            matches.append(player)
    return matches[0] if len(matches)==1 else None

def show_personal_bets():
    st.title("💸 My Bets · Robinhood")
    st.caption("Admin-only · November 7, 2026 · NBA predictions")
    st.info("November 7 positions imported from your Robinhood transaction text. Total cost includes actual reported fees for these 16 purchases. No legs have been verified or settled.")
    imported=imported_bet_rows()
    # The imported transaction listing is newest-first; display oldest-first.
    # Retain the original name as the settlement storage key.
    original_bets=list(reversed(ROBINHOOD_NOV7_BETS))
    all_bets=[(name,qty,price,legs) for name,qty,price,cost,fees,legs in original_bets]
    for i,item in enumerate(imported,1):
        all_bets.append((str(item.get("date",""))+" · Import "+str(i),int(item["qty"]),float(item["cents"]),item["legs"]))
    # Display labels are separate from persisted settlement IDs.
    labels={name:f"Parlay {i} - {len(legs)} Legs" for i,(name,qty,price,legs) in enumerate(all_bets,1)}
    saved=saved_bet_statuses()
    byid={r["Bet"]:r for _,r in saved.iterrows()} if not saved.empty else {}
    total=sum(cost for _,_,_,cost,_,_ in ROBINHOOD_NOV7_BETS)+sum(q*p/100 for _,q,p,_ in all_bets[len(ROBINHOOD_NOV7_BETS):])
    settled=[]
    for row in byid.values():
        if row.get("Status") in ["Won","Lost","Closed"]:
            try:settled.append(float(row["Net P/L"]))
            except (TypeError,ValueError):pass
    potential_profit=sum(qty for _,qty,_,_ in all_bets)-total
    a,b,c=st.columns(3)
    a.metric("Total entry cost","$"+format(total,",.2f"))
    b.metric("Total potential profit","$"+format(potential_profit,",.2f"))
    c.metric("Realized P/L","$"+format(sum(settled),",.2f") if settled else "Not recorded")
    st.caption(str(len(all_bets))+" combos · "+str(sum(len(legs) for _,_,_,legs in all_bets))+" legs · Potential profit assumes every Yes combo wins, with recorded entry fees included where available; excludes any future exit fees.")
    st.caption("November 7: $1,700.25 total paid including $166.78 in commissions and fees across 16 purchases. Additional bulk-imported bets are estimated before fees.")
    if storage_ready:
        with st.expander("Record settlement (admin)"):
            with st.form("personal_settlement"):
                bet=st.selectbox("Combo",[x[0] for x in all_bets],format_func=lambda key:labels.get(key,key))
                status=st.selectbox("Status",["Pending","Won","Lost","Closed","Voided"])
                pnl=st.text_input("Realized net P/L in dollars (blank if unknown)")
                submit=st.form_submit_button("Save")
            if submit:
                try:
                    if pnl.strip():float(pnl)
                    updated=saved[saved["Bet"]!=bet].copy()
                    updated=pd.concat([updated,pd.DataFrame([{"Bet":bet,"Status":status,"Net P/L":pnl}])],ignore_index=True)
                    github_file("personal_bets_status.csv",updated.to_csv(index=False).encode())
                    saved_bet_statuses.clear()
                    st.rerun()
                except ValueError:st.error("Enter a valid dollar amount.")
                except Exception as exc:st.error("Could not save: "+str(exc))
    @st.fragment(run_every="30s")
    def render_live_nba_tracker():
        st.subheader("🏀 NBA Player Prop Tracker")
        st.caption("Free ESPN public box-score feed (unofficial). Automatically refreshes every 30 seconds while this page is open; cached for up to 30 seconds. Statistical progress is not Robinhood settlement.")
        from datetime import date
        track_date=st.date_input("Game date",value=date(2026,11,7),key="nba_live_date")
        if st.button("↻ Refresh NBA stats",key="refresh_nba_stats"):
            espn_nba_boxscores.clear()
        try:
            games,players=espn_nba_boxscores(track_date.strftime("%Y%m%d"))
            if not games:
                st.info("No NBA games found for this date. Choose another date or retry later.")
            else:
                games.sort(key=lambda g:g.get("start_utc","") or "9999")
                st.caption("Games (earliest first): "+" · ".join(g["name"]+" ("+g["detail"]+")" for g in games))
                if any(g.get("boxscore_error") for g in games):
                    st.warning("Some box scores were unavailable. Missing stats are shown as unavailable, not zero.")
                unique_props=sorted({(p,m,int(t)) for _,_,_,legs in all_bets for p,m,t in legs})
                actuals={}
                rows=[]
                for p,m,t in unique_props:
                    player=match_espn_player(p,players)
                    value=player["stats"].get(m) if player else None
                    actuals[(p,m,t)]=value
                    game=player["game"] if player else None
                    state=game["state"] if game else "unknown"
                    if value is None:
                        progress="⚪ Unavailable"
                    elif value>=t:
                        progress="🟢 Reached"
                    elif state=="post":
                        progress="🔴 Below target (final)"
                    else:
                        progress="🟡 In progress" if state=="in" else "⚪ Not started / awaiting stats"
                    from zoneinfo import ZoneInfo
                    start_time=game.get("start_utc","") if game else ""
                    try:
                        tipoff=datetime.fromisoformat(start_time.replace("Z","+00:00")).astimezone(ZoneInfo("America/Los_Angeles")).strftime("%-I:%M %p PT")
                    except (ValueError,TypeError):
                        tipoff="Unknown"
                    rows.append({"Player":p,"Stat":m,"Target":str(t)+"+","Actual":value,
                                 "Game time":tipoff,"_sort_time":start_time or "9999",
                                 "Needed":max(0,t-value) if value is not None else None,
                                 "Game":game["name"] if game else "Unmatched",
                                 "Clock / Status":game["detail"] if game else "Unavailable",
                                 "Leg progress":progress})
                combos=[]
                for name,qty,price,legs in all_bets:
                    values=[actuals.get((p,m,int(t))) for p,m,t in legs]
                    hit=sum(v is not None and v>=int(t) for v,(_,_,t) in zip(values,legs))
                    unknown=sum(v is None for v in values)
                    combos.append({"Combo":labels.get(name,name),"Reached":str(hit)+"/"+str(len(legs)),
                                   "Unavailable legs":unknown,"Progress":hit/len(legs) if legs else 0})
                t1,t2=st.tabs(["Player statistics","Combo progress"])
                with t1:
                    stats_df=pd.DataFrame(rows).sort_values(["_sort_time","Game","Player","Stat","Target"],kind="stable").drop(columns=["_sort_time"])
                    st.dataframe(stats_df,hide_index=True,use_container_width=True)
                with t2:
                    st.dataframe(pd.DataFrame(combos),hide_index=True,use_container_width=True,
                                 column_config={"Progress":st.column_config.ProgressColumn("Progress",min_value=0,max_value=1,format="%.0f%%")})
                st.caption("An unavailable or unmatched player is never treated as zero or a lost leg. Reached thresholds are provisional until official market settlement.")
        except Exception as exc:
            st.warning("NBA live data is temporarily unavailable. Your bets and settlement records are unaffected.")
            with st.expander("Connection details"):
                st.code(str(exc))
    render_live_nba_tracker()
    st.subheader("Quick bet overview")
    summary=[]
    for name,qty,price,legs in all_bets:
        matched=next((r for r in ROBINHOOD_NOV7_BETS if r[0]==name and r[1]==qty and r[2]==price),None)
        cost=matched[3] if matched else qty*price/100
        summary.append({"Combo":labels.get(name,name),"Legs":len(legs),"Wager":round(cost,2),"Potential profit":round(qty-cost,2),"Status":byid.get(name,{}).get("Status","Pending")})
    st.dataframe(pd.DataFrame(summary),hide_index=True,use_container_width=True,column_config={"Wager":st.column_config.NumberColumn("Wager",format="$%.2f"),"Potential profit":st.column_config.NumberColumn("Potential profit",format="$%.2f")})
    from collections import Counter
    exposure=Counter((p,m,t) for _,_,_,legs in all_bets for p,m,t in legs)
    st.subheader("Repeated player props")
    st.caption("Shows which individual outcomes affect multiple combos. Counts are appearances, not independent bets.")
    repeated=[{"Player":p,"Prop":str(t)+"+ "+m,"Combos depending on it":n} for (p,m,t),n in exposure.most_common() if n>1]
    if repeated:st.dataframe(pd.DataFrame(repeated),hide_index=True,use_container_width=True)
    else:st.caption("No repeated props.")
    with st.expander("View individual combo legs"):
        for name,qty,price,legs in all_bets:
            matched=next((r for r in ROBINHOOD_NOV7_BETS if r[0]==name and r[1]==qty and r[2]==price),None)
            cost=matched[3] if matched else qty*price/100
            status=byid.get(name,{}).get("Status","Pending")
            with st.expander(labels.get(name,name)+" · "+status):
                st.caption("Wager: $"+format(cost,",.2f")+" · Max payout: $"+format(qty,",.2f")+" · Potential profit: $"+format(qty-cost,",.2f"))
                st.dataframe(pd.DataFrame([{"Player":p,"Market":m,"Target":str(t)+"+","Actual":"Not verified","Leg status":"Pending"} for p,m,t in legs]),hide_index=True,use_container_width=True)
    st.caption("Overlapping legs are tracked separately within combos but financial totals count each combo once. Settlements are manual and never inferred from incomplete box scores.")

with st.sidebar:
    st.title("🏀 Huie's Degen Center")
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
    section=st.radio("Navigate",["Overview","Bankroll Performance","🔴 Bankroll Live Tracking"]+(["💸 My Bets"] if is_admin else [])+["Bankroll Builder","Model's Favorite Props","All Player Props","Three-Point Projections","Individual Games"],label_visibility="visible")
    phone_view=st.toggle("📱 Phone-friendly cards",value=False,key="phone_view",help="Switch wide data tables to easy-to-read vertical cards on a phone.")

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
    st.title("🏀 Huie's Degen Center")
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

    if phone_view:
        mobile_cards(df,preferred=["Safer line","Our play","Model projection","Reference line","Last 3 hit rate"],max_rows=250)
    else:
        responsive_dataframe(df,"models_"+str(name).replace(" ","_"),
                             preferred=["Safer line","Our play","Model projection","Reference line","Last 3 hit rate"],
                             max_rows=12 if not allow_filters else 250,
                             desktop_frame=df.style.apply(paint_row,axis=1),
                             hide_index=True,use_container_width=True,
                             height=min(680,max(230,39*(len(df)+1))),column_config=config)
    st.download_button("Download filtered CSV",df.to_csv(index=False).encode("utf-8"),file_name="nba_"+name.lower().replace(" ","_")+".csv",mime="text/csv",key="download_"+name)

if section=="Overview":
    st.title("Daily NBA Projections")
    st.caption("Model projections · Favorites · Safer lines · Recent player performance")
    a,b,c,d=st.columns(4)
    a.metric("Games",len(sheets[schedule]) if schedule else len(games))
    b.metric("Player props",len(sheets[allprops]) if allprops else "—")
    c.metric("Model's Favorite Props",len(sheets[favorites]) if favorites else "—")
    d.metric("Bankroll plays",len(sheets[bankroll]) if bankroll else "—")
    st.subheader("📈 Bankroll performance")
    performance_graph(bankroll_history_frame())
    if st.button("View daily bankroll results",key="open_bankroll_performance"):
        st.info("Choose Bankroll Performance in the sidebar to view daily results and date filters.")
    st.subheader("Today's games")
    if schedule:show_table(schedule,False)
    else:st.info("No game schedule sheet found.")
    if allprops:
        candidates=historical_summary(sheets[allprops])
        if "Recent hits" in candidates:
            candidates=candidates[(candidates["Recent hits"]==3)&(candidates["Games available"]==3)]
            st.subheader("🔥 3-for-3 recent performance")
            st.caption("Historical matches to model projections, not guarantees or betting recommendations.")
            if len(candidates):
                wanted=[lookup(candidates,c) for c in ("Player","Game","Market","Model side","Model projection","Last 3 avg")]
                wanted=[c for c in wanted if c]
                responsive_dataframe(candidates[wanted].head(12),"overview_three_hits",preferred=["Market","Model side","Model projection","Last 3 avg"],hide_index=True,use_container_width=True)
                st.caption(f"{len(candidates)} prop rows had 3 of 3 recent games on the model side.")
            else:st.info("No props with three available recent games and a 3/3 historical match.")
    st.subheader("Bankroll builder")
    if bankroll:show_table(bankroll,False)
    st.subheader("Model's Favorite Props")
    if favorites:show_table(favorites,False)
elif section=="Bankroll Performance":
    show_bankroll_performance()
elif section=="🔴 Bankroll Live Tracking":
    show_bankroll_live_tracker()
elif section=="💸 My Bets" and is_admin:
    show_personal_bets()
elif section=="Model Accuracy & ROI":
    show_model_accuracy()
elif section=="Live Prop Tracker":
    show_live_tracker()
elif section=="Individual Games":
    st.title("Individual Game Projections")
    if games:
        selected=st.selectbox("Choose matchup",games)
        show_table(selected)
    else:st.info("No individual game tabs found.")
elif section=="Bankroll Builder":
    st.title("Bankroll Builder")
    show_table(bankroll)
else:
    chosen={"Bankroll Builder":bankroll,"Model's Favorite Props":favorites,"All Player Props":allprops,"Three-Point Projections":threes}.get(section)
    st.title(section)
    show_table(chosen)
