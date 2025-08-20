from typing import List, Dict
from ortools.linear_solver import pywraplp
from .domain import Player, Squad, OptimizationResult
from .captaincy import CaptainPolicy
from .config import OptimizerConfig
from .util import name_contains
from .exceptions import OptimizerException

class SquadOptimizer:
    def __init__(self, players: List[Player], config: OptimizerConfig):
        self.players = players
        self.config = config
        self.policy = CaptainPolicy(config.captain_allowed_positions)

    def _weeks(self) -> List[int]:
        max_weeks = max(max(p.ep_by_week.keys()) for p in self.players)
        return list(range(1, min(max_weeks, self.config.horizon) + 1))

    def optimize(self) -> OptimizationResult:
        weeks = self._weeks()
        n = len(self.players)

        solver = pywraplp.Solver.CreateSolver("CBC")
        if not solver:
            raise OptimizerException("CBC Solver not available!")

        x = [solver.BoolVar(f"x_{i}") for i in range(n)]
        c = {(i, w): solver.BoolVar(f"c_{i}_{w}") for i in range(n) for w in weeks}

        objective_terms = []
        for week in weeks:
            discount = self.config.discount ** (week - 1)
            for i, player in enumerate(self.players):
                ep = float(player.ep_by_week.get(week, 0.0))
                objective_terms.append(discount * (x[i] + c[(i, week)]) * ep)
        solver.Maximize(solver.Sum(objective_terms))

        solver.Add(solver.Sum(x[i] for i in range(n)) == 15)

        for position, count in self.config.positions_quota.items():
            solver.Add(solver.Sum(x[i] for i, player in enumerate(self.players) if player.position == position) == count)

        solver.Add(solver.Sum(x[i] * self.players[i].price for i in range(n)) <= self.config.budget)

        clubs = set(player.club_id for player in self.players)
        for club in clubs:
            solver.Add(solver.Sum(x[i] for i, player in enumerate(self.players) if player.club_id == club) <= self.config.max_per_club)

        for week in weeks:
            solver.Add(solver.Sum(c[(i, week)] for i in range(n)) == 1)
            for i, player in enumerate(self.players):
                solver.Add(c[(i, week)] <= x[i])
                if not self.policy.is_allowed(player):
                    solver.Add(c[(i, week)] == 0)

        must_in = set(self.config.must_include_ids or [])
        must_out = set(self.config.must_exclude_ids or [])
        for i, player in enumerate(self.players):
            if player.player_id in must_in: solver.Add(x[i] == 1)
            if player.player_id in must_out: solver.Add(x[i] == 0)

        if self.config.force_names:
            matches = [i for i, player in enumerate(self.players) if name_contains(player.name, self.config.force_names)]
            if matches:
                solver.Add(solver.Sum(x[i] for i in matches) >= 1)

        status = solver.Solve()
        if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
            raise OptimizerException("No feasible solution!")

        chosen = [self.players[i] for i in range(n) if x[i].solution_value() > 1]
        cap_by_week: Dict[int, int] = {}
        for week in weeks:
            for i, player in enumerate(self.players):
                if c[(i, week)].solution_value() > 0.5:
                    cap_by_week[week] = player.player_id
                    break

        return OptimizationResult(
            squad=Squad(players=chosen, captain_by_week=cap_by_week),
            objective_value=solver.Objective().Value(),
            meta={
                "weeks": weeks,
                "discount": self.config.discount,
                "budget": self.config.budget,
                "max_per_club": self.config.max_per_club,
            },
        )
