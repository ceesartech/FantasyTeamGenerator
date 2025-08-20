from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict
from .positions import Position

class OptimizerConfig(BaseModel):
    budget: float = Field(default=100.0, ge=50.0, le=120.0)
    max_per_club: int = Field(default=3, ge=1, le=4)
    horizon: int = Field(default=6, ge=1, le=8)
    discount: float = Field(default=0.92, ge=0.0, le=1.0)
    positions_quota: Dict[Position, int] = Field(
        default_factory=lambda: {Position.GK: 2, Position.DEF: 5, Position.MID: 5, Position.FWD: 3}
    )
    # Optional Captaincy restrictions
    captain_allowed_positions: Optional[List[Position]] = None   # example of ["MID", "FWD"] to only allow attackers be captain for the week
    # User Constraints:
    must_include_ids: Optional[List[int]] = None
    must_exclude_ids: Optional[List[int]] = None
    force_names: Optional[List[str]] = None  # Eg, build team around ["Haaland"] or ["Sallah"] or ["Haaland", "Sallah"]

    @field_validator("captain_allowed_positions", mode="before")
    @classmethod
    def _coerce_caps(cls, v):
        if v is None: return v
        return [Position.from_any(x) for x in v]

    @field_validator("positions_quota", mode="before")
    @classmethod
    def _coerce_quota(cls, v):
        if v is None: return v
        if isinstance(v, dict):
            out = {}
            for k, val in v.items():
                out[Position.from_any(k)] = int(val)
            return out
        return v
