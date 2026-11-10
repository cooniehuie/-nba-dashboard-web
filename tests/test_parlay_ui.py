"""Streamlit AppTest smoke check for the actual Smart Parlay UI (no network)."""
import unittest
from streamlit.testing.v1 import AppTest

APP = '''
import streamlit as st
import pandas as pd
import parlay_lab

# Mock only the external feed so the UI exercise is deterministic.
parlay_lab._live_nba_context=lambda: {
    "injuries":[],"injury_error":None,"games":[],
    "schedule_error":None,"starters":{},"checked_at":"2026-11-09T12:00:00-08:00"}
# Only this test process uses an empty secrets object.
st.secrets={}
frame=pd.DataFrame([
    {"Player":"Sample One","Market":"Points","Reference line":"10+",
     "Model projection":16,"Last game":12,"2 games ago":14,"3 games ago":13,"Game":"GSW at BOS"},
    {"Player":"Sample Two","Market":"Assists","Reference line":"4+",
     "Model projection":7,"Last game":6,"2 games ago":5,"3 games ago":7,"Game":"LAL at ATL"},
    {"Player":"Sample Three","Market":"Rebounds","Reference line":"7+",
     "Model projection":10,"Last game":9,"2 games ago":10,"3 games ago":11,"Game":"NYK at MIA"}
])
parlay_lab.render(frame)
'''

class ParlayUserInterfaceSmoke(unittest.TestCase):
    def test_model_lab_renders_eligible_parlays(self):
        app=AppTest.from_string(APP, default_timeout=90).run()
        errors=[str(e.message) for e in app.exception]
        self.assertFalse(errors,errors)
        rendered=" ".join(str(x.value) for x in app.title)
        self.assertIn("Smart Parlay",rendered)
        self.assertGreaterEqual(len(app.expander),1)

    def test_incomplete_workbook_history_stays_renderable(self):
        # Exercise All Player Props alone with deliberately missing game stats.
        extra = '''
props=frame.assign(**{"Last game":None,"2 games ago":None,"3 games ago":None,
                       "Last 3 avg":[12.0,6.0,9.0]})
parlay_lab.render(props)
'''
        script=APP.replace("parlay_lab.render(frame)",extra)
        app=AppTest.from_string(script,default_timeout=90).run()
        errors=[str(e.message) for e in app.exception]
        self.assertFalse(errors,errors)
        titles=" ".join(str(x.value) for x in app.title)
        self.assertIn("Smart Parlay",titles)

if __name__=="__main__":unittest.main()
