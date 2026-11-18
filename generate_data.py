"""
ScamTrace Synthetic Data Generator
Generates realistic, deterministic synthetic Indian UPI-style transaction data.
ALL DATA IS FICTIONAL. No real persons or accounts are implicated.
"""
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

random.seed(42)
np.random.seed(42)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

INDIAN_FIRST_NAMES = [
    'Aarav', 'Vihan', 'Arjun', 'Reyansh', 'Ayaan', 'Karan', 'Rohit', 'Priya', 'Anjali', 'Neha',
    'Pooja', 'Sunita', 'Amit', 'Suresh', 'Ramesh', 'Dinesh', 'Vikas', 'Deepak', 'Rahul', 'Sanjay',
    'Kavya', 'Meera', 'Riya', 'Tanvi', 'Shruti', 'Aishwarya', 'Divya', 'Sneha', 'Bhavna', 'Rekha',
    'Manish', 'Nitin', 'Prakash', 'Ashok', 'Vinod', 'Sunil', 'Rajesh', 'Pankaj', 'Girish', 'Mahesh',
    'Lakshmi', 'Saraswati', 'Parvati', 'Durga', 'Kamla', 'Usha', 'Sarla', 'Manju', 'Lata', 'Geeta',
    'Sachin', 'Gaurav', 'Vishal', 'Ankur', 'Kunal', 'Nikhil', 'Rishabh', 'Shubham', 'Himanshu', 'Varun',
    'Kritika', 'Swati', 'Pallavi', 'Nidhi', 'Rachna', 'Sonal', 'Vandana', 'Preeti', 'Madhu', 'Asha',
    'Ajay', 'Vijay', 'Sanjiv', 'Harish', 'Mukesh', 'Santosh', 'Hemant', 'Yogesh', 'Arun', 'Naresh',
    'Puja', 'Nisha', 'Shweta', 'Renu', 'Alka', 'Sudha', 'Jyoti', 'Savita', 'Anita', 'Vineeta',
    'Rohini', 'Chandra', 'Sudhir', 'Arvind', 'Rajeev', 'Sudhanshu', 'Akhil', 'Sourabh', 'Dinkar', 'Pranay'
]

INDIAN_LAST_NAMES = [
    'Sharma', 'Verma', 'Gupta', 'Singh', 'Kumar', 'Patel', 'Joshi', 'Rao', 'Reddy', 'Nair',
    'Pillai', 'Menon', 'Iyer', 'Krishnan', 'Mishra', 'Pandey', 'Tripathi', 'Dubey', 'Tiwari', 'Srivastava',
    'Shah', 'Mehta', 'Jain', 'Agarwal', 'Bansal', 'Garg', 'Mittal', 'Khanna', 'Malhotra', 'Kapoor',
    'Saxena', 'Rastogi', 'Chaturvedi', 'Shukla', 'Yadav', 'Chauhan', 'Thakur', 'Rajput', 'Bhatt', 'Negi',
    'Das', 'Bose', 'Ghosh', 'Mukherjee', 'Chatterjee', 'Banerjee', 'Dey', 'Roy', 'Sen', 'Mondal'
]

BANKS = ['SBI', 'HDFC', 'ICICI', 'Axis', 'Kotak', 'PNB', 'Yes Bank', 'Paytm', 'PhonePe', 'GPay']
BANK_UPI = {'SBI': 'oksbi', 'HDFC': 'okhdfc', 'ICICI': 'okicici', 'Axis': 'okhdfcbank',
             'Kotak': 'kotak', 'PNB': 'oksbi', 'Yes Bank': 'yesbank', 'Paytm': 'paytm',
             'PhonePe': 'ybl', 'GPay': 'okaxis'}
STATES = ['Maharashtra', 'Delhi', 'Karnataka', 'Tamil Nadu', 'Uttar Pradesh', 'Gujarat',
          'Rajasthan', 'West Bengal', 'Telangana', 'Andhra Pradesh', 'Madhya Pradesh',
          'Punjab', 'Haryana', 'Bihar', 'Odisha']
