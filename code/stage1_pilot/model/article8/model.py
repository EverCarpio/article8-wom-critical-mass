"""Paired exogenous environments, initial agent states and invariants."""
from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum
import math
from .config import Config
from .network import Network, make_network
from .randomness import stream


class Commercial(StrEnum):
    SUSCEPTIBLE = "susceptible"
    PENDING = "customer_pending_experience"
    EXPERIENCED = "customer_with_experience"


class Experience(StrEnum):
    UNEVALUATED = "unevaluated"
    NEUTRAL = "neutral"
    SATISFIED = "satisfied"
    DISSATISFIED = "dissatisfied"


class WOM(StrEnum):
    NONE = "none"
    PROMOTER_POTENTIAL = "promoter_potential"
    PROMOTER_ACTIVE = "promoter_active"
    PROMOTER_FATIGUED = "promoter_fatigued"
    DETRACTOR_POTENTIAL = "detractor_potential"
    DETRACTOR_ACTIVE = "detractor_active"
    DETRACTOR_INACTIVE = "detractor_inactive"


@dataclass(frozen=True)
class Traits:
    need: float
    fit: float
    credibility: float


@dataclass(frozen=True)
class Environment:
    key: tuple
    network: Network
    traits: tuple[Traits, ...]
    customers: frozenset[int]
    detractors: frozenset[int]
    promoter_order: tuple[tuple[int, ...], ...]
    community_order: tuple[int, ...]


@dataclass
class Agent:
    id: int
    community: int
    traits: Traits
    commercial: Commercial = Commercial.SUSCEPTIBLE
    experience: Experience = Experience.UNEVALUATED
    wom: WOM = WOM.NONE
    initial_customer: bool = False
    initial_promoter: bool = False
    initial_detractor: bool = False
    satisfaction: float | None = None
    positive_energy: float = 0.0
    negative_energy: float = 0.0
    positive_eligible: bool = False
    negative_eligible: bool = False
    purchase_time: int | None = None
    experience_time: int | None = None
    activation_time: int | None = None
    deactivation_time: int | None = None
    inactivity_reasons: tuple[str, ...] = ()
    contacted_positive: set[int] = field(default_factory=set)
    contacted_negative: set[int] = field(default_factory=set)
    positive_exposures: int = 0
    negative_exposures: int = 0
    positive_memory: float = 0.0
    negative_memory: float = 0.0
    parent: int | None = None
    generation: int | None = None

    def validate(self) -> None:
        if not isinstance(self.commercial, Commercial) or not isinstance(self.experience, Experience) or not isinstance(self.wom, WOM):
            raise ValueError("Unknown state value")
        for value in (self.positive_energy, self.negative_energy, self.traits.need,
                      self.traits.fit, self.traits.credibility):
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("Energy and traits must be in [0,1]")
        if self.satisfaction is not None and (not math.isfinite(self.satisfaction) or not 0 <= self.satisfaction <= 1):
            raise ValueError("Invalid satisfaction")
        if self.commercial != Commercial.EXPERIENCED:
            if self.experience != Experience.UNEVALUATED or self.wom != WOM.NONE or self.satisfaction is not None:
                raise ValueError("No assessed experience or WOM before experience")
        elif self.experience == Experience.UNEVALUATED or self.satisfaction is None:
            raise ValueError("Experienced customer needs an assessed experience")
        if self.wom in (WOM.PROMOTER_POTENTIAL, WOM.PROMOTER_ACTIVE, WOM.PROMOTER_FATIGUED):
            if self.experience != Experience.SATISFIED or not self.positive_eligible:
                raise ValueError("Promoter must be satisfied and eligible")
        if self.wom in (WOM.DETRACTOR_POTENTIAL, WOM.DETRACTOR_ACTIVE, WOM.DETRACTOR_INACTIVE):
            if self.experience != Experience.DISSATISFIED or not self.negative_eligible:
                raise ValueError("Detractor must be dissatisfied and eligible")
        if self.positive_eligible and self.negative_eligible:
            raise ValueError("Incompatible simultaneous WOM eligibility")
        if self.initial_promoter and self.initial_detractor:
            raise ValueError("Initial promoter and detractor sets must be disjoint")
        for count in (self.positive_exposures, self.negative_exposures):
            if type(count) is not int or count < 0:
                raise ValueError("Exposure counts must be nonnegative integers")
        for memory in (self.positive_memory, self.negative_memory):
            if not math.isfinite(memory) or memory < 0:
                raise ValueError("Invalid influence memory")


