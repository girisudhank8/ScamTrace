"""
ScamTrace Graph Analytics Module - NetworkX-based transaction graph analysis
"""
import os
import sys
import logging
import pandas as pd
import numpy as np
import networkx as nx
from collections import deque
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TransactionGraph:
    def __init__(self, transactions_df: pd.DataFrame, accounts_df: pd.DataFrame = None):
        self.transactions_df = transactions_df.copy() if not transactions_df.empty else pd.DataFrame()
        self.accounts_df = accounts_df.copy() if accounts_df is not None and not accounts_df.empty else pd.DataFrame()
        self.G = nx.DiGraph()
        self._node_metrics_cache = None
        self.build_graph()

    def build_graph(self):
        self.G.clear()
        if not self.accounts_df.empty:
            for _, acc in self.accounts_df.iterrows():
                self.G.add_node(
                    str(acc['account_id']),
                    holder=str(acc.get('account_holder', acc['account_id'])),
                    account_type=str(acc.get('account_type', 'UNKNOWN')),
                    bank=str(acc.get('bank_name', '')),
                    risk_status=str(acc.get('risk_status', 'NORMAL')),
                    upi_id=str(acc.get('upi_id', ''))
                )

        if not self.transactions_df.empty:
            for _, tx in self.transactions_df.iterrows():
                s, r = str(tx['sender_account']), str(tx['receiver_account'])
                if s not in self.G:
                    self.G.add_node(s, holder=s, account_type='UNKNOWN', risk_status='NORMAL')
                if r not in self.G:
                    self.G.add_node(r, holder=r, account_type='UNKNOWN', risk_status='NORMAL')

                cid = str(tx.get('complaint_id', '')) if pd.notna(tx.get('complaint_id')) else ''
                if self.G.has_edge(s, r):
                    self.G[s][r]['amount'] += float(tx['amount'])
                    self.G[s][r]['tx_count'] = self.G[s][r].get('tx_count', 1) + 1
                    if cid and not self.G[s][r].get('complaint_id'):
                        self.G[s][r]['complaint_id'] = cid
                else:
                    self.G.add_edge(s, r,
                        amount=float(tx['amount']),
                        timestamp=str(tx.get('timestamp', '')),
                        transaction_id=str(tx['transaction_id']),
                        complaint_id=cid,
                        tx_count=1
                    )
        logger.info(f"Graph: {self.G.number_of_nodes()} nodes, {self.G.number_of_edges()} edges")

    def trace_money_trail(self, source_account: str, max_depth: int = 5,
                           min_amount: float = 0, date_range: Optional[Tuple] = None) -> List[Dict]:
        if source_account not in self.G:
            return []

        txdf = self.transactions_df.copy()
        if not txdf.empty:
            txdf['timestamp'] = pd.to_datetime(txdf['timestamp'])
            if min_amount > 0:
                txdf = txdf[txdf['amount'] >= min_amount]
            if date_range and len(date_range) == 2 and date_range[0] and date_range[1]:
                txdf = txdf[(txdf['timestamp'] >= pd.Timestamp(date_range[0])) &
                             (txdf['timestamp'] <= pd.Timestamp(date_range[1]))]

        paths = []
        queue = deque([(source_account, [source_account], 0, [])])
        seen_paths = set()

        while queue:
            node, path, depth, edges = queue.popleft()
            outgoing = txdf[txdf['sender_account'] == node] if not txdf.empty else pd.DataFrame()

            at_limit = (depth >= max_depth)
            has_outgoing = not outgoing.empty

            if at_limit or not has_outgoing:
                if len(path) > 1:
                    key = tuple(path)
                    if key not in seen_paths:
                        seen_paths.add(key)
                        paths.append({'path': path, 'edges': edges, 'depth': depth})
                continue

            for _, tx in outgoing.iterrows():
                nxt = tx['receiver_account']
                if nxt not in path:
                    new_edge = {
                        'from': node, 'to': nxt,
                        'amount': float(tx['amount']),
                        'timestamp': str(tx['timestamp']),
                        'transaction_id': str(tx['transaction_id']),
                        'complaint_id': str(tx.get('complaint_id', '')) if pd.notna(tx.get('complaint_id')) else ''
                    }
                    queue.append((nxt, path + [nxt], depth + 1, edges + [new_edge]))
                else:
                    # Destination already in path — save partial path so far
                    if len(path) > 1:
                        key = tuple(path)
                        if key not in seen_paths:
                            seen_paths.add(key)
                            paths.append({'path': path, 'edges': edges, 'depth': depth})

        return paths

    def trace_incoming(self, target_account: str, max_depth: int = 5) -> List[Dict]:
        if target_account not in self.G:
            return []
        RG = self.G.reverse(copy=True)
        paths = []
        queue = deque([(target_account, [target_account], 0, [])])
        seen_paths = set()

        while queue:
            node, path, depth, edges = queue.popleft()
            successors = list(RG.successors(node)) if node in RG else []

            if not successors or depth >= max_depth:
                if len(path) > 1:
                    key = tuple(path)
                    if key not in seen_paths:
                        seen_paths.add(key)
                        paths.append({'path': list(reversed(path)), 'edges': edges, 'depth': depth})
                continue

            for nxt in successors:
                if nxt not in path:
                    txdf_filtered = self.transactions_df[
                        (self.transactions_df['sender_account'] == nxt) &
                        (self.transactions_df['receiver_account'] == node)
                    ] if not self.transactions_df.empty else pd.DataFrame()
                    edge_data = {}
                    if not txdf_filtered.empty:
                        row = txdf_filtered.iloc[0]
                        edge_data = {'from': nxt, 'to': node, 'amount': float(row['amount']),
                                      'timestamp': str(row['timestamp']), 'transaction_id': str(row['transaction_id'])}
                    queue.append((nxt, path + [nxt], depth + 1, edges + [edge_data]))

        return paths

    def find_cycles(self) -> List[List[str]]:
        try:
            return [c for c in nx.simple_cycles(self.G) if len(c) >= 2]
        except Exception as e:
            logger.error(f"Cycle detection error: {e}")
            return []

    def find_connected_components(self) -> List[List[str]]:
        return [list(c) for c in nx.connected_components(self.G.to_undirected())]

    def get_node_metrics(self) -> pd.DataFrame:
        if self.G.number_of_nodes() == 0:
            return pd.DataFrame()
        try:
            degree_cent = nx.degree_centrality(self.G)
            in_deg = dict(self.G.in_degree())
            out_deg = dict(self.G.out_degree())
            k = min(100, self.G.number_of_nodes())
            bet_cent = nx.betweenness_centrality(self.G, k=k, normalized=True, seed=42)
            pagerank = nx.pagerank(self.G, max_iter=200, alpha=0.85)

            rows = []
            for node in self.G.nodes():
                d = self.G.nodes[node]
                rows.append({
                    'account_id': node,
                    'holder': d.get('holder', node),
                    'risk_status': d.get('risk_status', 'NORMAL'),
                    'in_degree': in_deg.get(node, 0),
                    'out_degree': out_deg.get(node, 0),
                    'degree_centrality': round(degree_cent.get(node, 0), 4),
                    'betweenness_centrality': round(bet_cent.get(node, 0), 4),
                    'pagerank': round(pagerank.get(node, 0), 6)
                })
            df = pd.DataFrame(rows)
            self._node_metrics_cache = df
            return df
        except Exception as e:
            logger.error(f"Node metrics error: {e}")
            return pd.DataFrame()

    def find_common_accounts(self, complaint_ids: List[str],
                              complaints_df: pd.DataFrame = None,
                              transactions_df: pd.DataFrame = None) -> Dict:
        if transactions_df is None:
            transactions_df = self.transactions_df

        complaint_accounts = {}
        for cid in complaint_ids:
            cmp_txs = transactions_df[transactions_df['complaint_id'] == cid] if not transactions_df.empty else pd.DataFrame()
            if cmp_txs.empty:
                continue
            accs = set(cmp_txs['sender_account'].tolist() + cmp_txs['receiver_account'].tolist())
            # Extend via BFS
            for root in list(accs):
                for p in self.trace_money_trail(root, max_depth=3):
                    for a in p['path']:
                        accs.add(a)
            complaint_accounts[cid] = accs

        all_accounts = set()
        for accs in complaint_accounts.values():
            all_accounts.update(accs)

        shared = {}
        for acc in all_accounts:
            appears = [cid for cid, accs in complaint_accounts.items() if acc in accs]
            if len(appears) >= 2:
                total = transactions_df[
                    (transactions_df['sender_account'] == acc) |
                    (transactions_df['receiver_account'] == acc)
                ]['amount'].sum() if not transactions_df.empty else 0
                shared[acc] = {'account_id': acc, 'appears_in': appears,
                                'complaint_count': len(appears), 'total_amount': float(total)}

        return {'complaint_accounts': {k: list(v) for k, v in complaint_accounts.items()},
                'shared_accounts': shared}

    def detect_communities(self) -> List[List[str]]:
        UG = self.G.to_undirected()
        if UG.number_of_edges() == 0:
            return [[n] for n in UG.nodes()]
        try:
            return [list(c) for c in nx.community.greedy_modularity_communities(UG)]
        except Exception:
            return [list(c) for c in nx.connected_components(UG)]

    def get_subgraph(self, account_ids: List[str]) -> nx.DiGraph:
        return self.G.subgraph([a for a in account_ids if a in self.G]).copy()

    def shortest_path(self, source: str, target: str) -> Optional[List[str]]:
        try:
            return nx.shortest_path(self.G, source=source, target=target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def get_volume_per_account(self) -> pd.DataFrame:
        if self.transactions_df.empty:
            return pd.DataFrame()
        sent = self.transactions_df.groupby('sender_account')['amount'].sum().rename('total_sent')
        received = self.transactions_df.groupby('receiver_account')['amount'].sum().rename('total_received')
        result = pd.concat([sent, received], axis=1).fillna(0).reset_index()
        result.columns = ['account_id', 'total_sent', 'total_received']
        result['net_flow'] = result['total_received'] - result['total_sent']
        return result
