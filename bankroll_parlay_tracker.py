"""Dedicated Bankroll Builder wagers, separate from My Bets settlement ledger."""
import pandas as pd
import html
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
    """Match the existing Bankroll Builder Safe Line History hero design."""
    records=[]
    for p in PARLAYS:
        settlement=(settlements or {}).get(p.get("my_bets",""),{})
        settled=(settlement.get("status") in ("Won","Loss","Lost","Closed")
                 and settlement.get("realized_profit") is not None)
        records.append({"Date":p["date"],"Parlay":p["id"],"Invested":float(p["cost"]),
                        "Realized P/L":float(settlement["realized_profit"]) if settled else None,
                        "Status":settlement.get("status") if settled else "Pending"})
    frame=pd.DataFrame(records)
    confirmed=frame.dropna(subset=["Realized P/L"])
    invested=frame["Invested"].sum()
    realized=confirmed["Realized P/L"].sum()
    settled_count=len(confirmed)
    pending_count=len(frame)-settled_count
    daily=(confirmed.groupby("Date")["Realized P/L"].sum().to_dict()
           if settled_count else {})
    dates=sorted(set(frame["Date"]),reverse=True)
    max_magnitude=max([abs(v) for v in daily.values()] or [1])
    bars=[]
    for date in dates:
        value=daily.get(date)
        date_label=pd.to_datetime(date).strftime("%b %-d")
        if value is None:
            bar='<div class="bkpl-pending"></div>'
            label="Pending"
        else:
            height=max(3,abs(value)/max_magnitude*92) if value else 3
            color="#34d399" if value>=0 else "#fb7185"
            # Positive bars grow upward, negative bars grow downward from zero.
            side="bottom:50%" if value>=0 else "top:50%"
            bar=f'<div class="bkpl-amount" style="{side};height:{height/2:.1f}%;background:{color}"></div>'
            label=f'${value:+,.2f}'
        bars.append(f'<div class="bkpl-bar-wrap"><div class="bkpl-bar-track"><div class="bkpl-zero"></div>{bar}</div><span>{html.escape(date_label)}</span><b>{html.escape(label)}</b></div>')
    profit_color="#34d399" if realized>=0 else "#fb7185"
    profit_label=f'${realized:+,.2f}' if settled_count else "Pending"
    st.markdown("""<style>
    .bkpl-hero{border-radius:22px;padding:26px 30px;background:linear-gradient(125deg,#0f172a,#172554 62%,#0e7490);
      color:#fff;box-shadow:0 16px 35px #0f172a20;margin:14px 0 22px}
    .bkpl-kicker{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#93c5fd;font-weight:700}
    .bkpl-grid{display:grid;grid-template-columns:1.2fr 1fr;gap:24px;align-items:center}
    .bkpl-big{font-size:clamp(42px,5.5vw,76px);font-weight:850;line-height:1.12;letter-spacing:-.05em}
    .bkpl-muted{color:#cbd5e1;font-size:13px}
    .bkpl-stats{display:flex;gap:24px;flex-wrap:wrap;margin-top:18px}
    .bkpl-stat strong{display:block;font-size:25px;color:#fff;font-variant-numeric:tabular-nums}
    .bkpl-stat span{font-size:12px;color:#cbd5e1}
    .bkpl-track{height:12px;border-radius:30px;background:#ffffff2c;overflow:hidden;margin:16px 0 7px}
    .bkpl-fill{height:100%;background:linear-gradient(90deg,#34d399,#a7f3d0);border-radius:30px}
    .bkpl-chart{display:flex;align-items:end;gap:7px;height:170px;padding-top:12px;overflow-x:auto}
    .bkpl-bar-wrap{flex:1;min-width:42px;text-align:center;display:flex;flex-direction:column;align-items:center;gap:5px;height:100%}
    .bkpl-bar-track{position:relative;width:100%;height:118px;border-radius:7px;background:#ffffff14;overflow:hidden}
    .bkpl-zero{position:absolute;top:50%;height:1px;width:100%;background:#ffffff55}
    .bkpl-amount{position:absolute;left:0;width:100%;border-radius:5px}
    .bkpl-pending{position:absolute;left:0;top:46%;height:8%;width:100%;border-radius:4px;background:#94a3b866}
    .bkpl-bar-wrap span{font-size:10px;color:#cbd5e1;white-space:nowrap}
    .bkpl-bar-wrap b{font-size:10px;color:#fff;white-space:nowrap}
    @media(max-width:750px){
      .bkpl-hero{width:100%;max-width:100%;min-width:0;box-sizing:border-box;padding:16px;overflow:hidden}
      .bkpl-grid{grid-template-columns:minmax(0,1fr);gap:12px;min-width:0;max-width:100%}
      .bkpl-grid>div{min-width:0;max-width:100%}
      .bkpl-chart{height:160px;gap:6px;overflow-x:auto;overflow-y:hidden;padding-bottom:8px}
      .bkpl-bar-wrap{flex:0 0 60px;min-width:60px}
      .bkpl-big{font-size:46px}
    }
    </style>""",unsafe_allow_html=True)
    st.markdown(f"""<div class="bkpl-hero">
      <div class="bkpl-kicker">🏀 BANKROLL BUILDER · PARLAY P/L HISTORY</div>
      <div class="bkpl-grid">
        <div><div class="bkpl-big" style="color:{profit_color if settled_count else '#ffffff'}">{html.escape(profit_label)}</div>
          <div class="bkpl-muted">Realized P/L · {settled_count} settled of {len(frame)} parlays</div>
          <div class="bkpl-track"><div class="bkpl-fill" style="width:{100*settled_count/len(frame) if len(frame) else 0:.1f}%"></div></div>
          <div class="bkpl-stats">
            <div class="bkpl-stat"><strong>${invested:,.2f}</strong><span>INVESTED</span></div>
            <div class="bkpl-stat"><strong>{len(frame)}</strong><span>PARLAYS</span></div>
            <div class="bkpl-stat"><strong>{pending_count}</strong><span>PENDING</span></div>
          </div>
        </div>
        <div><div class="bkpl-muted">DAILY REALIZED P/L · BY BANKROLL LIST DATE</div>
          <div class="bkpl-chart">{''.join(bars)}</div></div>
      </div></div>""",unsafe_allow_html=True)
    with st.expander("Individual parlay settlements",expanded=False):
        st.dataframe(frame,hide_index=True,use_container_width=True)
    st.caption("Green = profit · Red = loss · Gray = pending. P/L is assigned to the original Bankroll Builder list date, not the settlement date.")
