"""
ScamTrace Fraud Detection Module - Explainable risk scoring and anomaly detection.

DISCLAIMER: Risk scores are heuristic indicators based on behavioral patterns.
They are NOT probabilities of criminal activity and do not establish guilt.
"""
import os
import sys
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import timedelta

logger = logging.getLogger(__name__)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RISK_DISCLAIMER = (
    "⚠️ Risk scores are heuristic behavioral indicators ONLY. "
    "They are NOT evidence of criminal activity and do not establish guilt. "
    "All flagged accounts require human investigation."
)

DEFAULT_WEIGHTS = {
    'velocity': 25, 'ratio': 20, 'withdrawal': 20,
    'counterparties': 15, 'holding_time': 10, 'large_tx': 10,
}

THRESHOLDS = {
    'velocity_high': 10, 'velocity_critical': 20,
    'ratio_suspicious': 0.9,
    'withdrawal_high': 0.7, 'withdrawal_critical': 0.9,
    'counterparties_high': 15, 'holding_hours_low': 2,
}


class FraudDetector:
    def __init__(self):
        self.features_df = None
        self.risk_scores_df = None

    def compute_account_features(self, transactions_df: pd.DataFrame,
                                   accounts_df: pd.DataFrame = None) -> pd.DataFrame:
        if transactions_df.empty:
            return pd.DataFrame()

        df = transactions_df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        all_accounts = set(df['sender_account'].unique()) | set(df['receiver_account'].unique())
        features = []

        for account in all_accounts:
            sent = df[df['sender_account'] == account]
            received = df[df['receiver_account'] == account]
            total_sent = float(sent['amount'].sum())
            total_received = float(received['amount'].sum())
            tx_count = len(sent) + len(received)

            all_tx = pd.concat([sent, received]).sort_values('timestamp')

            # 1. Max tx velocity in 24h window
            max_velocity = 0
            if len(all_tx) > 0:
                for i in range(min(len(all_tx), 50)):
                    t0 = all_tx.iloc[i]['timestamp']
                    w = all_tx[(all_tx['timestamp'] >= t0) & (all_tx['timestamp'] < t0 + timedelta(hours=24))]
                    max_velocity = max(max_velocity, len(w))

            # 2. IO ratio
            if total_received > 0:
                io_ratio = total_sent / total_received
            else:
                io_ratio = 0.0

            # 3. Rapid withdrawal ratio (out within 6h of receiving)
            rapid_out = 0.0
            for _, rx in received.iterrows():
                rx_time = rx['timestamp']
                w_out = sent[(sent['timestamp'] >= rx_time) & (sent['timestamp'] <= rx_time + timedelta(hours=6))]
                rapid_out += float(w_out['amount'].sum())
            rwr = min(rapid_out / total_received, 1.0) if total_received > 0 else 0.0

            # 4. Unique counterparties
            counterparties = set(sent['receiver_account'].unique()) | set(received['sender_account'].unique())
            unique_count = len(counterparties)

            # 5. Average holding time
            hold_times = []
            for _, rx in received.iterrows():
                nxt = sent[sent['timestamp'] > rx['timestamp']]
                if not nxt.empty:
                    h = (nxt['timestamp'].min() - rx['timestamp']).total_seconds() / 3600
                    hold_times.append(h)
            avg_hold = float(np.mean(hold_times)) if hold_times else 999.0

            # 6. Large tx ratio
            all_amounts = pd.concat([sent['amount'], received['amount']])
            large_ratio = float((all_amounts > 50000).mean()) if len(all_amounts) > 0 else 0.0

            # 7. Weekend activity
            weekend_ratio = float(all_tx['timestamp'].dt.day_of_week.isin([5, 6]).mean()) if len(all_tx) > 0 else 0.0

            features.append({
                'account_id': account, 'tx_count': tx_count,
                'total_sent': total_sent, 'total_received': total_received,
                'tx_velocity_24h': max_velocity,
                'incoming_outgoing_ratio': round(io_ratio, 4),
                'rapid_withdrawal_ratio': round(rwr, 4),
                'unique_counterparties': unique_count,
                'avg_holding_time_hours': round(avg_hold, 2),
                'large_tx_ratio': round(large_ratio, 4),
                'weekend_activity_ratio': round(weekend_ratio, 4),
                'incoming_sources': int(received['sender_account'].nunique()),
                'net_flow': total_received - total_sent
            })

        self.features_df = pd.DataFrame(features)
        if accounts_df is not None and not accounts_df.empty:
            merge_cols = [c for c in ['account_id', 'account_holder', 'account_type', 'bank_name', 'risk_status']
                          if c in accounts_df.columns]
            self.features_df = self.features_df.merge(accounts_df[merge_cols], on='account_id', how='left')

        return self.features_df

    def compute_risk_scores(self, features_df: pd.DataFrame, weights: Dict = None) -> pd.DataFrame:
        if features_df.empty:
            return pd.DataFrame()
        if weights is None:
            weights = DEFAULT_WEIGHTS

        results = []
        for _, row in features_df.iterrows():
            score = 0.0
            factors = []

            # Velocity
            vel = row.get('tx_velocity_24h', 0)
            if vel >= THRESHOLDS['velocity_critical']:
                v_s = weights['velocity']
                factors.append(f"Very high transaction velocity: {int(vel)} tx in 24h (critical threshold: {THRESHOLDS['velocity_critical']})")
            elif vel >= THRESHOLDS['velocity_high']:
                v_s = weights['velocity'] * 0.6
                factors.append(f"High transaction velocity: {int(vel)} tx in 24h (threshold: {THRESHOLDS['velocity_high']})")
            elif vel >= 5:
                v_s = weights['velocity'] * 0.3
                factors.append(f"Moderate transaction velocity: {int(vel)} tx in 24h")
            else:
                v_s = 0
            score += v_s

            # IO ratio
            ior = row.get('incoming_outgoing_ratio', 0)
            if ior >= THRESHOLDS['ratio_suspicious']:
                r_s = weights['ratio']
                factors.append(f"High pass-through ratio: {ior:.2f} (forwards {ior*100:.0f}% of received amount)")
            elif ior >= 0.7:
                r_s = weights['ratio'] * 0.5
                factors.append(f"Moderate pass-through ratio: {ior:.2f}")
            else:
                r_s = 0
            score += r_s

            # Rapid withdrawal
            rwr = row.get('rapid_withdrawal_ratio', 0)
            if rwr >= THRESHOLDS['withdrawal_critical']:
                w_s = weights['withdrawal']
                factors.append(f"Critical rapid withdrawal: {rwr*100:.0f}% withdrawn within 6h of receiving")
            elif rwr >= THRESHOLDS['withdrawal_high']:
                w_s = weights['withdrawal'] * 0.6
                factors.append(f"High rapid withdrawal: {rwr*100:.0f}% withdrawn within 6h")
            elif rwr >= 0.5:
                w_s = weights['withdrawal'] * 0.3
                factors.append(f"Moderate rapid withdrawal: {rwr*100:.0f}%")
            else:
                w_s = 0
            score += w_s

            # Counterparties
            cp = row.get('unique_counterparties', 0)
            if cp >= THRESHOLDS['counterparties_high']:
                cp_s = weights['counterparties']
                factors.append(f"Large unique counterparty count: {cp} accounts")
            elif cp >= 8:
                cp_s = weights['counterparties'] * 0.5
                factors.append(f"Moderate counterparties: {cp}")
            else:
                cp_s = 0
            score += cp_s

            # Holding time
            ht = row.get('avg_holding_time_hours', 999)
            if 0 <= ht < THRESHOLDS['holding_hours_low']:
                ht_s = weights['holding_time']
                factors.append(f"Very short holding time: {ht:.1f}h (funds forwarded almost immediately)")
            elif 0 <= ht < 6:
                ht_s = weights['holding_time'] * 0.5
                factors.append(f"Short holding time: {ht:.1f}h before forwarding")
            else:
                ht_s = 0
            score += ht_s

            # Large tx
            ltr = row.get('large_tx_ratio', 0)
            if ltr > 0.5:
                lt_s = weights['large_tx']
                factors.append(f"High proportion of large transactions (>₹50,000): {ltr*100:.0f}%")
            elif ltr > 0.2:
                lt_s = weights['large_tx'] * 0.5
                factors.append(f"Some large transactions: {ltr*100:.0f}% above ₹50,000")
            else:
                lt_s = 0
            score += lt_s

            score = min(100.0, round(score, 1))
            if score >= 90:
                level = 'CRITICAL'
            elif score >= 60:
                level = 'HIGH'
            elif score >= 30:
                level = 'MEDIUM'
            else:
                level = 'LOW'

            if not factors:
                factors = ["No significant anomalous indicators detected"]

            results.append({
                'account_id': row['account_id'],
                'account_holder': row.get('account_holder', row['account_id']),
                'risk_score': score, 'risk_level': level,
                'contributing_factors': '; '.join(factors),
                'velocity_score': round(v_s, 1), 'ratio_score': round(r_s, 1),
                'withdrawal_score': round(w_s, 1), 'counterparty_score': round(cp_s, 1),
                'holding_score': round(ht_s, 1), 'large_tx_score': round(lt_s, 1),
                'tx_count': int(row.get('tx_count', 0)),
                'total_received': float(row.get('total_received', 0)),
                'total_sent': float(row.get('total_sent', 0))
            })

        self.risk_scores_df = pd.DataFrame(results).sort_values('risk_score', ascending=False).reset_index(drop=True)
        return self.risk_scores_df

    def run_isolation_forest(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """Anomaly = statistically unusual, NOT criminal."""
        from sklearn.ensemble import IsolationForest
        if features_df.empty or len(features_df) < 5:
            features_df['if_anomaly'] = 1
            features_df['if_score'] = 0
            features_df['is_anomaly'] = False
            return features_df

        cols = ['tx_velocity_24h', 'incoming_outgoing_ratio', 'rapid_withdrawal_ratio',
                'unique_counterparties', 'large_tx_ratio', 'tx_count']
        avail = [c for c in cols if c in features_df.columns]
        X = features_df[avail].fillna(0)

        iso = IsolationForest(contamination=0.1, random_state=42, n_estimators=100)
        preds = iso.fit_predict(X)
        scores = iso.decision_function(X)

        result = features_df.copy()
        result['if_anomaly'] = preds
        result['if_score'] = scores
        result['is_anomaly'] = (preds == -1)
        return result

    def get_flag_reasons(self, account_id: str, features_df: pd.DataFrame,
                          risk_scores_df: pd.DataFrame) -> List[str]:
        if risk_scores_df is not None and not risk_scores_df.empty:
            row = risk_scores_df[risk_scores_df['account_id'] == account_id]
            if not row.empty:
                factors = row.iloc[0].get('contributing_factors', '')
                if factors:
                    return [f.strip() for f in str(factors).split(';') if f.strip()]
        return ["Insufficient data for detailed analysis"]

    def flag_mule_accounts(self, risk_scores_df: pd.DataFrame, threshold: float = 60) -> pd.DataFrame:
        if risk_scores_df.empty:
            return pd.DataFrame()
        return risk_scores_df[risk_scores_df['risk_score'] >= threshold].copy()