TX_TYPES = ['UPI', 'NEFT', 'IMPS', 'UPI', 'UPI', 'UPI']  # UPI more common
DESCRIPTIONS = [
    'UPI payment', 'Food delivery payment', 'Rent transfer', 'Bill payment',
    'Online shopping', 'Recharge', 'Electricity bill', 'Medical payment',
    'Salary advance', 'Loan repayment', 'Investment', 'Gift transfer',
    'Hotel booking', 'Travel booking', 'Subscription payment', 'Grocery payment'
]


def make_name():
    return f"{random.choice(INDIAN_FIRST_NAMES)} {random.choice(INDIAN_LAST_NAMES)}"


def make_upi(name, bank):
    fn = name.split()[0].lower()
    ln = name.split()[-1].lower() if len(name.split()) > 1 else ''
    suffix = BANK_UPI.get(bank, 'oksbi')
    return f"{fn}.{ln}@{suffix}"


def make_phone():
    return f"+91 {random.randint(70000,99999):05d}{random.randint(10000,99999):05d}"


def make_ref():
    return f"UPI/REF/2024{random.randint(100000000, 999999999)}"


def random_date(start, end):
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


# ═══════════════════════════════════════════════════════
# Generate Accounts
# ═══════════════════════════════════════════════════════
print("Generating accounts...")
accounts = []

# Victim accounts
victim_names = ['Priya Sharma', 'Amit Kumar', 'Sunita Verma', 'Rahul Singh', 'Meera Patel']
for i, name in enumerate(victim_names, 1):
    acc_id = f'ACC_V00{i}'
    bank = random.choice(BANKS)
    accounts.append({
        'account_id': acc_id,
        'account_holder': name,
        'account_type': 'SAVINGS',
        'bank_name': bank,
        'account_opening_date': '2020-01-15',
        'risk_status': 'NORMAL',
        'upi_id': make_upi(name, bank),
        'phone_number': make_phone(),
        'state': random.choice(STATES)
    })

# Mule accounts
mule_names = ['Karan Thakur', 'Vikas Yadav', 'Rohit Chauhan', 'Deepak Rajput', 'Sanjay Das',
              'Nitin Ghosh', 'Ajay Mondal', 'Suresh Bose', 'Ramesh Roy', 'Dinesh Sen']
for i, name in enumerate(mule_names, 1):
    acc_id = f'ACC_M{i:03d}'
    bank = random.choice(BANKS)
    accounts.append({
        'account_id': acc_id,
        'account_holder': name,
        'account_type': random.choice(['SAVINGS', 'CURRENT', 'WALLET']),
        'bank_name': bank,
        'account_opening_date': f'2023-{random.randint(1,12):02d}-{random.randint(1,28):02d}',
        'risk_status': 'NORMAL',
        'upi_id': make_upi(name, bank),
        'phone_number': make_phone(),
        'state': random.choice(STATES)
    })

# Legitimate accounts
used_names = set(victim_names + mule_names)
leg_names = []
while len(leg_names) < 105:
    n = make_name()
    if n not in used_names:
        leg_names.append(n)
        used_names.add(n)

for i, name in enumerate(leg_names, 1):
    acc_id = f'ACC_L{i:03d}'
    bank = random.choice(BANKS)
    accounts.append({
        'account_id': acc_id,
        'account_holder': name,
        'account_type': random.choice(['SAVINGS', 'SAVINGS', 'SAVINGS', 'CURRENT', 'WALLET']),
        'bank_name': bank,
        'account_opening_date': f'20{random.randint(15,22)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}',
        'risk_status': 'NORMAL',
        'upi_id': make_upi(name, bank),
        'phone_number': make_phone(),
        'state': random.choice(STATES)
    })

acc_df = pd.DataFrame(accounts)
acc_df.to_csv(os.path.join(DATA_DIR, 'synthetic_accounts.csv'), index=False)
print(f"  ✓ {len(acc_df)} accounts saved")

# ═══════════════════════════════════════════════════════
# Generate Transactions
# ═══════════════════════════════════════════════════════
print("Generating transactions...")
transactions = []

