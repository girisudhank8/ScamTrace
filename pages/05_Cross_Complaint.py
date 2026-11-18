"""
ScamTrace — Page 5: Cross-Complaint Correlation
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import config
from modules.database import DatabaseManager
from modules.graph_analytics import TransactionGraph

st.set_page_config(page_title="Cross-Complaint — SCAMTRACE", layout="wide", page_icon="🔗")

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

st.markdown("## 🔗 Cross-Complaint Correlation")
st.markdown(f"<div style='background:#1a1a2e;border:1px solid #d29922;border-radius:6px;padding:8px 12px;font-size:11px;color:#d29922;margin-bottom:16px;'>{config.SYNTHETIC_DATA_DISCLAIMER}</div>", unsafe_allow_html=True)

tx_df = db.get_transactions()
acc_df = db.get_accounts()
cmp_df = db.get_complaints()

if tx_df.empty or cmp_df.empty:
    st.warning("No data loaded. Load demo data from Overview page.")
    st.stop()

# ─── Complaint selection ───
st.markdown("#### Select Complaints to Correlate")
cmp_ids = cmp_df['complaint_id'].tolist()

col_sel, col_info = st.columns([1, 2])
with col_sel:
    selected_cmps = st.multiselect("Complaint IDs", cmp_ids, default=cmp_ids[:3],
                                    help="Select 2+ complaints to find shared accounts and patterns")
    correlate_btn = st.button("🔗 Correlate Selected Complaints", type="primary", use_container_width=True)

with col_info:
    if selected_cmps:
        for cid in selected_cmps:
            row = cmp_df[cmp_df['complaint_id'] == cid]
            if not row.empty:
                r = row.iloc[0]
                st.markdown(f"""
                <div style="background:#161b22;border:1px solid #21262d;border-radius:6px;padding:8px 12px;margin-bottom:6px;">
                    <span style="color:#58a6ff;font-weight:700;">{cid}</span>
                    <span style="color:#8b949e;font-size:11px;margin-left:8px;">{r.get('victim_id','')} | ₹{float(r.get('reported_amount',0)):,.0f} | {r.get('report_date','')}</span>
                    <div style="color:#e6edf3;font-size:11px;margin-top:4px;">{str(r.get('description',''))[:80]}...</div>
                </div>""", unsafe_allow_html=True)

if len(selected_cmps) < 2:
    st.info("Select at least 2 complaints to find correlations.")

elif correlate_btn or 'correlation_result' in st.session_state:
    if correlate_btn:
        with st.spinner("Analyzing complaint correlations..."):
            tg = TransactionGraph(tx_df, acc_df)
            result = tg.find_common_accounts(selected_cmps, cmp_df, tx_df)
            st.session_state['correlation_result'] = result
            st.session_state['correlation_cmps'] = selected_cmps
            db.log_investigation("CROSS_COMPLAINT", f"Correlated {selected_cmps}, {len(result.get('shared_accounts', {}))} shared accounts found")

    result = st.session_state.get('correlation_result', {})
    selected_cmps = st.session_state.get('correlation_cmps', selected_cmps)
    shared = result.get('shared_accounts', {})
    complaint_accounts = result.get('complaint_accounts', {})

    # ─── Summary ───
    st.markdown("---")
    sm1, sm2, sm3 = st.columns(3)
    with sm1: st.metric("Complaints Analyzed", len(selected_cmps))
    with sm2: st.metric("🔗 Shared Accounts", len(shared))
    with sm3:
        total_shared_amt = sum(v.get('total_amount', 0) for v in shared.values())
        st.metric("Volume Through Shared", f"₹{total_shared_amt:,.0f}")

    st.markdown("---")

    tab_shared, tab_graph, tab_why, tab_timeline = st.tabs(
        ["📋 Shared Accounts", "🌐 Correlation Graph", "💡 Why Connected", "📅 Timeline"])

    with tab_shared:
        st.markdown("#### Accounts Appearing in Multiple Complaints")
        if shared:
            shared_rows = []
            for acc_id, info in shared.items():
                acc_info = acc_df[acc_df['account_id'] == acc_id] if not acc_df.empty else pd.DataFrame()
                name = acc_info.iloc[0]['account_holder'] if not acc_info.empty else acc_id
                bank = acc_info.iloc[0]['bank_name'] if not acc_info.empty else ''
                shared_rows.append({
                    'Account ID': acc_id,
                    'Holder': name,
                    'Bank': bank,
                    'Appears In': ', '.join(info['appears_in']),
                    'Complaint Count': info['complaint_count'],
                    'Total Amount (₹)': f"{info['total_amount']:,.2f}"
                })
            shared_df = pd.DataFrame(shared_rows).sort_values('Complaint Count', ascending=False)
            
            # Highlight multi-complaint accounts
            st.dataframe(shared_df, use_container_width=True, hide_index=True,
                         column_config={'Complaint Count': st.column_config.NumberColumn(format="%d",
                                        help="Accounts in 2+ complaints are key suspects")})

            # Bar chart of shared accounts by complaint count
            fig = px.bar(shared_df.head(15), x='Account ID', y='Complaint Count',
                         template='plotly_dark', color='Complaint Count',
                         color_continuous_scale='OrRd', title='Shared Accounts — Complaint Frequency')
            fig.update_layout(paper_bgcolor='#161b22', plot_bgcolor='#0d1117',
                              height=280, margin=dict(l=0, r=0, t=40, b=0), font=dict(color='#e6edf3'))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No shared accounts found across selected complaints with current data.")

    with tab_graph:
        st.markdown("#### Complaint Correlation Network")
        try:
            from pyvis.network import Network
            net = Network(height="480px", width="100%", bgcolor="#0d1117",
                           font_color="#e6edf3", directed=False)
            net.set_options('{"physics": {"stabilization": {"iterations": 100}}, "interaction": {"hover": true}}')

            # Add complaint nodes
            for cid in selected_cmps:
                cmp_row = cmp_df[cmp_df['complaint_id'] == cid]
                amt = float(cmp_row.iloc[0]['reported_amount']) if not cmp_row.empty else 0
                net.add_node(cid, label=f"{cid}\n₹{amt/1000:.0f}K",
                             color='#f85149', size=35, shape='box', title=f"Complaint: {cid}\nAmount: ₹{amt:,.0f}")

            # Add shared account nodes and edges
            for acc_id, info in shared.items():
                acc_info = acc_df[acc_df['account_id'] == acc_id] if not acc_df.empty else pd.DataFrame()
                name = acc_info.iloc[0]['account_holder'] if not acc_info.empty else acc_id
                size = 15 + info['complaint_count'] * 10
                color = '#f85149' if info['complaint_count'] >= 3 else '#d29922' if info['complaint_count'] >= 2 else '#1f6feb'
                net.add_node(acc_id, label=f"{acc_id}\n{name[:10]}",
                             color=color, size=size, title=f"{acc_id}\n{name}\nIn {info['complaint_count']} complaints\n₹{info['total_amount']:,.0f}")
                for cid in info['appears_in']:
                    net.add_edge(cid, acc_id, color='#d29922', width=2 if info['complaint_count'] >= 2 else 1)

            # Add non-shared accounts (smaller)
            already_shown = set(shared.keys()) | set(selected_cmps)
            for cid, accs in complaint_accounts.items():
                for acc in list(accs)[:5]:
                    if acc not in already_shown:
                        net.add_node(acc, label=acc[:8], color='#30363d', size=8, title=acc)
                        net.add_edge(cid, acc, color='#21262d', width=0.5)
                        already_shown.add(acc)

            tmp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'temp_corr.html')
            net.save_graph(tmp)
            with open(tmp, 'r', encoding='utf-8') as f:
                html = f.read()
            components.html(html, height=490, scrolling=True)

            st.markdown("""<div style="font-size:11px;color:#8b949e;margin-top:4px;">
            🔴 Complaint nodes | 🟠 Shared accounts (in 2+ complaints) | 🔵 Single-complaint accounts</div>""",
            unsafe_allow_html=True)

        except ImportError:
            st.warning("PyVis not installed. Install with: pip install pyvis")
            if shared:
                for acc_id, info in shared.items():
                    st.markdown(f"**{acc_id}** appears in: {', '.join(info['appears_in'])}")

    with tab_why:
        st.markdown("#### 💡 Why These Cases Are Connected")
        if shared:
            # Auto-generate connection analysis
            high_shared = {k: v for k, v in shared.items() if v['complaint_count'] >= 2}
            
            st.markdown("""
            <div style="background:#161b22;border:1px solid #21262d;border-radius:8px;padding:16px;margin-bottom:12px;">
            <div style="color:#58a6ff;font-weight:700;margin-bottom:8px;">🔍 Connection Analysis</div>
            """, unsafe_allow_html=True)

            for acc_id, info in list(high_shared.items())[:5]:
                cmps_str = ' and '.join(info['appears_in'])
                acc_info = acc_df[acc_df['account_id'] == acc_id] if not acc_df.empty else pd.DataFrame()
                name = acc_info.iloc[0]['account_holder'] if not acc_info.empty else acc_id

                # Get timing from transactions
                acc_txs = tx_df[(tx_df['sender_account'] == acc_id) | (tx_df['receiver_account'] == acc_id)]
                acc_txs['timestamp'] = pd.to_datetime(acc_txs['timestamp'])

                st.markdown(f"""
                <div style="background:#0d1117;border-left:3px solid #d29922;padding:12px;margin-bottom:8px;border-radius:0 6px 6px 0;">
                    <div style="color:#d29922;font-weight:700;font-size:13px;">{acc_id} — {name}</div>
                    <div style="color:#e6edf3;font-size:12px;margin-top:4px;">
                        This account appears as a common intermediary in <b>{cmps_str}</b>.
                        It processed ₹{info['total_amount']:,.0f} total across {len(acc_txs)} transactions.
                        {"The repeated use of this account across multiple victim complaints suggests coordinated operation." if info['complaint_count'] >= 2 else ""}
                    </div>
                </div>""", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

            # Specific evidence
            st.markdown("**Specific Evidence:**")
            evidence_items = []
            for acc_id, info in high_shared.items():
                evidence_items.append(f"✓ **{acc_id}** is a shared node across {info['complaint_count']} complaints: {', '.join(info['appears_in'])}")
            
            # Check timing overlap
            for cid1 in selected_cmps:
                for cid2 in selected_cmps:
                    if cid1 >= cid2:
                        continue
                    txs1 = tx_df[tx_df['complaint_id'] == cid1]
                    txs2 = tx_df[tx_df['complaint_id'] == cid2]
                    if not txs1.empty and not txs2.empty:
                        txs1['timestamp'] = pd.to_datetime(txs1['timestamp'])
                        txs2['timestamp'] = pd.to_datetime(txs2['timestamp'])
                        t1_range = (txs1['timestamp'].min(), txs1['timestamp'].max())
                        t2_range = (txs2['timestamp'].min(), txs2['timestamp'].max())
                        # Check overlap
                        if t1_range[0] <= t2_range[1] and t2_range[0] <= t1_range[1]:
                            evidence_items.append(f"✓ **{cid1}** and **{cid2}** have overlapping transaction timeframes")

            for item in evidence_items:
                st.markdown(item)
        else:
            st.info("No shared accounts found — complaints appear independent.")

    with tab_timeline:
        st.markdown("#### 📅 Transaction Timeline by Complaint")
        all_complaint_txs = tx_df[tx_df['complaint_id'].isin(selected_cmps)].copy()
        if not all_complaint_txs.empty:
            all_complaint_txs['timestamp'] = pd.to_datetime(all_complaint_txs['timestamp'])
            all_complaint_txs['label'] = all_complaint_txs['sender_account'] + ' → ' + all_complaint_txs['receiver_account']
            
            fig_tl = px.scatter(all_complaint_txs, x='timestamp', y='complaint_id',
                                size='amount', color='complaint_id', hover_data=['sender_account', 'receiver_account', 'amount'],
                                template='plotly_dark', title='Complaint Transaction Timeline',
                                labels={'timestamp': 'Date/Time', 'complaint_id': 'Complaint'})
            fig_tl.update_layout(paper_bgcolor='#161b22', plot_bgcolor='#0d1117', height=300,
                                  margin=dict(l=0, r=0, t=40, b=0), font=dict(color='#e6edf3'))
            fig_tl.update_xaxes(gridcolor='#21262d')
            st.plotly_chart(fig_tl, use_container_width=True)

            # Detailed complaint tx table
            st.dataframe(all_complaint_txs[['complaint_id', 'transaction_id', 'timestamp', 'sender_account',
                                             'receiver_account', 'amount', 'transaction_type']].sort_values('timestamp'),
                         use_container_width=True, hide_index=True)
        else:
            st.info("No complaint-linked transactions found for selected complaints.")
