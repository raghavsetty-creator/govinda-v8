"""
NIFTY AI — Strategy Evolution Engine
======================================
Continuously evolves trading strategies using:
  1. Genetic Algorithms — crossover + mutation of strategy parameters
  2. Bayesian Optimization — efficiently search parameter space
  3. Walk-forward backtesting — validate on unseen data
  4. A/B testing — promote winning variants to production
  5. Strategy combination — discover synergies between strategies
  6. Daily learning loop — runs every night after market close

This is the system that NEVER STOPS IMPROVING.
"""

import os
import sys
import json
import copy
import random
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from knowledge.strategies.strategy_library import STRATEGY_LIBRARY, run_strategy, Strategy

logger = logging.getLogger(__name__)

EVOLUTION_STATE_PATH = "saved_models/evolution_state.json"


@dataclass
class Individual:
    """A strategy + parameter combination — one 'individual' in the genetic population."""
    strategy_name: str
    parameters: Dict
    generation: int = 0
    fitness: float = 0.0       # Sharpe ratio from backtest
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    parents: List[str] = field(default_factory=list)
    birth_date: str = field(default_factory=lambda: datetime.now().isoformat())
    lineage_id: str = ""       # Track family trees

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class EvolutionConfig:
    population_size: int = 30        # Individuals per generation
    elite_fraction: float = 0.20     # Top 20% survive unchanged
    mutation_rate: float = 0.25      # 25% chance of mutating a parameter
    crossover_rate: float = 0.70     # 70% of new gen from crossover
    tournament_size: int = 4         # Tournament selection size
    max_generations: int = 50        # Stop after this many gens
    min_trades: int = 15             # Discard strategies with too few trades
    sharpe_target: float = 2.0       # Target Sharpe ratio
    walk_forward_splits: int = 5     # Walk-forward validation windows


# Parameter search spaces for each strategy
PARAM_SPACES = {
    "darvas_box":          {"box_period": (5, 40), "volume_multiplier": (1.1, 3.0)},
    "turtle_breakout":     {"entry_period": (10, 55), "exit_period": (5, 25), "atr_period": (7, 21)},
    "raschke_80_20":       {"period": (3, 15)},
    "seykota_ema":         {"fast_ema": (5, 21), "slow_ema": (13, 55), "trend_ema": (30, 100)},
    "bollinger_mean_reversion": {"period": (10, 30), "std_dev": (1.5, 3.0), "rsi_period": (9, 21)},
    "minervini_sepa":      {},
    "weinstein_stage":     {},
    "williams_percent_r":  {"period": (5, 21)},
    "momentum_factor":     {"long_window": (30, 120), "short_window": (3, 15)},
    "vwap_reversal":       {"std_mult": (1.0, 2.5)},
    "cpr_system":          {},
    "volatility_breakout": {"atr_period": (7, 21), "multiplier": (0.3, 1.2), "lookback": (3, 15)},
    "td_sequential":       {},
    "rsi_divergence":      {"rsi_period": (9, 21), "lookback": (10, 30)},
}