# ─── SCENARIO 1: CMP001 — 4-hop chain via ACC_M007 ───
complaint_txs_1 = [
    ('TXN_S1_001', '2024-02-15 10:00:00', 'ACC_V001', 'ACC_M001', 50000, 'UPI', 'CMP001', 'Fraudulent payment - victim complaint CMP001'),
    ('TXN_S1_002', '2024-02-15 11:30:00', 'ACC_M001', 'ACC_M003', 45000, 'IMPS', 'CMP001', 'Inter-account transfer'),
    ('TXN_S1_003', '2024-02-15 14:00:00', 'ACC_M003', 'ACC_M007', 40000, 'NEFT', 'CMP001', 'Transfer to beneficiary'),
    ('TXN_S1_004', '2024-02-15 17:00:00', 'ACC_M007', 'ACC_L050', 35000, 'UPI', 'CMP001', 'Final withdrawal'),
]

# ─── SCENARIO 2: CMP002 — shares ACC_M007 as common node ───
complaint_txs_2 = [
    ('TXN_S2_001', '2024-03-10 09:00:00', 'ACC_V002', 'ACC_M002', 75000, 'UPI', 'CMP002', 'Fraudulent payment - victim complaint CMP002'),
    ('TXN_S2_002', '2024-03-10 10:00:00', 'ACC_M002', 'ACC_M004', 70000, 'IMPS', 'CMP002', 'Layering transfer'),
    ('TXN_S2_003', '2024-03-10 12:00:00', 'ACC_M004', 'ACC_M007', 65000, 'NEFT', 'CMP002', 'Transfer to consolidation account'),
    ('TXN_S2_004', '2024-03-10 15:00:00', 'ACC_M007', 'ACC_L060', 60000, 'UPI', 'CMP002', 'Final destination'),
]

# ─── SCENARIO 3: CMP003 — split-merge pattern ───
complaint_txs_3 = [
    ('TXN_S3_001', '2024-04-05 08:00:00', 'ACC_V003', 'ACC_M005', 30000, 'UPI', 'CMP003', 'Fraudulent payment - victim complaint CMP003'),
    ('TXN_S3_002', '2024-04-05 09:00:00', 'ACC_M005', 'ACC_M008', 15000, 'UPI', 'CMP003', 'Split transfer A'),
    ('TXN_S3_003', '2024-04-05 09:30:00', 'ACC_M005', 'ACC_M009', 14000, 'UPI', 'CMP003', 'Split transfer B'),
    ('TXN_S3_004', '2024-04-05 11:00:00', 'ACC_M008', 'ACC_M010', 14000, 'IMPS', 'CMP003', 'Merge transfer A'),
    ('TXN_S3_005', '2024-04-05 11:30:00', 'ACC_M009', 'ACC_M010', 13000, 'IMPS', 'CMP003', 'Merge transfer B'),
    ('TXN_S3_006', '2024-04-05 14:00:00', 'ACC_M010', 'ACC_L070', 25000, 'UPI', 'CMP003', 'Final withdrawal'),
]

# ─── SCENARIO 4: CMP004 ───
complaint_txs_4 = [
    ('TXN_S4_001', '2024-05-12 09:00:00', 'ACC_V004', 'ACC_M006', 20000, 'UPI', 'CMP004', 'Fraudulent payment - victim complaint CMP004'),
    ('TXN_S4_002', '2024-05-12 10:30:00', 'ACC_M006', 'ACC_M009', 18000, 'IMPS', 'CMP004', 'Layering'),
    ('TXN_S4_003', '2024-05-12 13:00:00', 'ACC_M009', 'ACC_L090', 16000, 'UPI', 'CMP004', 'Cash out'),
]

# ─── SCENARIO 5: CMP005 — ACC_M001 and ACC_M002 appear again ───
complaint_txs_5 = [
    ('TXN_S5_001', '2024-06-01 10:00:00', 'ACC_V005', 'ACC_M001', 100000, 'NEFT', 'CMP005', 'Large fraud - victim complaint CMP005'),
    ('TXN_S5_002', '2024-06-01 11:00:00', 'ACC_M001', 'ACC_M002', 95000, 'RTGS', 'CMP005', 'Transfer to co-conspirator'),
    ('TXN_S5_003', '2024-06-01 13:00:00', 'ACC_M002', 'ACC_L095', 90000, 'NEFT', 'CMP005', 'Final destination'),
]

