"""
ScamTrace — Page 8: Evidence Integrity
SHA-256 hashing, chain-of-custody, and verification.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import pandas as pd
from datetime import datetime
import config
from modules.database import DatabaseManager
from modules.evidence import EvidenceManager

st.set_page_config(page_title="Evidence Integrity — SCAMTRACE", layout="wide", page_icon="🔐")

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
em = EvidenceManager(db_manager=db)

st.markdown("## 🔐 Evidence Integrity")
st.markdown(
    f"<div style='background:#1a1a2e;border:1px solid #d29922;border-radius:6px;"
    f"padding:8px 12px;font-size:11px;color:#d29922;margin-bottom:16px;'>"
    f"{config.SYNTHETIC_DATA_DISCLAIMER}</div>",
    unsafe_allow_html=True,
)

tab_register, tab_registry, tab_verify, tab_custody = st.tabs(
    ["📤 Register Evidence", "📋 Evidence Registry", "✅ Verify Integrity", "🔗 Chain of Custody"])

# ─── Tab 1: Register ───
with tab_register:
    st.markdown("#### Register New Evidence File")
    st.markdown(
        "<small style='color:#8b949e;'>Files are stored with SHA-256 cryptographic hash. "
        "Original files are <b>never modified</b>.</small>", unsafe_allow_html=True)

    up_file = st.file_uploader("Upload file to register as evidence",
                                type=['csv','xlsx','pdf','txt','json'],
                                help="Supported: CSV, Excel, PDF, TXT, JSON. Max 50MB.")

    if up_file:
        file_bytes = up_file.getvalue()
        size_mb = len(file_bytes) / (1024*1024)
        sha_preview = EvidenceManager.compute_sha256_bytes(file_bytes)

        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #21262d;border-radius:8px;padding:14px;">
          <div style="color:#8b949e;font-size:11px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;">File Information</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
            <div><span style="color:#8b949e;font-size:11px;">Filename:</span>
                 <span style="color:#e6edf3;font-size:12px;margin-left:6px;">{up_file.name}</span></div>
            <div><span style="color:#8b949e;font-size:11px;">Size:</span>
                 <span style="color:#e6edf3;font-size:12px;margin-left:6px;">{size_mb:.3f} MB ({len(file_bytes):,} bytes)</span></div>
          </div>
          <div style="margin-top:10px;">
            <div style="color:#8b949e;font-size:11px;margin-bottom:4px;">SHA-256 Hash (computed):</div>
            <div style="font-family:monospace;font-size:11px;color:#3fb950;background:#0d1117;
                 padding:8px;border-radius:4px;word-break:break-all;">{sha_preview}</div>
          </div>
        </div>""", unsafe_allow_html=True)

        if size_mb > config.MAX_FILE_SIZE_MB:
            st.error(f"File exceeds {config.MAX_FILE_SIZE_MB}MB limit.")
        else:
            if st.button("🔒 Register as Evidence", type="primary"):
                record = em.register_evidence(up_file.name, file_bytes, len(file_bytes))
                st.success(f"✅ Evidence registered: **{record['evidence_id']}**")
                st.markdown(f"""
                <div style="background:#161b22;border:1px solid #3fb950;border-radius:8px;padding:14px;margin-top:8px;">
                  <div style="color:#3fb950;font-weight:700;margin-bottom:8px;">✓ Evidence Registered Successfully</div>
                  <div style="font-size:12px;line-height:2;">
                    <b>Evidence ID:</b> {record['evidence_id']}<br>
                    <b>Filename:</b>    {record['filename']}<br>
                    <b>SHA-256:</b>     <span style="font-family:monospace;font-size:10px;">{record['sha256_hash']}</span><br>
                    <b>Registered:</b>  {str(record['upload_timestamp'])[:19]} UTC<br>
                    <b>File Size:</b>   {record['file_size']:,} bytes
                  </div>
                </div>""", unsafe_allow_html=True)

    # Hash any text inline
    st.markdown("---")
    st.markdown("#### 🧮 Compute SHA-256 of Text / Data")
    test_text = st.text_area("Enter text to hash", value="ScamTrace evidence integrity demo", height=80)
    if st.button("Compute Hash"):
        h = EvidenceManager.compute_sha256_bytes(test_text.encode('utf-8'))
        st.code(h, language=None)

