"""Dedicated Bankroll Builder wagers, separate from My Bets settlement ledger."""
import pandas as pd
import html
import streamlit as st

PARLAYS = [
 {"date":"2026-11-10","id":"Assists","contracts":286,"cost":99.26,"fees":4.13,"filled_at":"09:10","my_bets":"Nov 10 · Parlay 3","legs":[("K. Wagler","Assists",2),("C. Gillespie","Assists",2),("F. Wagner","Assists",6),("D. Acuff Jr.","Assists",6)]},
 {"date":"2026-11-10","id":"Three-Pointers","contracts":246,"cost":99.82,"fees":3.63,"filled_at":"09:04","my_bets":"Nov 10 · Parlay 2","legs":[("A. Simons","Threes",1),("D. Jones Jr.","Threes",1),("L. Markkanen","Threes",2),("D. Bane","Threes",2)]},
 {"date":"2026-11-10","id":"Rebounds","contracts":346,"cost":99.98,"fees":4.83,"filled_at":"09:02","my_bets":"Nov 10 · Parlay 1","legs":[("A. Drummond","Rebounds",4),("W. Carter Jr.","Rebounds",8),("A. Black","Rebounds",4),("I. Hartenstein","Rebounds",8)]}
,
 {"date":"2026-11-10","id":"Points + Assists","contracts":270,"cost":99.79,"fees":3.94,"filled_at":"16:38","event_id":"82529a37-8c56-483c-a25c-389dba487cd9","my_bets":"Nov 10 · Parlay 16","legs":[("T. Silva","Points",10),("W. Carter Jr.","Points",10),("A. Caruso","Assists",2)]}
]

def render_bankroll_parlays(espn_nba_boxscores,match_espn_player,confirmed_settlements=None):
    from parlay_live_tracking import render_live_parlays
    bets=[]
    # Stable purchase snapshots: one record per actual Robinhood order.
    # The same bets may appear in My Bets; do not add these totals again.
    for index,p in enumerate(PARLAYS,1):
        bets.append({"date":p["date"],"id":p.get("event_id",p["id"]),
                     "label":"Bankroll Parlay "+str(index)+" · "+p["id"],
                     "quantity":p["contracts"],"cost":p["cost"],"fees":p["fees"],
                     "time":p["filled_at"],"legs":p["legs"],
                     "my_bets":p.get("my_bets","")})
    outcomes=bankroll_outcomes(confirmed_settlements,espn_nba_boxscores,match_espn_player)
    render_live_parlays(bets,espn_nba_boxscores,match_espn_player,
                        outcomes,prefix="bankroll_parlays",
                        title="Bankroll Builder Parlays · Live Tracking")

def automatic_game_results(espn_nba_boxscores, match_espn_player):
    """Compute box-score outcomes without treating them as Robinhood settlements."""
    feeds={}
    outcomes={}
    for p in PARLAYS:
        day=p["date"]
        if day not in feeds:
            try:
                feeds[day]=espn_nba_boxscores(day.replace("-",""))[1]
            except Exception:
                feeds[day]=[]
        statuses=[]
        for name,market,target in p["legs"]:
            athlete=match_espn_player(name,feeds[day],market)
            game=athlete.get("game",{}) if athlete else {}
            stat=athlete.get("stats",{}).get(market) if athlete else None
            if stat is None or athlete.get("dnp"):
                statuses.append("Unverified")
            elif stat>=target:
                statuses.append("Hit" if game.get("state")=="post" else "Live hit")
            elif game.get("state")=="post":
                statuses.append("Miss")
            else:
                statuses.append("Pending")
        if "Miss" in statuses:
            result="Game result: lost"
        elif all(s=="Hit" for s in statuses):
            result="Game result: won"
        else:
            result="Unverified / in progress"
        outcomes[(day,p["id"])]=result
    return outcomes

def inferred_settlements(espn_nba_boxscores, match_espn_player):
    """Full-hold contract outcomes. A final-game miss loses; all reached wins."""
    results={}
    feeds={}
    for p in PARLAYS:
        date=p["date"]
        if date not in feeds:
            try:
                feeds[date]=espn_nba_boxscores(date.replace("-",""))[1]
            except Exception:
                feeds[date]=[]
        hits=0
        misses=0
        for name,market,target in p["legs"]:
            athlete=match_espn_player(name,feeds[date],market)
            game=athlete.get("game",{}) if athlete else {}
            actual=athlete.get("stats",{}).get(market) if athlete else None
            if actual is not None and actual>=target:
                hits+=1
            elif actual is not None and game.get("state")=="post":
                misses+=1
        if misses:
            results[p["my_bets"]]={"status":"Loss","realized_profit":-p["cost"],"source":"Final box score"}
        elif hits==len(p["legs"]):
            results[p["my_bets"]]={"status":"Won","realized_profit":p["contracts"]-p["cost"],"source":"All targets reached"}
    return results