for txlist in [complaint_txs_1, complaint_txs_2, complaint_txs_3, complaint_txs_4, complaint_txs_5]:
    for tx in txlist:
        transactions.append({
            'transaction_id': tx[0], 'timestamp': tx[1],
            'sender_account': tx[2], 'receiver_account': tx[3],
            'amount': tx[4], 'transaction_type': tx[5],
            'payment_reference': make_ref(), 'complaint_id': tx[6], 'description': tx[7]
        })

# ─── CIRCULAR PATTERN ───
transactions.append({'transaction_id': 'TXN_CYC_001', 'timestamp': '2024-03-20 10:00:00',
    'sender_account': 'ACC_M003', 'receiver_account': 'ACC_M006', 'amount': 5000, 'transaction_type': 'UPI',
    'payment_reference': make_ref(), 'complaint_id': None, 'description': 'Transfer'})
transactions.append({'transaction_id': 'TXN_CYC_002', 'timestamp': '2024-03-20 15:00:00',
    'sender_account': 'ACC_M006', 'receiver_account': 'ACC_M003', 'amount': 4800, 'transaction_type': 'UPI',
    'payment_reference': make_ref(), 'complaint_id': None, 'description': 'Return transfer'})

# ─── HIGH VELOCITY: 12 incoming transactions to ACC_M001 within 24h ───
hv_senders = [f'ACC_L{i:03d}' for i in range(1, 13)]
base_hv = datetime(2024, 2, 14, 8, 0, 0)
for i, sender in enumerate(hv_senders, 1):
    ts = base_hv + timedelta(hours=i * 1.2)
    transactions.append({
        'transaction_id': f'TXN_HV_{i:03d}', 'timestamp': ts.strftime('%Y-%m-%d %H:%M:%S'),
        'sender_account': sender, 'receiver_account': 'ACC_M001',
        'amount': random.randint(1000, 5000), 'transaction_type': 'UPI',
        'payment_reference': make_ref(), 'complaint_id': None,
        'description': f'Payment from {sender}'
    })

# ─── RAPID WITHDRAWAL: ACC_M002 receives and quickly withdraws ───
transactions += [
    {'transaction_id': 'TXN_RW_001', 'timestamp': '2024-03-09 08:00:00',
     'sender_account': 'ACC_L010', 'receiver_account': 'ACC_M002', 'amount': 20000,
     'transaction_type': 'UPI', 'payment_reference': make_ref(), 'complaint_id': None, 'description': 'Payment'},
    {'transaction_id': 'TXN_RW_002', 'timestamp': '2024-03-09 09:00:00',
     'sender_account': 'ACC_L011', 'receiver_account': 'ACC_M002', 'amount': 15000,
     'transaction_type': 'IMPS', 'payment_reference': make_ref(), 'complaint_id': None, 'description': 'Transfer'},
    {'transaction_id': 'TXN_RW_003', 'timestamp': '2024-03-09 12:00:00',
     'sender_account': 'ACC_M002', 'receiver_account': 'ACC_L080', 'amount': 33000,
     'transaction_type': 'UPI', 'payment_reference': make_ref(), 'complaint_id': None, 'description': 'Withdrawal'},
]

# ─── LEGITIMATE TRANSACTIONS between ACC_L accounts ───
leg_accounts = [f'ACC_L{i:03d}' for i in range(1, 106)]
start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 6, 30)
count = 0
target = 600 - len(transactions)

while count < target:
    sender = random.choice(leg_accounts)
    receiver = random.choice(leg_accounts)
    if sender == receiver:
        continue
    tx_id = f'TXN_L{count+1:04d}'
    ts = random_date(start_date, end_date)
    transactions.append({
        'transaction_id': tx_id,
        'timestamp': ts.strftime('%Y-%m-%d %H:%M:%S'),
        'sender_account': sender, 'receiver_account': receiver,
        'amount': round(random.uniform(100, 25000), 2),
        'transaction_type': random.choice(TX_TYPES),
        'payment_reference': make_ref(),
        'complaint_id': None,
        'description': random.choice(DESCRIPTIONS)
    })
    count += 1

tx_df = pd.DataFrame(transactions)
tx_df = tx_df.drop_duplicates(subset=['transaction_id']).reset_index(drop=True)
tx_df.to_csv(os.path.join(DATA_DIR, 'synthetic_transactions.csv'), index=False)
print(f"  ✓ {len(tx_df)} transactions saved")

