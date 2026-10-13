"""Validated, serializable configuration; no silent percentage rounding."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import math


@dataclass(frozen=True)
class Config:
    n: int = 600
    communities: int = 6
    initial_customers: int = 120
    initial_detractors: int = 6
    p_within: float = 0.08
    p_between: float = 0.006
    promoter_share: float = 0.15
    distribution: str = "distributed"
    positive_energy: float = 0.6
    negative_energy: float = 0.6
    energy_threshold: float = 0.05
    negative_wom_enabled: bool = True
    negative_weight: float = 1.0
    seed: int = 20260925

    def promoter_count(self) -> int:
        try:
            count = Decimal(str(self.promoter_share)) * self.initial_customers
        except (InvalidOperation, TypeError) as exc:
            raise ValueError("promoter_share must be a finite decimal") from exc
        if not count.is_finite() or count != count.to_integral_value():
            raise ValueError("promoter_share * initial_customers must be an exact integer")
        return int(count)

    def validate(self) -> None:
        for name in ("n", "communities", "initial_customers", "initial_detractors", "seed"):
            if type(getattr(self, name)) is not int:
                raise ValueError(f"{name} must be an integer, not a boolean")
        if self.communities < 2 or self.n < self.communities:
            raise ValueError("At least two nonempty communities are required")
        if self.n % self.communities or self.initial_customers % self.communities:
            raise ValueError("Population and customers must divide equally among communities")
        if not 0 < self.initial_customers <= self.n:
            raise ValueError("initial_customers must be in [1, n]")
        if not 0 <= self.initial_detractors <= self.initial_customers:
            raise ValueError("Invalid initial_detractors")
        if self.initial_detractors % self.communities:
            raise ValueError("initial_detractors must divide equally among communities")
        if self.seed < 0:
            raise ValueError("seed must be nonnegative")
        for name in ("p_within", "p_between", "promoter_share", "positive_energy",
                     "negative_energy", "energy_threshold"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be a finite number in [0, 1]")
        if type(self.negative_weight) not in (int, float) or not math.isfinite(self.negative_weight) or self.negative_weight < 0:
            raise ValueError("negative_weight must be finite and nonnegative")
        if type(self.negative_wom_enabled) is not bool:
            raise ValueError("negative_wom_enabled must be a boolean")
        if self.distribution not in ("distributed", "concentrated"):
            raise ValueError("distribution must be distributed or concentrated")
        available = (self.initial_customers - self.initial_detractors) // self.communities
        selected_communities = self.communities if self.distribution == "distributed" else 2
        if self.promoter_count() > available * selected_communities:
            raise ValueError("Promoter count exceeds eligible customers in selected communities")

    def environment_key(self) -> tuple:
        """Parameters that define shared exogenous conditions within a replicate."""
        return (self.n, self.communities, self.initial_customers, self.initial_detractors,
                self.p_within, self.p_between, self.seed)

