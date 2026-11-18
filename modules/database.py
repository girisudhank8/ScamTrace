"""
ScamTrace Database Module - SQLite + SQLAlchemy persistence layer
"""
import os
import sys
import logging
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Text, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session

logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Base(DeclarativeBase):
    pass


class Transaction(Base):
    __tablename__ = 'transactions'
    transaction_id = Column(String, primary_key=True)
    timestamp = Column(DateTime)
    sender_account = Column(String, index=True)
    receiver_account = Column(String, index=True)
    amount = Column(Float)
    transaction_type = Column(String)
    payment_reference = Column(String)
    complaint_id = Column(String, nullable=True)
    description = Column(Text)


class Account(Base):
    __tablename__ = 'accounts'
    account_id = Column(String, primary_key=True)
    account_holder = Column(String)
    account_type = Column(String)
    bank_name = Column(String)
    account_opening_date = Column(String, nullable=True)
    risk_status = Column(String, default='NORMAL')
    upi_id = Column(String)
    phone_number = Column(String)
    state = Column(String)


class Complaint(Base):
    __tablename__ = 'complaints'
    complaint_id = Column(String, primary_key=True)
    victim_id = Column(String)
    reported_amount = Column(Float)
    report_date = Column(String)
    originating_account = Column(String)
    description = Column(Text)
    status = Column(String)


class EvidenceRecord(Base):
    __tablename__ = 'evidence_records'
    evidence_id = Column(String, primary_key=True)
    filename = Column(String)
    sha256_hash = Column(String)
    upload_timestamp = Column(DateTime)
    file_size = Column(Integer)
    processing_status = Column(String)
    original_path = Column(String)


class InvestigationLog(Base):
    __tablename__ = 'investigation_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(String)
    details = Column(Text)
    user = Column(String, default='investigator')


