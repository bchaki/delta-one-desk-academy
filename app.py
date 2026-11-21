"""Delta One Desk Academy: entry point. Navigation is built from content/modules.yaml."""

import streamlit as st

from ui.nav import run

st.set_page_config(
    page_title="Delta One Desk Academy", page_icon=":material/school:", layout="wide"
)
run()
