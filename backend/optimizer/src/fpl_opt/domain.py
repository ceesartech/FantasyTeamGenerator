from dataclasses import dataclass
from typing import Dict, List
from positions import Position

@dataclass(frozen=True)
class Player:
    player_id: int
    name: str
    club_id: int
    position: Position      #"GK", "MID"
    price: float
    ep_by_week: Dict[int, float]

@dataclass
class Squad:
    players: List[Player]
    captain_by_week: Dict[int, int]     # gw -> player_id

    def get_total_price(self) -> float:
        return sum(p.price for p in self.players)

    def get_ids(self)-> List[int]:
        return [p.player_id for p in self.players]

@dataclass
class OptimizationResult:
    squad: Squad
    objective_value: float
    meta: dict