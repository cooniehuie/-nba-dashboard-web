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

def render_overview_parlay_pl(settlements, bankroll_history=None):
    """One compact date-aligned summary beneath the existing Safe Line performance graph."""
    st.markdown("#### Bankroll Builder · Parlay P/L by List Date")
    records=[]
    for p in PARLAYS:
        settlement=(settlements or {}).get(p.get("my_bets",""),{})
        confirmed=(settlement.get("status") in ("Won","Loss","Lost","Closed")
                   and settlement.get("realized_profit") is not None)
        records.append({"Date":p["date"],"Parlay":p["id"],"Invested":p["cost"],
                        "Realized P/L":float(settlement["realized_profit"]) if confirmed else None,
                        "Status":settlement.get("status") if confirmed else "Pending"})
    frame=pd.DataFrame(records)
    history=bankroll_history.copy() if bankroll_history is not None else pd.DataFrame()
    dates=sorted(set(frame["Date"]).union(set(history["Date"]) if not history.empty else set()),reverse=True)
    summary=[]
    for date in dates:
        bets=frame[frame["Date"]==date]
        matched=history[history["Date"]==date] if not history.empty else pd.DataFrame()
        settled=bets.dropna(subset=["Realized P/L"])
        row=matched.iloc[0] if not matched.empty else None
        summary.append({"Bankroll List Date":date,
                        "Safe Line Hit Rate":f'{row["Hit rate"]:.1f}%' if row is not None and row["Graded"] else "—",
                        "Parlays":len(bets) if len(bets) else "—",
                        "Settled":len(settled) if len(bets) else "—",
                        "Realized P/L":f'${settled["Realized P/L"].sum():+,.2f}' if len(settled) else ("Pending" if len(bets) else "—")})
    # Compact visual date cards: one aligned row per Bankroll Builder list date.
    tiles=[]
    for item in summary:
        date=html.escape(pd.to_datetime(item["Bankroll List Date"]).strftime("%b %-d, %Y"))
        rate=item["Safe Line Hit Rate"]
        try:
            percent=max(0,min(100,float(rate.rstrip("%"))))
        except (ValueError,TypeError):
            percent=0
        count=item["Parlays"]
        pl=item["Realized P/L"]
        if pl=="Pending":
            pl_color="#fbbf24"
            pl_label="PENDING"
        elif pl=="—":
            pl_color="#94a3b8"
            pl_label="NO PARLAYS"
        else:
            pl_color="#34d399" if not str(pl).startswith("$-") else "#fb7185"
            pl_label="REALIZED P/L"
        tiles.append(f"""<div class="bkpl-day">
          <div class="bkpl-date">{date}</div>
          <div class="bkpl-rate">
            <span class="bkpl-small">SAFE LINE HIT RATE</span>
            <strong>{html.escape(str(rate))}</strong>
            <div class="bkpl-meter"><div style="width:{percent:.1f}%"></div></div>
          </div>
          <div class="bkpl-count"><span class="bkpl-small">PARLAYS</span><strong>{html.escape(str(count))}</strong></div>
          <div class="bkpl-pl"><span class="bkpl-small">{pl_label}</span><strong style="color:{pl_color}">{html.escape(str(pl))}</strong></div>
        </div>""")
    st.markdown("""<style>
    .bkpl-panel{background:linear-gradient(130deg,#111c33,#182b46);color:#f8fafc;
      padding:14px;border-radius:16px;border:1px solid #38516a;box-shadow:0 8px 24px #0f172a20}
    .bkpl-head{font-size:11px;letter-spacing:.09em;font-weight:750;color:#9db4d0;margin:2px 6px 12px}
    .bkpl-day{display:grid;grid-template-columns:minmax(110px,1.2fr) minmax(120px,1.4fr) minmax(65px,.55fr) minmax(110px,1.1fr);
      gap:14px;align-items:center;padding:13px 12px;border-radius:11px;background:#ffffff0a;margin:7px 0;border:1px solid #ffffff16}
    .bkpl-date{font-size:14px;font-weight:800}
    .bkpl-small{display:block;color:#a9bed4;font-size:10px;letter-spacing:.06em;font-weight:650;margin-bottom:5px}
    .bkpl-rate strong,.bkpl-count strong,.bkpl-pl strong{font-size:19px;font-weight:800;font-variant-numeric:tabular-nums}
    .bkpl-meter{height:5px;background:#ffffff2a;border-radius:9px;margin-top:7px;overflow:hidden}
    .bkpl-meter div{height:100%;border-radius:9px;background:#34d399}
    .bkpl-pl{text-align:right}
    @media(max-width:650px){
      .bkpl-panel{padding:10px}
      .bkpl-day{grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px;padding:12px}
      .bkpl-date{grid-column:1 / -1}
      .bkpl-pl{text-align:left}
      .bkpl-rate strong,.bkpl-count strong,.bkpl-pl strong{font-size:17px}
    }
    </style><div class="bkpl-panel"><div class="bkpl-head">DAILY RESULTS · PARLAY PROFIT & LOSS</div>"""
    +"".join(tiles)+"</div>",unsafe_allow_html=True)
    with st.expander("Individual Bankroll Builder parlays",expanded=False):
        st.dataframe(frame,hide_index=True,use_container_width=True)
    st.caption("P/L is attributed to the date of the Bankroll Builder list used to place the parlay, not the settlement date. Only confirmed net settlements count.")
