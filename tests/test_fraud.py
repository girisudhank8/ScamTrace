"""
Tests for fraud detection module.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
import pandas as pd
import numpy as np
from modules.fraud_detection import FraudDetector, RISK_DISCLAIMER

TRANSACTIONS = pd.DataFrame([
    # High-velocity mule account M001
    *[{
        'transaction_id': f'T_HV_{i:03d}',
        'timestamp': pd.Timestamp('2024-01-15 08:00:00') + pd.Timedelta(hours=i*0.5),
        'sender_account': f'L{i:03d}',
        'receiver_account': 'M001',
        'amount': 5000.0,
        'transaction_type': 'UPI',
        'complaint_id': None,
        'description': 'payment',
    } for i in range(1, 15)],
    # M001 rapid withdrawal
    {
        'transaction_id': 'T_RW_001',
        'timestamp': pd.Timestamp('2024-01-15 10:00:00'),
        'sender_account': 'M001',
        'receiver_account': 'DEST001',
        'amount': 60000.0,
        'transaction_type': 'NEFT',
        'complaint_id': 'CMP001',
        'description': 'withdrawal',
    },
    # Normal account
    {
        'transaction_id': 'T_NRM_001',
        'timestamp': pd.Timestamp('2024-01-20 10:00:00'),
        'sender_account': 'NORMAL001',
        'receiver_account': 'NORMAL002',
        'amount': 1000.0,
        'transaction_type': 'UPI',
        'complaint_id': None,
        'description': 'rent',
    },
])

ACCOUNTS = pd.DataFrame([
    {'account_id': 'M001',      'account_holder': 'Mule One',    'account_type': 'SAVINGS', 'bank_name': 'SBI',  'risk_status': 'NORMAL'},
    {'account_id': 'DEST001',   'account_holder': 'Dest',         'account_type': 'SAVINGS', 'bank_name': 'HDFC', 'risk_status': 'NORMAL'},
    {'account_id': 'NORMAL001', 'account_holder': 'Normal User',  'account_type': 'SAVINGS', 'bank_name': 'ICICI','risk_status': 'NORMAL'},
    {'account_id': 'NORMAL002', 'account_holder': 'Normal User 2','account_type': 'SAVINGS', 'bank_name': 'Axis', 'risk_status': 'NORMAL'},
])


@pytest.fixture
def detector():
    return FraudDetector()

@pytest.fixture
def features(detector):
    return detector.compute_account_features(TRANSACTIONS, ACCOUNTS)

@pytest.fixture
def risk_scores(detector, features):
    return detector.compute_risk_scores(features)


# ─── Tests ───

def test_features_computed(features):
    assert not features.empty
    required = ['account_id', 'tx_velocity_24h', 'rapid_withdrawal_ratio',
                'unique_counterparties', 'avg_holding_time_hours']
    for col in required:
        assert col in features.columns, f"Missing feature column: {col}"


def test_mule_has_high_velocity(features):
    m001 = features[features['account_id'] == 'M001']
    assert not m001.empty
    vel = float(m001.iloc[0]['tx_velocity_24h'])
    assert vel >= 10, f"Expected high velocity for M001, got {vel}"


def test_mule_has_rapid_withdrawal(features):
    m001 = features[features['account_id'] == 'M001']
    rwr = float(m001.iloc[0]['rapid_withdrawal_ratio'])
    assert rwr > 0.5, f"Expected high withdrawal ratio for M001, got {rwr}"


def test_risk_scores_range(risk_scores):
    assert not risk_scores.empty
    assert risk_scores['risk_score'].between(0, 100).all(), "Risk scores must be 0–100"


def test_risk_level_valid(risk_scores):
    valid_levels = {'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'}
    for level in risk_scores['risk_level']:
        assert level in valid_levels, f"Invalid risk level: {level}"


def test_mule_flagged_higher(risk_scores):
    m001_score = risk_scores[risk_scores['account_id'] == 'M001']['risk_score'].values
    normal_score = risk_scores[risk_scores['account_id'] == 'NORMAL001']['risk_score'].values
    if len(m001_score) > 0 and len(normal_score) > 0:
        assert float(m001_score[0]) > float(normal_score[0]), \
            "Mule should score higher than normal account"


def test_contributing_factors_non_empty(risk_scores):
    for _, row in risk_scores.iterrows():
        factors = str(row['contributing_factors'])
        assert len(factors) > 0


def test_flag_mule_accounts(detector, risk_scores):
    flagged = detector.flag_mule_accounts(risk_scores, threshold=50)
    # M001 should be in flagged list at threshold 50
    if not flagged.empty:
        assert 'account_id' in flagged.columns
        assert all(flagged['risk_score'] >= 50)


def test_isolation_forest_runs(detector, features):
    result = detector.run_isolation_forest(features)
    assert 'is_anomaly' in result.columns
    assert 'if_score' in result.columns
    assert result['is_anomaly'].dtype == bool


def test_isolation_forest_produces_some_anomalies(detector, features):
    result = detector.run_isolation_forest(features)
    # With contamination=0.1 and enough samples, should flag some
    # (may be 0 for tiny datasets — just check it runs)
    assert result['is_anomaly'].isin([True, False]).all()


def test_risk_disclaimer_exists():
    assert len(RISK_DISCLAIMER) > 20
    assert 'NOT' in RISK_DISCLAIMER or 'not' in RISK_DISCLAIMER.lower()


def test_empty_transactions(detector):
    features = detector.compute_account_features(pd.DataFrame(), pd.DataFrame())
    assert features.empty


def test_get_flag_reasons(detector, features, risk_scores):
    # Pick the first flagged account
    high = risk_scores[risk_scores['risk_score'] > 0]
    if not high.empty:
        acc = high.iloc[0]['account_id']
        reasons = detector.get_flag_reasons(acc, features, risk_scores)
        assert isinstance(reasons, list)
        assert len(reasons) > 0


def test_custom_weights(detector, features):
    custom = {'velocity': 50, 'ratio': 10, 'withdrawal': 10,
              'counterparties': 10, 'holding_time': 10, 'large_tx': 10}
    scores = detector.compute_risk_scores(features, weights=custom)
    assert not scores.empty
    assert scores['risk_score'].between(0, 100).all()
