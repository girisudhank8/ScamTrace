"""
ScamTrace — Page 1: Investigation Overview
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import config
from modules.database import DatabaseManager

st.set_page_config(page_title="Overview — SCAMTRACE", layout="wide", page_icon="📊")

css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'style.css')
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

@st.cache_resource
def get_db():
    db = DatabaseManager()
    if not db.is_data_loaded():
        db.load_synthetic_data()
    return db

db = get_db()

st.markdown("## 📊 Investigation Overview")
st.markdown(f"<div style='background:#1a1a2e;border:1px solid #d29922;border-radius:6px;padding:8px 12px;font-size:11px;color:#d29922;margin-bottom:16px;'>{config.SYNTHETIC_DATA_DISCLAIMER}</div>", unsafe_allow_html=True)

tx_df = db.get_transactions()
acc_df = db.get_accounts()
cmp_df = db.get_complaints()
logs_df = db.get_investigation_logs(limit=10)

# ─── Top Metrics ───
c1, c2, c3, c4, c5 = st.columns(5)
total_tx = len(tx_df)
total_amt = float(tx_df['amount'].sum()) if not tx_df.empty else 0
flagged_tx = int(tx_df['complaint_id'].notna().sum()) if not tx_df.empty else 0
active_cmp = len(cmp_df)

suspicious_accs = 0
if not acc_df.empty:
    suspicious_accs = len(acc_df[acc_df['risk_status'].isin(['HIGH', 'CRITICAL', 'MEDIUM'])])

def metric_card(label, value, sub="", color="#58a6ff"):
    return f"""<div style="background:#161b22;border:1px solid #21262d;border-radius:8px;padding:14px 18px;">
        <div style="color:#8b949e;font-size:11px;text-transform:uppercase;letter-spacing:.06em;">{label}</div>
        <div style="color:{color};font-size:26px;font-weight:700;margin-top:4px;">{value}</div>
        <div style="color:#8b949e;font-size:11px;margin-top:2px;">{sub}</div>
    </div>"""

with c1:
    st.markdown(metric_card("Total Transactions", f"{total_tx:,}", "in database"), unsafe_allow_html=True)
with c2:
    amt_str = f"₹{total_amt/100000:.1f}L" if total_amt < 10000000 else f"₹{total_amt/10000000:.2f}Cr"
    st.markdown(metric_card("Amount Processed", amt_str, "total volume"), unsafe_allow_html=True)
with c3:
    st.markdown(metric_card("Suspicious Accounts", str(suspicious_accs), "flagged for review", "#d29922"), unsafe_allow_html=True)
with c4:
    st.markdown(metric_card("Flagged Transactions", str(flagged_tx), "linked to complaints", "#f85149"), unsafe_allow_html=True)
with c5:
    st.markdown(metric_card("Active Complaints", str(active_cmp), "victim cases", "#2ea8a5"), unsafe_allow_html=True)

st.markdown("---")

# ─── Charts ───
col_l, col_r = st.columns(2)

with col_l:
    st.markdown("#### Transaction Volume by Day")
    if not tx_df.empty:
        tx_df['date'] = pd.to_datetime(tx_df['timestamp']).dt.date
        daily = tx_df.groupby('date')['amount'].sum().reset_index()
        daily.columns = ['date', 'amount']
        fig = px.bar(daily, x='date', y='amount', template='plotly_dark',
                     color_discrete_sequence=['#1f6feb'])
        fig.update_layout(paper_bgcolor='#161b22', plot_bgcolor='#0d1117',
                          margin=dict(l=0, r=0, t=10, b=0), height=280,
                          xaxis_title='', yaxis_title='Amount (₹)',
                          font=dict(color='#e6edf3', size=10))
        fig.update_yaxes(gridcolor='#21262d')
        fig.update_xaxes(gridcolor='#21262d')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No transaction data available")

with col_r:
    st.markdown("#### Transaction Types Distribution")
    if not tx_df.empty:
        type_counts = tx_df['transaction_type'].value_counts().reset_index()
        type_counts.columns = ['type', 'count']
        fig2 = px.pie(type_counts, values='count', names='type', template='plotly_dark',
                      color_discrete_sequence=['#1f6feb', '#2ea8a5', '#d29922', '#f85149'])
        fig2.update_layout(paper_bgcolor='#161b22', margin=dict(l=0, r=0, t=10, b=0),
                           height=280, font=dict(color='#e6edf3', size=10),
                           legend=dict(bgcolor='#161b22'))
        fig2.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# ─── Bottom panels ───
col_logs, col_alerts = st.columns([3, 2])

with col_logs:
    st.markdown("#### 🕐 Recent Investigation Activity")
    if not logs_df.empty:
        display_logs = logs_df[['timestamp', 'action', 'details', 'user']].copy()
        display_logs['timestamp'] = pd.to_datetime(display_logs['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        st.dataframe(display_logs, use_container_width=True, height=220,
                     column_config={'timestamp': 'Time', 'action': 'Action',
                                    'details': 'Details', 'user': 'User'})
    else:
        st.markdown("<div style='color:#8b949e; padding:20px; text-align:center;'>No activity logged yet. Load the demo investigation to begin.</div>", unsafe_allow_html=True)

with col_alerts:
    st.markdown("#### ⚠️ Active Alerts")
    # Flag complaint-linked accounts based on transactions
    if not tx_df.empty:
        complaint_accs = set()
        cmp_txs = tx_df[tx_df['complaint_id'].notna()]
        if not cmp_txs.empty:
            complaint_accs.update(cmp_txs['sender_account'].tolist())
            complaint_accs.update(cmp_txs['receiver_account'].tolist())

        mule_ids = [f'ACC_M{i:03d}' for i in range(1, 11)]
        
        for acc_id in mule_ids[:6]:
            if not acc_df.empty:
                acc_row = acc_df[acc_df['account_id'] == acc_id]
                name = acc_row.iloc[0]['account_holder'] if not acc_row.empty else acc_id
            else:
                name = acc_id
            in_complaint = acc_id in complaint_accs
            badge_color = "#f85149" if in_complaint else "#d29922"
            badge_text = "FLAGGED" if in_complaint else "WATCH"
            st.markdown(f"""
            <div style="background:#161b22;border:1px solid #21262d;border-radius:6px;
                 padding:8px 12px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div style="color:#e6edf3;font-size:12px;font-weight:600;">{acc_id}</div>
                    <div style="color:#8b949e;font-size:10px;">{name}</div>
                </div>
                <div style="background:{badge_color};color:white;font-size:9px;font-weight:700;
                     padding:2px 8px;border-radius:4px;">{badge_text}</div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("Load demo data to see alerts")

# ─── Complaint summary table ───
if not cmp_df.empty:
    st.markdown("---")
    st.markdown("#### 📁 Active Complaints")
    display_cmp = cmp_df.copy()
    display_cmp['reported_amount'] = display_cmp['reported_amount'].apply(lambda x: f"₹{x:,.0f}")
    st.dataframe(display_cmp[['complaint_id', 'victim_id', 'reported_amount', 'report_date', 'status', 'description']],
                 use_container_width=True, height=200)
