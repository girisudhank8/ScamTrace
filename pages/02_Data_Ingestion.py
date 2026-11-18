"""
ScamTrace — Page 2: Data Ingestion
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import pandas as pd
import io
import config
from modules.database import DatabaseManager
from modules.ingestion import TransactionIngester

st.set_page_config(page_title="Data Ingestion — SCAMTRACE", layout="wide", page_icon="📥")

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
ingester = TransactionIngester()

st.markdown("## 📥 Data Ingestion")
st.markdown(f"<div style='background:#1a1a2e;border:1px solid #d29922;border-radius:6px;padding:8px 12px;font-size:11px;color:#d29922;margin-bottom:16px;'>{config.SYNTHETIC_DATA_DISCLAIMER}</div>", unsafe_allow_html=True)

REQUIRED_COLS = ['transaction_id', 'timestamp', 'sender_account', 'receiver_account', 'amount']

tab1, tab2, tab3 = st.tabs(["📤 Upload Files", "🗂️ Column Mapping", "📊 Ingestion Results"])

with tab1:
    st.markdown("#### Upload Transaction Files")
    st.markdown("<small style='color:#8b949e;'>Supported: CSV, Excel (.xlsx), PDF (with tables). Max 50MB per file.</small>", unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Drop files here or click to browse",
        type=['csv', 'xlsx', 'xls', 'pdf'],
        accept_multiple_files=True,
        help="Upload bank statements, UPI logs, or payment gateway exports"
    )

    if uploaded_files:
        st.markdown("#### Uploaded Files")
        for uf in uploaded_files:
            size_mb = len(uf.getvalue()) / (1024 * 1024)
            status_color = "#f85149" if size_mb > config.MAX_FILE_SIZE_MB else "#3fb950"
            status_text = "⚠ TOO LARGE" if size_mb > config.MAX_FILE_SIZE_MB else "✓ Ready"
            st.markdown(f"""
            <div style="background:#161b22;border:1px solid #21262d;border-radius:6px;padding:10px 14px;margin-bottom:6px;">
                <span style="color:#e6edf3;font-weight:600;">{uf.name}</span>
                <span style="color:#8b949e;font-size:12px;margin-left:12px;">{size_mb:.2f} MB</span>
                <span style="color:{status_color};font-size:11px;float:right;font-weight:700;">{status_text}</span>
            </div>
            """, unsafe_allow_html=True)

    # Sample template download
    st.markdown("---")
    st.markdown("#### 📋 Download Sample CSV Template")
    template_csv = ingester.get_sample_template()
    st.download_button(
        "⬇️ Download Template CSV",
        data=template_csv.encode('utf-8'),
        file_name="scamtrace_transaction_template.csv",
        mime="text/csv"
    )

    # Also download sample data
    sample_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'synthetic_transactions.csv')
    if os.path.exists(sample_path):
        with open(sample_path, 'rb') as f:
            st.download_button(
                "⬇️ Download Sample Transaction Data (Synthetic)",
                data=f.read(),
                file_name="synthetic_transactions_sample.csv",
                mime="text/csv"
            )

with tab2:
    st.markdown("#### Column Mapping")

    if not uploaded_files:
        st.info("👆 Upload files in the first tab to configure column mapping.")
    else:
        for uf in uploaded_files:
            if uf.size > config.MAX_FILE_SIZE_BYTES:
                st.error(f"❌ {uf.name} exceeds 50MB limit")
                continue

            st.markdown(f"**Mapping for: `{uf.name}`**")
            file_bytes = uf.getvalue()

            try:
                if uf.name.endswith('.csv'):
                    preview_df = pd.read_csv(io.BytesIO(file_bytes), nrows=5)
                elif uf.name.endswith(('.xlsx', '.xls')):
                    preview_df = pd.read_excel(io.BytesIO(file_bytes), nrows=5)
                else:
                    st.warning(f"PDF column mapping not supported — will auto-extract")
                    continue

                file_cols = ['(auto-detect)'] + list(preview_df.columns)
                auto_map = ingester.auto_detect_mapping(preview_df.columns.tolist())

                col1, col2 = st.columns(2)
                mapping_key = f"mapping_{uf.name}"
                if mapping_key not in st.session_state:
                    st.session_state[mapping_key] = {}

                for i, req_col in enumerate(REQUIRED_COLS):
                    with (col1 if i % 2 == 0 else col2):
                        default_col = auto_map.get(req_col, '(auto-detect)')
                        idx = file_cols.index(default_col) if default_col in file_cols else 0
                        selected = st.selectbox(f"→ {req_col}", file_cols, index=idx, key=f"{uf.name}_{req_col}")
                        if selected != '(auto-detect)':
                            st.session_state[mapping_key][req_col] = selected

                if auto_map:
                    st.success(f"✓ Auto-detected {len(auto_map)} column(s): {list(auto_map.keys())}")

                with st.expander("Preview (first 5 rows)"):
                    st.dataframe(preview_df, use_container_width=True)

            except Exception as e:
                st.error(f"Cannot preview {uf.name}: {e}")

with tab3:
    st.markdown("#### Process & Ingest")

    if not uploaded_files:
        st.info("👆 Upload files first.")
    else:
        if st.button("▶️ Process & Ingest All Files", type="primary"):
            all_dfs = []
            existing_tx = db.get_transactions()

            for uf in uploaded_files:
                if uf.size > config.MAX_FILE_SIZE_BYTES:
                    st.error(f"⏭ Skipping {uf.name} (exceeds 50MB)")
                    continue

                st.markdown(f"**Processing `{uf.name}`...**")
                file_bytes = uf.getvalue()
                mapping = st.session_state.get(f"mapping_{uf.name}", None)

                with st.spinner(f"Ingesting {uf.name}..."):
                    if uf.name.endswith('.csv'):
                        df, logs = ingester.ingest_csv_bytes(file_bytes, mapping if mapping else None)
                    elif uf.name.endswith(('.xlsx', '.xls')):
                        df, logs = ingester.ingest_excel_bytes(file_bytes, mapping if mapping else None)
                    elif uf.name.endswith('.pdf'):
                        df, logs = ingester.ingest_pdf_bytes(file_bytes)
                    else:
                        st.warning(f"Unsupported file type: {uf.name}")
                        continue

                # Show logs
                log_html = '<br>'.join([
                    f"<span style='color:{'#3fb950' if '✓' in l else '#d29922' if '⚠' in l else '#f85149'};'>{l}</span>"
                    for l in logs
                ])
                st.markdown(f"<div style='background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:10px;font-family:monospace;font-size:11px;'>{log_html}</div>", unsafe_allow_html=True)

                if not df.empty:
                    # Duplicate detection
                    dupes = ingester.detect_duplicates(df, existing_tx)
                    if not dupes.empty:
                        st.warning(f"⚠ {len(dupes)} duplicate transaction(s) found and skipped")

                    df_new = df[~df['transaction_id'].isin(existing_tx['transaction_id'] if not existing_tx.empty else [])]

                    # Insert into DB
                    inserted = 0
                    for _, row in df_new.iterrows():
                        try:
                            record = {
                                'transaction_id': str(row['transaction_id']),
                                'timestamp': pd.Timestamp(row['timestamp']).to_pydatetime(),
                                'sender_account': str(row['sender_account']),
                                'receiver_account': str(row['receiver_account']),
                                'amount': float(row['amount']),
                                'transaction_type': str(row.get('transaction_type', 'UPI')),
                                'payment_reference': str(row.get('payment_reference', '')),
                                'complaint_id': str(row['complaint_id']) if pd.notna(row.get('complaint_id')) else None,
                                'description': str(row.get('description', ''))
                            }
                            db.upsert_transaction(record)
                            inserted += 1
                        except Exception as e:
                            pass

                    st.success(f"✓ Inserted {inserted} new records from {uf.name}")
                    db.log_investigation("INGEST_FILE", f"Ingested {inserted} records from {uf.name}")
                    all_dfs.append(df)

            if all_dfs:
                combined = pd.concat(all_dfs, ignore_index=True)
                st.markdown("---")
                st.markdown(f"#### Preview — {len(combined)} records processed")
                st.dataframe(combined.head(20), use_container_width=True)

                summary = ingester.get_ingestion_summary(combined)
                sc1, sc2, sc3, sc4 = st.columns(4)
                with sc1: st.metric("Total Rows", summary.get('total', 0))
                with sc2: st.metric("Unique Senders", summary.get('unique_senders', 0))
                with sc3: st.metric("Unique Receivers", summary.get('unique_receivers', 0))
                with sc4: st.metric("Total Amount", f"₹{summary.get('total_amount', 0):,.0f}")