def make_environment(config: Config) -> Environment:
    config.validate()
    network = make_network(config)
    traits_rng = stream(config.seed, "traits")
    traits = tuple(Traits(traits_rng.uniform(.5, 1), traits_rng.uniform(.5, 1),
                         traits_rng.uniform(.6, 1)) for _ in range(config.n))
    customer_rng = stream(config.seed, "customers")
    detractor_rng = stream(config.seed, "detractors")
    promoter_rng = stream(config.seed, "promoter_order")
    c_per = config.initial_customers // config.communities
    d_per = config.initial_detractors // config.communities
    customers, detractors, orders = set(), set(), []
    for c in range(config.communities):
        members = [i for i, group in enumerate(network.community) if group == c]
        c_ids = set(customer_rng.sample(members, c_per))
        d_ids = set(detractor_rng.sample(sorted(c_ids), d_per))
        eligible = sorted(c_ids - d_ids)
        promoter_rng.shuffle(eligible)
        customers.update(c_ids)
        detractors.update(d_ids)
        orders.append(tuple(eligible))
    communities = list(range(config.communities))
    stream(config.seed, "community_order").shuffle(communities)
    return Environment(config.environment_key(), network, traits, frozenset(customers),
                       frozenset(detractors), tuple(orders), tuple(communities))


