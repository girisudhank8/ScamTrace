"""
ScamTrace Evidence Integrity Module - SHA-256 hashing and chain-of-custody.
Original files are NEVER modified.
"""
import hashlib
import os
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class EvidenceManager:
    def __init__(self, upload_dir: str = None, db_manager=None):
        if upload_dir is None:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            upload_dir = os.path.join(base, 'uploads')
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)
        self.db = db_manager

    @staticmethod
    def compute_sha256(file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def compute_sha256_bytes(data_bytes: bytes) -> str:
        return hashlib.sha256(data_bytes).hexdigest()

    def register_evidence(self, filename: str, file_bytes: bytes, file_size: int = None) -> Dict:
        evidence_id = f"EVD-{uuid.uuid4().hex[:8].upper()}"
        sha256_hash = self.compute_sha256_bytes(file_bytes)

        # Store original (never modify)
        safe_name = f"{evidence_id}_{filename}"
        dest = os.path.join(self.upload_dir, safe_name)
        with open(dest, 'wb') as f:
            f.write(file_bytes)

        ts = datetime.utcnow()
        record = {
            'evidence_id': evidence_id,
            'filename': filename,
            'sha256_hash': sha256_hash,
            'upload_timestamp': ts,
            'file_size': file_size or len(file_bytes),
            'processing_status': 'REGISTERED',
            'original_path': dest
        }

        if self.db:
            try:
                self.db.insert_evidence(record)
                self.db.log_investigation('EVIDENCE_REGISTERED',
                    f"File: {filename}, Hash: {sha256_hash[:16]}..., ID: {evidence_id}")
            except Exception as e:
                logger.error(f"DB error: {e}")

        logger.info(f"Evidence registered: {evidence_id}")
        return record

    def verify_evidence(self, evidence_id: str, file_bytes: bytes, stored_hash: str) -> Dict:
        computed = self.compute_sha256_bytes(file_bytes)
        verified = (computed == stored_hash)
        result = {
            'evidence_id': evidence_id, 'verified': verified,
            'computed_hash': computed, 'stored_hash': stored_hash,
            'status': 'VERIFIED' if verified else 'HASH_MISMATCH',
            'timestamp': datetime.utcnow()
        }
        if self.db:
            status = 'INTEGRITY_VERIFIED' if verified else 'INTEGRITY_FAILED'
            self.db.log_investigation(status,
                f"Evidence {evidence_id}: {'Hash matches' if verified else 'HASH MISMATCH'}")
        return result

    def get_evidence_records(self) -> List[Dict]:
        if self.db:
            df = self.db.get_evidence_records()
            return df.to_dict('records') if not df.empty else []
        return []

    def generate_evidence_hash_report(self) -> Dict:
        records = self.get_evidence_records()
        return {
            'generated_at': datetime.utcnow().isoformat(),
            'total_evidence': len(records),
            'records': records
        }