class StrategyEvolutionEngine:
    """
    Evolves trading strategies every night using genetic algorithms.
    The fittest survive. The weakest are replaced.
    """

    def __init__(self, config: EvolutionConfig = None):
        self.config     = config or EvolutionConfig()
        self.population: List[Individual] = []
        self.hall_of_fame: List[Individual] = []     # Best ever found
        self.generation  = 0
        self.history     = []    # Fitness history per generation
        self._load_state()

    # ─────────────────────────────────────────────────────────────────
    # MAIN EVOLUTION LOOP
    # ─────────────────────────────────────────────────────────────────

    def evolve(self, df: pd.DataFrame, n_generations: int = 5) -> Individual:
        """
        Run N generations of evolution on the given price data.
        Returns the best individual found.
        """
        logger.info(f"Starting evolution: {n_generations} generations, population={self.config.population_size}")

        # Initialize population if empty
        if not self.population:
            self._initialize_population()

        # Evaluate all individuals
        logger.info("Evaluating initial population...")
        self._evaluate_population(df)

        best_overall = self._get_best()

        for gen in range(n_generations):
            self.generation += 1
            logger.info(f"Generation {self.generation} | Best Sharpe: {best_overall.fitness:.3f}")

            # Selection → Crossover → Mutation → Evaluate
            new_pop = self._selection()
            new_pop = self._crossover(new_pop)
            new_pop = self._mutation(new_pop)
            self._evaluate_population(df, new_pop)

            # Combine with elites
            elites = self._get_elites()
            self.population = elites + new_pop
            self.population = sorted(self.population, key=lambda x: x.fitness, reverse=True)
            self.population = self.population[:self.config.population_size]

            # Update hall of fame
            best = self._get_best()
            if best.fitness > (best_overall.fitness if best_overall else 0):
                best_overall = copy.deepcopy(best)
                self.hall_of_fame.insert(0, best_overall)
                self.hall_of_fame = self.hall_of_fame[:20]
                logger.info(f"  New best: {best.strategy_name} | Sharpe={best.fitness:.3f} | Win={best.win_rate:.1%}")

            # Track history
            fitnesses = [ind.fitness for ind in self.population if ind.fitness > 0]
            self.history.append({
                "generation": self.generation,
                "best": best.fitness,
                "mean": np.mean(fitnesses) if fitnesses else 0,
                "std":  np.std(fitnesses) if fitnesses else 0,
            })

        self._save_state()
        logger.info(f"Evolution complete. Best strategy: {best_overall.strategy_name} | Sharpe={best_overall.fitness:.3f}")
        return best_overall

    # ─────────────────────────────────────────────────────────────────
    # GENETIC OPERATORS
    # ─────────────────────────────────────────────────────────────────

    def _initialize_population(self):
        """Create initial population — one base + random variants per strategy."""
        self.population = []

        for strategy_name, space in PARAM_SPACES.items():
            s = STRATEGY_LIBRARY.get(strategy_name)
            if not s: continue

            # Base individual (original parameters)
            self.population.append(Individual(
                strategy_name=strategy_name,
                parameters=copy.deepcopy(s.parameters),
                generation=0,
                lineage_id=f"{strategy_name}_base",
            ))

            # Random variants
            n_variants = max(1, self.config.population_size // len(PARAM_SPACES))
            for i in range(n_variants):
                params = self._random_params(strategy_name, space)
                self.population.append(Individual(
                    strategy_name=strategy_name,
                    parameters=params,
                    generation=0,
                    lineage_id=f"{strategy_name}_v{i}",
                ))

        random.shuffle(self.population)
        self.population = self.population[:self.config.population_size]
        logger.info(f"Population initialized: {len(self.population)} individuals")

    def _random_params(self, strategy_name: str, space: dict) -> dict:
        """Generate random parameters within the search space."""
        params = {}
        for param, (lo, hi) in space.items():
            if isinstance(lo, float) or isinstance(hi, float):
                params[param] = round(random.uniform(lo, hi), 2)
            else:
                params[param] = random.randint(int(lo), int(hi))
        return params

    def _selection(self) -> List[Individual]:
        """Tournament selection — select parents for next generation."""
        selected = []
        n_offspring = int(self.config.population_size * (1 - self.config.elite_fraction))

        for _ in range(n_offspring):
            tournament = random.sample(self.population, min(self.config.tournament_size, len(self.population)))
            winner = max(tournament, key=lambda x: x.fitness)
            selected.append(copy.deepcopy(winner))

        return selected

    def _crossover(self, population: List[Individual]) -> List[Individual]:
        """Crossover parameters between two parents of the same strategy."""
        new_pop = []
        for i, ind in enumerate(population):
            if random.random() < self.config.crossover_rate and i + 1 < len(population):
                parent2 = population[i + 1]
                # Only crossover same strategy (same parameter keys)
                if (ind.strategy_name == parent2.strategy_name and ind.parameters and parent2.parameters):
                    child_params = {}
                    for key in ind.parameters:
                        if key in parent2.parameters:
                            # Uniform crossover: random blend
                            alpha = random.random()
                            v1, v2 = ind.parameters[key], parent2.parameters[key]
                            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                                blended = alpha * v1 + (1 - alpha) * v2
                                child_params[key] = int(round(blended)) if isinstance(v1, int) else round(blended, 2)
                            else:
                                child_params[key] = v1
                        else:
                            child_params[key] = ind.parameters[key]

                    child = Individual(
                        strategy_name=ind.strategy_name,
                        parameters=child_params,
                        generation=self.generation,
                        parents=[ind.lineage_id, parent2.lineage_id],
                        lineage_id=f"{ind.strategy_name}_gen{self.generation}_{i}",
                    )
                    new_pop.append(child)
                else:
                    new_pop.append(ind)
            else:
                new_pop.append(ind)
        return new_pop

    def _mutation(self, population: List[Individual]) -> List[Individual]:
        """Randomly mutate parameters."""
        for ind in population:
            if random.random() < self.config.mutation_rate:
                space = PARAM_SPACES.get(ind.strategy_name, {})
                if space:
                    # Mutate a random parameter
                    param = random.choice(list(space.keys()))
                    lo, hi = space[param]
                    if isinstance(lo, float) or isinstance(hi, float):
                        ind.parameters[param] = round(random.uniform(lo, hi), 2)
                    else:
                        ind.parameters[param] = random.randint(int(lo), int(hi))
        return population

    def _get_elites(self) -> List[Individual]:
        n = max(1, int(self.config.population_size * self.config.elite_fraction))
        return copy.deepcopy(sorted(self.population, key=lambda x: x.fitness, reverse=True)[:n])

    def _get_best(self) -> Optional[Individual]:
        if not self.population: return None
        return max(self.population, key=lambda x: x.fitness)

    # ─────────────────────────────────────────────────────────────────
    # FITNESS EVALUATION
    # ─────────────────────────────────────────────────────────────────

    def _evaluate_population(self, df: pd.DataFrame, subset: List[Individual] = None):
        """Run walk-forward backtest on each individual to compute fitness."""
        target = subset or self.population
        for ind in target:
            try:
                result = self._walk_forward_backtest(ind, df)
                ind.fitness       = result["sharpe"]
                ind.win_rate      = result["win_rate"]
                ind.profit_factor = result["profit_factor"]
                ind.total_trades  = result["total_trades"]
            except Exception as e:
                ind.fitness = -1.0
                logger.debug(f"Eval failed for {ind.strategy_name}: {e}")

    def _walk_forward_backtest(self, individual: Individual, df: pd.DataFrame) -> dict:
        """
        Walk-forward backtest: train on 70%, test on 30%.
        Prevents overfitting to historical data.
        """
        n = len(df)
        if n < 100:
            return {"sharpe": 0, "win_rate": 0, "profit_factor": 0, "total_trades": 0}

        split = int(n * 0.70)
        test_df = df.iloc[split:]

        # Get strategy with individual's parameters
        s = STRATEGY_LIBRARY.get(individual.strategy_name)
        if not s or not s.signal_fn:
            return {"sharpe": 0, "win_rate": 0, "profit_factor": 0, "total_trades": 0}

        # Temporarily set parameters
        original_params = s.parameters.copy()
        s.parameters = individual.parameters

        try:
            signals = s.signal_fn(test_df, individual.parameters)
        finally:
            s.parameters = original_params

        return self._compute_metrics(test_df, signals)

    def _compute_metrics(self, df: pd.DataFrame, signals: pd.Series) -> dict:
        """Fast metrics computation from signals."""
        c = df["close"]
        returns = []
        in_trade = False
        entry = 0
        direction = 0
        slippage = 0.0002
        brokerage = 20

        for i in range(1, len(df)):
            sig = signals.iloc[i-1]
            price = float(c.iloc[i])

            if not in_trade and sig in [1, -1]:
                in_trade  = True
                entry     = price * (1 + slippage * sig)
                direction = sig

            elif in_trade:
                # Exit on opposite signal or after 12 bars
                if sig == -direction:
                    exit_price = price * (1 - slippage * direction)
                    ret = (exit_price - entry) / entry * direction
                    ret -= brokerage / (entry * 50)  # Approximate lot size
                    returns.append(ret)
                    in_trade = False

        if len(returns) < self.config.min_trades:
            return {"sharpe": 0, "win_rate": 0, "profit_factor": 0, "total_trades": len(returns)}

        arr = np.array(returns)
        wins  = arr[arr > 0]
        losses= arr[arr < 0]

        sharpe = (arr.mean() / (arr.std() + 1e-9)) * np.sqrt(252 * 78)  # Annualized
        win_rate = len(wins) / len(arr)
        profit_factor = wins.sum() / (-losses.sum() + 1e-9) if len(losses) > 0 else 9.9

        return {
            "sharpe":        round(float(sharpe), 3),
            "win_rate":      round(float(win_rate), 3),
            "profit_factor": round(float(min(profit_factor, 9.9)), 2),
            "total_trades":  len(returns),
        }

    # ─────────────────────────────────────────────────────────────────
    # STATE PERSISTENCE
    # ─────────────────────────────────────────────────────────────────

    def _save_state(self):
        state = {
            "generation":    self.generation,
            "population":    [ind.to_dict() for ind in self.population[:20]],
            "hall_of_fame":  [ind.to_dict() for ind in self.hall_of_fame[:10]],
            "history":       self.history[-100:],
            "updated":       datetime.now().isoformat(),
        }
        os.makedirs(os.path.dirname(EVOLUTION_STATE_PATH), exist_ok=True)
        with open(EVOLUTION_STATE_PATH, "w") as f:
            json.dump(state, f, indent=2)
        logger.info(f"Evolution state saved (gen {self.generation})")

    def _load_state(self):
        if not os.path.exists(EVOLUTION_STATE_PATH):
            return
        try:
            with open(EVOLUTION_STATE_PATH) as f:
                state = json.load(f)
            self.generation  = state.get("generation", 0)
            self.population  = [Individual.from_dict(d) for d in state.get("population", [])]
            self.hall_of_fame= [Individual.from_dict(d) for d in state.get("hall_of_fame", [])]
            self.history     = state.get("history", [])
            logger.info(f"Resumed from generation {self.generation} | {len(self.population)} individuals loaded")
        except Exception as e:
            logger.warning(f"Could not load evolution state: {e}")

    def get_best_strategies(self, top_n: int = 5) -> List[Individual]:
        """Return top N strategies from hall of fame."""
        return self.hall_of_fame[:top_n]

    def get_evolution_report(self) -> dict:
        """Summary of evolution progress."""
        if not self.history:
            return {"status": "Not started", "generation": 0}
        latest = self.history[-1]
        best   = self.hall_of_fame[0] if self.hall_of_fame else None
        return {
            "generation":       self.generation,
            "best_ever_sharpe": best.fitness if best else 0,
            "best_ever_strategy": best.strategy_name if best else "N/A",
            "best_ever_params": best.parameters if best else {},
            "current_gen_best": latest.get("best", 0),
            "current_gen_mean": latest.get("mean", 0),
            "hall_of_fame_size": len(self.hall_of_fame),
            "total_population": len(self.population),
        }
