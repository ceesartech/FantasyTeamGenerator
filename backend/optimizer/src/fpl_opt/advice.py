from typing import Dict, List

class TransferAdvisor:
    @staticmethod
    def suggest(current_ids: List[int], optimal_ids: List[int], free_transfers: int = 1, hit_cost: int = 4) -> Dict:
        current = set(map(int, current_ids or []))
        optimal = set(map(int, optimal_ids))
        outs = sorted(list(current - optimal))
        ins = sorted(list(optimal - current))
        transfers = max(len(ins), len(outs))
        hits = max(0, transfers - int(free_transfers))
        penalty = hits * hit_cost
        return {"out": outs, "in": ins, "hits": hits, "points_penalty": penalty}
