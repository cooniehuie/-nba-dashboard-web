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
/* Compact live-tracking cards: scan the current stat and amount needed first. */
.bk-live-game{padding:9px 2px 3px;font-size:.87rem}
.bk-live-game small{font-size:.71rem;margin-top:1px}
.bk-live-card{padding:10px 12px;margin:5px 0 8px}
.bk-live-name{font-size:1.03rem}
.bk-live-status{font-size:.70rem;padding:3px 7px}
.bk-live-subtitle{font-size:.84rem;line-height:1.35;margin:5px 0 3px;opacity:.9}
.bk-live-subtitle b{font-weight:750}
.bk-live-model-short{opacity:.8}
.bk-live-focus{display:flex;justify-content:space-between;align-items:end;gap:8px;margin:4px 0}
.bk-live-current small{display:block;font-size:.67rem;font-weight:650;opacity:.7}
.bk-live-current strong{font-size:1.75rem;line-height:1.08;font-variant-numeric:tabular-nums}
.bk-live-needed{font-size:.86rem;font-weight:750;text-align:right;padding-bottom:3px}
.bk-live-card .bk-live-progress{margin:8px 0 0}
@media(max-width:768px){
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
.mobile-data-badge.status-hit{background:#dcfce7!important;border-color:#16a34a!important;color:#166534!important}
.mobile-data-badge.status-miss{background:#fee2e2!important;border-color:#dc2626!important;color:#991b1b!important}
.mobile-data-badge.status-unverified{background:#e5e7eb!important;border-color:#9ca3af!important;color:#374151!important}
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
.st-key-mobile_top_header,.st-key-mobile_bottom_nav,.st-key-mobile_overview,[class*="st-key-mobile_data_"]{display:none!important}
@media(max-width:768px){
 html,body{overflow-x:hidden!important}
 [data-testid="stAppViewContainer"]{overflow-x:hidden!important}
 [data-testid="stMainBlockContainer"],.block-container{padding:.65rem .7rem calc(7.2rem + env(safe-area-inset-bottom))!important;max-width:100%!important}
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
 [class*="st-key-desktop_data_"],.st-key-desktop_overview{display:none!important}
 .st-key-mobile_overview{display:block!important}
 .st-key-mobile_overview [data-testid="stExpander"]{
  border:1px solid #94a3b855!important;border-radius:13px!important;margin:0 0 10px!important;
  background:var(--secondary-background-color,#f8fafc)}
 .st-key-mobile_overview [data-testid="stExpander"] summary{min-height:53px!important;align-items:center!important}
 .st-key-mobile_overview [data-testid="stExpander"] summary p{font-size:1.02rem!important;font-weight:750!important;line-height:1.3!important}
 .st-key-mobile_overview [data-testid="stExpander"] [data-testid="stExpanderDetails"]{padding-top:3px!important}

 /* iPhone bottom nav: five equal-size buttons instead of mobile auto-stacked columns. */
 .st-key-mobile_bottom_nav{
  display:block!important;position:fixed!important;z-index:9999!important;
  inset:auto 0 0 0!important;width:100%!important;max-width:100vw!important;
  margin:0!important;box-sizing:border-box!important;
  background:var(--background-color,#fff);border-top:1px solid #94a3b855;
  box-shadow:0 -5px 20px #00000015;
  padding:8px max(8px,env(safe-area-inset-right)) calc(9px + env(safe-area-inset-bottom)) max(8px,env(safe-area-inset-left))!important}
 .st-key-mobile_bottom_nav [data-testid="stVerticalBlock"],
 .st-key-mobile_bottom_nav [data-testid="stElementContainer"]{
  width:100%!important;min-width:0!important;max-width:100%!important}
 .st-key-mobile_bottom_nav [data-testid="stHorizontalBlock"]{
  display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;
  width:100%!important;max-width:100%!important;min-width:0!important;
  gap:6px!important;flex-wrap:nowrap!important;align-items:stretch!important}
 .st-key-mobile_bottom_nav [data-testid="column"]{
  display:block!important;min-width:0!important;width:100%!important;max-width:100%!important;
  flex:none!important;margin:0!important;padding:0!important}
 .st-key-mobile_bottom_nav button{
  display:flex!important;align-items:center!important;justify-content:center!important;
  width:100%!important;max-width:100%!important;min-width:0!important;min-height:52px!important;
  padding:7px 2px!important;border-radius:11px!important;font-size:.76rem!important;
  font-weight:700!important;line-height:1.25!important;white-space:normal!important;
  overflow-wrap:anywhere!important;text-align:center!important}
 .st-key-mobile_bottom_nav button p{font-size:inherit!important;line-height:inherit!important;margin:0!important}
 /* Four tabs for viewers; five for admins (Bets). */
 .st-key-mobile_bottom_nav [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(5)){
  grid-template-columns:repeat(5,minmax(0,1fr))!important}
 /* Wrap full tab names onto two lines without ellipses. */
 .st-key-mobile_bottom_nav button,
 .st-key-mobile_bottom_nav button p,
 .st-key-mobile_bottom_nav button span{
  white-space:normal!important;overflow:visible!important;text-overflow:clip!important;
  word-break:normal!important;overflow-wrap:normal!important}
 .st-key-mobile_bottom_nav button p{width:100%!important;text-align:center!important}
 .st-key-mobile_bottom_nav [data-testid="stPopover"] button svg{display:none!important}
 .st-key-mobile_bottom_nav button{font-size:.79rem!important;letter-spacing:-.02em!important;padding-inline:1px!important}
 @media(max-width:360px){.st-key-mobile_bottom_nav button{font-size:.70rem!important;padding:6px 1px!important}}
 .bk-hero{padding:16px 14px!important;border-radius:15px!important}
 .bk-big{font-size:46px!important}.bk-grid{grid-template-columns:1fr!important;gap:12px!important}
 .bk-chart{overflow-x:auto;gap:5px!important}.bk-bar-wrap{min-width:30px!important}
 .bk-stat strong{font-size:21px!important}
}
</style>""",unsafe_allow_html=True)
# Public visitors can browse read-only model data. Admin login is optional.
# ADMIN_PASSWORD is stored only in Streamlit Secrets, never in source code.
admin_password=st.secrets.get("ADMIN_PASSWORD","")
if not admin_password:
    st.error("Administrator authentication is not configured. Add ADMIN_PASSWORD to Streamlit Secrets before enabling public access.")
    st.stop()
is_admin=bool(st.session_state.get("admin_authenticated",False))

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
    if data is not None and not st.session_state.get("admin_authenticated",False):
        raise PermissionError("Administrator login required to modify private storage.")
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
@st.cache_data(ttl=60,show_spinner=False)
def saved_bankroll_results():
    try:
        blob=github_file("bankroll_verified_results.json")
        return json.loads(blob.decode("utf-8")) if blob else {}
    except Exception:
        return {}

def save_daily_bankroll_snapshot(frame,game_date):
    """Keep the exact original picks; never replace an existing dated snapshot."""
    if not st.session_state.get("admin_authenticated"):
        return False
    if not lookup(frame,"Player") or not lookup(frame,"Safer line"):
        return False
    path="bankroll_picks_"+game_date+".json"
    if github_file(path):
        return False
    records=json.loads(frame.where(pd.notna(frame),None).to_json(orient="records"))
    github_file(path,json.dumps({"date":game_date,"picks":records}).encode("utf-8"))
    return True


def auto_archive_yesterday_bankroll():
    """On admin visit, grade yesterday's saved picks and archive only complete results."""
    if not st.session_state.get("admin_authenticated"):
        return None
    from datetime import timedelta
    from zoneinfo import ZoneInfo
    yesterday=(datetime.now(ZoneInfo("America/Los_Angeles")).date()-timedelta(days=1)).isoformat()
    saved=saved_bankroll_results()
    if yesterday in saved:
        return yesterday
    raw=github_file("bankroll_picks_"+yesterday+".json")
    if not raw:
        return None
    snapshot=json.loads(raw.decode("utf-8"))
    picks=pd.DataFrame(snapshot.get("picks",[]))
    if picks.empty:
        return None
    rows=grade_bankroll_sheet(picks,yesterday)
    if len(rows)!=len(picks) or any(row["Result"] not in ("Hit","Loss","DNP") for row in rows):
        return None
    # Re-read before writing to preserve other dates.
    saved=saved_bankroll_results()
    if yesterday not in saved:
        saved[yesterday]={"picks":rows,"saved_at":datetime.now(timezone.utc).isoformat(),"source":"automatic yesterday snapshot"}
        github_file("bankroll_verified_results.json",json.dumps(saved).encode("utf-8"))
        saved_bankroll_results.clear()
    return yesterday


def grade_bankroll_sheet(frame,game_date):
    """Grade only final games; never turn absent stats into a loss."""
    import re
    from zoneinfo import ZoneInfo
    playercol=lookup(frame,"Player")
    linecol=lookup(frame,"Safer line")
    gamecol=lookup(frame,"Game")
    marketcol=lookup(frame,"Market","Stat")
    if not playercol or not linecol:return []
    games,players=espn_nba_boxscores(game_date.replace("-",""))
    if not games:return []
    def normalize_team(code):
        aliases={"GS":"GSW","WSH":"WAS","NY":"NYK","SA":"SAS","NO":"NOP","UTAH":"UTA"}
        code=str(code).strip().upper()
        return aliases.get(code,code)
    def norm_team(value):
        return {normalize_team(code) for code in re.findall(r"[A-Z]{2,4}",str(value).upper())}
    team_pairs={}
    try:
        req=urllib.request.Request("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates="+game_date.replace("-",""),headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req,timeout=12) as response:
            for event in json.load(response).get("events",[]):
                comps=(event.get("competitions") or [{}])[0].get("competitors",[])
                team_pairs[str(event.get("id"))]={normalize_team(c.get("team",{}).get("abbreviation","")) for c in comps}
    except Exception:pass
    rows=[]
    for idx,pick in frame.iterrows():
        player_name=str(pick[playercol])
        line=str(pick[linecol])
        market=str(pick[marketcol]).strip().title() if marketcol else ""
        if market not in ("Points","Rebounds","Assists","Threes"):
            low=line.lower()
            market=next((m for key,m in [("assist","Assists"),("rebound","Rebounds"),("three","Threes"),("3pt","Threes"),("point","Points")] if key in low),"")
        target_match=re.search(r"\d+(?:\.\d+)?",line)
        target=float(target_match.group()) if target_match else None
        expected=norm_team(pick[gamecol]) if gamecol else set()
        # Resolve a player within the intended matchup, not across the entire slate.
        # ESPN and the workbook use different abbreviations for some teams.
        eligible=[p for p in players if not expected or team_pairs.get(str(p["game"]["id"])) in (None,expected)]
        candidate=match_espn_player(player_name,eligible)
        game=candidate["game"] if candidate else next((g for g in games if expected and team_pairs.get(str(g["id"]))==expected),None)
        actual=candidate["stats"].get(market) if candidate else None
        result="Pending"
        if game and game["state"]=="post":
            if candidate and candidate.get("dnp"):
                result="DNP"
                actual=None
            elif actual is None:
                # Missing boxscore stats may indicate DNP, injury, or a feed error.
                # Only explicit inactive/didNotPlay evidence should be excluded.
                result="Unverified"
            elif target is None:
                result="Unverified"
            elif ("under" in line.lower() and actual<target) or ("under" not in line.lower() and actual>=target):
                result="Hit"
            else:
                result="Loss"
        rows.append({"Player":player_name,"Game":str(pick[gamecol]) if gamecol else "",
                     "Market":market,"Safer line":line,"Actual":actual,
                     "Result":result,"Game status":game["detail"] if game else "Unavailable"})
    return rows

@st.cache_data(ttl=300,show_spinner=False)
def historical_safe_line_grades(date_key):
    """Use original dated selections, not the latest workbook, for past dates."""
    if date_key=="2026-11-05":
        picks=[(p,m,line) for p,m,line,_ in NOV5_PICKS]
    elif date_key=="2026-11-06":
        picks=list(NOV6_PICKS)
    else:
        return []
    games,players=espn_nba_boxscores(date_key.replace("-",""))
    if not games:return []
    rows=[]
    for p,m,line in picks:
        player=match_espn_player(p,players)
        actual=player["stats"].get(m) if player else None
        game=player["game"] if player else None
        if player and player.get("dnp") and game and game["state"]=="post":
            result="DNP"
            actual=None
        elif actual is None:
            result="Unverified"
        elif game["state"]=="post":
            result="Hit" if actual>=line else "Loss"
        else:
            result="Pending"
        rows.append({"Player":p,"Market":m,"Safer line":f"{line}+ {m.lower()}",
                     "Actual":actual if actual is not None else ("DNP" if result=="DNP" else "Unavailable"),
                     "Result":result,
                     "Game status":game["detail"] if game else "Unmatched"})
    return rows

def bankroll_verified_summary(rows):
    wins=sum(r["Result"]=="Hit" for r in rows)
    losses=sum(r["Result"]=="Loss" for r in rows)
    excluded=sum(r["Result"]=="DNP" for r in rows)
    return {"Wins":wins,"Losses":losses,"Excluded":excluded,
            "Graded":wins+losses,"Hit rate":100*wins/(wins+losses) if wins+losses else 0}

def bankroll_history_frame():
    frame=pd.DataFrame(BANKROLL_HISTORY)
    verified=saved_bankroll_results()
    for date,record in verified.items():
        summary=bankroll_verified_summary(record.get("picks",[]))
        replacement={"Date":date,"Wins":summary["Wins"],"Losses":summary["Losses"],
                     "Excluded":summary["Excluded"],"Status":"Box-score verified"}
        frame=frame[frame["Date"]!=date]
        frame=pd.concat([frame,pd.DataFrame([replacement])],ignore_index=True)
    frame=frame.sort_values("Date").reset_index(drop=True)
    frame["Graded"]=frame["Wins"]+frame["Losses"]
    frame["Hit rate"]=frame.apply(lambda r:100*r["Wins"]/r["Graded"] if r["Graded"] else 0,axis=1)
    return frame

def performance_graph(frame):
    # Display newest date first (leftmost), then older dates as you scroll right.
    frame=frame[frame["Graded"]>0].copy()
    frame=frame.assign(_sort_date=pd.to_datetime(frame["Date"],errors="coerce"))
    frame=frame.sort_values("_sort_date",ascending=False,kind="stable").drop(columns="_sort_date")
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
    /* Keep the daily bars inside the performance card on narrow phones.
       The graph scrolls horizontally rather than enlarging the entire card. */
    @media(max-width:750px){
      .bk-hero{
        width:100%;max-width:100%;min-width:0;box-sizing:border-box;
        padding:16px;overflow:hidden}
      .bk-grid{grid-template-columns:minmax(0,1fr);gap:12px;min-width:0;max-width:100%}
      .bk-grid>div{min-width:0;max-width:100%;overflow:hidden}
      .bk-track{max-width:100%}
      .bk-chart{
        display:flex;width:100%;max-width:100%;min-width:0;box-sizing:border-box;
        height:160px;gap:6px;overflow-x:auto;overflow-y:hidden;
        -webkit-overflow-scrolling:touch;overscroll-behavior-x:contain;
        padding-bottom:8px;scrollbar-width:thin}
      .bk-bar-wrap{flex:0 0 36px;min-width:36px;max-width:36px}
      .bk-bar-wrap span{font-size:9px}
    }
    </style>""",unsafe_allow_html=True)
    st.markdown(f"""<div class="bk-hero">
      <div class="bk-kicker">🏀 BANKROLL BUILDER · SAFE LINE HISTORY</div>
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
        if badge and badge!="—":
            status_text=html.unescape(badge).lower()
            status_class=("status-hit" if status_text in ("hit","🟢 hit") else
                          "status-miss" if status_text in ("loss","miss","🔴 miss") else
                          "status-unverified" if status_text in ("unverified","pending","dnp","⚪ unverified") else "")
            pieces.append('<span class="mobile-data-badge '+status_class+'">'+badge+'</span>')
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
    st.title("📈 Bankroll Builder Performance")
    from bankroll_parlay_tracker import render_bankroll_parlays
    render_bankroll_parlays(espn_nba_boxscores,match_espn_player,ROBINHOOD_CONFIRMED_BET_SETTLEMENTS)
    st.divider()
    if is_admin:
        try:
            archived=auto_archive_yesterday_bankroll()
            if archived:
                st.caption("Yesterday's saved Safe Line picks are checked automatically against final NBA results.")
        except Exception:
            st.caption("Automatic historical results check is temporarily unavailable.")
    st.caption("safe line picks · October 27–November 6, 2026 · Daily totals from prior ChatGPT tracker; not independently verified")
    st.subheader("Final box-score results")
    st.caption("The latest Bankroll Builder workbook is used as the pick list. Only completed games are graded; missing stats stay unverified.")
    from zoneinfo import ZoneInfo
    today=datetime.now(ZoneInfo("America/Los_Angeles")).date()
    grade_date=st.date_input("Results date",value=today,key="bankroll_grade_date",max_value=today)
    date_key=grade_date.isoformat()
    verified=saved_bankroll_results()
    if date_key in verified:
        st.success("Saved verified results available for "+date_key)
        auto_rows=verified[date_key].get("picks",[])
    elif bankroll:
        try:
            auto_rows=grade_bankroll_sheet(sheets[bankroll],date_key)
        except Exception as exc:
            auto_rows=[]
            st.warning("Could not retrieve final box scores for this date.")
    else:
        auto_rows=[]
    if auto_rows:
        auto_summary=bankroll_verified_summary(auto_rows)
        a,b,c,d=st.columns(4)
        a.metric("Final hits",auto_summary["Wins"])
        b.metric("Final misses",auto_summary["Losses"])
        c.metric("Unverified / pending",sum(r["Result"] in ("Unverified","Pending") for r in auto_rows))
        d.metric("Final hit rate",f'{auto_summary["Hit rate"]:.1f}%')
        responsive_dataframe(pd.DataFrame(auto_rows),"verified_bankroll_preview",
                             preferred=["Player","Game","Safer line","Actual","Result"],hide_index=True,use_container_width=True)
        if is_admin and date_key not in verified:
            if st.button("Save final results to history",key="save_verified_bankroll"):
                if any(r["Result"]=="Pending" for r in auto_rows):
                    st.warning("Some games are not final yet. Wait until all games finish before saving.")
                else:
                    verified[date_key]={"picks":auto_rows,"saved_at":datetime.now(timezone.utc).isoformat()}
                    github_file("bankroll_verified_results.json",json.dumps(verified).encode("utf-8"))
                    saved_bankroll_results.clear()
                    st.rerun()
    else:
        st.info("No graded picks are available for this date. Historical picks require their original dated workbook.")
    st.divider()
    history=bankroll_history_frame()
    dates=history["Date"].tolist()
    selected=st.multiselect("Filter by date",dates,default=dates,key="bankroll_history_dates")
    visible=history[history["Date"].isin(selected)]
    if visible.empty:
        st.info("Select at least one date to view performance.")
        return
    performance_graph(visible)
    st.subheader("Daily results")
    display=visible[["Date","Wins","Losses","Excluded","Graded","Hit rate"]].copy()
    display["Hit rate"]=display["Hit rate"].map(lambda x:f"{x:.1f}%")
    responsive_dataframe(display,"performance_daily",preferred=["Wins","Losses","Hit rate","Excluded"],hide_index=True,use_container_width=True)
    st.download_button("Download historical results CSV",display.to_csv(index=False),file_name="bankroll_builder_performance_history.csv",mime="text/csv")
    st.subheader("Player-by-player results")
    chosen_date=st.selectbox("Select a date to see individual safer-line results",dates,index=len(dates)-1,key="bankroll_drilldown_date",format_func=lambda d:pd.to_datetime(d).strftime("%b %d, %Y"))
    if chosen_date in verified:
        detail=pd.DataFrame(verified[chosen_date].get("picks",[]))
        st.caption("Saved final results for this date.")
    else:
        try:
            detail=pd.DataFrame(historical_safe_line_grades(chosen_date))
        except Exception:
            detail=pd.DataFrame()
            st.warning("NBA box scores are temporarily unavailable for this date.")
    if detail.empty:
        st.warning("The original player-by-player Safe Line selections are not saved for this date. Historical daily totals alone cannot identify which players hit or missed.")
        if is_admin:
            with st.expander("Admin · Add original picks for this date"):
                st.caption("Upload a CSV containing Player, Market and Safer line. The file must be the actual selections from the chosen date.")
                upload=st.file_uploader("Original dated Safe Line picks (CSV)",type=["csv"],key="historical_picks_"+chosen_date)
                if upload is not None:
                    try:
                        original=pd.read_csv(upload)
                        required={"Player","Market","Safer line"}
                        if not required.issubset(original.columns):
                            st.error("Required columns: Player, Market, Safer line")
                        else:
                            if st.button("Verify these dated picks",key="verify_historical_"+chosen_date):
                                st.session_state["historical_input_"+chosen_date]=original.to_dict("records")
                                st.rerun()
                    except Exception as exc:
                        st.error("Could not read the CSV: "+str(exc))
                custom=st.session_state.get("historical_input_"+chosen_date)
                if custom:
                    try:
                        original=pd.DataFrame(custom)
                        graded=grade_bankroll_sheet(original,chosen_date)
                        st.dataframe(pd.DataFrame(graded),hide_index=True,use_container_width=True)
                        if st.button("Save verified historical picks",key="save_historical_"+chosen_date):
                            if any(row["Result"]=="Pending" for row in graded):
                                st.warning("Some games are not final yet.")
                            else:
                                records=saved_bankroll_results()
                                records[chosen_date]={"picks":graded,"saved_at":datetime.now(timezone.utc).isoformat()}
                                github_file("bankroll_verified_results.json",json.dumps(records).encode("utf-8"))
                                saved_bankroll_results.clear()
                                st.rerun()
                    except Exception:
                        st.warning("Could not grade the uploaded picks against NBA box scores.")
    else:
        verified_count=int(detail["Result"].isin(["Hit","Loss"]).sum())
        hit_count=int((detail["Result"]=="Hit").sum())
        loss_count=int((detail["Result"]=="Loss").sum())
        dnp_count=int((detail["Result"]=="DNP").sum())
        st.caption(f"Box-score graded: {verified_count}/{len(detail)} picks · {hit_count} hits · {loss_count} misses · {dnp_count} DNPs. Unavailable player stats remain unverified unless ESPN explicitly marks the player as DNP.")
        tab_all,tab_hits,tab_losses,tab_unknown=st.tabs([
            f"All ({len(detail)})",f"✅ Hits ({hit_count})",f"❌ Misses ({loss_count})",
            f"DNP / Unverified ({len(detail)-verified_count})"])
        subsets=(detail,detail[detail["Result"]=="Hit"],detail[detail["Result"]=="Loss"],
                 detail[~detail["Result"].isin(["Hit","Loss"])])
        for idx,(tab,subset) in enumerate(zip((tab_all,tab_hits,tab_losses,tab_unknown),subsets)):
            with tab:
                if subset.empty:st.caption("No selections in this category.")
                else:responsive_dataframe(subset,"performance_detail_"+str(idx),preferred=["Safer line","Actual","Result"],hide_index=True,use_container_width=True)
        st.download_button("Download player results CSV",detail.to_csv(index=False),
                           file_name="bankroll_builder_players_"+chosen_date+".csv",mime="text/csv",key="player_detail_csv")
        if is_admin and chosen_date not in verified:
            if st.button("Save these final player results",key="save_player_detail_"+chosen_date):
                if any(x in ("Pending","Unverified") for x in detail["Result"]):
                    st.warning("Some selections are still pending or unverified. Resolve them before replacing the historical daily total.")
                else:
                    records=saved_bankroll_results()
                    records[chosen_date]={"picks":detail.to_dict("records"),"saved_at":datetime.now(timezone.utc).isoformat()}
                    github_file("bankroll_verified_results.json",json.dumps(records).encode("utf-8"))
                    saved_bankroll_results.clear()
                    st.rerun()
    st.caption("Only dates with original saved selections can be independently graded. Earlier chat-reported totals remain separate until verified.")


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
                        responsive_dataframe(candidate.head(10),"outcome_import_preview",hide_index=True)
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
        responsive_dataframe(group,"model_accuracy_by_market",preferred=["Total","Wins","Hit rate"],hide_index=True,use_container_width=True)
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
    responsive_dataframe(d,"model_accuracy_history",preferred=["Market","Model side","Reference line","Model projection"],hide_index=True,use_container_width=True)
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
    if not embedded:st.title("🔴 Bankroll Builder Live Tracking")
    else:st.subheader("🔴 Bankroll Builder Live Tracker")
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
        st.warning("The Bankroll Builder sheet needs Player and Safer line columns for tracking.")
        return
    # Snapshot today's selections on an admin visit, before a new daily upload replaces them.
    if is_admin and not embedded:
        try:
            save_daily_bankroll_snapshot(frame,datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat())
        except Exception:
            st.caption("Today's Safe Line snapshot could not be saved; historical archiving may need review.")
    prefix="embedded_bankroll" if embedded else "bankroll_live"
    chosen_day=st.session_state.get(prefix+"_date",datetime.now(ZoneInfo("America/Los_Angeles")).date())
    with st.expander("📅 "+chosen_day.strftime("%b %d, %Y")+" · Change date",expanded=False):
        game_date=st.date_input("Game date",value=chosen_day,key=prefix+"_date")
    @st.fragment(run_every="30s")
    def render_bankroll_live():
        try:
            games,players=espn_nba_boxscores(game_date.strftime("%Y%m%d"))
        except Exception as exc:
            st.warning("ESPN box scores unavailable. No picks have been graded or saved.")
            with st.expander("Connection details"):st.code(str(exc))
            return
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
        def normalize_team(code):
            aliases={"GS":"GSW","GSW":"GSW","WSH":"WAS","WAS":"WAS",
                     "NY":"NYK","NYK":"NYK","SA":"SAS","SAS":"SAS",
                     "NO":"NOP","NOP":"NOP","UTAH":"UTA","UTA":"UTA"}
            code=str(code).strip().upper()
            return aliases.get(code,code)
        def teams_from_matchup(value):
            # Normalize workbook abbreviations against ESPN's team codes.
            return {normalize_team(x) for x in re.findall(r"[A-Z]{2,4}",str(value).upper())}
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
                team_pairs[str(event.get("id"))]={normalize_team(c.get("team",{}).get("abbreviation","")) for c in competitors}
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
            # Match within the workbook matchup first: A. Thompson can refer
            # to Ausar (DET) or Amen (HOU), so global initials are ambiguous.
            eligible_players=[
                athlete for athlete in players
                if not expected_teams
                or team_pairs.get(str(athlete["game"]["id"])) in (None,expected_teams)
            ]
            candidate=match_espn_player(player_name,eligible_players,market)
            game=candidate["game"] if candidate else None
            actual=candidate["stats"].get(market) if candidate else None
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
            if actual is None and display_game and display_game["state"]=="pre":
                result="⚪ Awaiting tipoff"
            elif actual is None and candidate and candidate.get("dnp") and display_game and display_game["state"]=="post":
                result="⚪ DNP"
            elif actual is None and display_game and display_game["state"]=="in":
                result="⚪ Awaiting player stats"
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
        output=output.sort_values(["_tipoff","Game","Player"],kind="stable")
        # Keep the desktop summary above the table; on phones player progress comes first.
        with st.container(key=prefix+"_desktop_grid"):
            c1,c2,c3,c4=st.columns(4)
            c1.metric("Props",len(output))
            c2.metric("Reached / hit",sum(v for k,v in counts.items() if "Target reached" in k or k=="🟢 Hit"))
            c3.metric("Misses",int(counts.get("🔴 Miss",0)))
            c4.metric("Unverified",sum(v for k,v in counts.items() if "Unverified" in k))
            st.dataframe(output.drop(columns=["_tipoff"]),hide_index=True,use_container_width=True)
        with st.container(key=prefix+"_mobile_ui"):
            import html
            with st.expander("Filter players",expanded=False):
                choice=st.radio("Show",["Active","All","Live","Hit","Miss","Unverified"],
                                horizontal=True,key=prefix+"_mobile_filter",label_visibility="collapsed")
            def unverified_status(status):
                return "Unverified" in status or "Not started" in status
            def card_group(data):
                if data.empty:
                    st.caption("No matching props.")
                    return
                chunks=[]
                # Follow tipoff order and make the actual stat the focal point.
                for (start,matchup),group in data.groupby(["_tipoff","Game"],sort=False,dropna=False):
                    start_label=""
                    if start and start!="9999":
                        try:
                            start_label=datetime.fromisoformat(str(start).replace("Z","+00:00")).astimezone(
                                ZoneInfo("America/Los_Angeles")).strftime("%-I:%M %p")
                        except (ValueError,TypeError):
                            pass
                    game_label=str(matchup) if matchup and str(matchup)!="nan" else "Matchup unavailable"
                    game_status=str(group.iloc[0]["Game status"])
                    game_context=" · ".join(p for p in (start_label,game_status if game_status not in ("Unavailable","Scheduled") else "") if p)
                    chunks.append('<div class="bk-live-game">'+html.escape(game_label)+
                                  ('<small>'+html.escape(game_context)+'</small>' if game_context else "")+'</div>')
                    for _,r in group.iterrows():
                        state=str(r["Live status"])
                        kind=("hit" if "🟢" in state else "miss" if "🔴" in state
                              else "live" if "🟡" in state else "unverified")
                        actual=r["Actual"]
                        has_actual=pd.notna(actual)
                        actual_text=format(float(actual),"g") if has_actual else "—"
                        line=str(r["Safer line"])
                        match=re.search(r"\d+(?:\.\d+)?",line)
                        threshold=float(match.group()) if match else None
                        under="under" in line.lower()
                        pct=(min(100,max(0,float(actual)/threshold*100))
                             if has_actual and threshold and threshold>0 and not under else 0)
                        status_text=("Hit" if state=="🟢 Hit" else
                                     "Reached" if "Target reached" in state else
                                     "Miss" if "Miss" in state else
                                     "Live" if "progress" in state else
                                     "Pending")
                        market_code={"Points":"PTS","Rebounds":"REB","Assists":"AST","Threes":"3PM"}.get(str(r["Market"]),str(r["Market"]))
                        raw_model=str(r["Model line"]).strip()
                        model_info=('<span class="bk-live-model-short"> · Model <b>'+
                                    html.escape(raw_model)+'</b></span>'
                                    if raw_model and raw_model.lower() not in ("nan","none") else "")
                        if not has_actual:
                            needed_label="Awaiting stats"
                        elif under and threshold is not None:
                            needed_label="Below line" if float(actual)<threshold else "Above line"
                        elif threshold is None:
                            needed_label=""
                        elif float(actual)>=threshold:
                            needed_label="Reached"
                        elif "Miss" in state:
                            needed_label="Short "+format(threshold-float(actual),"g")
                        else:
                            needed_label="Need "+format(threshold-float(actual),"g")
                        bar=('<div class="bk-live-progress"><div class="bk-live-progress-fill" style="width:'+
                             f'{pct:.0f}%"></div></div>' if threshold and not under and has_actual else "")
                        chunks.append('<div class="bk-live-card '+kind+'">'+
                            '<div class="bk-live-head"><span class="bk-live-name">'+
                            html.escape(str(r["Player"]))+'</span><span class="bk-live-status">'+
                            html.escape(status_text)+'</span></div>'+
                            '<div class="bk-live-subtitle">'+html.escape(market_code)+' · <b>'+
                            html.escape(line)+'</b>'+model_info+'</div>'+
                            '<div class="bk-live-focus"><div class="bk-live-current"><small>NOW</small><strong>'+
                            html.escape(actual_text)+'</strong></div><div class="bk-live-needed">'+
                            html.escape(needed_label)+'</div></div>'+bar+'</div>')
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
        st.caption("Updated "+datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%-I:%M %p")+" · Auto-refresh 30s · Live results provisional")
        if st.button("↻ Refresh",key=prefix+"_refresh"):
            espn_nba_boxscores.clear()
            espn_nfl_boxscores.clear()
            st.rerun()
    render_bankroll_live()


def show_live_tracker():
    st.title("🔴 Live Prop Tracker")
    st.caption("ESPN box-score feed · manually refreshed · approximately 2-minute cache · not guaranteed real-time")
    from zoneinfo import ZoneInfo
    pacific=ZoneInfo("America/Los_Angeles")
    day=st.date_input("NBA game date (must match the workbook)",value=datetime.now(pacific).date(),key="live_date")
    st.warning("The currently uploaded workbook may be from another date. Select the matching game date; player-name matches alone do not verify a matchup.")
    choice=st.radio("Prop source",["Bankroll Builder safer lines","Model reference lines"],horizontal=True)
    sheet=bankroll if choice=="Bankroll Builder safer lines" else allprops
    if not sheet:
        st.info("The selected sheet is not available in the workbook.")
        return
    props=sheets[sheet].copy()
    playercol=lookup(props,"Player")
    marketcol=lookup(props,"Market")
    linecol=lookup(props,"Safer line") if choice=="Bankroll Builder safer lines" else lookup(props,"Reference line")
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
        if threshold is None and choice=="Bankroll Builder safer lines":
            import re
            match=re.search(r"\d+(?:\.\d+)?",str(row.get(linecol,"")))
            if match:threshold=float(match.group())
        if actual is None or threshold is None:return "Unverified"
        final=str(row.get("Game state","")).lower()=="post"
        if choice=="Bankroll Builder safer lines":
            if final:return "Hit" if actual>=threshold else "Miss"
            return "Target reached (in progress)" if actual>=threshold else "In progress"
        direction=str(row.get(sidecol,"")).strip().lower() if sidecol else ""
        if direction not in ["over","under"]:return "Unverified"
        if not final:return "In progress (not graded)"
        if actual==threshold:return "Push"
        return "Hit" if ((direction=="over" and actual>threshold) or (direction=="under" and actual<threshold)) else "Miss"
    joined["Live result"]=joined.apply(outcome,axis=1)
    cols=[playercol,marketcol,linecol,"Actual","Live result","Matchup","Game status"]
    if choice!="Bankroll Builder safer lines" and sidecol:cols.insert(3,sidecol)
    responsive_dataframe(joined[[c for c in cols if c in joined.columns]],"extra_live_tracker",preferred=["Market","Actual","Model projection","Reference line"],hide_index=True,use_container_width=True)
    st.caption("Missing players, ambiguous names, incomplete box scores and games still in progress are not counted as final losses. Results are not automatically saved to the historical model accuracy log.")


PERSONAL_BETS=[
("3-leg B",289,32.4,[("C. Johnson","Threes",1),("J. Murray","Threes",3),("A. Nembhard","Threes",2)]),
("3-leg A",1264,6.6,[("J. Murray","Threes",4),("A. Nembhard","Threes",3),("O. Toppin","Threes",2)]),
("7-leg B",1117,7.6,[("J. Murray","Threes",2),("A. Nembhard","Assists",6),("A. Nembhard","Points",15),("A. Nesmith","Points",10),("O. Toppin","Points",10),("J. Murray","Rebounds",4),("O. Toppin","Rebounds",4)]),
("7-leg A",483,39.4,[("J. Murray","Threes",2),("A. Nembhard","Threes",1),("A. Nembhard","Assists",4),("P. Siakam","Assists",2),("A. Nembhard","Points",10),("P. Siakam","Points",15),("P. Siakam","Rebounds",4)]),
("9-leg",1113,7.8,[("A. Nembhard","Assists",6),("C. Braun","Points",10),("J. Murray","Points",20),("N. Jokic","Points",20),("A. Nesmith","Points",10),("P. Siakam","Points",15),("A. Gordon","Rebounds",4),("J. Murray","Rebounds",4),("N. Jokic","Rebounds",8)])
]
ROBINHOOD_NOV7_BETS=[
("2-leg C",1247,6.7,99.92,16.37,[["J. Holiday","Threes",3],["T. Camara","Threes",4]]),
("2-leg B",351,26.5,99.95,6.94,[["J. Holiday","Threes",2],["T. Camara","Threes",3]]),
("3-leg J",273,34.6,99.92,5.46,[["D. Booker","Points",20],["S. Curry","Points",20],["V. Wembanyama","Points",25]]),
("4-leg L",1187,7.9,109.97,16.2,[["J. Smith Jr.","Threes",3],["S. Curry","Threes",3],["T. Silva","Threes",3],["T. Camara","Threes",3]]),
("3-leg I",362,25.6,99.75,7.08,[["F. VanVleet","Threes",2],["J. Smith Jr.","Threes",2],["R. Sheppard","Threes",2]]),
("4-leg K",523,17.4,100,9,[["B. Podziemski","Threes",2],["S. Curry","Threes",4],["A. Black","Threes",1],["T. Silva","Threes",3]]),
("4-leg J",221,43.2,99.9,4.43,[["S. Curry","Threes",3],["Y. Lendeborg","Threes",1],["A. Black","Threes",1],["T. Silva","Threes",2]]),
("2-leg A",229,41.5,99.62,4.59,[["S. Gilgeous-Alexander","Threes",2],["K. George","Threes",2]]),
("4-leg I",369,25.1,99.78,7.16,[["N. Alexander-Walker","Threes",3],["J. Smith Jr.","Threes",2],["T. Silva","Threes",2],["T. Camara","Threes",2]]),
("4-leg H",1216,6.9,99.98,16.08,[["N. Alexander-Walker","Threes",4],["J. Smith Jr.","Threes",2],["T. Silva","Threes",3],["T. Camara","Threes",3]]),
("5-leg B2",1201,7.0,99.99,15.92,[["D. Mitchell","Threes",3],["J. Harden","Threes",3],["J. Brunson","Threes",3],["D. Mitchell","Assists",4],["J. Harden","Assists",4]]),
("4-leg E",352,26.4,99.87,6.94,[["D. Mitchell","Threes",2],["E. Mobley","Threes",1],["J. Harden","Threes",2],["J. Brunson","Threes",2]]),
("4-leg D",309,30.3,99.81,6.18,[["N. Alexander-Walker","Threes",3],["C. McCollum","Assists",2],["D. Daniels","Assists",4],["O. Okongwu","Rebounds",6]]),
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

ROBINHOOD_NOV8_BETS=[
("Nov 8 · Parlay 68",1177,12.0,149.95,8.71,[["Tampa Bay","Game winner",1]],"2026-11-08","20:13"),
("Nov 8 · Parlay 67",1128,10.0,119.91,7.11,[["Tampa Bay","Game winner",1]],"2026-11-08","19:59"),
("Nov 8 · Parlay 66",408,47.5,199.91,6.11,[["D. Swift","Rush+Rec yds",-70],["D. Swift","Receptions",-2]],"2026-11-08","19:25"),
("Nov 8 · Parlay 65",419,22.6,99.83,5.14,[["C. Williams","Pass TDs",4],["C. Williams","Pass yds",300]],"2026-11-08","18:06"),
("Nov 8 · Parlay 64",255,37.2,99.96,5.1,[["D. Acuff Jr.","Assists",6],["P. Achiuwa","Points",10],["P. Achiuwa","Rebounds",6]],"2026-11-08","17:52"),
("Nov 8 · Parlay 63",1113,7.8,101.96,15.15,[["D. Acuff Jr.","Assists",10],["P. Achiuwa","Rebounds",10]],"2026-11-08","17:52"),
("Nov 8 · Parlay 62",1286,7.3,99.98,6.10,[["D. Swift","Rush yds",50],["E. Egbuka","Rec yds",40],["C. Loveland","Rec yds",40],["L. Burden III","Rec yds",40],["R. Odunze","Rec yds",40],["D. Swift","Rush+Rec yds",70],["C. Godwin Jr.","Rec yds",15]],"2026-11-08","16:28"),
("Nov 8 · Parlay 61",1219,7.7,99.94,6.08,[["E. Egbuka","Rec yds",40],["B. Irving","Rush yds",60],["D. Swift","Receptions",2],["C. Loveland","Receptions",4],["L. Burden III","Rec yds",40],["R. Odunze","Rec yds",25],["D. Swift","Rush yds",40]],"2026-11-08","16:23"),
("Nov 8 · Parlay 60",564,34.0,199.93,8.17,[["C. Williams","Pass TDs",2],["C. Williams","Pass yds",250]],"2026-11-08","16:08"),
("Nov 8 · Parlay 59",303,30.9,99.69,6.06,[["M. Porter Jr.","Threes",2],["K. Irving","Threes",2],["T. Herro","Threes",2],["K. Thompson","Threes",2],["D. Acuff Jr.","Threes",2]],"2026-11-08","16:03"),
("Nov 8 · Parlay 58",768,11.5,99.91,11.59,[["M. Porter Jr.","Threes",3],["T. Herro","Threes",3],["K. Thompson","Threes",3],["D. Acuff Jr.","Threes",3]],"2026-11-08","16:02"),
("Nov 8 · Parlay 57",333,28,99.9,6.66,[["P. Washington","Points",10],["J. Jaquez Jr.","Points",10],["K. Thompson","Points",10],["S. Bey","Points",10]],"2026-11-08","15:24"),
("Nov 8 · Parlay 56",2242,3.3,99.99,26,[["P. Washington","Points",15],["J. Jaquez Jr.","Points",15],["D. Mitchell","Points",15],["S. Bey","Points",15]],"2026-11-08","15:23"),
("Nov 8 · Parlay 55",348,26.7,99.81,6.89,[["K. Thompson","Points",10],["D. Acuff Jr.","Points",20],["D. Hunter","Points",10],["D. Sabonis","Points",10]],"2026-11-08","15:19"),
("Nov 8 · Parlay 54",326,28.6,99.76,6.52,[["D. Garland","Assists",6],["B. Lopez","Points",10],["S. Bey","Points",10],["Z. Williamson","Points",15]],"2026-11-08","15:18"),
("Nov 8 · Parlay 53",374,24.8,99.99,7.24,[["J. Tatum","Assists",6],["J. Jaquez Jr.","Points",10],["P. George","Rebounds",4],["K. Kuzma","Rebounds",4]],"2026-11-08","15:16"),
("Nov 8 · Parlay 52",410,22.5,99.93,7.68,[["M. Porter Jr.","Points",20],["P. Washington","Points",10],["D. Sharpe","Rebounds",6],["J. Randle","Rebounds",6]],"2026-11-08","15:13"),
("Nov 8 · Parlay 51",330,28.3,99.99,6.6,[["L. Markkanen","Threes",2],["D. Peterson","Assists",2],["A. Dosunmu","Points",15],["J. McDaniels","Points",15],["R. Gobert","Rebounds",10]],"2026-11-08","15:10"),
("Nov 8 · Parlay 50",340,28.0,99.97,4.77,[["W. Marks","Anytime TD",1]],"2026-11-08","14:37"),
("Nov 8 · Parlay 49",1252,7.5,99.99,6.09,[["C. Williams","Anytime TD",1],["C. Williams","Pass yds",275]],"2026-11-08","14:34"),
("Nov 8 · Parlay 48",427,22.2,99.96,5.17,[["B. Irving","Anytime TD",1],["C. Williams","Pass TDs",2],["C. Williams","Pass yds",200]],"2026-11-08","14:33"),
("Nov 8 · Parlay 47",1174,8,109.99,16.07,[["M. Porter Jr.","Threes",3],["T. Herro","Threes",3],["D. Robinson","Threes",3],["K. Thompson","Threes",3],["D. Acuff Jr.","Threes",3]],"2026-11-08","14:23"),
("Nov 8 · Parlay 46",1851,4.2,99.99,22.25,[["M. Porter Jr.","Threes",4],["J. Jaquez Jr.","Threes",1],["D. Robinson","Threes",5],["K. Thompson","Threes",2],["D. Acuff Jr.","Threes",3]],"2026-11-08","14:20"),
("Nov 8 · Parlay 45",1298,6.4,99.95,16.88,[["D. Jenkins","Assists",4],["D. Robinson","Points",15],["A. Reaves","Points",25],["A. Thompson","Rebounds",8]],"2026-11-08","14:04"),
("Nov 8 · Parlay 44",960,9.0,99.94,13.54,[["C. Cunningham","Threes",2],["D. Robinson","Threes",4],["A. Reaves","Threes",3],["J. LaRavia","Threes",1]],"2026-11-08","13:30"),
("Nov 8 · Parlay 43",468,20.2,99.82,5.28,[["C. McCaffrey","Rush yds",60],["T. McMillan","Rec yds",60],["J. Gibbs","Rec yds",20]],"2026-11-08","10:00"),
("Nov 8 · Parlay 42",1104,7.7,99.98,14.97,[["A. Simons","Threes",1],["J. Brown","Assists",4],["L. James","Assists",6],["J. Brown","Points",15],["T. Maxey","Rebounds",4],["V. Edgecombe","Rebounds",6]],"2026-11-08","09:46"),
("Nov 8 · Parlay 41",1393,5.9,99.99,17.8,[["A. Simons","Threes",2],["J. Brown","Threes",2],["T. Maxey","Threes",3],["V. Edgecombe","Threes",2]],"2026-11-08","09:41"),
("Nov 8 · Parlay 40",233,40.8,99.73,4.67,[["A. Simons","Threes",1],["J. Brown","Threes",1],["T. Maxey","Threes",2],["V. Edgecombe","Threes",1]],"2026-11-08","09:40"),
("Nov 8 · Parlay 39",528,17.2,99.86,9.04,[["D. Sharpe","Assists",4],["T. Herro","Assists",4],["D. Peterson","Assists",4]],"2026-11-08","09:31"),
("Nov 8 · Parlay 38",274,35,99.89,3.99,[["C. Douglas","Rec yds",25],["A. Williams","Rec yds",25],["D. Robinson","Rec yds",25]],"2026-11-08","09:25"),
("Nov 8 · Parlay 37",334,27.9,99.87,6.68,[["P. Pritchard","Points",10],["P. Larsson","Points",10],["M. Strus","Points",10]],"2026-11-08","09:22"),
("Nov 8 · Parlay 36",219,43.6,99.87,4.39,[["J. Randle","Assists",2],["N. Marshall","Assists",2],["D. Mitchell","Assists",4],["D. Acuff Jr.","Assists",4],["D. Sabonis","Assists",4],["J. Fears","Assists",2]],"2026-11-08","09:20"),
("Nov 8 · Parlay 35",257,36.8,99.72,5.14,[["P. Washington","Threes",1],["J. Jaquez Jr.","Threes",1],["D. Robinson","Threes",3]],"2026-11-08","09:17"),
("Nov 8 · Parlay 34",274,34.4,99.74,5.48,[["B. Portis","Rebounds",4],["P. Achiuwa","Rebounds",4],["J. Embiid","Rebounds",6],["R. Gobert","Rebounds",10]],"2026-11-08","09:16"),
("Nov 8 · Parlay 33",360,26.4,99.94,4.9,[["J. Gibbs","Anytime TD",1],["J. Williams","Anytime TD",1],["K. Williams","Anytime TD",1]],"2026-11-08","09:13"),
("Nov 8 · Parlay 32",316,30.2,99.92,4.49,[["G. Smith","Pass yds",175],["J. Goff","Pass yds",200],["J. McCarthy","Pass yds",175],["T. Shough","Pass yds",175]],"2026-11-08","08:45"),
("Nov 8 · Parlay 31",1489,6.3,99.96,6.15,[["K. Walker","Anytime TD",1],["J. Gibbs","Anytime TD",1],["C. Hubbard","Anytime TD",1],["P. Nacua","Anytime TD",1],["C. Lamb","Anytime TD",1]],"2026-11-08","07:07"),
("Nov 8 · Parlay 30",1252,7.5,99.99,6.09,[["M. Gesicki","Anytime TD",1],["I. Likely","Anytime TD",1]],"2026-11-08","07:04")
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
                    responsive_dataframe(pd.DataFrame(item["legs"],columns=["Player","Market","Target"]),"bulk_import_"+str(i),preferred=["Market","Target"],hide_index=True,use_container_width=True)
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
                        # Only mark DNP when ESPN explicitly reports non-participation.
                        # Missing/unmatched stats alone do not establish a DNP.
                        is_dnp=bool(athlete.get("didNotPlay") or athlete.get("inactive"))
                        reason=str(athlete.get("reason") or athlete.get("status") or "").lower()
                        if reason in ("dnp","did not play","inactive"):
                            is_dnp=True
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
                                        "game":game, "stats":({k:None for k in values} if is_dnp else values), "dnp":is_dnp,
                                        "jersey":str(athlete_info.get("jersey") or athlete.get("jersey") or "").strip()})
        except Exception:
            game["boxscore_error"]=True
    return games,players

@st.cache_data(ttl=30,show_spinner=False)
def espn_nfl_boxscores(date_string):
    """Read NFL rushing, receiving, passing and TD statistics without guessing missing values."""
    from datetime import datetime as dt
    from zoneinfo import ZoneInfo
    def fetch(url):
        req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
        with urllib.request.urlopen(req,timeout=12) as response:return json.load(response)
    scoreboard=fetch("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates="+date_string)
    games=[]
    players=[]
    for event in scoreboard.get("events",[]):
        status=event.get("status",{}).get("type",{})
        game={"name":event.get("shortName",event.get("name","NFL")),"start_utc":event.get("date",""),
              "state":status.get("state","unknown"),"detail":status.get("shortDetail",status.get("detail",""))}
        games.append(game)
        # Preserve a live-game association for known bet players even before
        # ESPN includes them in a statistical box-score category. Never infer
        # participation or a zero from these placeholders.
        competitors=event.get("competitions",[{}])[0].get("competitors",[])
        team_codes={str(c.get("team",{}).get("abbreviation","")).upper() for c in competitors}
        if "TB" in team_codes or "TAM" in team_codes:
            for full_name in ("Emeka Egbuka","Bucky Irving","Chris Godwin Jr."):
                players.append({"name":full_name,"game":game,"stats":{},
                                "jersey":"","sport":"NFL","game_only":True})
        try:
            summary=fetch("https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event="+str(event["id"]))
            for team in summary.get("boxscore",{}).get("players",[]):
                for category in team.get("statistics",[]):
                    kind=str(category.get("name","")).lower()
                    labels=[str(v).upper() for v in category.get("labels",[])]
                    for athlete in category.get("athletes",[]):
                        info=athlete.get("athlete",{})
                        name=info.get("displayName",info.get("fullName",""))
                        if not name:continue
                        stats=athlete.get("stats",[])
                        def numeric(keys):
                            for key in keys:
                                if key in labels:
                                    idx=labels.index(key)
                                    if idx<len(stats):
                                        try:return float(str(stats[idx]).replace(",",""))
                                        except (ValueError,TypeError):pass
                            return None
                        values={}
                        if kind=="passing":
                            values["Pass yds"]=numeric(["YDS","PASS YDS"])
                            values["Pass TDs"]=numeric(["TD","TDS","PASS TD"])
                        elif kind=="rushing":
                            values["Rush yds"]=numeric(["YDS","RUSH YDS"])
                        elif kind=="receiving":
                            values["Rec yds"]=numeric(["YDS","REC YDS"])
                            values["Receptions"]=numeric(["REC","RECEPTIONS"])
                        # Total touchdowns from rushing and receiving; do not double-count player rows.
                        if kind in ("rushing","receiving"):
                            values["_td_"+kind]=numeric(["TD","TDS"])
                        def athlete_key(value):
                            return " ".join(str(value).lower().replace(".","").split()).removesuffix(" jr")
                        existing=next((p for p in players if p["game"] is game
                                       and athlete_key(p["name"])==athlete_key(name)),None)
                        if existing is None:
                            existing={"name":name,"game":game,"stats":{},"jersey":str(info.get("jersey") or ""),"sport":"NFL"}
                            players.append(existing)
                        existing["name"]=name
                        existing["jersey"]=str(info.get("jersey") or existing.get("jersey",""))
                        existing["game_only"]=False
                        existing["stats"].update({k:v for k,v in values.items() if v is not None})
            for p in players:
                if p["game"] is game:
                    tds=[p["stats"].get("_td_rushing"),p["stats"].get("_td_receiving")]
                    if any(v is not None for v in tds):
                        p["stats"]["Anytime TD"]=sum(v or 0 for v in tds)
                    rush=p["stats"].get("Rush yds")
                    rec=p["stats"].get("Rec yds")
                    if rush is not None or rec is not None:
                        p["stats"]["Rush+Rec yds"]=(rush or 0)+(rec or 0)
        except Exception:
            game["boxscore_error"]=True
    return games,players

def match_espn_player(short_name,players,market=None):
    """Match Robinhood initials to ESPN athletes without confusing same-surname players."""
    import re
    import unicodedata
    def norm(value):
        value=unicodedata.normalize("NFKD",str(value).lower())
        # Apostrophes inside first names are not word separators: D\u2019Andre -> dandre.
        value=value.replace("\u2019","").replace("\u0027","").replace("\u02bc","")
        # ESPN may use P.J. / J.J. as a single first name. Preserve those initials
        # as PJ / JJ rather than treating J as part of the surname.
        value=re.sub(r"\b([a-z])\.\s*([a-z])\.",r"\1\2",value)
        return " ".join("".join(ch if ch.isalnum() else " " for ch in value).split())
    parts=norm(short_name).split()
    if market:
        sport="NFL" if market in ("Pass yds","Pass TDs","Rush yds","Rec yds","Rush+Rec yds","Anytime TD","Receptions") else "NBA"
        players=[p for p in players if p.get("sport","NBA")==sport]
    if len(parts)<2:return None
    # Robinhood's Nov 9 A. Thompson rebound leg refers to Ausar Thompson.
    # Avoid confusing him with Amen Thompson when both share the initial.
    # Apply only to NBA rebounds, not other markets or NFL players.
    if parts==["a","thompson"] and market=="Rebounds":
        ausar=[p for p in players if norm(p.get("name","")).split()[:2]==["ausar","thompson"]]
        if len(ausar)==1:return ausar[0]
    particles={"da","de","del","van","von","di","dos","du","la","le"}
    suffixes={"jr","sr","ii","iii","iv"}
    aliases={"j holiday":{"jrue"},"c johnson":{"cameron","cam"},
             "m porter jr":{"michael"},"t silva":{"tristan"}}
    first=parts[0]
    surname=parts[1:]
    # Robinhood P. Washington refers to ESPN's PJ Washington (Jr.).
    if market not in ("Pass yds","Pass TDs","Rush yds","Rec yds","Rush+Rec yds","Anytime TD","Receptions") and parts==["p","washington"]:
        candidates=[]
        for athlete in players:
            full=norm(athlete.get("name","")).split()
            if len(full)>1 and full[0]=="pj" and full[1]=="washington" and (len(full)==2 or full[2:]==["jr"]):
                candidates.append(athlete)
        if len(candidates)==1:
            return candidates[0]
    def strip_particles(seq):
        return [x for x in seq if x not in particles]
    def surname_matches(full):
        actual=full[1:]
        # Compare full surnames first; also permit omitted surname particles
        # and a missing Jr./III in Robinhood, never mismatched suffixes.
        if actual==surname or strip_particles(actual)==surname:
            return True
        if surname and surname[-1] not in suffixes and actual and actual[-1] in suffixes:
            return actual[:-1]==surname or strip_particles(actual[:-1])==surname
        return False
    matches=[]
    for player in players:
        full=norm(player.get("name","")).split()
        if len(full)>1 and full[0].startswith(first) and surname_matches(full):
            matches.append(player)
    # Known NFL initials must be checked before accepting a unique but wrong
    # surname match (e.g. Jameson Williams instead of Javonte Williams).
    if market in ("Pass yds","Pass TDs","Rush yds","Rec yds","Rush+Rec yds","Anytime TD","Receptions"):
        nfl_first={"g smith":{"geno"},"j williams":{"javonte"},"k williams":{"kyren"},
                   "j mccarthy":{"jj","jonathan"},
                   "d robinson":{"demarcus","demarcus"}}
        preferred_first=nfl_first.get(" ".join(parts))
        if preferred_first:
            exact=[p for p in matches if norm(p.get("name","")).split()[0] in preferred_first]
            if len(exact)==1:return exact[0]
            # ESPN may spell JJ McCarthy without spaces, so also inspect
            # known aliases when the initial J does not match ESPN's JJ token.
            candidates=[p for p in players if norm(p.get("name","")).split()[-1:]==surname
                        and norm(p.get("name","")).split()[0] in preferred_first]
            if len(candidates)==1:return candidates[0]
            return None
    if len(matches)==1:return matches[0]
    # NFL player-specific disambiguation: Kyren Williams versus other K. Williams.
    # Keep J. Williams unresolved if multiple players share the abbreviation.
    if market in ("Pass yds","Pass TDs","Rush yds","Rec yds","Rush+Rec yds","Anytime TD","Receptions"):
        nfl_aliases={
            "g smith":{"geno"},
            "k williams":{"kyren"},
            "j williams":{"javonte"},
            "j mccarthy":{"jj","jonathan"}
        }
        nfl_preferred=nfl_aliases.get(" ".join(parts))
        if nfl_preferred:
            exact=[p for p in matches if norm(p.get("name","")).split()[0] in nfl_preferred]
            if len(exact)==1:return exact[0]
    preferred=aliases.get(" ".join(parts))
    if preferred and matches:
        exact=[p for p in matches if norm(p.get("name","")).split()[0] in preferred]
        if len(exact)==1:return exact[0]
    # Do not pick an arbitrary athlete when multiple players match.
    return None

def automatic_parlay_result(legs,players):
    """Infer live results for cumulative Yes NBA prop legs."""
    all_reached=bool(legs)
    missed_final=False
    for name,market,target in legs:
        player=match_espn_player(name,players,market)
        actual=player["stats"].get(market) if player else None
        if actual is None:
            all_reached=False
        elif int(target)<0:
            if actual>=abs(int(target)):
                missed_final=True
                all_reached=False
            elif player["game"]["state"]!="post":
                all_reached=False
        elif actual<int(target):
            all_reached=False
            if player["game"]["state"]=="post":
                missed_final=True
    return "Loss" if missed_final else ("Won" if all_reached else "Pending")


ROBINHOOD_NOV9_BETS=[
("Nov 9 · Parlay 26",100,99.0,99.07,0.07,[["New York I","Game winner",1]],"2026-11-09","21:51"),
("Nov 9 · Parlay 25",1252,7.43,99.06,6.03,[["J. Fears","Points",20],["S. Curry","Points",30],["D. Queen","Rebounds",8],["D. Green","Assists",4]],"2026-11-09","18:40"),
("Nov 9 · Parlay 24",352,27,99.9,4.86,[["F. VanVleet","Points",10],["F. VanVleet","Assists",4],["T. Eason","Rebounds",4],["J. Murray","Threes",2]],"2026-11-09","17:37"),
("Nov 9 · Parlay 23",1769,5.3,99.97,6.21,[["J. Champagnie","Threes",3],["F. VanVleet","Threes",3],["J. Murray","Threes",3],["J. Smith Jr.","Threes",3]],"2026-11-09","17:35"),
("Nov 9 · Parlay 22",597,15.8,99.89,5.56,[["F. VanVleet","Threes",2],["J. Murray","Threes",2],["J. Smith Jr.","Threes",2],["J. Champagnie","Threes",2],["T. Murphy III","Threes",2],["Y. Lendeborg","Threes",2]],"2026-11-09","17:34"),
("Nov 9 · Parlay 21",522,18.1,99.9,5.42,[["S. Curry","Threes",4],["T. Murphy III","Threes",3],["Y. Lendeborg","Threes",2],["S. Bey","Threes",1]],"2026-11-09","17:32"),
("Nov 9 · Parlay 20",429,22.1,99.99,5.18,[["J. Smith Jr.","Threes",2],["F. VanVleet","Threes",2],["N. Jokic","Assists",8],["A. Sengun","Assists",6]],"2026-11-09","17:10"),
("Nov 9 · Parlay 19",1341,7,99.99,6.12,[["O. Beckham Jr.","Anytime TD",1]],"2026-11-09","17:08"),
("Nov 9 · Parlay 18",368,25.8,99.88,4.94,[["J. Allen","Anytime TD",1],["J. Cook III","Anytime TD",1]],"2026-11-09","17:07"),
("Nov 9 · Parlay 17",1189,7.9,99.99,6.06,[["J. Allen","Anytime TD",1],["J. Cook III","Rush yds",60],["T. Hockenson","Receptions",3],["BUF","Game winner",1],["D. Moore","Rec yds",30],["K. Shakir","Rec yds",30],["J. Jefferson","Rec yds",60],["K. Shakir","Receptions",2],["D. Moore","Receptions",2]],"2026-11-09","16:50"),
("Nov 9 · Parlay 16",1341,7,99.99,6.12,[["C. Wentz","Interceptions",3]],"2026-11-09","15:34"),
("Nov 9 · Parlay 15",402,23.6,99.95,5.08,[["D. Queen","Points",10],["S. Bey","Points",15],["Y. Lendeborg","Points",15],["Z. Williamson","Rebounds",4],["D. Green","Assists",6]],"2026-11-09","15:30"),
("Nov 9 · Parlay 14",231,41.8,99.99,3.43,[["D. Vassell","Points",10],["O. Ighodaro","Rebounds",4],["K. Maluach","Rebounds",4],["S. Castle","Rebounds",4]],"2026-11-09","15:22"),
("Nov 9 · Parlay 13",340,28,99.97,4.77,[["O. Toppin","Points",10],["A. Nembhard","Assists",6],["I. Zubac","Rebounds",8]],"2026-11-09","15:19"),
("Nov 9 · Parlay 12",361,26.21,99.53,4.9,[["C. Coward","Points",10],["J. Wells","Points",10],["C. Boozer","Rebounds",8]],"2026-11-09","15:17"),
("Nov 9 · Parlay 11",425,22.3,99.94,5.17,[["D. Jenkins","Points",10],["A. Thompson","Assists",4],["P. Reed","Points",10]],"2026-11-09","13:07"),
("Nov 9 · Parlay 10",417,22.4,98.49,5.08,[["G. Allen","Threes",3],["N. Alexander-Walker","Threes",3],["D. Robinson","Threes",3],["S. Curry","Threes",3]],"2026-11-09","12:39"),
("Nov 9 · Parlay 9",1219,7.7,99.94,6.08,[["G. Allen","Threes",4],["D. Mitchell","Threes",3],["E. Mobley","Threes",2]],"2026-11-09","12:37"),
("Nov 9 · Parlay 8",1380,6.8,99.97,6.13,[["A. Reaves","Threes",2],["A. Wiggins","Threes",2],["C. McCollum","Threes",2],["N. Alexander-Walker","Threes",3],["L. Doncic","Threes",4],["Z. Williams","Threes",1]],"2026-11-09","12:33"),
("Nov 9 · Parlay 7",377,25.2,99.99,4.99,[["L. Doncic","Threes",4],["N. Alexander-Walker","Threes",3],["A. Wiggins","Threes",2],["A. Reaves","Threes",1]],"2026-11-09","12:31"),
("Nov 9 · Parlay 6",2285,4.1,99.98,6.3,[["L. Doncic","Threes",5],["N. Alexander-Walker","Threes",4],["A. Wiggins","Threes",3],["A. Reaves","Threes",2],["Z. Williams","Threes",1]],"2026-11-09","12:29"),
("Nov 9 · Parlay 5",4679,2,100,6.42,[["L. Doncic","Threes",6],["N. Alexander-Walker","Threes",5],["A. Wiggins","Threes",3],["C. McCollum","Threes",1],["Z. Williams","Threes",1]],"2026-11-09","12:26"),
("Nov 9 · Parlay 4",355,26.2,100,6.99,[["F. VanVleet","Assists",4],["A. Nembhard","Assists",4],["C. McCollum","Assists",2],["D. Green","Assists",4],["D. Queen","Assists",2],["J. Fears","Assists",2]],"2026-11-09","09:46"),
("Nov 9 · Parlay 3",223,42.7,99.69,4.47,[["D. Queen","Rebounds",4],["K. Maluach","Rebounds",4],["A. Thompson","Rebounds",6]],"2026-11-09","09:39"),
("Nov 9 · Parlay 2",217,43.9,99.61,4.35,[["J. Harden","Threes",1],["A. Wiggins","Threes",1],["Z. Williams","Threes",1],["D. Jenkins","Threes",1]],"2026-11-09","09:37"),
("Nov 9 · Parlay 1",343,27.1,99.78,6.83,[["E. Mobley","Threes",1],["J. Harden","Threes",2],["A. Wiggins","Threes",2],["N. Alexander-Walker","Threes",2]],"2026-11-09","09:36"),
]

ROBINHOOD_NOV10_BETS=[
("Nov 10 · Parlay 25",1219,7.66,99.41,6.04,[["R. Williams III","Rebounds",6],["I. Hartenstein","Rebounds",10],["S. Gilgeous-Alexander","Points",35],["D. Avdija","Assists",6],["D. Clingan","Rebounds",6]],"2026-11-10","19:46"),
("Nov 10 · Parlay 24",1489,6.27,99.44,6.13,[["S. Gilgeous-Alexander","Threes",3],["J. Holiday","Threes",2],["T. Camara","Threes",2],["D. Acuff Jr.","Threes",2],["D. Bane","Threes",3],["K. Wagler","Threes",1]],"2026-11-10","17:39"),
("Nov 10 · Parlay 23",1304,7.12,98.88,6.05,[["K. Wagler","Threes",2],["R. Hachimura","Threes",2],["D. Booker","Threes",2],["D. Brooks","Threes",2]],"2026-11-10","17:34"),
("Nov 10 · Parlay 22",1252,7.47,99.59,6.06,[["D. Lillard","Threes",3],["T. Camara","Threes",3],["D. Acuff Jr.","Threes",3],["D. Bane","Threes",4]],"2026-11-10","17:30"),
("Nov 10 · Parlay 21",229,38.24,90.92,3.36,[["D. Acuff Jr.","Threes",2],["T. Silva","Threes",2],["D. Bane","Threes",2],["D. Lillard","Threes",2],["T. Camara","Threes",2]],"2026-11-10","17:27"),
("Nov 10 · Parlay 20",833,10.82,95.71,5.61,[["T. Silva","Threes",3],["D. Bane","Threes",3],["T. Camara","Threes",3],["D. Lillard","Threes",3],["D. Acuff Jr.","Threes",3]],"2026-11-10","17:26"),
("Nov 10 · Parlay 19",1471,19.3,299.95,16.05,[["D. Brooks","Threes",2],["R. Hachimura","Threes",2],["Miles Bridges","Rebounds",6],["Davion Mitchell","Assists",6]],"2026-11-10","17:17"),
("Nov 10 · Parlay 18",317,29.75,98.80,4.50,[["K. Dunn","Threes",1],["S. Gilgeous-Alexander","Threes",2],["Jalen Green","Assists",2]],"2026-11-10","17:13"),
("Nov 10 · Parlay 17",1235,7.6,99.93,6.07,[["J. Brown","Threes",2],["T. Maxey","Threes",3],["P. George","Threes",3],["S. Hauser","Threes",2]],"2026-11-10","17:07"),
("Nov 10 · Parlay 16",270,35.5,99.79,3.94,[["T. Silva","Points",10],["W. Carter Jr.","Points",10],["A. Caruso","Assists",2]],"2026-11-10","16:38"),
("Nov 10 · Parlay 15",414,22.9,99.93,5.12,[["J. Richardson","Assists",2],["Jalen Green","Assists",2],["K. Thompson","Assists",2],["W. Carter Jr.","Rebounds",8]],"2026-11-10","16:34"),
("Nov 10 · Parlay 14",1000,9.4,99.96,5.96,[["A. Caruso","Assists",2],["K. Wagler","Points",10],["A. Black","Points",15],["A. Bailey","Rebounds",6]],"2026-11-10","16:17"),
("Nov 10 · Parlay 13",848,11.1,99.99,5.86,[["T. Camara","Threes",4],["D. Lillard","Threes",3],["S. Gilgeous-Alexander","Threes",2],["J. Holiday","Threes",1]],"2026-11-10","15:35"),
("Nov 10 · Parlay 12",303,32.02,101.36,4.35,[["T. Maxey","Threes",2],["J. Brown","Threes",2],["P. George","Threes",2]],"2026-11-10","15:34"),
("Nov 10 · Parlay 11",217,42,94.36,3.22,[["J. Brunson","Threes",2],["L. Shamet","Threes",2],["T. Herro","Threes",2]],"2026-11-10","15:31"),
("Nov 10 · Parlay 10",569,16.6,99.97,5.52,[["L. Markkanen","Threes",4],["D. Peterson","Threes",3],["Davion Mitchell","Threes",2],["A. Bailey","Threes",1]],"2026-11-10","15:25"),
("Nov 10 · Parlay 9",2402,3.87,99.19,6.26,[["D. Bane","Threes",5],["T. Silva","Threes",4],["D. Acuff Jr.","Threes",3]],"2026-11-10","14:52"),
("Nov 10 · Parlay 8",1563,5.97,99.43,6.15,[["D. Bane","Threes",4],["D. Acuff Jr.","Threes",3],["T. Silva","Threes",3],["A. Black","Threes",2]],"2026-11-10","14:51"),
("Nov 10 · Parlay 7",1304,7.2,99.99,6.1,[["K. Kuzma","Points",10],["B. Stirtz","Points",10],["K. Murray","Points",10]],"2026-11-10","14:41"),
("Nov 10 · Parlay 6",1705,5.5,99.99,6.22,[["Davion Mitchell","Threes",3],["D. Peterson","Threes",3],["R. Hachimura","Threes",3]],"2026-11-10","14:40"),
("Nov 10 · Parlay 5",377,25.2,99.99,4.99,[["R. Hachimura","Threes",2],["Davion Mitchell","Threes",2],["D. Peterson","Threes",2]],"2026-11-10","14:40"),
("Nov 10 · Parlay 4",421,24.8,109.91,5.50,[["K. Wagler","Threes",1],["S. Gilgeous-Alexander","Threes",2],["W. Carter Jr.","Threes",1]],"2026-11-10","09:20"),
("Nov 10 · Parlay 3",286,33.26,99.26,4.13,[["K. Wagler","Assists",2],["C. Gillespie","Assists",2],["F. Wagner","Assists",6],["D. Acuff Jr.","Assists",6]],"2026-11-10","09:10"),
("Nov 10 · Parlay 2",246,39.1,99.82,3.63,[["A. Simons","Threes",1],["D. Jones Jr.","Threes",1],["L. Markkanen","Threes",2],["D. Bane","Threes",2]],"2026-11-10","09:04"),
("Nov 10 · Parlay 1",346,27.5,99.98,4.83,[["A. Drummond","Rebounds",4],["W. Carter Jr.","Rebounds",8],["A. Black","Rebounds",4],["I. Hartenstein","Rebounds",8]],"2026-11-10","09:02"),

]

ROBINHOOD_CONFIRMED_BET_SETTLEMENTS={
    "Nov 9 · Parlay 26":{"date":"2026-11-09","time":"22:03","settlement_date":"2026-11-09","status":"Loss",
        "settlement_price":0.0,"quantity":100,"payout":0.0,
        "realized_profit":-99.00,"event_id":"7153e8e6-9337-4cf1-92bd-d863bc44c7a9",
        "note":"Robinhood-confirmed realized loss excludes $0.07 original commission; purchase total cost $99.07 preserved."},
    "Nov 9 · Parlay 14":{"date":"2026-11-09","time":"10:11","settlement_date":"2026-11-10","status":"Won",
        "settlement_price":0.776,"quantity":231,"payout":179.26,
        "realized_profit":82.70,"event_id":"ef52725a-5bf2-4b30-a13e-f98f9328eeea",
        "note":"Robinhood-confirmed Nov 10 payout for Nov 9 purchase; original entry cost preserved."},
    "Nov 9 · Parlay 22":{"date":"2026-11-09","time":"10:11","settlement_date":"2026-11-10","status":"Won",
        "settlement_price":0.811,"quantity":597,"payout":484.17,
        "realized_profit":389.84,"event_id":"5dc177b6-d1c0-4908-9fcf-b689f37d0b86",
        "note":"Robinhood-confirmed Nov 10 payout for Nov 9 purchase; original entry cost preserved."},
    "Nov 9 · Parlay 21":{"date":"2026-11-09","time":"21:47","status":"Won",
        "settlement_price":0.47,"quantity":522,"payout":245.34,
        "realized_profit":150.86,"event_id":"a71f31da-6b1f-4683-a514-e8ce6a1dee41",
        "note":"Robinhood-confirmed partial-price payout; realized profit as reported, original purchase cost preserved."},
    # User-reported Nov 9 losses; settlement details not yet supplied.
    "Nov 9 · Parlay 16":{"date":"2026-11-09","status":"Loss",
        "realized_profit":-99.99,"note":"User reported C. Wentz interceptions 3+ contract lost; estimated entry-cost loss pending settlement."},
    "Nov 9 · Parlay 19":{"date":"2026-11-09","status":"Loss",
        "realized_profit":-99.99,"note":"User reported O. Beckham Jr. anytime TD contract lost; estimated entry-cost loss pending settlement."},
    # Game-result losses reported by user; Robinhood contract settlement not yet supplied.
    "Nov 8 · Parlay 68":{"date":"2026-11-08","status":"Loss",
        "realized_profit":-149.95,"note":"Tampa Bay lost; estimated full entry-cost loss pending Robinhood settlement."},
    "Nov 8 · Parlay 67":{"date":"2026-11-08","status":"Loss",
        "realized_profit":-119.91,"note":"Tampa Bay lost; estimated full entry-cost loss pending Robinhood settlement."},
    "Nov 8 · Parlay 55":{"date":"2026-11-08","time":"20:57","status":"Won",
        "settlement_price":0.80,"quantity":348,"payout":278.40,
        "realized_profit":185.48,"event_id":"8fd533eb-6ceb-4384-be6a-49cb393b9bf5",
        "note":"Robinhood-confirmed settlement; realized profit overrides inferred ESPN leg outcomes."},
    "Nov 8 · Parlay 36":{"date":"2026-11-08","time":"20:58","status":"Won",
        "settlement_price":0.83,"quantity":219,"payout":181.77,
        "realized_profit":86.29,"event_id":"9d9614a4-83dd-49ef-ac99-615b0c952015",
        "note":"Robinhood-confirmed settlement; recorded profit takes precedence over individual ESPN leg statuses."},
    "Nov 8 · Parlay 51":{"date":"2026-11-08","time":"19:06","status":"Won",
        "settlement_price":0.82,"quantity":330,"payout":270.60,
        "realized_profit":177.21,"event_id":"0d3d62e9-41fb-49d4-bffc-dcb9b36ae9a2",
        "note":"Robinhood settled at $0.82 despite DNP; recorded realized profit takes precedence over box scores."}
}

ROBINHOOD_CONFIRMED_PAYOUTS=[
    {"event_id":"7fef0b82-e731-44e0-b89c-d444bdf23091","date":"2026-11-08","time":"13:43",
     "label":"NFL 7-leg · CIN / DAL / DEN / DET / LAR / NYG / KC",
     "quantity":1334,"settlement_price":1.0,"payout":1334.0,
     "realized_profit":1251.29,"implied_entry_cost":82.71}
]

def show_personal_bets():
    st.title("💸 My Bets · Robinhood")
    from datetime import date
    available_days=[date(2026,11,10),date(2026,11,9),date(2026,11,8),date(2026,11,7)]
    selected_day=st.selectbox("Bet date",available_days,format_func=lambda d:d.strftime("%B %-d, %Y"),key="my_bets_selected_date")
    st.caption("Daily bet tracking · Historical bets and settlement records are retained separately.")
    imported=imported_bet_rows()
    # Keep original November 7 settlement IDs intact; date selection never overwrites records.
    historical=list(reversed(ROBINHOOD_NOV7_BETS))
    current=list(reversed(ROBINHOOD_NOV8_BETS))
    dated_bets=(historical if selected_day==date(2026,11,7) else current if selected_day==date(2026,11,8) else list(reversed(ROBINHOOD_NOV9_BETS)) if selected_day==date(2026,11,9) else list(reversed(ROBINHOOD_NOV10_BETS)))
    all_bets=[(name,qty,price,legs) for name,qty,price,cost,fees,legs,*_ in dated_bets]
    for i,item in enumerate(imported,1):
        if str(item.get("date",""))==selected_day.isoformat():
            all_bets.append((str(item.get("date",""))+" · Import "+str(i),int(item["qty"]),float(item["cents"]),item["legs"]))
    # Parlay numbering is display-only and restarts at #1 for each selected date.
    # Stable internal bet identifiers and settlement records are unchanged.
    labels={}
    for i,(name,qty,price,legs) in enumerate(all_bets,1):
        labels[name]=f"Parlay {i} - {len(legs)} Legs"
    saved=saved_bet_statuses()
    byid={r["Bet"]:r for _,r in saved.iterrows()} if not saved.empty else {}
    total=sum(row[3] for row in dated_bets)+sum(q*p/100 for name,q,p,legs in all_bets if name not in {row[0] for row in dated_bets})
    confirmed_payouts=[p for p in ROBINHOOD_CONFIRMED_PAYOUTS if p['date']==selected_day.isoformat()]
    settled=[]
    for row in byid.values():
        if row.get("Status") in ["Won","Lost","Closed"]:
            try:settled.append(float(row["Net P/L"]))
            except (TypeError,ValueError):pass
    potential_profit=sum(qty for _,qty,_,_ in all_bets)-total
    a,b,c=st.columns(3)
    a.metric("Total entry cost","$"+format(total,",.2f"))
    b.metric("Total potential profit","$"+format(potential_profit,",.2f"))
    with c:
        @st.fragment(run_every="30s")
        def render_realized_pnl():
            from datetime import date
            selected_day=st.session_state.get("my_bets_selected_date",date(2026,11,8))
            try:
                _,pnl_players=espn_nba_boxscores(selected_day.strftime("%Y%m%d"))
                _,nfl_players=espn_nfl_boxscores(selected_day.strftime("%Y%m%d"))
                pnl_players+=nfl_players
            except Exception:
                pnl_players=[]
            realized_total=0.0
            recorded_count=0
            auto_losses=0
            auto_wins=0
            for name,qty,price,legs in all_bets:
                recorded=byid.get(name,{})
                confirmed=ROBINHOOD_CONFIRMED_BET_SETTLEMENTS.get(name)
                if confirmed and confirmed["date"]==selected_day.isoformat():
                    realized_total+=confirmed["realized_profit"]
                    recorded_count+=1
                    continue
                recorded_status=recorded.get("Status","Pending")
                recorded_pnl=recorded.get("Net P/L","")
                # Recorded settlement always takes precedence; never double-count.
                if recorded_status in ("Won","Lost","Closed"):
                    try:
                        realized_total+=float(recorded_pnl)
                        recorded_count+=1
                    except (TypeError,ValueError):
                        pass
                    continue
                if recorded_status=="Voided":
                    continue
                inferred=automatic_parlay_result(legs,pnl_players)
                if inferred in ("Won","Loss"):
                    original=next((b for b in dated_bets if b[0]==name and b[1]==qty and b[2]==price),None)
                    cost=original[3] if original else qty*price/100
                    realized_total+=(qty-cost) if inferred=="Won" else -cost
                    if inferred=="Won":
                        auto_wins+=1
                    else:
                        auto_losses+=1
            realized_total+=sum(p["realized_profit"] for p in confirmed_payouts)
            st.metric("Realized P/L","$"+format(realized_total,",.2f") if recorded_count or auto_losses or auto_wins or confirmed_payouts else "Not recorded")
            if auto_losses or auto_wins:
                st.caption(str(auto_wins)+" reached parlay(s), "+str(auto_losses)+" losing parlay(s) · ESPN-based estimate, not Robinhood settlement · refreshes every 30s")
        render_realized_pnl()
    st.caption(str(len(all_bets)+len(confirmed_payouts))+" parlays shown (including "+str(len(confirmed_payouts))+" payout-only settlement) · "+str(sum(len(legs) for _,_,_,legs in all_bets)+7*len(confirmed_payouts))+" legs · Purchase totals exclude payout-only records; potential profit assumes all open Yes combos win.")
    st.caption(selected_day.strftime("%B %-d")+": $"+format(sum(b[3] for b in dated_bets),",.2f")+" paid including $"+format(sum(b[4] for b in dated_bets),",.2f")+" fees across "+str(len(dated_bets))+" recorded purchases. Additional bulk imports are estimated before fees.")
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
        st.subheader("🏀🏈 Daily Player Prop Tracker")
        st.caption("NBA and NFL ESPN box-score feeds (unofficial). Refreshes every 30 seconds while open; statistical progress is not Robinhood settlement.")
        from datetime import date
        track_date=selected_day
        if st.button("↻ Refresh NBA stats",key="refresh_nba_stats"):
            espn_nba_boxscores.clear()
        try:
            games,players=espn_nba_boxscores(track_date.strftime("%Y%m%d"))
            nfl_games,nfl_players=espn_nfl_boxscores(track_date.strftime("%Y%m%d"))
            games+=nfl_games
            players+=nfl_players
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
                    player=match_espn_player(p,players,m)
                    value=player["stats"].get(m) if player else None
                    actuals[(p,m,t)]=value
                    game=player["game"] if player else None
                    state=game["state"] if game else "unknown"
                    if value is None:
                        progress=("⚪ DNP (final)" if player and player.get("dnp") and state=="post"
                                  else "⚪ Awaiting tipoff" if state=="pre"
                                  else "🟡 Game live · stats pending" if player and state=="in"
                                  else "⚪ Stats pending" if player
                                  else "⚪ Unmatched / unavailable")
                    elif t<0:
                        progress=("🔴 No lost" if value>=abs(t) else "🟢 No won (final)" if state=="post" else "🟡 No still possible")
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
                    jersey=player.get("jersey","") if player else ""
                    display_player=p+(" #"+jersey if jersey else "")
                    rows.append({"Player":display_player,"Stat":m,"Target":("No "+str(abs(t))+"+" if t<0 else str(t)+"+"),"Actual":value,
                                 "Game time":tipoff,"_sort_time":start_time or "9999",
                                 "Needed":(max(0,abs(t)-value) if t<0 else max(0,t-value)) if value is not None else None,
                                 "Game":game["name"] if game else "Unmatched",
                                 "Clock / Status":game["detail"] if game else "Unavailable",
                                 "Leg progress":progress})
                combos=[]
                for name,qty,price,legs in all_bets:
                    values=[actuals.get((p,m,int(t))) for p,m,t in legs]
                    hit=sum(v is not None and ((v<abs(int(t)) and (match_espn_player(p,players,m) or {}).get("game",{}).get("state")=="post") if t<0 else v>=int(t)) for v,(p,m,t) in zip(values,legs))
                    unknown=sum(v is None for v in values)
                    combos.append({"Combo":labels.get(name,name),"Reached":str(hit)+"/"+str(len(legs)),
                                   "Unavailable legs":unknown,"Progress":hit/len(legs) if legs else 0})
                t1,t2=st.tabs(["Player statistics","Combo progress"])
                with t1:
                    stats_df=pd.DataFrame(rows)
                    # Active games first, upcoming games second, completed games last.
                    # Keep the original tipoff ordering within each group.
                    status_order={"in":0,"pre":1,"post":2}
                    stats_df["_game_priority"]=[
                        status_order.get(
                            (match_espn_player(row["Player"].split(" #")[0],players,row["Stat"]) or {}).get("game",{}).get("state","unknown"),
                            1
                        ) for row in rows
                    ]
                    stats_df=stats_df.sort_values(
                        ["_game_priority","_sort_time","Game","Player","Stat","Target"],
                        kind="stable"
                    ).drop(columns=["_game_priority","_sort_time"])
                    responsive_dataframe(stats_df,"mybets_live_stats",preferred=["Stat","Target","Actual","Needed"],hide_index=True,use_container_width=True)
                with t2:
                    responsive_dataframe(pd.DataFrame(combos),"mybets_combo_progress",preferred=["Reached","Progress","Unavailable legs"],hide_index=True,use_container_width=True,
                                 column_config={"Progress":st.column_config.ProgressColumn("Progress",min_value=0,max_value=1,format="%.0f%%")})
                st.caption("An unavailable or unmatched player is never treated as zero or a lost leg. Reached thresholds are provisional until official market settlement.")
        except Exception as exc:
            st.warning("NBA live data is temporarily unavailable. Your bets and settlement records are unaffected.")
            with st.expander("Connection details"):
                st.code(str(exc))
    render_live_nba_tracker()
    @st.fragment(run_every="30s")
    def render_bet_overview():
        st.subheader("Quick bet overview")
        st.caption("Tap a parlay to see live Actual, Needed, and Leg progress. Uses the game date selected above.")
        from datetime import date
        selected_day=st.session_state.get("my_bets_selected_date",date(2026,11,8))
        try:
            _,overview_players=espn_nba_boxscores(selected_day.strftime("%Y%m%d"))
            _,nfl_players=espn_nfl_boxscores(selected_day.strftime("%Y%m%d"))
            overview_players+=nfl_players
            overview_error=False
        except Exception:
            overview_players=[]
            overview_error=True
        if overview_error:st.caption("Box-score feed unavailable; missing values remain unverified.")
        import html
        def esc(value):return html.escape(str(value),quote=True)
        table_html=['''<style>
        .bet-table{width:100%;border:1px solid #9ca3af55;border-radius:10px;overflow:hidden;font-size:14px}
        .bet-cols{display:grid;grid-template-columns:2fr .65fr 1fr 1.15fr 1fr;align-items:center}
        .bet-cols>span{padding:10px 12px;min-width:0;border-right:1px solid #9ca3af30}
        .bet-cols>span:last-child{border-right:0}
        .bet-head{background:#80808012;color:inherit;font-weight:600}
        .bet-entry{border-top:1px solid #9ca3af40}
        .bet-entry summary{list-style:none;cursor:pointer}
        .bet-entry summary::-webkit-details-marker{display:none}
        .bet-entry summary:hover{background:#80808015}
        .bet-entry summary span:first-child:before{content:"▸";margin-right:8px;color:#64748b}
        .bet-entry[open] summary span:first-child:before{content:"▾"}
        .bet-number{text-align:right;font-variant-numeric:tabular-nums}
        .bet-legs{padding:12px 16px 16px;background:#8080800a;border-top:1px solid #9ca3af35}
        .bet-legs table{width:100%;border-collapse:collapse}
        .bet-legs th,.bet-legs td{padding:7px 9px;text-align:left;border-bottom:1px solid #9ca3af30}
        .bet-legs th{font-size:12px;opacity:.8}
        @media(max-width:650px){
          .bet-table{font-size:12px}
          .bet-cols{grid-template-columns:1.65fr .45fr .9fr 1fr .7fr}
          .bet-cols>span{padding:9px 4px;overflow-wrap:anywhere}
          .bet-legs{padding:10px 5px;overflow-x:auto}
          .bet-legs table{font-size:12px;min-width:650px}
        }
        </style><div class="bet-table">
        <div class="bet-cols bet-head"><span>Combo</span><span>Legs</span><span>Wager</span><span>Potential profit</span><span>Status</span></div>''']
        overview_bets=[]
        for original_index,(name,qty,price,legs) in enumerate(all_bets):
            recorded_status=byid.get(name,{}).get("Status","Pending")
            inferred=automatic_parlay_result(legs,overview_players)
            confirmed=ROBINHOOD_CONFIRMED_BET_SETTLEMENTS.get(name)
            status=confirmed["status"] if confirmed and confirmed["date"]==selected_day.isoformat() else (recorded_status if recorded_status in ("Won","Lost","Closed","Voided") else inferred)
            is_loss=status in ("Loss","Lost")
            overview_bets.append((is_loss,original_index,name,qty,price,legs,status))
        # Display confirmed payout-only parlays in the same expandable overview.
        # They are NOT inserted into all_bets, preventing duplicate P/L or speculative entry-cost accounting.
        for payout in confirmed_payouts:
            payout_key="confirmed-payout:"+payout["event_id"]
            team_legs=[[team,"Winner",1] for team in payout["label"].split(" · ")[-1].split(" / ")]
            overview_bets.append((False,len(overview_bets),payout_key,payout["quantity"],0.0,team_legs,"Won"))
            labels[payout_key]="NFL 7-Leg · Won · Settled 1:43 PM"
        # Keep pending parlays first, losing parlays next, and won parlays last.
        # Within the won group, order by number of legs (fewest first).
        overview_bets.sort(key=lambda item:(
            2 if item[6]=="Won" else (1 if item[6] in ("Loss","Lost") else 0),
            len(item[5]) if item[6]=="Won" else item[1],
            item[1]
        ))
        for missed_final,_,name,qty,price,legs,status in overview_bets:
            matched=next((r for r in dated_bets if r[0]==name and r[1]==qty and r[2]==price),None)
            payout=next((p for p in confirmed_payouts if name=="confirmed-payout:"+p["event_id"]),None)
            cost=payout["implied_entry_cost"] if payout else (matched[3] if matched else qty*price/100)
            status_style=(' style="color:#dc2626;font-weight:700"' if missed_final else (' style="color:#16a34a;font-weight:700"' if status=="Won" else ""))
            # Highlight a parlay in the collapsed overview whenever at least
            # one of its player games is currently live and its leg is unresolved.
            has_live_leg=False
            if not payout and status=="Pending":
                for player_name,market,target in legs:
                    live_player=match_espn_player(player_name,overview_players,market)
                    if live_player and live_player["game"]["state"]=="in":
                        live_actual=live_player["stats"].get(market)
                        if live_actual is None or (live_actual<abs(int(target)) if int(target)<0 else live_actual<int(target)):
                            has_live_leg=True
                            break
            live_indicator=' <span title="At least one leg is in progress" style="color:#b77900;font-weight:700">🟡 Live</span>' if has_live_leg else ""
            table_html.append('<details class="bet-entry"><summary class="bet-cols">'+
                              '<span>'+esc(labels.get(name,name))+live_indicator+'</span>'+
                              '<span class="bet-number">'+str(len(legs))+'</span>'+
                              '<span class="bet-number">$'+format(cost,",.2f")+'</span>'+
                              '<span class="bet-number">$'+format(qty-cost,",.2f")+'</span>'+
                              '<span'+status_style+'>'+esc(status)+'</span></summary>')
            confirmed_bet=ROBINHOOD_CONFIRMED_BET_SETTLEMENTS.get(name)
            if confirmed_bet:
                if all(key in confirmed_bet for key in ("time","settlement_price","payout")):
                    realized=float(confirmed_bet.get("realized_profit",0))
                    pnl_text=("-" if realized<0 else "+")+"$"+format(abs(realized),",.2f")
                    detail=(f"Robinhood settled {confirmed_bet['time']} at ${confirmed_bet['settlement_price']:.2f}"
                            +f" · Payout: ${confirmed_bet['payout']:,.2f} · Realized P/L: {pnl_text}"
                            +" · Robinhood settlement confirmed")
                else:
                    realized=float(confirmed_bet.get("realized_profit",0))
                    pnl_text=("-" if realized<0 else "+")+"$"+format(abs(realized),",.2f")
                    detail=("Game result: "+str(confirmed_bet.get("status","Pending"))
                            +" · Estimated P/L: "+pnl_text
                            +" · Robinhood settlement not yet confirmed")
            elif payout:
                payout_amount=float(payout["payout"])
                profit_amount=float(payout["realized_profit"])
                detail=f"Confirmed payout: ${payout_amount:,.2f} · Realized profit: +${profit_amount:,.2f} · Entry cost inferred from payout"
            else:
                detail=f"Max payout: ${qty:,.2f}"
            table_html.append('<div class="bet-legs"><div style="margin-bottom:8px">'+esc(detail)+'</div>'+
                              '<table><thead><tr><th>Leg</th><th>Player</th><th>Market</th><th>Target</th><th>Actual</th><th>Needed</th><th>Leg progress</th></tr></thead><tbody>')
            for i,(p,m,t) in enumerate(legs,1):
                if payout:
                    table_html.append('<tr><td>'+str(i)+'</td><td>'+esc(p)+'</td><td>Game winner</td><td>Yes</td><td>Settled</td><td>0</td><td>🟢 Won</td></tr>')
                    continue
                if confirmed_bet:
                    table_html.append('<tr><td>'+str(i)+'</td><td>'+esc(p)+'</td><td>'+esc(m)+'</td><td>'+esc(t)+'+</td><td>—</td><td>—</td><td>🟢 Settled by Robinhood</td></tr>')
                    continue
                matched_player=match_espn_player(p,overview_players,m)
                actual=matched_player["stats"].get(m) if matched_player else None
                state=matched_player["game"]["state"] if matched_player else "unknown"
                if actual is None:
                    needed="—"
                    leg_progress=("⚪ DNP (final)" if matched_player and matched_player.get("dnp") and state=="post"
                                  else "⚪ Awaiting tipoff" if state=="pre"
                                  else "⚪ Stats pending" if matched_player
                                  else "⚪ Unmatched / unavailable")
                    actual_label="—"
                else:
                    actual_label=str(actual)
                    needed=str(max(0,abs(int(t))-actual)) if int(t)<0 else str(max(0,int(t)-actual))
                    if int(t)<0:
                        leg_progress=("🔴 No lost" if actual>=abs(int(t)) else "🟢 No won (final)" if state=="post" else "🟡 No still possible")
                    elif actual>=int(t):
                        leg_progress="🟢 Reached"
                    elif state=="post":
                        leg_progress="🔴 Missed (final)"
                    elif state=="in":
                        leg_progress="🟡 In progress"
                    else:
                        leg_progress="⚪ Awaiting game"
                jersey=matched_player.get('jersey','') if matched_player else ''
                player_label=p+(' #'+jersey if jersey else '')
                table_html.append('<tr><td>'+str(i)+'</td><td>'+esc(player_label)+'</td><td>'+esc(m)+'</td><td>'+esc(('No '+str(abs(int(t)))+'+') if int(t)<0 else str(t)+'+')+'</td><td>'+esc(actual_label)+'</td><td>'+esc(needed)+'</td><td>'+esc(leg_progress)+'</td></tr>')
            table_html.append('</tbody></table></div></details>')
        table_html.append('</div>')
        st.html("".join(table_html))
    if st.button("▸ Collapse all",key="my_bets_collapse_all",help="Close all expanded parlays in Quick bet overview"):
        st.rerun()
    render_bet_overview()
    from collections import Counter
    exposure=Counter((p,m,t) for _,_,_,legs in all_bets for p,m,t in legs)
    st.subheader("Repeated player props")
    st.caption("Shows which individual outcomes affect multiple combos. Counts are appearances, not independent bets.")
    repeated=[{"Player":p,"Prop":("No "+str(abs(t))+"+" if t<0 else str(t)+"+")+" "+m,"Combos depending on it":n} for (p,m,t),n in exposure.most_common() if n>1]
    if repeated:responsive_dataframe(pd.DataFrame(repeated),"mybets_repeated",preferred=["Prop","Combos depending on it"],hide_index=True,use_container_width=True)
    else:st.caption("No repeated props.")
    st.caption("Overlapping legs are tracked separately within combos but financial totals count each combo once. Settlements are manual and never inferred from incomplete box scores.")

with st.sidebar:
    st.title("🏀 Huie's Degen Center")
    st.caption("Public NBA projections & live player tracking")
    if is_admin:
        st.caption("🔐 Administrator")
        if st.button("Log out of admin",use_container_width=True):
            st.session_state.admin_authenticated=False
            st.session_state.pop("role",None)
            st.rerun()
    else:
        st.caption("🌐 Public · Read-only")
        with st.expander("🔐 Admin Login"):
            with st.form("admin_login_form"):
                entered=st.text_input("Admin password",type="password",autocomplete="current-password")
                submit=st.form_submit_button("Unlock admin tools",use_container_width=True)
            if submit:
                from time import monotonic
                now=monotonic()
                attempts=st.session_state.get("admin_login_attempts",[])
                attempts=[t for t in attempts if now-t<900]
                if len(attempts)>=5:
                    st.error("Too many attempts. Try again later.")
                elif hmac.compare_digest(entered,admin_password):
                    st.session_state.admin_authenticated=True
                    st.session_state.role="admin"
                    st.session_state.admin_login_attempts=[]
                    st.rerun()
                else:
                    attempts.append(now)
                    st.session_state.admin_login_attempts=attempts
                    st.error("Incorrect administrator password.")
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
    st.divider()
    nav_options=["Overview","Bankroll Builder Performance","🔴 Bankroll Builder Live Tracking"]+(["💸 My Bets"] if is_admin else [])+["Bankroll Builder","🧪 Smart Parlay Builder & Model Lab","📊 Huie Parlay Performance","Model's Favorite Props","All Player Props","Three-Point Projections","Individual Games","🏀 Huie Projections"]
    section=st.radio("Navigate",nav_options,label_visibility="visible",key="site_nav")
    phone_view=st.toggle("📱 Preview phone cards on desktop",value=False,key="phone_view",help="Cards appear automatically on phones. Enable this to preview card layout on desktop.")

with st.container(key="mobile_top_header"):
    st.markdown("""<div class="mobile-site-head"><div><b>🏀 Huie's Degen Center</b><small>NBA models &amp; player tracking</small></div><span class="mobile-live-dot">● NBA</span></div>""",unsafe_allow_html=True)

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

def normalized_nba_team(code):
    aliases={"GS":"GSW","GSW":"GSW","WSH":"WAS","WAS":"WAS",
             "NY":"NYK","NYK":"NYK","SA":"SAS","SAS":"SAS",
             "NO":"NOP","NOP":"NOP","UTAH":"UTA","UTA":"UTA"}
    code=str(code).strip().upper()
    return aliases.get(code,code)


@st.cache_data(ttl=300,show_spinner=False)
def nba_tipoff_times(date_key):
    """Game start times from ESPN scoreboard; no player boxscore requests."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    url="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates="+date_key
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=12) as response:
        events=json.load(response).get("events",[])
    result={}
    for event in events:
        competitors=(event.get("competitions") or [{}])[0].get("competitors",[])
        teams={normalized_nba_team(c.get("team",{}).get("abbreviation","")) for c in competitors}
        if len(teams)!=2:continue
        try:
            tip=datetime.fromisoformat(event["date"].replace("Z","+00:00"))
            local=tip.astimezone(ZoneInfo("America/Los_Angeles")).strftime("%I:%M %p PT").lstrip("0")
            result[frozenset(teams)]=(tip.timestamp(),local)
        except (ValueError,TypeError,KeyError):continue
    return result

def show_table(name, allow_filters=True, key_suffix=""):
    if not name:
        st.info("This section is not present in the uploaded workbook.")
        return
    df=sheets[name].copy()
    if df.empty:
        st.warning("No rows found in this section.")
        return
    if name==bankroll:
        # Group picks by matchup, ordered by actual scheduled tipoff.
        # Keep the original workbook values unchanged.
        import re
        from zoneinfo import ZoneInfo
        game_col=lookup(df,"Game")
        if game_col:
            try:
                selected_date=st.session_state.get("bankroll_builder_date")
                date_key=selected_date.strftime("%Y%m%d") if selected_date else datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y%m%d")
                tipoffs=nba_tipoff_times(date_key)
            except Exception:
                tipoffs={}
            def game_sort(value):
                teams=re.findall(r"[A-Z]{2,4}",str(value).upper())
                record=tipoffs.get(frozenset(normalized_nba_team(t) for t in teams)) if len(teams)==2 else None
                return record if record else (float("inf"),"Time unavailable")
            df["_tipoff_sort"]=df[game_col].map(lambda v:game_sort(v)[0])
            df["_tipoff_label"]=df[game_col].map(lambda v:game_sort(v)[1])
            df=df.sort_values(["_tipoff_sort",game_col],kind="stable")
            df.insert(df.columns.get_loc(game_col)+1,"Game time",df["_tipoff_label"])
            df=df.drop(columns=["_tipoff_sort","_tipoff_label"])
    if allow_filters:
        game_col=lookup(df,"Game")
        if game_col:
            available=sorted(df[game_col].dropna().astype(str).unique())
            if 1<len(available)<40:
                game_choice=st.selectbox("Matchup",["All games"]+available,key="game_"+name+key_suffix)
                if game_choice!="All games":df=df[df[game_col].astype(str)==game_choice]
        c1,c2,c3=st.columns([2,1,1])
        search=c1.text_input("Search players or props",key="search_"+name+key_suffix)
        if search:
            df=df[df.astype(str).apply(lambda col:col.str.contains(search,case=False,regex=False,na=False)).any(axis=1)]
        market=lookup(df,"Market","Stat")
        side=lookup(df,"Model side")
        if market:
            opts=sorted(df[market].dropna().astype(str).unique())
            if len(opts)<=80:
                selected=c2.multiselect("Market",opts,key="market_"+name+key_suffix)
                if selected:df=df[df[market].astype(str).isin(selected)]
        if side:
            opts=sorted(df[side].dropna().astype(str).unique())
            selected=c3.multiselect("Model side",opts,key="side_"+name+key_suffix)
            if selected:df=df[df[side].astype(str).isin(selected)]
    if allow_filters and lookup(df,"Model side") and lookup(df,"Model projection"):
        df=historical_summary(df)
        hit1,hit2=st.columns([1,3])
        only_three=hit1.checkbox("Show 3/3 recent hits",key="perfect_"+name+key_suffix,help="Three available games all on the model side of the projection.")
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
    two_decimal={"model projection","reference line","away model pts","home model pts","projected total","edge"}
    for c in df.columns:
        if str(c).lower() in number_keys:
            digits=1 if ("avg" in str(c).lower() or "average" in str(c).lower()) else (2 if str(c).lower() in two_decimal else 0)
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
        responsive_dataframe(df,"models_"+str(name).replace(" ","_")+key_suffix,
                             preferred=["Safer line","Our play","Model projection","Reference line","Last 3 hit rate"],
                             max_rows=12 if not allow_filters else 250,
                             desktop_frame=df.style.apply(paint_row,axis=1),
                             hide_index=True,use_container_width=True,
                             height=min(680,max(230,39*(len(df)+1))),column_config=config)
    st.download_button("Download filtered CSV",df.to_csv(index=False).encode("utf-8"),file_name="nba_"+name.lower().replace(" ","_")+".csv",mime="text/csv",key="download_"+name+key_suffix)

if section=="Overview":
    # Desktop keeps the original, fully expanded homepage.
    with st.container(key="desktop_overview"):
        st.subheader("📈 Bankroll Builder Performance")
        performance_graph(bankroll_history_frame())
        if st.button("View daily Bankroll Builder results",key="open_bankroll_performance"):
            st.info("Choose Bankroll Builder Performance in the sidebar to view daily results and date filters.")
        st.title("Daily NBA Projections")
        st.caption("Model projections · Safer lines · Recent player performance")
        a,b,c=st.columns(3)
        a.metric("Games",len(sheets[schedule]) if schedule else len(games))
        b.metric("Player props",len(sheets[allprops]) if allprops else "—")
        c.metric("Bankroll Builder plays",len(sheets[bankroll]) if bankroll else "—")
        st.subheader("Today's games")
        if schedule:show_table(schedule,False)
        else:st.info("No game schedule sheet found.")
        st.subheader("Bankroll Builder")
        if bankroll:show_table(bankroll,False)

    # Mobile-only homepage: performance stays visible; other sections start collapsed.
    with st.container(key="mobile_overview"):
        st.subheader("📈 Bankroll Builder Performance")
        performance_graph(bankroll_history_frame())
        if st.button("View daily Bankroll Builder results",key="open_bankroll_performance_mobile",
                     on_click=lambda:st.session_state.update({"site_nav":"Bankroll Builder Performance"})):
            pass
        with st.expander("🏀 Daily NBA Projections",expanded=False):
            st.caption("Model projections · Safer lines")
            a,b=st.columns(2)
            a.metric("Games",len(sheets[schedule]) if schedule else len(games))
            b.metric("Player props",len(sheets[allprops]) if allprops else "—")
            st.metric("Bankroll Builder plays",len(sheets[bankroll]) if bankroll else "—")
        with st.expander("🏀 Today's Games",expanded=False):
            if schedule:show_table(schedule,False,key_suffix="_mobile_home")
            else:st.info("No game schedule sheet found.")
        with st.expander("💰 Bankroll Builder",expanded=False):
            if bankroll:show_table(bankroll,False,key_suffix="_mobile_home")
            else:st.info("No Bankroll Builder sheet found.")
elif section=="🧪 Smart Parlay Builder & Model Lab":
    from parlay_lab import render as render_parlay_lab
    render_parlay_lab(sheets[allprops] if allprops else None)
elif section=="📊 Huie Parlay Performance":
    from huie_parlay_performance import render as render_huie_parlay_performance
    render_huie_parlay_performance(espn_nba_boxscores,match_espn_player,ROBINHOOD_CONFIRMED_BET_SETTLEMENTS)
elif section=="Bankroll Builder Performance":
    show_bankroll_performance()
elif section=="🔴 Bankroll Builder Live Tracking":
    show_bankroll_live_tracker()
elif section=="💸 My Bets" and is_admin:
    show_personal_bets()
elif section=="Model Accuracy & ROI":
    show_model_accuracy()
elif section=="Live Prop Tracker":
    show_live_tracker()
elif section=="🏀 Huie Projections":
    from huie_individual_games import render as render_huie_games
    render_huie_games(sheets[allprops] if allprops else None)
elif section=="Individual Games":
    st.title("Individual Game Projections")
    if games:
        selected=st.selectbox("Choose matchup",games)
        show_table(selected)
    else:st.info("No individual game tabs found.")
elif section=="Bankroll Builder":
    st.title("Bankroll Builder")
    from zoneinfo import ZoneInfo
    selected_date=st.date_input(
        "📅 Props game date",
        value=datetime.now(ZoneInfo("America/Los_Angeles")).date(),
        key="bankroll_builder_date",
        help="Select the game date that matches the uploaded Bankroll Builder picks. This is not automatically verified from the workbook."
    )
    st.caption("Showing props for **"+selected_date.strftime("%A, %B %d, %Y")+"** (selected date). Confirm it matches your uploaded workbook.")
    show_table(bankroll)
else:
    chosen={"Bankroll Builder":bankroll,"Model's Favorite Props":favorites,"All Player Props":allprops,"Three-Point Projections":threes}.get(section)
    st.title(section)
    show_table(chosen)

# Touch-friendly phone navigation; the original desktop sidebar is unchanged.
def navigate_phone(destination):
    st.session_state["site_nav"]=destination

with st.container(key="mobile_bottom_nav"):
    # Favorites is available in More. The three key pages use their full labels.
    shortcuts=[("Home","Overview"),
               ("Live Tracker","🔴 Bankroll Builder Live Tracking"),
               ("Bankroll Builder","Bankroll Builder")]
    if is_admin:
        shortcuts.append(("Bets","💸 My Bets"))
    columns=st.columns(len(shortcuts)+1)
    for i,(label,destination) in enumerate(shortcuts):
        with columns[i]:
            st.button(label,key="phone_nav_"+str(i),use_container_width=True,
                      type="primary" if section==destination else "secondary",
                      on_click=navigate_phone,args=(destination,))
    with columns[-1]:
        with st.popover("More",use_container_width=True):
            st.caption("Navigate to another page")
            for j,destination in enumerate(nav_options):
                st.button(destination,key="phone_more_"+str(j),use_container_width=True,
                          type="primary" if section==destination else "secondary",
                          on_click=navigate_phone,args=(destination,))
            st.caption("Uploads, sign-out and admin settings remain in the sidebar.")
