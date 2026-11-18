"""
ScamTrace — Page 4: Mule Account Detection
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import config
from modules.database import DatabaseManager
from modules.fraud_detection import FraudDetector, RISK_DISCLAIMER

st.set_page_config(page_title="Mule Detection — SCAMTRACE", layout="wide", page_icon="🎯")

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

st.markdown("## 🎯 Mule Account Detection")
st.markdown(f"<div style='background:#1a1a2e;border:1px solid #d29922;border-radius:6px;padding:8px 12px;font-size:11px;color:#d29922;margin-bottom:8px;'>{config.SYNTHETIC_DATA_DISCLAIMER}</div>", unsafe_allow_html=True)
st.markdown(f"<div style='background:#1a1a2e;border:1px solid #f85149;border-radius:6px;padding:8px 12px;font-size:11px;color:#f85149;margin-bottom:16px;'>{RISK_DISCLAIMER}</div>", unsafe_allow_html=True)

tx_df = db.get_transactions()
acc_df = db.get_accounts()

if tx_df.empty:
    st.warning("No data loaded. Load demo data from Overview page.")
    st.stop()

# ─── Configuration ───
with st.expander("⚙️ Detection Configuration", expanded=False):
    cfg_c1, cfg_c2, cfg_c3 = st.columns(3)
    with cfg_c1:
        risk_threshold = st.slider("Risk Score Threshold (flag above)", 0, 100, 60)
        use_iso_forest = st.toggle("Enable Isolation Forest", value=True)
    with cfg_c2:
        w_velocity = st.slider("Velocity Weight", 0, 50, 25)
        w_ratio = st.slider("IO Ratio Weight", 0, 50, 20)
    with cfg_c3:
        w_withdrawal = st.slider("Rapid Withdrawal Weight", 0, 50, 20)
        w_counterparties = st.slider("Counterparty Weight", 0, 30, 15)

custom_weights = {
    'velocity': w_velocity, 'ratio': w_ratio, 'withdrawal': w_withdrawal,
    'counterparties': w_counterparties, 'holding_time': 10, 'large_tx': 10,
}

# ─── Run Detection ───
run_btn = st.button("▶️ Run Detection Analysis", type="primary")

if run_btn or 'risk_scores' in st.session_state:
    if run_btn:
        with st.spinner("Computing account features and risk scores..."):
            detector = FraudDetector()
            features = detector.compute_account_features(tx_df, acc_df)
            risk_scores = detector.compute_risk_scores(features, custom_weights)

            if use_iso_forest and not features.empty:
                features = detector.run_isolation_forest(features)
                risk_scores['is_anomaly'] = features.set_index('account_id').reindex(
                    risk_scores['account_id'])['is_anomaly'].values if 'is_anomaly' in features.columns else False

            st.session_state['risk_scores'] = risk_scores
            st.session_state['features'] = features

            # Update DB risk statuses
            for _, row in risk_scores.iterrows():
                if row['risk_score'] >= risk_threshold:
                    db.update_account_risk(row['account_id'], row['risk_level'])

            db.log_investigation("MULE_DETECTION", f"Analyzed {len(risk_scores)} accounts, {len(detector.flag_mule_accounts(risk_scores, risk_threshold))} flagged above threshold {risk_threshold}")

    risk_scores = st.session_state.get('risk_scores', pd.DataFrame())
    features = st.session_state.get('features', pd.DataFrame())

    if risk_scores.empty:
        st.error("Detection produced no results.")
        st.stop()

    # ─── Summary metrics ───
    flagged = risk_scores[risk_scores['risk_score'] >= risk_threshold]
    critical = risk_scores[risk_scores['risk_level'] == 'CRITICAL']
    high = risk_scores[risk_scores['risk_level'] == 'HIGH']
    anomalies = risk_scores[risk_scores.get('is_anomaly', pd.Series(False, index=risk_scores.index))].shape[0] if 'is_anomaly' in risk_scores.columns else 0

    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Accounts Analyzed", len(risk_scores))
    with m2: st.metric("⚠ Flagged (≥threshold)", len(flagged), delta=f"threshold: {risk_threshold}")
    with m3: st.metric("🔴 Critical Risk", len(critical))
    with m4: st.metric("🤖 IF Anomalies", anomalies)

    st.markdown("---")

    tab_results, tab_dist, tab_scatter, tab_explain, tab_iso = st.tabs(
        ["📋 Results Table", "📊 Score Distribution", "🔵 Feature Scatter", "🔎 Account Explainer", "🤖 Isolation Forest"])

    with tab_results:
        st.markdown("#### Risk-Sorted Account List")
        st.caption("Sorted by risk score (highest first). Click to expand per-account details.")

        def risk_badge(level):
            colors = {'CRITICAL': '#f85149', 'HIGH': '#d29922', 'MEDIUM': '#58a6ff', 'LOW': '#3fb950'}
            c = colors.get(level, '#8b949e')
            return f"<span style='background:{c};color:white;font-size:9px;font-weight:700;padding:2px 7px;border-radius:4px;'>{level}</span>"

        for _, row in risk_scores.head(30).iterrows():
            score = row['risk_score']
            level = row['risk_level']
            bar_color = {'CRITICAL': '#f85149', 'HIGH': '#d29922', 'MEDIUM': '#58a6ff', 'LOW': '#3fb950'}.get(level, '#3fb950')
            bar_pct = int(score)

            with st.expander(f"{row['account_id']} — {row.get('account_holder', '')} | Score: {score}/100 | {level}"):
                ec1, ec2 = st.columns([2, 1])
                with ec1:
                    st.markdown(f"""
                    <div style="margin-bottom:8px;">
                        <div style="color:#8b949e;font-size:11px;margin-bottom:4px;">RISK SCORE</div>
                        <div style="background:#21262d;border-radius:4px;height:12px;overflow:hidden;">
                            <div style="background:{bar_color};width:{bar_pct}%;height:100%;transition:width .3s;"></div>
                        </div>
                        <div style="color:{bar_color};font-size:20px;font-weight:700;margin-top:4px;">{score}/100</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    factors = str(row.get('contributing_factors', ''))
                    for f in factors.split(';'):
                        if f.strip():
                            st.markdown(f"• {f.strip()}")

                with ec2:
                    st.metric("Tx Count", int(row.get('tx_count', 0)))
                    st.metric("Total Received", f"₹{float(row.get('total_received', 0)):,.0f}")
                    st.metric("Total Sent", f"₹{float(row.get('total_sent', 0)):,.0f}")

                st.caption(f"⚠️ {RISK_DISCLAIMER}")

    with tab_dist:
        st.markdown("#### Risk Score Distribution")
        fig = px.histogram(risk_scores, x='risk_score', nbins=20, template='plotly_dark',
                           color_discrete_sequence=['#1f6feb'])
        fig.add_vline(x=risk_threshold, line_dash="dash", line_color="#f85149",
                      annotation_text=f"Threshold: {risk_threshold}", annotation_position="top right")
        fig.update_layout(paper_bgcolor='#161b22', plot_bgcolor='#0d1117', height=300,
                          margin=dict(l=0, r=0, t=20, b=0), xaxis_title='Risk Score',
                          yaxis_title='Number of Accounts', font=dict(color='#e6edf3'))
        fig.update_yaxes(gridcolor='#21262d')
        st.plotly_chart(fig, use_container_width=True)

        # Score by level donut
        level_counts = risk_scores['risk_level'].value_counts().reset_index()
        level_counts.columns = ['level', 'count']
        fig2 = px.pie(level_counts, values='count', names='level', hole=0.5, template='plotly_dark',
                      color='level', color_discrete_map={'CRITICAL': '#f85149', 'HIGH': '#d29922', 'MEDIUM': '#58a6ff', 'LOW': '#3fb950'})
        fig2.update_layout(paper_bgcolor='#161b22', height=250, margin=dict(l=0, r=0, t=10, b=0),
                           font=dict(color='#e6edf3'), legend=dict(bgcolor='#161b22'))
        st.plotly_chart(fig2, use_container_width=True)

    with tab_scatter:
        st.markdown("#### Feature Scatter — Velocity vs Withdrawal Ratio")
        if not features.empty:
            merged = features.merge(risk_scores[['account_id', 'risk_score', 'risk_level']], on='account_id', how='left')
            fig3 = px.scatter(merged, x='tx_velocity_24h', y='rapid_withdrawal_ratio',
                              color='risk_score', size='unique_counterparties',
                              hover_data=['account_id'] + (['account_holder'] if 'account_holder' in merged.columns else []),
                              template='plotly_dark', color_continuous_scale='RdYlGn_r',
                              labels={'tx_velocity_24h': 'Max Tx Velocity (24h)',
                                      'rapid_withdrawal_ratio': 'Rapid Withdrawal Ratio'})
            fig3.update_layout(paper_bgcolor='#161b22', plot_bgcolor='#0d1117', height=350,
                               margin=dict(l=0, r=0, t=20, b=0), font=dict(color='#e6edf3'))
            fig3.update_yaxes(gridcolor='#21262d')
            fig3.update_xaxes(gridcolor='#21262d')
            st.plotly_chart(fig3, use_container_width=True)

    with tab_explain:
        st.markdown("#### Account Risk Explainer")
        selected_acc = st.selectbox("Select Account", risk_scores['account_id'].tolist(),
                                     format_func=lambda x: f"{x} — {risk_scores[risk_scores['account_id']==x]['risk_level'].values[0] if len(risk_scores[risk_scores['account_id']==x]) > 0 else ''}")

        if selected_acc:
            acc_row = risk_scores[risk_scores['account_id'] == selected_acc].iloc[0]
            feat_row = features[features['account_id'] == selected_acc].iloc[0] if not features.empty and selected_acc in features['account_id'].values else None

            expl_c1, expl_c2 = st.columns([1, 2])
            with expl_c1:
                score = acc_row['risk_score']
                level = acc_row['risk_level']
                bar_color = {'CRITICAL': '#f85149', 'HIGH': '#d29922', 'MEDIUM': '#58a6ff', 'LOW': '#3fb950'}.get(level, '#3fb950')
                st.markdown(f"""
                <div style="background:#161b22;border:1px solid #21262d;border-radius:8px;padding:16px;text-align:center;">
                    <div style="color:#8b949e;font-size:12px;">RISK SCORE</div>
                    <div style="color:{bar_color};font-size:48px;font-weight:800;">{score}</div>
                    <div style="background:{bar_color};color:white;padding:4px 12px;border-radius:4px;display:inline-block;font-weight:700;">{level}</div>
                </div>""", unsafe_allow_html=True)

                if feat_row is not None:
                    st.markdown("**Key Metrics:**")
                    st.metric("Tx Velocity 24h", f"{feat_row.get('tx_velocity_24h', 0):.0f} tx/24h")
                    st.metric("Rapid Withdrawal", f"{feat_row.get('rapid_withdrawal_ratio', 0)*100:.1f}%")
                    st.metric("IO Ratio", f"{feat_row.get('incoming_outgoing_ratio', 0):.2f}")
                    st.metric("Counterparties", f"{feat_row.get('unique_counterparties', 0)}")

            with expl_c2:
                score_cols = ['velocity_score', 'ratio_score', 'withdrawal_score',
                              'counterparty_score', 'holding_score', 'large_tx_score']
                score_labels = ['Velocity', 'IO Ratio', 'Withdrawal', 'Counterparties', 'Holding Time', 'Large Tx']
                score_vals = [float(acc_row.get(c, 0)) for c in score_cols]

                fig4 = go.Figure(go.Bar(
                    x=score_vals, y=score_labels, orientation='h',
                    marker_color=['#f85149' if v >= 15 else '#d29922' if v >= 8 else '#1f6feb' for v in score_vals],
                    text=[f"{v:.1f}" for v in score_vals], textposition='outside'
                ))
                fig4.update_layout(template='plotly_dark', paper_bgcolor='#161b22', plot_bgcolor='#0d1117',
                                   height=280, margin=dict(l=0, r=50, t=20, b=0),
                                   title='Score Contributions', font=dict(color='#e6edf3', size=11))
                st.plotly_chart(fig4, use_container_width=True)

                st.markdown("**Contributing Factors:**")
                factors = str(acc_row.get('contributing_factors', ''))
                for f in factors.split(';'):
                    if f.strip():
                        st.markdown(f"⚠️ {f.strip()}")

            st.warning(RISK_DISCLAIMER)

    with tab_iso:
        st.markdown("#### 🤖 Isolation Forest Anomaly Detection")
        st.info("**Note:** Anomaly = statistically unusual transaction behavior. NOT evidence of criminal activity.")

        if 'is_anomaly' in risk_scores.columns:
            iso_counts = risk_scores['is_anomaly'].value_counts()
            n_anomalies = int(iso_counts.get(True, 0))
            n_normal = int(iso_counts.get(False, 0))

            ic1, ic2 = st.columns(2)
            with ic1: st.metric("🔴 Statistical Anomalies", n_anomalies, help="Statistically unusual accounts")
            with ic2: st.metric("🔵 Normal Behavior", n_normal)

            if 'if_score' in risk_scores.columns:
                fig5 = px.scatter(risk_scores, x='risk_score', y='if_score',
                                  color='is_anomaly', template='plotly_dark',
                                  color_discrete_map={True: '#f85149', False: '#1f6feb'},
                                  hover_data=['account_id'],
                                  labels={'risk_score': 'Heuristic Risk Score', 'if_score': 'IF Anomaly Score'},
                                  title='Isolation Forest vs Heuristic Score')
                fig5.update_layout(paper_bgcolor='#161b22', plot_bgcolor='#0d1117', height=300,
                                   margin=dict(l=0, r=0, t=40, b=0), font=dict(color='#e6edf3'))
                st.plotly_chart(fig5, use_container_width=True)

            anomaly_accs = risk_scores[risk_scores.get('is_anomaly', False)]
            if not anomaly_accs.empty:
                st.markdown("**Statistically Anomalous Accounts:**")
                st.dataframe(anomaly_accs[['account_id', 'account_holder', 'risk_score', 'risk_level', 'tx_count']].head(20),
                             use_container_width=True, hide_index=True)
        else:
            st.info("Enable Isolation Forest in configuration and re-run detection.")
