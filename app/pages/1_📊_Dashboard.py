"""
Tembo Corridors — Dashboard page (Looker Studio, embedded)

Streamlit auto-generates sidebar navigation from files in app/pages/, so
this becomes a second page in the SAME deployed app — one link, two views:
the main page is the interactive Explorer, this page is the fixed-view
summary Dashboard.

Setup required (one-time): get the EMBED url, not the normal share link.
In Looker Studio: File -> Embed report -> toggle "Enable embedding" ->
copy the URL it gives you -> paste below as EMBED_URL.

Also required: the report's sharing setting must allow "Anyone with the
link can view" — otherwise viewers who aren't signed into your Google
account will see a login/access-denied screen inside the embedded frame.
"""

import streamlit as st

st.set_page_config(page_title="Tembo Corridors — Dashboard", page_icon="📊", layout="wide")

st.title("📊 Dashboard")
st.caption(
    "The summary view — four KPIs, priority zones by settlement, the RQ3 "
    "correlation charts, and critical corridor gaps, built for a 30-second "
    "skim. For filtering, click-into-a-zone detail, and the live corridor "
    "map, use the Explorer page in the sidebar."
)

# --- One-time setup: paste your Looker Studio EMBED url below ---
EMBED_URL = "https://datastudio.google.com/embed/reporting/b4b16df4-0a6f-4c18-8b82-787b3470a4e0/page/WH98F"
DIRECT_LINK = "https://datastudio.google.com/reporting/b4b16df4-0a6f-4c18-8b82-787b3470a4e0"

if "PASTE_YOUR_EMBED_URL_HERE" in EMBED_URL:
    st.warning(
        "Embed URL not set yet. In Looker Studio: **File → Embed report → "
        "enable embedding → copy the URL**, then paste it into `EMBED_URL` "
        "in `app/pages/1_📊_Dashboard.py`. Until then, use the link below."
    )
    st.link_button("Open the dashboard in a new tab", DIRECT_LINK)
else:
    st.components.v1.iframe(EMBED_URL, height=900, scrolling=True)
    st.link_button("Open in a new tab instead", DIRECT_LINK)