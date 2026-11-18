"""
Tests for evidence integrity module.
"""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from modules.evidence import EvidenceManager


@pytest.fixture
def em(tmp_path):
    return EvidenceManager(upload_dir=str(tmp_path), db_manager=None)


# ─── SHA-256 tests ───

def test_sha256_bytes_known():
    """SHA-256 of empty bytes is well-known."""
    result = EvidenceManager.compute_sha256_bytes(b'')
    assert result == 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'


def test_sha256_bytes_hello():
    h = EvidenceManager.compute_sha256_bytes(b'hello')
    assert h == '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'


def test_sha256_bytes_length():
    h = EvidenceManager.compute_sha256_bytes(b'ScamTrace test data')
    assert len(h) == 64


def test_sha256_bytes_hex_chars():
    h = EvidenceManager.compute_sha256_bytes(b'test')
    assert all(c in '0123456789abcdef' for c in h)


def test_sha256_deterministic():
    data = b'deterministic input 12345'
    h1 = EvidenceManager.compute_sha256_bytes(data)
    h2 = EvidenceManager.compute_sha256_bytes(data)
    assert h1 == h2


def test_sha256_different_inputs_different_hashes():
    h1 = EvidenceManager.compute_sha256_bytes(b'input one')
    h2 = EvidenceManager.compute_sha256_bytes(b'input two')
    assert h1 != h2


def test_sha256_file(tmp_path):
    fpath = tmp_path / 'test.txt'
    fpath.write_bytes(b'file content for hashing')
    computed = EvidenceManager.compute_sha256(str(fpath))
    expected = EvidenceManager.compute_sha256_bytes(b'file content for hashing')
    assert computed == expected


# ─── Register / verify tests ───

def test_register_evidence(em, tmp_path):
    data = b'test evidence file content'
    record = em.register_evidence('test.csv', data, len(data))
    assert record['evidence_id'].startswith('EVD-')
    assert record['sha256_hash'] == EvidenceManager.compute_sha256_bytes(data)
    assert record['filename'] == 'test.csv'
    assert record['file_size'] == len(data)
    assert record['processing_status'] == 'REGISTERED'


def test_register_evidence_stores_file(em, tmp_path):
    data = b'persistent file content'
    record = em.register_evidence('persist.csv', data, len(data))
    # File should exist in upload dir
    assert os.path.exists(record['original_path'])
    with open(record['original_path'], 'rb') as f:
        stored = f.read()
    assert stored == data  # Original unchanged


def test_verify_evidence_correct(em):
    data = b'correct file content'
    record = em.register_evidence('correct.csv', data, len(data))
    result = em.verify_evidence(record['evidence_id'], data, record['sha256_hash'])
    assert result['verified'] is True
    assert result['status'] == 'VERIFIED'


def test_verify_evidence_tampered(em):
    data = b'original content'
    record = em.register_evidence('tampered.csv', data, len(data))
    tampered = b'modified content!!'
    result = em.verify_evidence(record['evidence_id'], tampered, record['sha256_hash'])
    assert result['verified'] is False
    assert result['status'] == 'HASH_MISMATCH'
    assert result['computed_hash'] != result['stored_hash']


def test_verify_evidence_hashes_returned(em):
    data = b'hash comparison test'
    record = em.register_evidence('hash_test.csv', data, len(data))
    result = em.verify_evidence(record['evidence_id'], data, record['sha256_hash'])
    assert 'computed_hash' in result
    assert 'stored_hash' in result
    assert len(result['computed_hash']) == 64
    assert len(result['stored_hash']) == 64


def test_hash_report_no_db(em):
    report = em.generate_evidence_hash_report()
    assert 'generated_at' in report
    assert 'total_evidence' in report
    assert 'records' in report
    assert isinstance(report['records'], list)


def test_evidence_id_unique(em):
    ids = set()
    for i in range(5):
        rec = em.register_evidence(f'file_{i}.csv', f'content {i}'.encode(), 10)
        ids.add(rec['evidence_id'])
    assert len(ids) == 5  # All unique
