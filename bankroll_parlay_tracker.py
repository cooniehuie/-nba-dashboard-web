"""Dedicated Bankroll Builder wagers, separate from My Bets settlement ledger."""
import pandas as pd
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

def render_overview_parlay_pl(settlements):
    """Plot confirmed net settlement P/L only, alongside Bankroll Builder hit-rate chart."""
    st.markdown("#### 🎟️ Bankroll Builder Parlay Realized P/L")
    records=[]
    for p in PARLAYS:
        settlement=(settlements or {}).get(p.get("my_bets",""),{})
        confirmed=(settlement.get("status") in ("Won","Loss","Lost","Closed")
                   and settlement.get("realized_profit") is not None)
        records.append({"Date":p["date"],"Parlay":p["id"],
                        "Invested":p["cost"],
                        "Realized P/L":float(settlement["realized_profit"]) if confirmed else None,
                        "Status":settlement.get("status") if confirmed else "Pending"})
    frame=pd.DataFrame(records)
    confirmed=frame.dropna(subset=["Realized P/L"])
    a,b,c=st.columns(3)
    a.metric("Parlays",len(frame))
    b.metric("Invested",f'${frame["Invested"].sum():,.2f}')
    c.metric("Realized P/L",f'${confirmed["Realized P/L"].sum():+,.2f}' if len(confirmed) else "Pending")
    if confirmed.empty:
        st.caption("No confirmed settlements yet. The P/L graph will populate when Robinhood settlement results are recorded.")
    else:
        daily=confirmed.groupby("Date",as_index=False)["Realized P/L"].sum().sort_values("Date")
        daily["Cumulative P/L"]=daily["Realized P/L"].cumsum()
        st.line_chart(daily.set_index("Date")[["Cumulative P/L"]],y_label="Realized P/L ($)")
        st.bar_chart(daily.set_index("Date")[["Realized P/L"]],y_label="Daily realized P/L ($)")
    with st.expander("Parlay settlement breakdown",expanded=False):
        st.dataframe(frame,hide_index=True,use_container_width=True)
    st.caption("Only confirmed net settlement profit/loss is charted; pending wagers do not count as losses or wins.")
