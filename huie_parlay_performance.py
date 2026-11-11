"""Huie-only parlay performance: distinct from My Bets and bankroll selections."""
from datetime import date
import pandas as pd
import streamlit as st

# Immutable snapshots of the actual contracts. Values include Robinhood fees.
# These are also recorded in the main My Bets view (#22 and #23); never sum
# Huie totals into the overall My Bets totals a second time.
HUIE_BETS=[
 {"id":"4cfd2ec8-b0ea-4039-b0cd-0b090b5a9439","date":"2026-11-10",
  "time":"17:39","my_bets":"Nov 10 · Parlay 23","label":"Huie Parlay 2 · 6 Legs",
  "quantity":1489,"price":0.0627,"fees":6.13,"cost":99.44,
  "legs":[("S. Gilgeous-Alexander","Threes",3),("J. Holiday","Threes",2),
          ("T. Camara","Threes",2),("D. Acuff Jr.","Threes",2),
          ("D. Bane","Threes",3),("K. Wagler","Threes",1)]},
 {"id":"c5e264c8-d12f-411d-93ad-c68c7dac7e41","date":"2026-11-10",
  "time":"17:34","my_bets":"Nov 10 · Parlay 22","label":"Huie Parlay 1 · 4 Legs",
  "quantity":1304,"price":0.0712,"fees":6.05,"cost":98.88,
  "legs":[("K. Wagler","Threes",2),("R. Hachimura","Threes",2),
          ("D. Booker","Threes",2),("D. Brooks","Threes",2)]}
]

def render(espn_nba_boxscores, match_espn_player, confirmed_settlements=None):
    st.title("🏀 Huie Projections Performance")
    st.caption("Parlays specifically placed from Huie's model · Separate performance attribution; bets also remain in My Bets.")
    confirmed_settlements=confirmed_settlements or {}
    unique_days=sorted({b["date"] for b in HUIE_BETS},reverse=True)
    selected=st.selectbox("Bet date",unique_days,format_func=lambda d:date.fromisoformat(d).strftime("%B %d, %Y"),
                          key="huie_parlay_date")
    bets=[b for b in HUIE_BETS if b["date"]==selected]
    cost=sum(b["cost"] for b in bets)
    potential=sum(b["quantity"]-b["cost"] for b in bets)
    try:
        games,players=espn_nba_boxscores(selected.replace("-",""))
        feed_error=None
    except Exception as exc:
        games,players=[],[]
        feed_error=type(exc).__name__
    if feed_error:
        st.warning("Live ESPN stats are temporarily unavailable ("+feed_error+"). No leg outcomes were assumed.")

    all_rows=[]
    statuses={}
    settled_profit=0.
    settled_count=0
    for bet in bets:
        bstatus="Pending"
        hit=miss=unverified=0
        for name,market,target in bet["legs"]:
            found=match_espn_player(name,players,market)
            actual=found.get("stats",{}).get(market) if found else None
            state=found.get("game",{}).get("state","") if found else ""
            dnp=bool(found.get("dnp")) if found else False
            if dnp:
                result="DNP (settlement unverified)"
                unverified+=1
            elif actual is None:
                result="Unverified"
                unverified+=1
            elif actual>=target:
                result="Hit"
                hit+=1
            elif state=="post":
                result="Miss"
                miss+=1
            else:
                result="In progress" if state=="in" else "Not started"
                unverified+=1
            all_rows.append({"Bet":bet["label"],"Player":name,"Market":market,
                             "Target":str(target)+"+","Actual":actual,"Result":result,
                             "Game":found.get("game",{}).get("name","—") if found else "—"})
        if miss:
            bstatus="Lost (game result)"
        elif hit==len(bet["legs"]):
            bstatus="Won (game result)"
        settlement=confirmed_settlements.get(bet["my_bets"],{})
        # A completed leg is not a confirmed Robinhood cash settlement.
        if settlement.get("status") in ("Won","Loss","Lost","Closed") and settlement.get("realized_profit") is not None:
            bstatus="Settled "+("Won" if settlement["status"]=="Won" else "Lost")
            settled_profit+=float(settlement["realized_profit"])
            settled_count+=1
        statuses[bet["id"]]=(bstatus,hit,miss,unverified,settlement)

    c1,c2,c3=st.columns(3)
    c1.metric("Total entry cost",f"${cost:,.2f}")
    c2.metric("Maximum potential profit",f"+${potential:,.2f}")
    c3.metric("Realized P/L",f"${settled_profit:+,.2f}")
    a,b,c=st.columns(3)
    a.metric("Parlays",len(bets))
    b.metric("Settled",f"{settled_count}/{len(bets)}")
    c.metric("Verified leg hits",f"{sum(s[1] for s in statuses.values())}/{sum(len(x['legs']) for x in bets)}")
    st.caption("Realized P/L counts confirmed Robinhood settlement records only. ESPN results are provisional; pending investments are not recorded as losses.")

    for bet in sorted(bets,key=lambda x:x["time"]):
        status,hit,miss,unknown,settlement=statuses[bet["id"]]
        with st.expander(f"{bet['label']} · {status} · {hit}/{len(bet['legs'])} hits",expanded=True):
            x,y,z=st.columns(3)
            x.metric("Cost (with fees)",f"${bet['cost']:,.2f}")
            y.metric("Maximum payout",f"${bet['quantity']:,.2f}")
            z.metric("Potential profit",f"+${bet['quantity']-bet['cost']:,.2f}")
            st.caption(f"Robinhood · {bet['my_bets']} · Filled {bet['time']} PT · Fees ${bet['fees']:.2f}")
            st.dataframe(pd.DataFrame([r for r in all_rows if r["Bet"]==bet["label"]]).drop(columns="Bet"),
                         use_container_width=True,hide_index=True)
            st.link_button("View Robinhood event","https://robinhood.com/events/combos/"+bet["id"]+"?source=event_contract_order")
    st.subheader("Huie strategy history")
    history=[]
    for bet in bets:
        status,hit,miss,unknown,settlement=statuses[bet["id"]]
        history.append({"Date":bet["date"],"Parlay":bet["label"],"Legs":len(bet["legs"]),
                        "Hits":hit,"Misses":miss,"Unverified / live":unknown,
                        "Cost":bet["cost"],"Potential profit":bet["quantity"]-bet["cost"],
                        "Status":status,"Realized P/L":settlement.get("realized_profit")})
    st.dataframe(pd.DataFrame(history),hide_index=True,use_container_width=True)
    st.download_button("Export Huie parlay performance",pd.DataFrame(history).to_csv(index=False),
                       "huie_parlay_performance.csv","text/csv")
    st.caption("For meaningful model evaluation, compare both the projected hit probability and the observed hit rate over many days. A large potential payout is not evidence of a positive expected return.")