# ─── Tab 2: Registry ───
with tab_registry:
    st.markdown("#### Registered Evidence Files")
    ev_records = em.get_evidence_records()
    if ev_records:
        df = pd.DataFrame(ev_records)
        # Format for display
        display_df = df.copy()
        if 'sha256_hash' in display_df.columns:
            display_df['sha256_hash'] = display_df['sha256_hash'].apply(
                lambda h: f"{str(h)[:20]}…{str(h)[-8:]}" if len(str(h)) > 28 else str(h))
        if 'upload_timestamp' in display_df.columns:
            display_df['upload_timestamp'] = pd.to_datetime(
                display_df['upload_timestamp'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M')
        if 'file_size' in display_df.columns:
            display_df['file_size'] = display_df['file_size'].apply(
                lambda s: f"{int(s):,} B" if pd.notna(s) else '—')

        keep_cols = [c for c in ['evidence_id','filename','sha256_hash','upload_timestamp',
                                  'file_size','processing_status'] if c in display_df.columns]
        st.dataframe(display_df[keep_cols], use_container_width=True, hide_index=True)

        # Full hashes expandable
        with st.expander("🔍 Full SHA-256 Hashes"):
            for ev in ev_records:
                st.markdown(f"**{ev.get('evidence_id','')} — {ev.get('filename','')}:**")
                st.code(ev.get('sha256_hash',''), language=None)
    else:
        st.info("No evidence files registered yet. Register a file in the first tab.")
        st.markdown("""
        <div style="background:#161b22;border:1px dashed #21262d;border-radius:8px;padding:24px;text-align:center;color:#8b949e;">
          <div style="font-size:32px;margin-bottom:8px;">📂</div>
          <div>Upload and register evidence files to build the chain of custody.</div>
        </div>""", unsafe_allow_html=True)

    # Auto-register synthetic data files
    st.markdown("---")
    st.markdown("#### ⚡ Quick Action: Register Synthetic Dataset as Evidence")
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    if st.button("🔒 Register All Synthetic Data Files", use_container_width=False):
        for fname in ['synthetic_transactions.csv', 'synthetic_accounts.csv', 'synthetic_complaints.csv']:
            fpath = os.path.join(data_dir, fname)
            if os.path.exists(fpath):
                with open(fpath, 'rb') as f:
                    fbytes = f.read()
                rec = em.register_evidence(fname, fbytes, len(fbytes))
                st.success(f"✓ {fname} → {rec['evidence_id']} | Hash: {rec['sha256_hash'][:24]}…")
        st.rerun()

# ─── Tab 3: Verify ───
with tab_verify:
    st.markdown("#### Verify Evidence Integrity")
    st.markdown("<small style='color:#8b949e;'>Upload a file and compare its SHA-256 hash against a registered record to confirm it has not been tampered with.</small>", unsafe_allow_html=True)

    ev_records_list = em.get_evidence_records()
    if not ev_records_list:
        st.info("No evidence registered yet. Register files first.")
    else:
        ev_df     = pd.DataFrame(ev_records_list)
        ev_ids    = ev_df['evidence_id'].tolist()
        sel_ev_id = st.selectbox("Select Evidence Record to Verify",
                                  ev_ids,
                                  format_func=lambda x: f"{x} — {ev_df[ev_df['evidence_id']==x]['filename'].values[0]}")

        sel_row = ev_df[ev_df['evidence_id'] == sel_ev_id].iloc[0]
        stored_hash = sel_row['sha256_hash']
        st.markdown(f"**Stored Hash:** `{stored_hash}`")

        verify_file = st.file_uploader("Upload file to verify (should match the registered original)",
                                        key="verify_uploader")
        if verify_file:
            fbytes = verify_file.getvalue()
            if st.button("🔍 Verify Integrity", type="primary"):
                result = em.verify_evidence(sel_ev_id, fbytes, stored_hash)
                if result['verified']:
                    st.markdown(f"""
                    <div style="background:#0d2b1a;border:2px solid #3fb950;border-radius:8px;padding:20px;text-align:center;">
                      <div style="font-size:36px;">✅</div>
                      <div style="color:#3fb950;font-size:20px;font-weight:700;margin-top:8px;">INTEGRITY VERIFIED</div>
                      <div style="color:#e6edf3;font-size:12px;margin-top:8px;">
                        File hash matches the registered evidence record.<br>
                        No tampering detected.
                      </div>
                      <div style="font-family:monospace;font-size:10px;color:#8b949e;margin-top:12px;">
                        {result['computed_hash']}
                      </div>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background:#2b0d0d;border:2px solid #f85149;border-radius:8px;padding:20px;text-align:center;">
                      <div style="font-size:36px;">❌</div>
                      <div style="color:#f85149;font-size:20px;font-weight:700;margin-top:8px;">HASH MISMATCH — POSSIBLE TAMPERING</div>
                      <div style="color:#e6edf3;font-size:12px;margin-top:8px;">
                        The file hash does NOT match the registered record.
                      </div>
                      <div style="margin-top:12px;text-align:left;">
                        <div style="color:#8b949e;font-size:11px;">Stored:   <span style="font-family:monospace;color:#3fb950;">{result['stored_hash']}</span></div>
                        <div style="color:#8b949e;font-size:11px;">Computed: <span style="font-family:monospace;color:#f85149;">{result['computed_hash']}</span></div>
                      </div>
                    </div>""", unsafe_allow_html=True)

# ─── Tab 4: Chain of Custody ───
with tab_custody:
    st.markdown("#### 🔗 Chain of Custody Log")
    st.markdown(
        "<small style='color:#8b949e;'>Complete audit trail of all evidence-related events.</small>",
        unsafe_allow_html=True)

    logs_df = db.get_investigation_logs(limit=100)
    if not logs_df.empty:
        ev_actions = ['EVIDENCE_REGISTERED', 'INTEGRITY_VERIFIED', 'INTEGRITY_FAILED',
                      'LOAD_DEMO_DATA', 'INGEST_FILE']
        custody_logs = logs_df[logs_df['action'].isin(ev_actions)].copy()
        if not custody_logs.empty:
            custody_logs['timestamp'] = pd.to_datetime(custody_logs['timestamp'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
            st.dataframe(custody_logs[['timestamp','action','details','user']],
                         use_container_width=True, hide_index=True,
                         column_config={
                             'timestamp': 'Timestamp (UTC)',
                             'action': 'Action',
                             'details': 'Details',
                             'user': 'User',
                         })
        else:
            st.info("No custody events recorded yet.")
    else:
        st.info("No logs found.")

    # Disclaimer box
    st.markdown("---")
    st.info(
        "🔐 **Evidence Integrity Guarantee:** Original files are stored unchanged in the "
        "`uploads/` directory. SHA-256 hashes are computed at registration time and preserved "
        "in the database. Any subsequent modification of a file will produce a different hash, "
        "detectable via the Verify tab.\n\n"
        "**This system is for demonstration purposes only and uses synthetic data.**"
    )

    # SHA-256 education
    with st.expander("📚 What is SHA-256?"):
        st.markdown("""
**SHA-256 (Secure Hash Algorithm 256-bit)** is a one-way cryptographic hash function that:

- Produces a fixed 64-character hexadecimal string from any input
- Is **deterministic**: the same file always produces the same hash
- Is **collision-resistant**: two different files are astronomically unlikely to share a hash
- Is **tamper-evident**: even a single byte change produces a completely different hash

**How ScamTrace uses it:**
1. When a file is uploaded, its SHA-256 hash is computed and stored in the database
2. The original file is preserved unchanged in `uploads/`
3. At any future point, the file can be re-hashed and compared to the stored value
4. A match confirms the file is identical to the registered original (**integrity verified**)
5. A mismatch signals that the file has been altered (**potential evidence tampering**)

This provides a basic **digital chain of custody** for forensic evidence management.
        """)