def select_promoters(environment: Environment, config: Config) -> frozenset[int]:
    communities = environment.community_order if config.distribution == "distributed" else environment.community_order[:2]
    selected = []
    for k in range(config.promoter_count()):
        group = communities[k % len(communities)]
        selected.append(environment.promoter_order[group][k // len(communities)])
    return frozenset(selected)


@dataclass
class InitialState:
    config: Config
    environment: Environment
    agents: tuple[Agent, ...]
    time: int = 0

    def eligible_contacts(self, agent_id: int, sign: str) -> tuple[int, ...]:
        if sign not in ("positive", "negative"):
            raise ValueError("Unknown contact sign")
        if type(agent_id) is not int or not 0 <= agent_id < len(self.agents):
            raise ValueError("Invalid agent id")
        a = self.agents[agent_id]
        used = a.contacted_positive if sign == "positive" else a.contacted_negative
        return tuple(j for j in sorted(self.environment.network.neighbors[agent_id])
                     if self.agents[j].commercial == Commercial.SUSCEPTIBLE and j not in used)

    def capacity(self, sign: str) -> float:
        if sign not in ("positive", "negative"):
            raise ValueError("Unknown capacity sign")
        if sign == "negative" and not self.config.negative_wom_enabled:
            return 0.0
        state = WOM.PROMOTER_ACTIVE if sign == "positive" else WOM.DETRACTOR_ACTIVE
        values = []
        for a in self.agents:
            if a.wom == state:
                degree = len(self.environment.network.neighbors[a.id])
                h = len(self.eligible_contacts(a.id, sign)) / degree if degree else 0.0
                energy = a.positive_energy if sign == "positive" else a.negative_energy
                values.append(energy * a.traits.credibility * h)
        return math.fsum(values)

    def summary(self) -> dict:
        counts = Counter(a.wom for a in self.agents)
        customers = sum(a.commercial != Commercial.SUSCEPTIBLE for a in self.agents)
        positive, negative = self.capacity("positive"), self.capacity("negative")
        return {
            "time": self.time, "population": len(self.agents), "customers": customers,
            "susceptibles": len(self.agents) - customers,
            "nominal_initial_promoters": sum(a.initial_promoter for a in self.agents),
            "nominal_initial_share_customers": self.config.promoter_count() / self.config.initial_customers,
            "nominal_initial_share_population": self.config.promoter_count() / self.config.n,
            **{str(s): counts[s] for s in WOM},
            "positive_capacity": positive, "negative_capacity": negative,
            "net_pressure": positive - self.config.negative_weight * negative,
            "new_purchases": 0, "positive_events": 0, "negative_events": 0,
            "reproduction_ratio": None, "replacement_ratio": None,
            "diffusion_class": "not_evaluated_m1",
        }

    def validate(self) -> None:
        cfg, env = self.config, self.environment
        cfg.validate()
        env.network.validate()
        if self.time != 0 or len(self.agents) != cfg.n or env.key != cfg.environment_key():
            raise ValueError("Invalid initial state or mismatched environment")
        if tuple(a.id for a in self.agents) != tuple(range(cfg.n)):
            raise ValueError("Agent ids must be ordered and unique")
        selected = select_promoters(env, cfg)
        if sum(a.initial_customer for a in self.agents) != cfg.initial_customers:
            raise ValueError("Incorrect customer count")
        if Counter(a.community for a in self.agents if a.initial_customer) != Counter({c: cfg.initial_customers // cfg.communities for c in range(cfg.communities)}):
            raise ValueError("Unbalanced initial customer allocation")
        for a in self.agents:
            a.validate()
            if a.community != env.network.community[a.id] or a.traits != env.traits[a.id]:
                raise ValueError("Agent differs from shared environment")
            if (a.initial_customer != (a.id in env.customers) or a.initial_detractor != (a.id in env.detractors)
                    or a.initial_promoter != (a.id in selected)):
                raise ValueError("Initial role assignment mismatch")
            expected_commercial = Commercial.EXPERIENCED if a.initial_customer else Commercial.SUSCEPTIBLE
            expected_experience = (Experience.SATISFIED if a.initial_promoter else
                                   Experience.DISSATISFIED if a.initial_detractor else
                                   Experience.NEUTRAL if a.initial_customer else Experience.UNEVALUATED)
            expected_satisfaction = 1.0 if a.initial_promoter else 0.0 if a.initial_detractor else .5 if a.initial_customer else None
            if (a.commercial != expected_commercial or a.experience != expected_experience or a.satisfaction != expected_satisfaction):
                raise ValueError("Incorrect initial commercial/experience state")
            if a.contacted_positive or a.contacted_negative or a.positive_exposures or a.negative_exposures or a.positive_memory or a.negative_memory:
                raise ValueError("Initial exposure history must be empty")
            expected_ep = cfg.positive_energy if a.initial_promoter else 0.0
            expected_en = cfg.negative_energy if a.initial_detractor else 0.0
            if a.positive_energy != expected_ep or a.negative_energy != expected_en:
                raise ValueError("Initial energy assignment mismatch")
            if a.positive_eligible != a.initial_promoter or a.negative_eligible != a.initial_detractor:
                raise ValueError("Incorrect initial eligibility")
            expected = WOM.NONE
            if a.initial_promoter:
                active = a.positive_energy > cfg.energy_threshold and bool(self.eligible_contacts(a.id, "positive"))
                expected = WOM.PROMOTER_ACTIVE if active else WOM.PROMOTER_FATIGUED
            elif a.initial_detractor:
                active = cfg.negative_wom_enabled and a.negative_energy > cfg.energy_threshold and bool(self.eligible_contacts(a.id, "negative"))
                expected = WOM.DETRACTOR_ACTIVE if active else WOM.DETRACTOR_INACTIVE
            if a.wom != expected:
                raise ValueError("Inconsistent active/inactive state")
            reasons = []
            if a.initial_promoter or a.initial_detractor:
                sign = "positive" if a.initial_promoter else "negative"
                energy = a.positive_energy if a.initial_promoter else a.negative_energy
                if a.initial_detractor and not cfg.negative_wom_enabled:
                    reasons.append("negative_wom_disabled")
                if energy <= cfg.energy_threshold:
                    reasons.append("energy_exhausted")
                if not self.eligible_contacts(a.id, sign):
                    reasons.append("contacts_exhausted")
            if a.inactivity_reasons != tuple(reasons) or a.deactivation_time != (0 if reasons else None):
                raise ValueError("Incorrect initial inactivity reasons/timestamp")
            active = a.wom in (WOM.PROMOTER_ACTIVE, WOM.DETRACTOR_ACTIVE)
            if a.activation_time != (0 if active else None):
                raise ValueError("Invalid initial activation time")
            if a.parent is not None or a.generation != (0 if a.initial_promoter else None):
                raise ValueError("Invalid initial genealogy")
            if a.purchase_time != (0 if a.initial_customer else None) or a.experience_time != (0 if a.initial_customer else None):
                raise ValueError("Invalid initial experience timestamps")


def initialize(config: Config = Config(), environment: Environment | None = None) -> InitialState:
    config.validate()
    env = make_environment(config) if environment is None else environment
    if env.key != config.environment_key():
        raise ValueError("Cannot reuse environment with different exogenous settings")
    promoters = select_promoters(env, config)
    agents = []
    for i in range(config.n):
        a = Agent(i, env.network.community[i], env.traits[i])
        if i in env.customers:
            a.initial_customer = True
            a.commercial, a.experience = Commercial.EXPERIENCED, Experience.NEUTRAL
            a.satisfaction, a.purchase_time, a.experience_time = .5, 0, 0
        if i in promoters:
            a.initial_promoter, a.positive_eligible = True, True
            a.experience, a.satisfaction = Experience.SATISFIED, 1.0
            a.positive_energy, a.generation = config.positive_energy, 0
        elif i in env.detractors:
            a.initial_detractor, a.negative_eligible = True, True
            a.experience, a.satisfaction = Experience.DISSATISFIED, 0.0
            a.negative_energy = config.negative_energy
        agents.append(a)
    result = InitialState(config, env, tuple(agents))
    for a in result.agents:
        if not (a.initial_promoter or a.initial_detractor):
            continue
        sign = "positive" if a.initial_promoter else "negative"
        energy = a.positive_energy if a.initial_promoter else a.negative_energy
        reasons = []
        if sign == "negative" and not config.negative_wom_enabled:
            reasons.append("negative_wom_disabled")
        if energy <= config.energy_threshold:
            reasons.append("energy_exhausted")
        if not result.eligible_contacts(a.id, sign):
            reasons.append("contacts_exhausted")
        if reasons:
            a.wom = WOM.PROMOTER_FATIGUED if a.initial_promoter else WOM.DETRACTOR_INACTIVE
            a.inactivity_reasons, a.deactivation_time = tuple(reasons), 0
        else:
            a.wom = WOM.PROMOTER_ACTIVE if a.initial_promoter else WOM.DETRACTOR_ACTIVE
            a.activation_time = 0
    result.validate()
    return result
