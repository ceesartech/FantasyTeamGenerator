from typing import Dict, List, Optional
from .positions import Position
from .domain import Player

class CaptainPolicy:
    def __init__(self, allowed_positions: Optional[List[Position]] = None):
        self.allowed = set(allowed_positions or [])

    def is_allowed(self, player: Player) -> bool:
        if not self.allowed:
            return True
        return player.position in self.allowed

    def allowed_mask(self, players: List[Player]) -> Dict[int, bool]:
        return {p.player_id: self.is_allowed(p) for p in players}