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
    from parlay_live_tracking import render_live_parlays
    st.title("🏀 Huie Projections Performance")
    st.caption("Model-only purchases · separate from Bankroll Builder · also included in My Bets without double-counting.")
    dates=sorted({bet["date"] for bet in HUIE_BETS},reverse=True)
    selected=st.selectbox("Bet date",dates,format_func=lambda day:date.fromisoformat(day).strftime("%B %d, %Y"),key="huie_parlay_date")
    bets=[bet for bet in HUIE_BETS if bet["date"]==selected]
    render_live_parlays(bets,espn_nba_boxscores,match_espn_player,
                        confirmed_settlements,prefix="huie_parlays",title="Huie Projections · Live Parlays")
    st.caption("The legs and entry terms are saved snapshots. A newer workbook does not change historical purchases.")
