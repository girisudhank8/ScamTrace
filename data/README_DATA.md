# ScamTrace Synthetic Dataset

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