class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            try:
                import config
                db_path = config.DB_PATH
            except ImportError:
                db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scamtrace.db')
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False, connect_args={"check_same_thread": False})
        self.init_db()

    def init_db(self):
        Base.metadata.create_all(self.engine)
        logger.info("Database initialized.")

    def is_data_loaded(self):
        try:
            with Session(self.engine) as session:
                count = session.execute(text("SELECT COUNT(*) FROM transactions")).scalar()
                return count > 0
        except Exception:
            return False

    def load_synthetic_data(self, data_dir=None):
        if data_dir is None:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base, 'data')
        logs = []

        # Accounts
        acc_path = os.path.join(data_dir, 'synthetic_accounts.csv')
        if os.path.exists(acc_path):
            df = pd.read_csv(acc_path)
            with Session(self.engine) as session:
                inserted = 0
                for _, row in df.iterrows():
                    if not session.get(Account, str(row['account_id'])):
                        session.add(Account(
                            account_id=str(row['account_id']),
                            account_holder=str(row.get('account_holder', '')),
                            account_type=str(row.get('account_type', 'SAVINGS')),
                            bank_name=str(row.get('bank_name', '')),
                            account_opening_date=str(row.get('account_opening_date', '')),
                            risk_status=str(row.get('risk_status', 'NORMAL')),
                            upi_id=str(row.get('upi_id', '')),
                            phone_number=str(row.get('phone_number', '')),
                            state=str(row.get('state', ''))
                        ))
                        inserted += 1
                session.commit()
            logs.append(f"✓ Loaded {inserted} accounts")

        # Transactions
        tx_path = os.path.join(data_dir, 'synthetic_transactions.csv')
        if os.path.exists(tx_path):
            df = pd.read_csv(tx_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            with Session(self.engine) as session:
                inserted = 0
                for _, row in df.iterrows():
                    if not session.get(Transaction, str(row['transaction_id'])):
                        session.add(Transaction(
                            transaction_id=str(row['transaction_id']),
                            timestamp=row['timestamp'].to_pydatetime(),
                            sender_account=str(row['sender_account']),
                            receiver_account=str(row['receiver_account']),
                            amount=float(row['amount']),
                            transaction_type=str(row.get('transaction_type', 'UPI')),
                            payment_reference=str(row.get('payment_reference', '')),
                            complaint_id=str(row['complaint_id']) if pd.notna(row.get('complaint_id')) else None,
                            description=str(row.get('description', ''))
                        ))
                        inserted += 1
                session.commit()
            logs.append(f"✓ Loaded {inserted} transactions")

        # Complaints
        cmp_path = os.path.join(data_dir, 'synthetic_complaints.csv')
        if os.path.exists(cmp_path):
            df = pd.read_csv(cmp_path)
            with Session(self.engine) as session:
                inserted = 0
                for _, row in df.iterrows():
                    if not session.get(Complaint, str(row['complaint_id'])):
                        session.add(Complaint(
                            complaint_id=str(row['complaint_id']),
                            victim_id=str(row['victim_id']),
                            reported_amount=float(row['reported_amount']),
                            report_date=str(row['report_date']),
                            originating_account=str(row['originating_account']),
                            description=str(row.get('description', '')),
                            status=str(row.get('status', 'OPEN'))
                        ))
                        inserted += 1
                session.commit()
            logs.append(f"✓ Loaded {inserted} complaints")

        self.log_investigation("LOAD_DEMO_DATA", "Synthetic dataset loaded into database")
        return logs

    def _read_sql(self, query: str) -> pd.DataFrame:
        """pandas 3.x + SQLAlchemy 2.x compatible SQL read using raw sqlite3 DBAPI connection."""
        import sqlite3
        try:
            raw_conn = sqlite3.connect(self.db_path)
            df = pd.read_sql(query, raw_conn)
            raw_conn.close()
            return df
        except Exception as e:
            logger.error(f"SQL read error: {e}")
            return pd.DataFrame()

    def get_transactions(self, filters=None):
        df = self._read_sql("SELECT * FROM transactions")
        if df.empty:
            return df
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        if filters:
            if filters.get('account_id'):
                acc = filters['account_id']
                df = df[(df['sender_account'] == acc) | (df['receiver_account'] == acc)]
            if filters.get('complaint_id'):
                df = df[df['complaint_id'] == filters['complaint_id']]
            if filters.get('min_amount', 0) > 0:
                df = df[df['amount'] >= filters['min_amount']]
            if filters.get('date_range'):
                s, e = filters['date_range']
                df = df[(df['timestamp'] >= pd.Timestamp(s)) & (df['timestamp'] <= pd.Timestamp(e))]
        return df

    def get_accounts(self):
        return self._read_sql("SELECT * FROM accounts")

    def get_complaints(self):
        return self._read_sql("SELECT * FROM complaints")

    def upsert_transaction(self, data: dict):
        with Session(self.engine) as session:
            existing = session.get(Transaction, data['transaction_id'])
            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
            else:
                session.add(Transaction(**data))
            session.commit()

    def log_investigation(self, action: str, details: str, user: str = 'investigator'):
        try:
            with Session(self.engine) as session:
                session.add(InvestigationLog(
                    timestamp=datetime.utcnow(),
                    action=action,
                    details=details,
                    user=user
                ))
                session.commit()
        except Exception as e:
            logger.error(f"Log error: {e}")

    def get_investigation_logs(self, limit=50):
        return self._read_sql(
            f"SELECT * FROM investigation_logs ORDER BY timestamp DESC LIMIT {limit}"
        )

    def insert_evidence(self, evidence_data: dict):
        with Session(self.engine) as session:
            rec = EvidenceRecord(**evidence_data)
            session.add(rec)
            session.commit()

    def get_evidence_records(self):
        return self._read_sql("SELECT * FROM evidence_records")

    def update_account_risk(self, account_id: str, risk_status: str):
        with Session(self.engine) as session:
            acc = session.get(Account, account_id)
            if acc:
                acc.risk_status = risk_status
                session.commit()
