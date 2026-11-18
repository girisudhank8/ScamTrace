"""
SCAMTRACE — Financial Crime Intelligence & Investigation Platform
Main Streamlit Application Entry Point
"""
import os
import sys
import logging
import streamlit as st

# ─── Path setup ───
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import config
from modules.database import DatabaseManager

# ─── Logging ───
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Page config (MUST be first Streamlit call) ───
st.set_page_config(
    page_title=config.APP_NAME,
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={'About': f"# {config.APP_NAME}\n{config.APP_SUBTITLE}\nVersion {config.VERSION}"}
)

# ─── Load CSS ───
css_path = os.path.join(BASE_DIR, 'assets', 'style.css')
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ─── Initialize DB ───
@st.cache_resource
def get_db():
    db = DatabaseManager()
    if not db.is_data_loaded():
        db.load_synthetic_data()
    return db

db = get_db()

# ─── Sidebar ───
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center; padding: 12px 0 8px;">
        <div style="font-size:22px; font-weight:800; color:#58a6ff; letter-spacing:0.1em;">🔍 {config.APP_NAME}</div>
        <div style="font-size:10px; color:#8b949e; margin-top:4px; line-height:1.4;">{config.APP_SUBTITLE}</div>
        <div style="font-size:9px; color:#3fb950; margin-top:4px;">v{config.VERSION}</div>
    </div>
    <hr style="border-color:#21262d; margin:8px 0;">
    """, unsafe_allow_html=True)

    st.markdown("<div style='color:#8b949e; font-size:11px; margin-bottom:4px;'>NAVIGATION</div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="color:#8b949e; font-size:11px; line-height:2;">
    📊 Overview<br>
    📥 Data Ingestion<br>
    🔍 Money Trail<br>
    🎯 Mule Detection<br>
    🔗 Cross-Complaint<br>
    🌐 Network Intelligence<br>
    📋 Forensic Reports<br>
    🔐 Evidence Integrity
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#21262d; margin:8px 0;'>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background:#1a1a2e; border:1px solid #21262d; border-radius:6px; padding:8px; font-size:9px; color:#d29922;">
    {config.SYNTHETIC_DATA_DISCLAIMER}
    </div>
    """, unsafe_allow_html=True)

# ─── Main Page ───
st.markdown(f"""
<div style="background:linear-gradient(90deg,#0d1117 0%,#161b22 100%);
     border:1px solid #21262d; border-radius:10px; padding:24px 32px; margin-bottom:24px;">
    <h1 style="color:#58a6ff; font-size:2.2rem; font-weight:800; margin:0; letter-spacing:0.05em;">
        🔍 {config.APP_NAME}
    </h1>
    <p style="color:#8b949e; margin:6px 0 0; font-size:1rem;">{config.APP_SUBTITLE}</p>
</div>
""", unsafe_allow_html=True)

# ─── Quick stats ───
tx_df = db.get_transactions()
acc_df = db.get_accounts()
cmp_df = db.get_complaints()

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("📊 Transactions", f"{len(tx_df):,}")
with col2:
    total_amt = tx_df['amount'].sum() if not tx_df.empty else 0
    st.metric("💰 Volume", f"₹{total_amt/100000:.1f}L")
with col3:
    st.metric("👥 Accounts", f"{len(acc_df):,}")
with col4:
    flagged = len(tx_df[tx_df['complaint_id'].notna()]) if not tx_df.empty else 0
    st.metric("⚠️ Flagged Tx", f"{flagged:,}")
with col5:
    st.metric("📁 Complaints", f"{len(cmp_df):,}")

st.markdown("---")

# ─── Demo Load ───
col_a, col_b = st.columns([2, 1])
with col_a:
    st.markdown("""
    ### Welcome to ScamTrace
    Navigate using the **sidebar** to access all investigation modules.
    
    **Demo workflow:**
    1. 📊 **Overview** → see the case landscape
    2. 🔍 **Money Trail** → trace funds from victim accounts  
    3. 🎯 **Mule Detection** → identify suspicious accounts
    4. 🔗 **Cross-Complaint** → find shared intermediaries
    5. 🌐 **Network Intelligence** → visualize the full graph
    6. 📋 **Forensic Reports** → generate PDF evidence
    """)

with col_b:
    st.markdown("""
    <div style="background:#161b22; border:1px solid #21262d; border-radius:8px; padding:16px;">
    <div style="color:#58a6ff; font-weight:700; margin-bottom:8px;">🔄 Demo Status</div>
    """, unsafe_allow_html=True)
    
    if db.is_data_loaded():
        st.success("✓ Demo data loaded")
        st.markdown(f"<small style='color:#8b949e;'>{len(tx_df)} transactions ready</small>", unsafe_allow_html=True)
    
    if st.button("🔄 Reload Demo Data", use_container_width=True):
        with st.spinner("Loading synthetic dataset..."):
            logs = db.load_synthetic_data()
            st.cache_resource.clear()
            for log in logs:
                st.write(log)
            st.success("✓ Demo investigation loaded!")
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

# ─── Recent activity ───
logs_df = db.get_investigation_logs(limit=5)
if not logs_df.empty:
    st.markdown("### 🕐 Recent Activity")
    for _, row in logs_df.iterrows():
        ts = str(row.get('timestamp', ''))[:19]
        st.markdown(f"<small style='color:#8b949e;'>[{ts}]</small> `{row.get('action', '')}` — <small>{str(row.get('details', ''))[:80]}</small>", unsafe_allow_html=True)
