"""
ScamTrace Preprocessing Module
"""
import pandas as pd
import numpy as np
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


def normalize_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    return df


def clean_amounts(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if 'amount' in df.columns and df['amount'].dtype == object:
        df['amount'] = df['amount'].astype(str).str.replace(r'[₹,\s]', '', regex=True)
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    return df


def standardize_account_ids(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ['sender_account', 'receiver_account', 'account_id']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
    return df


def compute_transaction_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    df['hour_of_day'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    df['amount_zscore'] = df.groupby('sender_account')['amount'].transform(
        lambda x: (x - x.mean()) / x.std() if len(x) > 1 and x.std() > 0 else 0
    )
    df['receiver_incoming_count'] = df.groupby('receiver_account')['transaction_id'].transform('count')
    return df


def merge_with_accounts(tx_df: pd.DataFrame, acc_df: pd.DataFrame) -> pd.DataFrame:
    if acc_df.empty:
        return tx_df
    sender_info = acc_df[['account_id', 'account_holder', 'bank_name', 'risk_status']].copy()
    sender_info.columns = ['sender_account', 'sender_name', 'sender_bank', 'sender_risk']
    receiver_info = acc_df[['account_id', 'account_holder', 'bank_name', 'risk_status']].copy()
    receiver_info.columns = ['receiver_account', 'receiver_name', 'receiver_bank', 'receiver_risk']
    result = tx_df.merge(sender_info, on='sender_account', how='left')
    result = result.merge(receiver_info, on='receiver_account', how='left')
    return result
