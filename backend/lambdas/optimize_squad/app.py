import os, json, boto3
from backend.optimizer.src.fpl_opt.config import OptimizerConfig
from backend.optimizer.src.fpl_opt.optimizer import SquadOptimizer
from backend.optimizer.src.fpl_opt.advice import TransferAdvisor
from backend.optimizer.src.fpl_opt.data_access import S3ParquetLoader

dynamodb = boto3.resource('dynamodb')
TABLE = os.environ['DDB_TABLE']

def persist(game_week: int, variant: str, result, extra_meta: dict):
    table = dynamodb.Table(TABLE)
    pk, sk = f"GW#{game_week}", f"variant#{variant}"
    item = {
        "pk": pk, "sk": sk,
        "meta": {**result.meta, **extra_meta, "objective": result.objective_value},
        "players": [{
            "player_id": player.player_id, "name": player.name, "club_id": player.club_id,
            "position": player.position.value, "price": player.price
        } for player in result.squad.players],
        "captaincy": result.squad.captain_by_week
    }
    table.put_item(Item=item)
    return item

def lambda_handler(event, context):
    xpts_s3 = event["xpts_s3"]
    game_week = int(event.get("game_week", 4))
    variant = event.get("variant", "user_specified")
    config = OptimizerConfig(
        budget=float(event.get("budget", 100.0)),
        max_per_club=int(event.get("max_per_club", 3)),
        horizon=int(event.get("horizon", 6)),
        discount=float(event.get("discount", 0.92)),
        positions_quota=event.get("positions_quota") or None,
        captain_allowed_positions=event.get("captain_allowed_positions"),
        must_include_ids=event.get("must_include_ids"),
        must_exclude_ids=event.get("must_exclude_ids"),
        force_names=event.get("force_names")
    )
    players = S3ParquetLoader(xpts_s3).load_players()
    optimizer = SquadOptimizer(players, config)
    result = optimizer.optimize()

    advice = None
    if "current_squad_ids" in event:
        advice = TransferAdvisor.suggest(
            current_ids=event.get("current_squad_ids", []),
            optimal_ids=result.squad.get_ids(),
            free_transfers=int(event.get("free_transfers", 1)),
            hit_cost=int(event.get("transfer_cost", 4)),
        )

    if event.get("suggest_only"):
        return {
            "status": "ok",
            "meta": {**result.meta, "variant": variant, "xpts_s3": xpts_s3},
            "players": [{
                "player_id": player.player_id, "name": player.name, "club_id": player.club_id,
                "position": player.position.value, "price": player.price
            } for player in result.squad.players],
            "captaincy": result.squad.captain_by_week,
            "advice": advice
        }

    stored = persist(game_week=game_week, variant=variant, result=result, extra_meta={"xpts_s3": xpts_s3, "variant": variant})
    return {
        "status": "ok",
        "stored": {"pk": stored["pk"], "sk": stored["sk"]},
        "advice": advice,
        "result": stored,
    }