# ═══════════════════════════════════════════════════════
# Generate Complaints
# ═══════════════════════════════════════════════════════
print("Generating complaints...")
complaints = [
    {'complaint_id': 'CMP001', 'victim_id': 'ACC_V001', 'reported_amount': 50000,
     'report_date': '2024-02-16', 'originating_account': 'ACC_V001',
     'description': 'Victim reports ₹50,000 transferred to unknown UPI ID after receiving OTP phishing call. Funds traced to ACC_M001.',
     'status': 'UNDER_INVESTIGATION'},
    {'complaint_id': 'CMP002', 'victim_id': 'ACC_V002', 'reported_amount': 75000,
     'report_date': '2024-03-11', 'originating_account': 'ACC_V002',
     'description': 'Victim reports ₹75,000 lost in investment fraud. Transferred to fake trading platform linked to ACC_M002.',
     'status': 'UNDER_INVESTIGATION'},
    {'complaint_id': 'CMP003', 'victim_id': 'ACC_V003', 'reported_amount': 30000,
     'report_date': '2024-04-06', 'originating_account': 'ACC_V003',
     'description': 'Victim reports ₹30,000 sent to impersonator posing as bank official. Amount split across multiple mule accounts.',
     'status': 'OPEN'},
    {'complaint_id': 'CMP004', 'victim_id': 'ACC_V004', 'reported_amount': 20000,
     'report_date': '2024-05-13', 'originating_account': 'ACC_V004',
     'description': 'Victim reports ₹20,000 lost in job fraud. Transferred to fraudulent recruiter account ACC_M006.',
     'status': 'OPEN'},
    {'complaint_id': 'CMP005', 'victim_id': 'ACC_V005', 'reported_amount': 100000,
     'report_date': '2024-06-02', 'originating_account': 'ACC_V005',
     'description': 'Victim reports ₹1,00,000 transferred in KYC update fraud. High-value case connecting to previously identified mule network.',
     'status': 'ESCALATED'},
]
cmp_df = pd.DataFrame(complaints)
cmp_df.to_csv(os.path.join(DATA_DIR, 'synthetic_complaints.csv'), index=False)
print(f"  ✓ {len(cmp_df)} complaints saved")

# ─── Data README ───
readme = """# ScamTrace Synthetic Dataset

**⚠️ ALL DATA IS SYNTHETIC AND FICTIONAL. No real persons, accounts, or transactions are implicated.**

## Files

| File | Rows | Description |
|------|------|-------------|
| synthetic_accounts.csv | 120 | Fictional UPI/bank accounts |
| synthetic_transactions.csv | ~600 | Synthetic UPI/NEFT/IMPS transactions |
| synthetic_complaints.csv | 5 | Fictional victim complaints |

## Key Account Groups
- **ACC_V001-V005**: Victim accounts (starting points for investigation)
- **ACC_M001-M010**: Mule accounts (intermediaries with suspicious patterns)
- **ACC_L001-L105**: Legitimate accounts (normal transaction behavior)

## Investigation Scenarios
- **CMP001**: 4-hop chain V001→M001→M003→M007→L050
- **CMP002**: 4-hop chain V002→M002→M004→M007→L060 (shares M007 with CMP001)
- **CMP003**: Split-merge pattern V003→M005→{M008,M009}→M010→L070
- **CMP004**: 3-hop chain V004→M006→M009→L090
- **CMP005**: V005→M001→M002→L095 (M001 & M002 appear across complaints)

## Special Patterns
- **Circular**: M003↔M006 (cycle detection demo)
- **High velocity**: M001 receives 12 transactions in 24h
- **Rapid withdrawal**: M002 withdraws 94% within 6h
"""
with open(os.path.join(DATA_DIR, 'README_DATA.md'), 'w') as f:
    f.write(readme)

print("\n✅ Synthetic dataset generated successfully!")
print(f"   Location: {DATA_DIR}")
print(f"   Accounts: {len(acc_df)}")
print(f"   Transactions: {len(tx_df)}")
print(f"   Complaints: {len(cmp_df)}")
