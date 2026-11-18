"""
ScamTrace — Page 6: Network Intelligence
Full transaction graph visualization using NetworkX + PyVis.
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

st.set_page_config(page_title="Network Intelligence — SCAMTRACE", layout="wide", page_icon="🌐")

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

MULE_IDS  = {f'ACC_M{i:03d}' for i in range(1, 11)}
VICTIM_IDS = {f'ACC_V00{i}' for i in range(1, 6)}

st.markdown("## 🌐 Network Intelligence")
st.markdown(
    f"<div style='background:#1a1a2e;border:1px solid #d29922;border-radius:6px;"
    f"padding:8px 12px;font-size:11px;color:#d29922;margin-bottom:16px;'>"
    f"{config.SYNTHETIC_DATA_DISCLAIMER}</div>",
    unsafe_allow_html=True,
)

if tx_df.empty:
    st.warning("No data loaded. Go to Overview and load demo data.")
    st.stop()

tx_df['timestamp'] = pd.to_datetime(tx_df['timestamp'])

# ─── Graph Controls ───
with st.expander("⚙️ Graph Controls", expanded=True):
    gc1, gc2, gc3 = st.columns(3)
    with gc1:
        show_filter = st.radio(
            "Show Accounts",
            ["All", "Flagged / Mule Only", "Complaint-Related Only"],
            horizontal=False,
        )
    with gc2:
        min_date = tx_df['timestamp'].min().date()
        max_date = tx_df['timestamp'].max().date()
        date_range = st.date_input("Date Range", value=(min_date, max_date),
                                    min_value=min_date, max_value=max_date)
        min_amount = st.number_input("Min Transaction Amount (₹)", min_value=0, value=0, step=5000)
    with gc3:
        layout_algo = st.selectbox("Layout Algorithm",
                                    ["barnes_hut", "force_atlas_2based", "hierarchical"])
        max_nodes = st.slider("Max Nodes to Display", 20, 120, 60,
                               help="Limit for performance")
        render_btn = st.button("🌐 Render Network Graph", type="primary", use_container_width=True)

# ─── Build + Render ───
if render_btn or 'net_html' in st.session_state:
    if render_btn:
        with st.spinner("Building transaction graph…"):
            # Filter transactions
            filtered_tx = tx_df.copy()
            if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                filtered_tx = filtered_tx[
                    (filtered_tx['timestamp'] >= pd.Timestamp(date_range[0])) &
                    (filtered_tx['timestamp'] <= pd.Timestamp(date_range[1]))
                ]
            if min_amount > 0:
                filtered_tx = filtered_tx[filtered_tx['amount'] >= min_amount]
            if show_filter == "Flagged / Mule Only":
                mule_set = MULE_IDS | VICTIM_IDS
                filtered_tx = filtered_tx[
                    filtered_tx['sender_account'].isin(mule_set) |
                    filtered_tx['receiver_account'].isin(mule_set)
                ]
            elif show_filter == "Complaint-Related Only":
                filtered_tx = filtered_tx[filtered_tx['complaint_id'].notna()]

            tg = TransactionGraph(filtered_tx, acc_df)

            # Metrics
            node_metrics = tg.get_node_metrics()
            cycles       = tg.find_cycles()
            components_  = tg.find_connected_components()
            communities  = tg.detect_communities()
            volume_df    = tg.get_volume_per_account()

            st.session_state['tg']            = tg
            st.session_state['node_metrics']  = node_metrics
            st.session_state['cycles']        = cycles
            st.session_state['components']    = components_
            st.session_state['communities']   = communities
            st.session_state['volume_df']     = volume_df
            st.session_state['filtered_tx']   = filtered_tx

            # Build PyVis
            try:
                from pyvis.network import Network
                import math

                net = Network(height="580px", width="100%", bgcolor="#0d1117",
                              font_color="#e6edf3", directed=True)

                # Physics options
                physics_opts = {
                    "barnes_hut": '{"physics":{"barnesHut":{"gravitationalConstant":-8000,"centralGravity":0.3,"springLength":200},"stabilization":{"iterations":150}},"interaction":{"hover":true,"tooltipDelay":100}}',
                    "force_atlas_2based": '{"physics":{"forceAtlas2Based":{"gravitationalConstant":-50,"centralGravity":0.01,"springLength":200,"damping":0.4},"solver":"forceAtlas2Based","stabilization":{"iterations":150}},"interaction":{"hover":true}}',
                    "hierarchical": '{"layout":{"hierarchical":{"enabled":true,"direction":"UD","levelSeparation":150}},"physics":{"enabled":false},"interaction":{"hover":true}}'
                }
                net.set_options(physics_opts.get(layout_algo, physics_opts["barnes_hut"]))

                # Node subset (top by degree)
                all_nodes = list(tg.G.nodes())
                if len(all_nodes) > max_nodes:
                    degree_map = dict(tg.G.degree())
                    all_nodes = sorted(all_nodes, key=lambda n: degree_map.get(n, 0), reverse=True)[:max_nodes]
                subg = tg.G.subgraph(all_nodes)

                # Volume lookup
                vol_lookup = {}
                if not volume_df.empty:
                    for _, vr in volume_df.iterrows():
                        vol_lookup[vr['account_id']] = float(vr.get('total_received', 0)) + float(vr.get('total_sent', 0))

                # Add nodes
                nm_lookup = {}
                if not node_metrics.empty:
                    for _, nr in node_metrics.iterrows():
                        nm_lookup[nr['account_id']] = nr

                for node in subg.nodes():
                    nd = tg.G.nodes[node]
                    holder = nd.get('holder', node)
                    risk   = nd.get('risk_status', 'NORMAL')
                    vol    = vol_lookup.get(node, 0)
                    nm     = nm_lookup.get(node)
                    bc     = float(nm['betweenness_centrality']) if nm is not None else 0

                    if node in VICTIM_IDS:   color = '#f85149'
                    elif node in MULE_IDS:   color = '#d29922'
                    elif risk == 'CRITICAL': color = '#f85149'
                    elif risk == 'HIGH':     color = '#d29922'
                    elif risk == 'MEDIUM':   color = '#58a6ff'
                    else:                    color = '#1f6feb'

                    size = max(10, min(40, 10 + math.log1p(vol / 1000) * 4))
                    title_str = (f"{node}\n{holder}\nRisk: {risk}\n"
                                 f"Volume: ₹{vol:,.0f}\nBetweenness: {bc:.4f}")
                    net.add_node(node, label=f"{node[:8]}\n{holder[:8]}", title=title_str,
                                 color=color, size=size)

                # Add edges
                complaint_accs = set()
                if not filtered_tx.empty:
                    cmp_txs = filtered_tx[filtered_tx['complaint_id'].notna()]
                    complaint_accs.update(cmp_txs['sender_account'])
                    complaint_accs.update(cmp_txs['receiver_account'])

                for s, r, data in subg.edges(data=True):
                    amt  = float(data.get('amount', 0))
                    cid  = data.get('complaint_id', '')
                    is_c = bool(cid) or (s in complaint_accs and r in complaint_accs)
                    ec   = '#f85149' if is_c else '#30363d'
                    ew   = max(0.5, min(5, math.log1p(amt / 5000)))
                    net.add_edge(s, r, title=f"₹{amt:,.0f}\n{data.get('transaction_id','')}",
                                 color=ec, width=ew)

                tmp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   'temp_network.html')
                net.save_graph(tmp)
                with open(tmp, 'r', encoding='utf-8') as f:
                    st.session_state['net_html'] = f.read()

            except ImportError:
                st.session_state['net_html'] = None

            db.log_investigation("NETWORK_RENDER",
                f"Rendered graph: {len(all_nodes)} nodes, filter={show_filter}")

    # Display graph
    net_html = st.session_state.get('net_html')
    if net_html:
        components.html(net_html, height=590, scrolling=True)
        st.markdown("""
        <div style="font-size:11px;color:#8b949e;margin-top:4px;">
        🔴 Victim/Critical &nbsp;|&nbsp; 🟠 Mule/High &nbsp;|&nbsp;
        🔵 Medium &nbsp;|&nbsp; ⚫ Normal &nbsp;|&nbsp;
        <span style="color:#f85149;">━━ Complaint-linked</span>
        &nbsp;|&nbsp; Node size ∝ transaction volume
        </div>""", unsafe_allow_html=True)
    else:
        st.warning("PyVis not installed. Install with: `pip install pyvis`")

    # ─── Metric panels ───
    tg           = st.session_state.get('tg')
    node_metrics = st.session_state.get('node_metrics', pd.DataFrame())
    cycles       = st.session_state.get('cycles', [])
    components_  = st.session_state.get('components', [])
    communities  = st.session_state.get('communities', [])
    filtered_tx  = st.session_state.get('filtered_tx', tx_df)

    st.markdown("---")
    gm1, gm2, gm3, gm4 = st.columns(4)
    with gm1: st.metric("Total Nodes",  tg.G.number_of_nodes() if tg else 0)
    with gm2: st.metric("Total Edges",  tg.G.number_of_edges() if tg else 0)
    with gm3: st.metric("Connected Components", len(components_))
    with gm4: st.metric("Detected Cycles",      len(cycles))

    tab_metrics, tab_node, tab_communities, tab_cycles = st.tabs(
        ["📊 Graph Metrics", "🔎 Node Details", "👥 Communities", "🔄 Cycles"])

    with tab_metrics:
        col_bet, col_pr = st.columns(2)
        with col_bet:
            st.markdown("#### Top 10 — Betweenness Centrality")
            if not node_metrics.empty:
                top_bet = node_metrics.nlargest(10, 'betweenness_centrality')[
                    ['account_id', 'holder', 'betweenness_centrality', 'in_degree', 'out_degree', 'risk_status']]
                st.dataframe(top_bet, use_container_width=True, hide_index=True)
        with col_pr:
            st.markdown("#### Top 10 — PageRank")
            if not node_metrics.empty:
                top_pr = node_metrics.nlargest(10, 'pagerank')[
                    ['account_id', 'holder', 'pagerank', 'in_degree', 'out_degree', 'risk_status']]
                st.dataframe(top_pr, use_container_width=True, hide_index=True)

        if not node_metrics.empty:
            fig = px.scatter(node_metrics, x='betweenness_centrality', y='pagerank',
                             size='in_degree', color='risk_status',
                             hover_data=['account_id', 'holder'],
                             color_discrete_map={'CRITICAL':'#f85149','HIGH':'#d29922',
                                                 'MEDIUM':'#58a6ff','NORMAL':'#1f6feb','LOW':'#3fb950'},
                             template='plotly_dark',
                             title='Betweenness Centrality vs PageRank')
            fig.update_layout(paper_bgcolor='#161b22', plot_bgcolor='#0d1117',
                              height=320, margin=dict(l=0,r=0,t=40,b=0),
                              font=dict(color='#e6edf3'))
            st.plotly_chart(fig, use_container_width=True)

    with tab_node:
        st.markdown("#### Node Details")
        if not node_metrics.empty:
            sel_node = st.selectbox("Select Account", node_metrics['account_id'].tolist(),
                                    format_func=lambda x: f"{x} — {node_metrics[node_metrics['account_id']==x]['holder'].values[0]}")
            nr = node_metrics[node_metrics['account_id'] == sel_node].iloc[0]
            nc1, nc2, nc3 = st.columns(3)
            with nc1:
                st.metric("In-Degree",  int(nr['in_degree']))
                st.metric("Out-Degree", int(nr['out_degree']))
            with nc2:
                st.metric("Betweenness", f"{float(nr['betweenness_centrality']):.4f}")
                st.metric("PageRank",    f"{float(nr['pagerank']):.6f}")
            with nc3:
                st.metric("Degree Centrality", f"{float(nr['degree_centrality']):.4f}")
                st.metric("Risk Status", nr['risk_status'])

            # Transaction history for this node
            node_txs = tx_df[
                (tx_df['sender_account'] == sel_node) |
                (tx_df['receiver_account'] == sel_node)
            ].sort_values('timestamp', ascending=False)
            st.markdown(f"**Transaction History ({len(node_txs)} records):**")
            st.dataframe(node_txs[['transaction_id','timestamp','sender_account',
                                    'receiver_account','amount','transaction_type','complaint_id']].head(20),
                         use_container_width=True, hide_index=True)

    with tab_communities:
        st.markdown("#### Detected Communities")
        if communities:
            comm_rows = []
            for i, comm in enumerate(communities):
                risk_counts = {}
                key_accs = []
                for a in comm:
                    if a in MULE_IDS or a in VICTIM_IDS:
                        key_accs.append(a)
                has_risk = bool(set(comm) & (MULE_IDS | VICTIM_IDS))
                comm_rows.append({
                    'Community': f"C-{i+1}",
                    'Size': len(comm),
                    'Key Accounts': ', '.join(key_accs[:5]) or '—',
                    'Has Flagged Accounts': '⚠️ Yes' if has_risk else 'No',
                })
            comm_df = pd.DataFrame(comm_rows).sort_values('Size', ascending=False)
            st.dataframe(comm_df, use_container_width=True, hide_index=True)

            fig_c = px.bar(comm_df.head(20), x='Community', y='Size',
                           color='Has Flagged Accounts', template='plotly_dark',
                           color_discrete_map={'⚠️ Yes': '#d29922', 'No': '#1f6feb'},
                           title='Community Sizes')
            fig_c.update_layout(paper_bgcolor='#161b22', plot_bgcolor='#0d1117',
                                height=260, margin=dict(l=0,r=0,t=40,b=0),
                                font=dict(color='#e6edf3'))
            st.plotly_chart(fig_c, use_container_width=True)

    with tab_cycles:
        st.markdown("#### Detected Circular Transfers")
        if cycles:
            st.warning(f"⚠️ {len(cycles)} circular transfer pattern(s) detected.")
            for i, cycle in enumerate(cycles[:10]):
                cycle_str = ' → '.join(cycle) + f' → {cycle[0]}'
                is_suspicious = any(a in MULE_IDS for a in cycle)
                badge = "🟠 Involves Mule" if is_suspicious else "🔵 Legitimate"
                # Get amounts
                total = 0
                for j in range(len(cycle)):
                    s, r = cycle[j], cycle[(j+1) % len(cycle)]
                    edge_txs = tx_df[(tx_df['sender_account']==s) & (tx_df['receiver_account']==r)]
                    total += float(edge_txs['amount'].sum())
                st.markdown(f"""
                <div style="background:#161b22;border:1px solid {'#d29922' if is_suspicious else '#21262d'};
                     border-radius:6px;padding:10px 14px;margin-bottom:6px;">
                  <div style="color:#e6edf3;font-size:12px;font-weight:600;">Cycle {i+1}: {cycle_str}</div>
                  <div style="color:#8b949e;font-size:11px;margin-top:4px;">
                    {badge} &nbsp;|&nbsp; Total amount: ₹{total:,.0f}
                  </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.success("✓ No circular transfer patterns detected in current filter.")

else:
    st.markdown("""
    <div style="background:#161b22;border:1px dashed #21262d;border-radius:8px;
         padding:60px 40px;text-align:center;color:#8b949e;">
        <div style="font-size:48px;margin-bottom:16px;">🌐</div>
        <div style="font-size:16px;color:#e6edf3;">Configure filters above and click "Render Network Graph"</div>
        <div style="font-size:12px;margin-top:8px;">Start with "Flagged / Mule Only" for the most revealing view</div>
    </div>""", unsafe_allow_html=True)
