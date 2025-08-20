from enum import Enum
class Position(Enum):
    GK = "GK"
    DEF = "DEF"
    MID = "MID"
    FWD = "FWD"

    @classmethod
    def from_any(cls, v: object) -> "Position":
        """
        Accepts Position, string (case-insensitive), or raises ValueError.
        """
        if isinstance(v, Position):
            return v
        if isinstance(v, str):
            s = v.strip().upper()
            try:
                return Position[s] if s in Position.__members__ else Position(s)
            except Exception:
                # fallback if someone passed e.g. "goalkeeper"
                alias = {"GOALKEEPER": "GK", "DEFENDER": "DEF", "MIDFIELDER": "MID", "FORWARD": "FWD"}
                if s in alias:
                    return Position(alias[s])
        raise ValueError(f"Invalid position: {v!r}")