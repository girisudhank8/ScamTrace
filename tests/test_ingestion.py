"""
Tests for data ingestion module.
"""
import os, sys, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
import pandas as pd
from modules.ingestion import TransactionIngester

VALID_CSV = b"""transaction_id,timestamp,sender_account,receiver_account,amount,transaction_type,payment_reference,complaint_id,description
TXN001,2024-01-15 10:30:00,ACC001,ACC002,5000.00,UPI,REF001,,Food payment
TXN002,2024-01-16 11:00:00,ACC003,ACC004,15000.50,NEFT,REF002,CMP001,Rent transfer
TXN003,2024-01-17 09:00:00,ACC005,ACC006,250.00,IMPS,REF003,,Recharge
"""

ALIASED_CSV = b"""txn_id,date,sender,receiver,value,type
TX001,2024-02-01 08:00:00,ACCA,ACCB,1000,UPI
TX002,2024-02-02 09:00:00,ACCC,ACCD,2500,NEFT
"""

INVALID_CSV = b"""transaction_id,timestamp,sender_account,receiver_account,amount
,2024-01-01 10:00:00,ACC001,ACC002,5000
TXN_OK,2024-01-01 11:00:00,ACC003,ACC004,-100
TXN_GOOD,2024-01-01 12:00:00,ACC005,ACC006,8000
"""

DUPLICATE_CSV = b"""transaction_id,timestamp,sender_account,receiver_account,amount,transaction_type,payment_reference,complaint_id,description
TXN001,2024-01-15 10:30:00,ACC001,ACC002,5000.00,UPI,REF001,,Dup test
TXN001,2024-01-15 10:30:00,ACC001,ACC002,5000.00,UPI,REF001,,Dup test
TXN002,2024-01-16 11:00:00,ACC003,ACC004,15000.50,NEFT,REF002,,Normal
"""


@pytest.fixture
def ingester():
    return TransactionIngester()


# ─── Tests ───

def test_ingest_valid_csv(ingester):
    df, logs = ingester.ingest_csv_bytes(VALID_CSV)
    assert not df.empty
    assert len(df) == 3
    assert 'transaction_id' in df.columns
    assert 'amount' in df.columns


def test_ingest_csv_amounts_float(ingester):
    df, _ = ingester.ingest_csv_bytes(VALID_CSV)
    assert df['amount'].dtype in [float, 'float64']
    assert float(df[df['transaction_id']=='TXN001']['amount'].values[0]) == 5000.0


def test_ingest_csv_timestamps_parsed(ingester):
    df, _ = ingester.ingest_csv_bytes(VALID_CSV)
    assert pd.api.types.is_datetime64_any_dtype(df['timestamp'])


def test_ingest_csv_account_ids_uppercase(ingester):
    df, _ = ingester.ingest_csv_bytes(VALID_CSV)
    for col in ['sender_account', 'receiver_account']:
        for val in df[col]:
            assert val == val.upper(), f"Account ID not uppercase: {val}"


def test_auto_detect_mapping(ingester):
    df_raw = pd.read_csv(io.BytesIO(ALIASED_CSV))
    mapping = ingester.auto_detect_mapping(df_raw.columns.tolist())
    assert 'transaction_id' in mapping  # txn_id -> transaction_id
    assert 'timestamp' in mapping       # date -> timestamp
    assert 'sender_account' in mapping  # sender -> sender_account
    assert 'amount' in mapping          # value -> amount


def test_ingest_with_aliased_columns(ingester):
    df, logs = ingester.ingest_csv_bytes(ALIASED_CSV)
    assert not df.empty
    assert 'sender_account' in df.columns
    assert 'receiver_account' in df.columns
    assert 'amount' in df.columns


def test_invalid_rows_filtered(ingester):
    df, logs = ingester.ingest_csv_bytes(INVALID_CSV)
    # Row with missing transaction_id and row with negative amount should be filtered
    assert len(df) >= 1  # TXN_GOOD should pass
    if not df.empty:
        assert all(df['amount'] > 0)


def test_duplicate_detection(ingester):
    df, _ = ingester.ingest_csv_bytes(DUPLICATE_CSV)
    dupes = ingester.detect_duplicates(df)
    assert len(dupes) >= 1  # TXN001 appears twice


def test_duplicate_against_existing(ingester):
    df, _ = ingester.ingest_csv_bytes(VALID_CSV)
    existing = pd.DataFrame({'transaction_id': ['TXN001', 'TXN999']})
    dupes = ingester.detect_duplicates(df, existing)
    assert any(dupes['transaction_id'] == 'TXN001')


def test_ingestion_logs_populated(ingester):
    _, logs = ingester.ingest_csv_bytes(VALID_CSV)
    assert len(logs) > 0
    assert any('✓' in l for l in logs)


def test_file_size_rejection(ingester):
    # Create a fake >50MB file
    large_data = b'x' * (51 * 1024 * 1024)
    df, logs = ingester.ingest_csv_bytes(large_data)
    assert df.empty
    assert any('50MB' in l or 'limit' in l for l in logs)


def test_validate_record_valid(ingester):
    row = pd.Series({
        'transaction_id': 'TXN001',
        'timestamp': pd.Timestamp('2024-01-01'),
        'sender_account': 'ACC001',
        'receiver_account': 'ACC002',
        'amount': 5000.0,
    })
    is_valid, issues = ingester.validate_record(row)
    assert is_valid
    assert len(issues) == 0


def test_validate_record_missing_field(ingester):
    row = pd.Series({
        'transaction_id': 'TXN001',
        'timestamp': pd.Timestamp('2024-01-01'),
        'sender_account': 'ACC001',
        'receiver_account': 'ACC002',
        # amount missing
    })
    is_valid, issues = ingester.validate_record(row)
    assert not is_valid
    assert len(issues) > 0


def test_validate_record_negative_amount(ingester):
    row = pd.Series({
        'transaction_id': 'TXN001',
        'timestamp': pd.Timestamp('2024-01-01'),
        'sender_account': 'ACC001',
        'receiver_account': 'ACC002',
        'amount': -100.0,
    })
    is_valid, issues = ingester.validate_record(row)
    assert not is_valid


def test_ingestion_summary(ingester):
    df, _ = ingester.ingest_csv_bytes(VALID_CSV)
    summary = ingester.get_ingestion_summary(df)
    assert summary['total'] == 3
    assert summary['unique_senders'] <= 3
    assert summary['total_amount'] > 0


def test_sample_template_format(ingester):
    template = ingester.get_sample_template()
    assert 'transaction_id' in template
    assert 'sender_account' in template
    assert 'amount' in template
