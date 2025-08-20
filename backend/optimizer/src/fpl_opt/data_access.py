import io
from typing import List, Dict
import pandas as pd
import boto3
from urllib.parse import urlparse
from .domain import Player
from .positions import Position
from .exceptions import DataError

class S3ParquetLoader:
    def __init__(self, s3_uri: str):
        self.s3_uri = s3_uri
        self.s3_client = boto3.client("s3")

    def load_players(self) -> List[Player]:
        bucket, key = self._parse(self.s3_uri)
        obj = self.s3_client.get_object(Bucket=bucket, Key=key)
        df = pd.read_parquet(io.BytesIO(obj["Body"].read()))
        required = {"player_id", "name", "club_id", "position", "price"}
        missing = required - set(df.columns)
        if missing:
            raise DataError(f"Missing columns in parquet: {missing}")

        def to_pos(x) -> Position:
            try: return Position.from_any(x)
            except Exception as e: raise DataError(str(e)) from e

        players: List[Player] = []
        ep_cols = [c for c in df.columns if c.startswith("ep_w")]
        if ep_cols:
            weeks = sorted(int(c.split("ep_w")[1]) for c in ep_cols)
            for _, row in df.iterrows():
                ep_by_week: Dict[int, float] = {week: float(row.get(f"ep_w{week}", 0.0)) for week in weeks}
                players.append(Player(
                    player_id=int(row["player_id"]),
                    name=str(row["name"]),
                    club_id=int(row["club_id"]),
                    position=to_pos(row["position"]),
                    price=float(row["price"]),
                    ep_by_week=ep_by_week,
                ))
        else:
            if "expected_points" not in df.columns:
                raise DataError("No ep_w* or expected_points columns present.")
            for _, row in df.iterrows():
                players.append(Player(
                    player_id=int(row["player_id"]),
                    name=str(row["name"]),
                    club_id=int(row["club_id"]),
                    position=to_pos(row["position"]),
                    price=float(row["price"]),
                    ep_by_week={1: float(row["expected_points"])},
                ))
        return players

    @staticmethod
    def _parse(s3_uri):
        parsed = urlparse(s3_uri)
        return parsed.netloc, parsed.path.lstrip("/")