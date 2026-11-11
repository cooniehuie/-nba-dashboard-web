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
    render_live_parlays(bets,espn_nba_boxscores,match_espn_player,
                        confirmed_settlements,prefix="bankroll_parlays",
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

def render_overview_parlay_pl(settlements, bankroll_history=None, espn_nba_boxscores=None, match_espn_player=None):
    """Stable Overview performance view using native Streamlit components."""
    records=[]
    for p in PARLAYS:
        settlement=(settlements or {}).get(p.get("my_bets",""),{})
        settled=(settlement.get("status") in ("Won","Loss","Lost","Closed")
                 and settlement.get("realized_profit") is not None)
        records.append({"Date":p["date"],"Parlay":p["id"],"Invested":p["cost"],
                        "Realized P/L":float(settlement["realized_profit"]) if settled else None,
                        "Status":settlement.get("status") if settled else "Pending"})
    frame=pd.DataFrame(records)
    confirmed=frame.dropna(subset=["Realized P/L"])
    invested=frame["Invested"].sum()
    pl=confirmed["Realized P/L"].sum()
    a,b,c=st.columns(3)
    a.metric("Invested","${:,.2f}".format(invested))
    b.metric("Parlays",len(frame))
    c.metric("Realized P/L",("{:+,.2f}".format(pl)) if len(confirmed) else "Pending")
    st.caption("Daily realized P/L by original Bankroll Builder list date")
    if len(confirmed):
        daily=confirmed.groupby("Date",as_index=False)["Realized P/L"].sum()
        st.bar_chart(daily.set_index("Date"),height=220)
    else:
        st.caption("P/L bars appear after confirmed Robinhood settlements.")
    with st.expander("Individual parlay results"):
        st.dataframe(frame,hide_index=True,use_container_width=True)
