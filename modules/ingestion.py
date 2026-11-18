"""
ScamTrace Data Ingestion Module
"""
import os
import sys
import io
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Tuple, List, Dict

logger = logging.getLogger(__name__)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REQUIRED_COLUMNS = ['transaction_id', 'timestamp', 'sender_account', 'receiver_account', 'amount']
OPTIONAL_COLUMNS = ['transaction_type', 'payment_reference', 'complaint_id', 'description']
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024

COLUMN_ALIASES = {
    'transaction_id': ['txn_id', 'trans_id', 'id', 'ref_no', 'reference_id'],
    'timestamp': ['date', 'time', 'datetime', 'transaction_date', 'txn_date'],
    'sender_account': ['sender', 'from_account', 'from', 'debit_account', 'payer'],
    'receiver_account': ['receiver', 'to_account', 'to', 'credit_account', 'payee', 'beneficiary'],
    'amount': ['value', 'txn_amount', 'transaction_amount', 'debit', 'credit'],
    'transaction_type': ['type', 'txn_type', 'mode', 'payment_mode'],
    'payment_reference': ['ref', 'utr', 'reference'],
    'complaint_id': ['complaint', 'case_id'],
    'description': ['narration', 'remarks', 'note', 'details']
}


class TransactionIngester:
    def __init__(self):
        self.logs = []
        self.errors = []
        self.warnings = []

    def _log(self, msg: str, level: str = 'info'):
        entry = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        self.logs.append(entry)
        if level == 'error':
            self.errors.append(entry)
        elif level == 'warning':
            self.warnings.append(entry)

    def auto_detect_mapping(self, columns: List[str]) -> Dict[str, str]:
        mapping = {}
        cols_lower = {c.lower().strip(): c for c in columns}
        for std_col, aliases in COLUMN_ALIASES.items():
            if std_col in cols_lower:
                mapping[std_col] = cols_lower[std_col]
                continue
            for alias in aliases:
                if alias in cols_lower:
                    mapping[std_col] = cols_lower[alias]
                    break
        return mapping

    def apply_column_mapping(self, df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
        reverse_map = {v: k for k, v in mapping.items()}
        return df.rename(columns=reverse_map)

    def normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        if 'amount' in df.columns:
            df['amount'] = df['amount'].astype(str).str.replace(r'[₹,\s]', '', regex=True)
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        for col in ['sender_account', 'receiver_account']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.upper()
        for col in OPTIONAL_COLUMNS:
            if col not in df.columns:
                df[col] = None
        if 'transaction_id' in df.columns:
            df['transaction_id'] = df['transaction_id'].astype(str).str.strip()
        return df

    def validate_record(self, row: pd.Series) -> Tuple[bool, List[str]]:
        issues = []
        for col in REQUIRED_COLUMNS:
            if col not in row.index or pd.isna(row[col]) or str(row[col]).strip() in ('', 'nan'):
                issues.append(f"Missing: {col}")
        if 'amount' in row.index:
            try:
                if float(row['amount']) <= 0:
                    issues.append("Amount must be positive")
            except (ValueError, TypeError):
                issues.append(f"Invalid amount: {row.get('amount')}")
        return len(issues) == 0, issues

    def detect_duplicates(self, df: pd.DataFrame, existing_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        dupes = df[df.duplicated(subset=['transaction_id'], keep='first')].copy()
        if existing_df is not None and not existing_df.empty and 'transaction_id' in existing_df.columns:
            overlap = df[df['transaction_id'].isin(existing_df['transaction_id'])].copy()
            dupes = pd.concat([dupes, overlap]).drop_duplicates()
        return dupes

    def _process_dataframe(self, df: pd.DataFrame, column_mapping: Optional[Dict]) -> Tuple[pd.DataFrame, List[str]]:
        if column_mapping:
            df = self.apply_column_mapping(df, column_mapping)
            self._log(f"✓ Applied column mapping")
        else:
            auto_map = self.auto_detect_mapping(df.columns.tolist())
            if auto_map:
                df = self.apply_column_mapping(df, auto_map)
                self._log(f"✓ Auto-detected mapping for: {list(auto_map.keys())}")
        df = self.normalize_dataframe(df)
        self._log("✓ Normalized data types")
        valid_rows, error_count = [], 0
        for idx, row in df.iterrows():
            is_valid, issues = self.validate_record(row)
            if is_valid:
                valid_rows.append(idx)
            else:
                error_count += 1
                if error_count <= 5:
                    self._log(f"⚠ Row {idx}: {'; '.join(issues)}", 'warning')
        if error_count > 5:
            self._log(f"⚠ {error_count - 5} more validation errors", 'warning')
        df_valid = df.loc[valid_rows].reset_index(drop=True)
        self._log(f"✓ Validation: {len(df_valid)} valid, {error_count} invalid rows")
        return df_valid, self.logs

    def ingest_csv_bytes(self, file_bytes: bytes, column_mapping: Optional[Dict] = None) -> Tuple[pd.DataFrame, List[str]]:
        self.logs, self.errors = [], []
        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            self._log("File exceeds 50MB limit", 'error')
            return pd.DataFrame(), self.logs
        try:
            df = pd.read_csv(io.BytesIO(file_bytes))
            self._log(f"✓ Read {len(df)} rows from CSV")
        except Exception as e:
            self._log(f"Failed to read CSV: {e}", 'error')
            return pd.DataFrame(), self.logs
        return self._process_dataframe(df, column_mapping)

    def ingest_excel_bytes(self, file_bytes: bytes, column_mapping: Optional[Dict] = None) -> Tuple[pd.DataFrame, List[str]]:
        self.logs, self.errors = [], []
        try:
            df = pd.read_excel(io.BytesIO(file_bytes))
            self._log(f"✓ Read {len(df)} rows from Excel")
        except Exception as e:
            self._log(f"Failed to read Excel: {e}", 'error')
            return pd.DataFrame(), self.logs
        return self._process_dataframe(df, column_mapping)

    def ingest_pdf_bytes(self, file_bytes: bytes) -> Tuple[pd.DataFrame, List[str]]:
        self.logs, self.errors = [], []
        try:
            import pdfplumber
            dfs = []
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    table = page.extract_table()
                    if table and len(table) > 1:
                        dfs.append(pd.DataFrame(table[1:], columns=table[0]))
            if dfs:
                df = pd.concat(dfs, ignore_index=True)
                self._log(f"✓ Extracted {len(df)} rows from PDF")
                return self._process_dataframe(df, None)
            else:
                self._log("No tables found in PDF", 'warning')
                return pd.DataFrame(), self.logs
        except ImportError:
            self._log("pdfplumber not available. PDF ingestion limited.", 'warning')
            return pd.DataFrame(), self.logs
        except Exception as e:
            self._log(f"PDF extraction error: {e}", 'error')
            return pd.DataFrame(), self.logs

    def get_ingestion_summary(self, df: pd.DataFrame) -> Dict:
        if df.empty:
            return {'total': 0, 'errors': len(self.errors), 'warnings': len(self.warnings)}
        return {
            'total': len(df),
            'unique_senders': df['sender_account'].nunique() if 'sender_account' in df.columns else 0,
            'unique_receivers': df['receiver_account'].nunique() if 'receiver_account' in df.columns else 0,
            'total_amount': df['amount'].sum() if 'amount' in df.columns else 0,
            'errors': len(self.errors),
            'warnings': len(self.warnings)
        }

    def get_sample_template(self) -> str:
        """Return CSV template content."""
        return "transaction_id,timestamp,sender_account,receiver_account,amount,transaction_type,payment_reference,complaint_id,description\nTXN001,2024-01-15 10:30:00,ACC001,ACC002,5000.00,UPI,UPI/REF/2024001,,Sample payment\n"