def bankroll_outcomes(settlements, espn_nba_boxscores=None, match_espn_player=None):
    """Preserve confirmed transactions; otherwise use full-hold outcome rules."""
    results=dict(settlements or {})
    if espn_nba_boxscores is not None and match_espn_player is not None:
        inferred=inferred_settlements(espn_nba_boxscores,match_espn_player)
        for key,value in inferred.items():
            current=results.get(key,{})
            if current.get("realized_profit") is None or current.get("status") not in ("Won","Loss","Lost","Closed"):
                results[key]=value
    return results

def render_overview_parlay_pl(settlements, bankroll_history=None, espn_nba_boxscores=None, match_espn_player=None):
    """Match the existing Safe Line History hero with daily P/L bars."""
    outcomes=bankroll_outcomes(settlements,espn_nba_boxscores,match_espn_player)
    records=[]
    for p in PARLAYS:
        settlement=outcomes.get(p.get("my_bets",""),{})
        settled=(settlement.get("status") in ("Won","Loss","Lost","Closed")
                 and settlement.get("realized_profit") is not None)
        records.append({"Date":p["date"],"Parlay":p["id"],"Invested":float(p["cost"]),
                        "Realized P/L":float(settlement["realized_profit"]) if settled else None,
                        "Status":settlement.get("status") if settled else "Pending"})
    frame=pd.DataFrame(records)
    confirmed=frame.dropna(subset=["Realized P/L"])
    total=float(confirmed["Realized P/L"].sum())
    invested=float(frame["Invested"].sum())
    won=int((confirmed["Realized P/L"]>0).sum())
    lost=int((confirmed["Realized P/L"]<0).sum())
    pending=len(frame)-len(confirmed)
    daily=confirmed.groupby("Date")["Realized P/L"].sum().to_dict() if len(confirmed) else {}
    dates=sorted(frame["Date"].unique(),reverse=True)
    magnitude=max([abs(v) for v in daily.values()] or [1.0])
    bars=[]
    for date in dates:
        value=daily.get(date)
        label=pd.to_datetime(date).strftime("%b %-d")
        if value is None:
            height=4
            color="#94a3b8"
            amount="Pending"
        else:
            height=max(5,100*abs(value)/magnitude)
            color="#34d399" if value>=0 else "#fb7185"
            amount="${:+,.2f}".format(value)
        bars.append('<div class="bkpl-bar-wrap"><div class="bkpl-bar-track"><div class="bkpl-bar" style="height:{:.1f}%;background:{}"></div></div><span>{}</span><b>{}</b></div>'.format(height,color,label,amount))
    total_label="${:+,.2f}".format(total) if len(confirmed) else "Pending"
    st.markdown("""<style>
    .bkpl-hero{border-radius:22px;padding:26px 30px;background:linear-gradient(125deg,#0f172a,#172554 62%,#0e7490);color:#fff;box-shadow:0 16px 35px #0f172a20;margin:14px 0 22px}
    .bkpl-kicker{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#93c5fd;font-weight:700}
    .bkpl-grid{display:grid;grid-template-columns:1.2fr 1fr;gap:24px;align-items:center}
    .bkpl-big{font-size:clamp(48px,6vw,82px);font-weight:850;line-height:1.12;letter-spacing:-.05em}
    .bkpl-muted{color:#cbd5e1;font-size:13px}
    .bkpl-stats{display:flex;gap:20px;flex-wrap:wrap;margin-top:18px}
    .bkpl-stat strong{display:block;font-size:25px;color:#fff}
    .bkpl-stat span{font-size:12px;color:#cbd5e1}
    .bkpl-track{height:12px;border-radius:30px;background:#ffffff30;overflow:hidden;margin:16px 0 7px}
    .bkpl-fill{height:100%;background:linear-gradient(90deg,#34d399,#a7f3d0);border-radius:30px}
    .bkpl-chart{display:flex;align-items:end;gap:7px;height:170px;padding-top:12px}
    .bkpl-bar-wrap{flex:1;min-width:0;text-align:center;display:flex;flex-direction:column;align-items:center;gap:5px;height:100%}
    .bkpl-bar-track{width:100%;height:118px;display:flex;align-items:end;border-radius:7px;background:#ffffff14;overflow:hidden}
    .bkpl-bar{width:100%;border-radius:6px 6px 0 0}
    .bkpl-bar-wrap span{font-size:10px;color:#cbd5e1;white-space:nowrap}
    .bkpl-bar-wrap b{font-size:10px;color:white;white-space:nowrap}
    @media(max-width:750px){
      .bkpl-hero{width:100%;max-width:100%;min-width:0;box-sizing:border-box;padding:16px;overflow:hidden}
      .bkpl-grid{grid-template-columns:minmax(0,1fr);gap:12px;min-width:0;max-width:100%}
      .bkpl-grid>div{min-width:0;max-width:100%;overflow:hidden}
      .bkpl-chart{width:100%;max-width:100%;min-width:0;box-sizing:border-box;height:160px;gap:6px;overflow-x:auto;overflow-y:hidden;padding-bottom:8px}
      .bkpl-bar-wrap{flex:0 0 70px;min-width:70px}
      .bkpl-big{font-size:46px}
    }
    /* Matches the compact Safe Line History sizing on phones for one-screen screenshots. */
    @media(max-width:750px){
      .bkpl-hero{padding:11px 13px!important;margin:4px 0 8px!important;border-radius:15px!important}
      .bkpl-kicker{font-size:9px!important;letter-spacing:.09em!important;line-height:1.2!important;white-space:nowrap}
      .bkpl-grid{gap:5px!important}
      .bkpl-big{font-size:36px!important;line-height:1.04!important}
      .bkpl-muted{font-size:10px!important;line-height:1.2!important}
      .bkpl-track{height:7px!important;margin:8px 0 4px!important}
      .bkpl-stats{gap:11px!important;flex-wrap:nowrap!important;margin-top:5px!important;align-items:start!important}
      .bkpl-stat{min-width:0}
      .bkpl-stat strong{font-size:16px!important;line-height:1.1!important;white-space:nowrap}
      .bkpl-stat span{font-size:8px!important;line-height:1.15!important}
      .bkpl-chart{height:93px!important;padding:4px 0 0!important;gap:5px!important}
      .bkpl-bar-track{height:57px!important;flex:0 0 57px!important;border-radius:5px!important}
      .bkpl-bar-wrap{flex:0 0 66px!important;min-width:66px!important;max-width:66px!important;gap:2px!important}
      .bkpl-bar-wrap span,.bkpl-bar-wrap b{font-size:9px!important;line-height:1.15!important}
    }
    </style>""",unsafe_allow_html=True)
    markup='''<div class="bkpl-hero"><div class="bkpl-kicker">🏀 BANKROLL BUILDER · PARLAY P/L HISTORY</div>
      <div class="bkpl-grid"><div><div class="bkpl-big">{}</div>
      <div class="bkpl-muted">Realized P/L · {} graded parlays</div>
      <div class="bkpl-track"><div class="bkpl-fill" style="width:{:.1f}%"></div></div>
      <div class="bkpl-stats">
      <div class="bkpl-stat"><strong>${:,.2f}</strong><span>INVESTED</span></div>
      <div class="bkpl-stat"><strong>{}</strong><span>PARLAYS</span></div>
      <div class="bkpl-stat"><strong>{}</strong><span>WINS</span></div>
      <div class="bkpl-stat"><strong>{}</strong><span>LOSSES</span></div>
      <div class="bkpl-stat"><strong>{}</strong><span>PENDING</span></div></div></div>
      <div><div class="bkpl-muted">DAILY REALIZED P/L</div>
      <div class="bkpl-chart">{}</div></div></div></div>'''.format(
        total_label,len(confirmed),100*len(confirmed)/len(frame) if len(frame) else 0,
        invested,len(frame),won,lost,pending,"".join(bars))
    st.markdown(markup,unsafe_allow_html=True)
    with st.expander("Individual parlay results",expanded=False):
        st.dataframe(frame,hide_index=True,use_container_width=True)
    st.caption("Daily P/L follows the original Bankroll Builder list date. Green = profit; red = loss; gray = pending.")
