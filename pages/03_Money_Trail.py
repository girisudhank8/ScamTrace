"""
ScamTrace — Page 3: Money Trail Investigation
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import config
from modules.database import DatabaseManager
from modules.graph_analytics import TransactionGraph

st.set_page_config(page_title="Money Trail — SCAMTRACE", layout="wide", page_icon="🔍")

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

@st.cache_data(ttl=300)
def load_data():
    db = get_db()
    return db.get_transactions(), db.get_accounts()

db = get_db()
tx_df, acc_df = load_data()

MULE_IDS = {f'ACC_M{i:03d}' for i in range(1, 11)}
VICTIM_IDS = {f'ACC_V00{i}' for i in range(1, 6)}

def node_color(acc_id):
    if acc_id in VICTIM_IDS: return '#f85149'
    if acc_id in MULE_IDS: return '#d29922'
    return '#1f6feb'

st.markdown("## 🔍 Money Trail Investigation")
st.markdown(f"<div style='background:#1a1a2e;border:1px solid #d29922;border-radius:6px;padding:8px 12px;font-size:11px;color:#d29922;margin-bottom:16px;'>{config.SYNTHETIC_DATA_DISCLAIMER}</div>", unsafe_allow_html=True)

if tx_df.empty:
    st.warning("No transaction data loaded. Go to Overview and load demo data.")
    st.stop()

# ─── Controls ───
all_accounts = sorted(set(tx_df['sender_account'].tolist() + tx_df['receiver_account'].tolist()))
victim_accounts = [a for a in all_accounts if a.startswith('ACC_V')]
mule_accounts = [a for a in all_accounts if a.startswith('ACC_M')]
priority_accounts = victim_accounts + mule_accounts + [a for a in all_accounts if a not in victim_accounts + mule_accounts]

col_ctrl, col_graph = st.columns([1, 3])

with col_ctrl:
    st.markdown("#### ⚙️ Trace Controls")
    
    selected_account = st.selectbox(
        "Source Account",
        priority_accounts,
        help="Select the account to start tracing from",
        format_func=lambda x: f"{'🔴' if x in VICTIM_IDS else '🟠' if x in MULE_IDS else '🔵'} {x}"
    )
    
    direction = st.radio("Direction", ["Outgoing (Follow the Money)", "Incoming (Trace Sources)", "Both"],
                         help="Outgoing traces where money goes; Incoming traces where it came from")
    
    max_depth = st.slider("Max Hops", 1, 8, 4)
    min_amount = st.number_input("Min Amount (₹)", min_value=0, value=0, step=1000)
    
    tx_df['timestamp'] = pd.to_datetime(tx_df['timestamp'])
    min_date = tx_df['timestamp'].min().date()
    max_date = tx_df['timestamp'].max().date()
    date_range = st.date_input("Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    
    trace_btn = st.button("🔍 Trace Money Trail", type="primary", use_container_width=True)
    
    # Quick presets
    st.markdown("---")
    st.markdown("**Quick Demos:**")
    if st.button("🔴 Trace CMP001 (ACC_V001)", use_container_width=True):
        st.session_state['quick_account'] = 'ACC_V001'
    if st.button("🔴 Trace CMP002 (ACC_V002)", use_container_width=True):
        st.session_state['quick_account'] = 'ACC_V002'
    if st.button("🟠 Trace Shared Node (ACC_M007)", use_container_width=True):
        st.session_state['quick_account'] = 'ACC_M007'

if 'quick_account' in st.session_state:
    selected_account = st.session_state['quick_account']
    trace_btn = True

with col_graph:
    if trace_btn:
        with st.spinner(f"Tracing money trail from {selected_account}..."):
            tg = TransactionGraph(tx_df, acc_df)

            dr = None
            if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                dr = (str(date_range[0]), str(date_range[1]))

            paths_out, paths_in = [], []
            if "Outgoing" in direction or direction == "Both":
                paths_out = tg.trace_money_trail(selected_account, max_depth, min_amount, dr)
            if "Incoming" in direction or direction == "Both":
                paths_in = tg.trace_incoming(selected_account, max_depth)

            all_paths = paths_out + paths_in

            if not all_paths:
                st.warning(f"No transaction paths found from **{selected_account}** with current filters.")
            else:
                # Build PyVis graph
                try:
                    from pyvis.network import Network
                    net = Network(height="480px", width="100%", bgcolor="#0d1117",
                                   font_color="#e6edf3", directed=True)
                    net.set_options("""
                    {
                      "edges": {"arrows": {"to": {"enabled": true, "scaleFactor": 0.8}},
                                "color": {"color": "#30363d", "highlight": "#58a6ff"},
                                "smooth": {"type": "curvedCW", "roundness": 0.2}},
                      "physics": {"enabled": true, "stabilization": {"iterations": 100}},
                      "interaction": {"hover": true, "tooltipDelay": 100}
                    }
                    """)

                    added_nodes = set()
                    all_edges = []
                    for p in all_paths:
                        for e in p.get('edges', []):
                            all_edges.append(e)

                    for e in all_edges:
                        for acc in [e.get('from', ''), e.get('to', '')]:
                            if acc and acc not in added_nodes:
                                acc_info = acc_df[acc_df['account_id'] == acc] if not acc_df.empty else pd.DataFrame()
                                label = acc
                                title = acc
                                if not acc_info.empty:
                                    name = acc_info.iloc[0].get('account_holder', acc)
                                    bank = acc_info.iloc[0].get('bank_name', '')
                                    label = f"{acc}\n{name[:12]}"
                                    title = f"{acc}\n{name}\n{bank}"
                                color = node_color(acc)
                                size = 30 if acc == selected_account else 20
                                net.add_node(acc, label=label, title=title, color=color, size=size)
                                added_nodes.add(acc)

                        frm, to_ = e.get('from', ''), e.get('to', '')
                        if frm and to_:
                            amt = float(e.get('amount', 0))
                            is_complaint = bool(e.get('complaint_id', ''))
                            edge_color = '#f85149' if is_complaint else '#30363d'
                            net.add_edge(frm, to_,
                                         title=f"₹{amt:,.0f}\n{e.get('timestamp', '')[:16]}\n{e.get('transaction_id', '')}",
                                         label=f"₹{amt/1000:.0f}K" if amt >= 1000 else f"₹{amt:.0f}",
                                         color=edge_color, width=max(1, min(5, amt / 10000)))

                    tmp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'temp_trail.html')
                    net.save_graph(tmp_path)
                    with open(tmp_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    components.html(html_content, height=500, scrolling=True)

                    # Legend
                    st.markdown("""
                    <div style="display:flex;gap:16px;font-size:11px;color:#8b949e;margin-top:4px;">
                        <span>🔴 Victim</span><span>🟠 Mule/Flagged</span><span>🔵 Regular</span>
                        <span style="color:#f85149;">━━ Complaint-linked</span><span>━━ Normal</span>
                    </div>""", unsafe_allow_html=True)

                except ImportError:
                    st.warning("PyVis not installed. Showing text-based path view.")

                # Path details table
                st.markdown("---")
                st.markdown(f"#### 📋 Path Details ({len(all_paths)} path(s) found)")

                for idx, p in enumerate(all_paths[:10]):
                    path_str = " → ".join(p['path'])
                    with st.expander(f"Path {idx+1}: {path_str} ({p['depth']} hops)"):
                        edges = p.get('edges', [])
                        if edges:
                            edge_rows = []
                            for hop_i, e in enumerate(edges):
                                amt = float(e.get('amount', 0))
                                edge_rows.append({
                                    'Hop': hop_i + 1,
                                    'From': e.get('from', ''),
                                    'To': e.get('to', ''),
                                    'Amount (₹)': f"{amt:,.2f}",
                                    'Timestamp': str(e.get('timestamp', ''))[:19],
                                    'Tx ID': e.get('transaction_id', ''),
                                    'Complaint': e.get('complaint_id', '') or '—'
                                })
                            hop_df = pd.DataFrame(edge_rows)
                            st.dataframe(hop_df, use_container_width=True, hide_index=True)

                # Summary card
                if all_paths:
                    max_hops = max(p['depth'] for p in all_paths)
                    total_edges = sum(len(p['edges']) for p in all_paths)
                    all_edge_data = [e for p in all_paths for e in p.get('edges', [])]
                    source_amt = all_edge_data[0]['amount'] if all_edge_data else 0
                    dest_amt = all_edge_data[-1]['amount'] if all_edge_data else 0
                    retention = (dest_amt / source_amt * 100) if source_amt > 0 else 0

                    st.markdown("---")
                    st.markdown("#### 📊 Path Summary")
                    s1, s2, s3, s4 = st.columns(4)
                    with s1: st.metric("Max Hops", max_hops)
                    with s2: st.metric("Source Amount", f"₹{source_amt:,.0f}")
                    with s3: st.metric("Final Amount", f"₹{dest_amt:,.0f}")
                    with s4: st.metric("Amount Retained", f"{retention:.1f}%")

                    # Export
                    if all_edge_data:
                        export_df = pd.DataFrame(all_edge_data)
                        st.download_button("⬇️ Export Path Data as CSV", export_df.to_csv(index=False).encode(),
                                           file_name=f"money_trail_{selected_account}.csv", mime="text/csv")

                    db.log_investigation("MONEY_TRAIL", f"Traced {selected_account}, {len(all_paths)} paths, max depth {max_hops}")

    else:
        st.markdown("""
        <div style="background:#161b22;border:1px dashed #21262d;border-radius:8px;padding:40px;text-align:center;color:#8b949e;min-height:400px;display:flex;align-items:center;justify-content:center;flex-direction:column;">
            <div style="font-size:48px;margin-bottom:16px;">🔍</div>
            <div style="font-size:16px;margin-bottom:8px;color:#e6edf3;">Select an account and click "Trace Money Trail"</div>
            <div style="font-size:12px;">Try ACC_V001 (Victim) or ACC_M007 (Shared Mule Node)</div>
        </div>""", unsafe_allow_html=True)
