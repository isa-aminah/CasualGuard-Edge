"""CAUSALGUARD-EDGE multipage application entrypoint."""

import streamlit as st

from navigation import render_sidebar
from style import apply_theme

st.set_page_config(
    page_title="CAUSALGUARD-EDGE",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

pages = {
    "Dashboard": st.Page("app/dashboard.py", title="Dashboard", default=True),
    "Video Analysis": st.Page("app/pages/2_Video_Analysis.py", title="Video Analysis"),
    "Causal Analysis": st.Page("app/pages/3_Causal_Analysis.py", title="Causal Analysis"),
    "Counterfactual Analysis": st.Page("app/pages/4_Counterfactual_Analysis.py", title="Counterfactual Analysis"),
    "Alert Status": st.Page("app/pages/6_Alert_Settings.py", title="Alert Status"),
}
navigation = st.navigation(list(pages.values()), position="hidden")
render_sidebar(pages)
navigation.run()
