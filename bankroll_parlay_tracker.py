"""Dedicated Bankroll Builder wagers, separate from My Bets settlement ledger."""
import pandas as pd
import streamlit as st

PARLAYS = [
 {"date":"2026-11-10","id":"Assists","contracts":286,"cost":99.26,"fees":4.13,"filled_at":"09:10","legs":[("K. Wagler","Assists",2),("C. Gillespie","Assists",2),("F. Wagner","Assists",6),("D. Acuff Jr.","Assists",6)]},
 {"date":"2026-11-10","id":"Three-Pointers","contracts":246,"cost":99.82,"fees":3.63,"filled_at":"09:04","legs":[("A. Simons","Threes",1),("D. Jones Jr.","Threes",1),("L. Markkanen","Threes",2),("D. Bane","Threes",2)]},
 {"date":"2026-11-10","id":"Rebounds","contracts":346,"cost":99.98,"fees":4.83,"filled_at":"09:02","legs":[("A. Drummond","Rebounds",4),("W. Carter Jr.","Rebounds",8),("A. Black","Rebounds",4),("I. Hartenstein","Rebounds",8)]}
,
 {"date":"2026-11-10","id":"Points + Assists","contracts":270,"cost":99.79,"fees":3.94,"filled_at":"16:38","event_id":"82529a37-8c56-483c-a25c-389dba487cd9","legs":[("T. Silva","Points",10),("W. Carter Jr.","Points",10),("A. Caruso","Assists",2)]}
]

def render_bankroll_parlays():
    st.subheader("🎟️ My Bankroll Builder Parlays")
    st.caption("Actual Robinhood purchases sourced from your submitted orders. Separate from the My Bets ledger; no double counting. Results remain pending until verified.")
    invested=sum(p["cost"] for p in PARLAYS)
    payout=sum(p["contracts"] for p in PARLAYS)
    a,b,c,d=st.columns(4)
    a.metric("Invested",f"${invested:,.2f}")
    b.metric("Parlays",len(PARLAYS))
    c.metric("Legs",sum(len(p["legs"]) for p in PARLAYS))
    d.metric("Realized P/L","—")
    st.caption("Realized P/L is unavailable until settlements are verified. Pending potential returns are not counted as realized profit.")
    st.info("No settled results yet. Realized P/L and win-rate charts will appear after verified settlements are recorded.")
    for p in PARLAYS:
        with st.expander(f'{p["date"]} · {p["id"]} · {len(p["legs"])} legs · Pending · ${p["cost"]:.2f}'):
            st.caption(f'{p["contracts"]} YES contracts · Fees included in cost: ${p["fees"]:.2f} · Filled {p["filled_at"]} Pacific')
            legs=pd.DataFrame([{"Player":name,"Market":market,"Target":f"{target}+","Actual":"—","Status":"Unverified"} for name,market,target in p["legs"]])
            st.dataframe(legs,hide_index=True,use_container_width=True)
            st.caption("Realized P/L: Pending settlement")
