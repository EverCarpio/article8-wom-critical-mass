"""M2: synchronous positive WOM, finite contacts and one-time purchase.

Energy is constant; newly acquired customers await an unimplemented experience
module. No negative WOM, endogenous promoters or takeoff classification.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import asdict, dataclass
import json
import math
from .config import Config
from .model import Commercial, Experience, InitialState, WOM, initialize
from .randomness import indexed_uniform


@dataclass(frozen=True)
class PositiveConfig:
    periods: int = 60
    opportunities: int = 2
    opportunity_factor: float = .8
    memory_retention: float = .5
    intercept: float = -2.0
    need_coefficient: float = 1.5
    fit_coefficient: float = 1.5
    positive_coefficient: float = 1.2
    record_agents: bool = True

    def validate(self):
        for name in ("periods", "opportunities"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        for name in ("opportunity_factor", "memory_retention"):
            x = getattr(self, name)
            if type(x) not in (int, float) or not math.isfinite(x) or not 0 <= x <= 1:
                raise ValueError(f"{name} must be finite in [0,1]")
        for name in ("intercept", "need_coefficient", "fit_coefficient", "positive_coefficient"):
            x = getattr(self, name)
            if type(x) not in (int, float) or not math.isfinite(x):
                raise ValueError(f"{name} must be finite")
        if min(self.need_coefficient, self.fit_coefficient, self.positive_coefficient) < 0:
            raise ValueError("Influence coefficients must be nonnegative")
        if type(self.record_agents) is not bool:
            raise ValueError("record_agents must be boolean")


def adoption_probability(need, fit, positive_memory, has_new_positive_message, config):
    """Fresh-message gate is applied before the bounded influence/logistic rule."""
    if not has_new_positive_message:
        return 0.0
    h = -math.expm1(-positive_memory)
    z = (config.intercept + config.need_coefficient * need +
         config.fit_coefficient * fit + config.positive_coefficient * h)
    # Stable sigmoid, including intentionally extreme finite test coefficients.
    if z >= 0:
        return 1 / (1 + math.exp(-z))
    exp_z = math.exp(z)
    return exp_z / (1 + exp_z)


EVENT_COLUMNS = ["event_id", "period", "sign", "sender", "receiver", "slot",
                 "sender_community", "receiver_community", "sender_energy",
                 "sender_credibility", "opportunity_draw", "target_draw",
                 "receiver_positive_exposures_before_period", "first_positive_reach",
                 "receiver_bought_this_period", "credited_purchase_parent"]
DECISION_COLUMNS = ["period", "receiver", "community", "new_positive_messages",
                    "positive_memory_before", "positive_memory_after", "positive_influence",
                    "probability", "purchase_draw", "adopted", "parent",
                    "scheduled_experience_time"]


class PositiveSimulation:
    def __init__(self, initial: InitialState | None = None,
                 dynamics: PositiveConfig = PositiveConfig(), draw=None):
        dynamics.validate()
        if initial is None:
            initial = initialize(Config(negative_wom_enabled=False))
        initial.validate()
        self._validate_initial_mode(initial)
        self.initial = deepcopy(initial)
        self.state = InitialState(initial.config, initial.environment, deepcopy(initial.agents))
        self.dynamics = dynamics
        self.custom_draw = draw is not None
        self._draw_fn = draw or (lambda agent, period, mechanism, slot:
                                indexed_uniform(initial.config.seed, agent, period, mechanism, slot))
        self.events = []
        self.decisions = []
        self.system = [self._system_row(0, 0, 0, 0)]
        self.agent_history = self.agent_rows() if dynamics.record_agents else []

    @property
    def time(self):
        return self.state.time

    def _validate_initial_mode(self, initial):
        if initial.config.negative_wom_enabled:
            raise ValueError("Positive-only simulations require negative_wom_enabled=False (CLI: --negative-off)")

    @property
    def agents(self):
        return self.state.agents

    def _draw(self, agent, period, mechanism, slot=0):
        value = self._draw_fn(agent, period, mechanism, slot)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value < 1:
            raise ValueError("Uniform draws must be finite in [0,1)")
        return value

    def agent_rows(self):
        rows = []
        for a in self.agents:
            row = {"period": self.time, **asdict(a)}
            row.update(row.pop("traits"))
            for key in ("contacted_positive", "contacted_negative"):
                row[key] = json.dumps(sorted(row[key]))
            row["inactivity_reasons"] = json.dumps(row["inactivity_reasons"])
            row["degree"] = len(self.state.environment.network.neighbors[a.id])
            row["remaining_positive_contacts"] = len(self.state.eligible_contacts(a.id, "positive"))
            row["aware"] = a.positive_exposures > 0
            row["scheduled_experience_time"] = (a.purchase_time + 1
                                                if a.commercial == Commercial.PENDING else None)
            rows.append(row)
        return rows

    def _system_row(self, new_purchases, new_events, new_reach, deactivated):
        cumulative = len(self.events)
        unique = sum(a.positive_exposures > 0 for a in self.agents)
        return {**self.state.summary(), "new_purchases": new_purchases,
                "positive_events": new_events, "new_unique_positive_recipients": new_reach,
                "cumulative_new_purchases": sum(not a.initial_customer and a.commercial != Commercial.SUSCEPTIBLE for a in self.agents),
                "cumulative_positive_events": cumulative, "cumulative_unique_positive_recipients": unique,
                "cumulative_positive_redundancy": 1 - unique / cumulative if cumulative else None,
                "deactivated_promoters": deactivated, "new_promoters": 0,
                "pending_experience_customers": sum(a.commercial == Commercial.PENDING for a in self.agents),
                "diffusion_class": "not_evaluated_m2"}

    def step(self, sender_order=None):
        return self._step_batch(sender_order)

    def _step_batch(self, sender_order=None):
        if self.time >= self.dynamics.periods:
            raise ValueError("Configured horizon already reached")
        t = self.time + 1
        susceptible = {a.id for a in self.agents if a.commercial == Commercial.SUSCEPTIBLE}
        active = [a.id for a in self.agents if a.wom == WOM.PROMOTER_ACTIVE]
        order = active if sender_order is None else list(sender_order)
        if len(order) != len(active) or set(order) != set(active):
            raise ValueError("sender_order must be a permutation of current active promoters")
        # Plan all messages using the same beginning-of-period snapshot.
        planned = []
        for i in order:
            a = self.agents[i]
            if a.positive_energy <= self.state.config.energy_threshold:
                continue
            candidates = sorted((self.state.environment.network.neighbors[i] & susceptible) - a.contacted_positive)
            for slot in range(self.dynamics.opportunities):
                if not candidates:
                    break
                u = self._draw(i, t, "positive_opportunity", slot)
                if u >= self.dynamics.opportunity_factor * a.positive_energy:
                    continue
                target_draw = self._draw(i, t, "positive_target", slot)
                target = candidates.pop(int(target_draw * len(candidates)))
                planned.append({"event_id": f"p{t:04d}-s{i:06d}-k{slot:03d}",
                                "period": t, "sign": "positive", "sender": i,
                                "receiver": target, "slot": slot,
                                "sender_community": a.community, "receiver_community": self.agents[target].community,
                                "sender_energy": a.positive_energy, "sender_credibility": a.traits.credibility,
                                "opportunity_draw": u, "target_draw": target_draw,
                                "receiver_positive_exposures_before_period": self.agents[target].positive_exposures})
        planned.sort(key=lambda e: (e["sender"], e["slot"]))
        by_receiver = defaultdict(list)
        for event in planned:
            by_receiver[event["receiver"]].append(event)

        # Compute every memory and purchase decision before mutating any agent.
        memories, trials = {}, []
        for j in sorted(susceptible):
            a = self.agents[j]
            incoming = by_receiver.get(j, [])
            memory = (self.dynamics.memory_retention * a.positive_memory +
                      math.fsum(e["sender_credibility"] for e in incoming))
            memories[j] = memory
            if not incoming:
                continue  # No purchase draw and no purchase with old exposure alone.
            probability = adoption_probability(a.traits.need, a.traits.fit, memory, True, self.dynamics)
            u = self._draw(j, t, "purchase", 0)
            adopted = u < probability
            parent = min(incoming, key=lambda e: (-e["sender_credibility"], e["sender"]))["sender"] if adopted else None
            trials.append({"period": t, "receiver": j, "community": a.community,
                           "new_positive_messages": len(incoming), "positive_memory_before": a.positive_memory,
                           "positive_memory_after": memory, "positive_influence": -math.expm1(-memory),
                           "probability": probability, "purchase_draw": u, "adopted": adopted,
                           "parent": parent, "scheduled_experience_time": t + 1 if adopted else None})

        # Commit the batch; multiple messages to one receiver cause one decision.
        buyers = {d["receiver"]: d["parent"] for d in trials if d["adopted"]}
        first_reached = set()
        for event in planned:
            i, j = event["sender"], event["receiver"]
            first = event["receiver_positive_exposures_before_period"] == 0 and j not in first_reached
            event["first_positive_reach"] = first
            if first:
                first_reached.add(j)
            event["receiver_bought_this_period"] = j in buyers
            event["credited_purchase_parent"] = j in buyers and buyers[j] == i
            self.agents[i].contacted_positive.add(j)
            self.agents[j].positive_exposures += 1
        for j, memory in memories.items():
            self.agents[j].positive_memory = memory
        for j, parent in buyers.items():
            a = self.agents[j]
            a.commercial, a.purchase_time, a.parent = Commercial.PENDING, t, parent
            # Experience, satisfaction and generation remain unassigned.
        deactivated = self._close_period(t, active, planned)
        self.state.time = t
        self.events.extend(planned)
        self.decisions.extend(trials)
        self.system.append(self._system_row(len(buyers), len(planned), len(first_reached), deactivated))
        if self.dynamics.record_agents:
            self.agent_history.extend(self.agent_rows())
        return dict(self.system[-1])

    def _close_period(self, period, active, messages):
        """M2/M3 close: constant energy and deactivation by exhausted contacts."""
        deactivated = 0
        for i in active:
            a = self.agents[i]
            if not self.state.eligible_contacts(i, "positive"):
                a.wom, a.deactivation_time = WOM.PROMOTER_FATIGUED, period
                a.inactivity_reasons = ("contacts_exhausted",)
                deactivated += 1
        return deactivated

    def run(self, until=None):
        target = self.dynamics.periods if until is None else until
        if type(target) is not int or not self.time <= target <= self.dynamics.periods:
            raise ValueError("until must be an integer between current time and configured horizon")
        while self.time < target:
            self.step()
        self.validate()
        return self

    def summary(self):
        return {"scope": "M2 positive WOM and purchase only", "completed_periods": self.time,
                "configured_periods": self.dynamics.periods,
                "negative_wom_enabled": False, "energy_dynamics_enabled": False,
                "experience_dynamics_enabled": False, "new_promoter_formation_enabled": False,
                "custom_draw_function": self.custom_draw, **self.system[-1]}

    def _validate_sender(self, agent, event):
        if not agent.initial_promoter:
            raise ValueError("Non-initial sender in M2")

    def _validate_energy(self, agent, original):
        if agent.positive_energy != original.positive_energy or agent.negative_energy != original.negative_energy:
            raise ValueError("Energy changed in M2")

    def _validate_purchase(self, agent, decision):
        if not (agent.commercial == Commercial.PENDING and agent.purchase_time == decision["period"]
                and agent.parent == decision["parent"]):
            raise ValueError("Purchase-state mismatch")
        if not (agent.experience_time is None and agent.experience == Experience.UNEVALUATED
                and agent.wom == WOM.NONE and agent.generation is None):
            raise ValueError("Premature experience/promotion")

    def validate(self):
        """Reconcile final state with events and purchase-decision ledgers."""
        def require(condition, message):
            if not condition:
                raise ValueError(message)
        require(len(self.agents) == self.state.config.n, "Population changed")
        require(tuple(a.id for a in self.agents) == tuple(range(len(self.agents))), "Invalid ids")
        pairs, event_ids = set(), set()
        exposures, sent = Counter(), defaultdict(set)
        per_period_sender, receipts = Counter(), defaultdict(list)
        for e in self.events:
            i, j, t = e["sender"], e["receiver"], e["period"]
            require(1 <= t <= self.time and e["sign"] == "positive", "Invalid event period/sign")
            require(e["event_id"] not in event_ids and (i, j) not in pairs, "Repeated event/pair")
            self._validate_sender(self.agents[i], e)
            require(j in self.state.environment.network.neighbors[i], "Non-neighbor contact")
            a = self.agents[j]
            require(not a.initial_customer and (a.purchase_time is None or a.purchase_time >= t), "Contact after purchase")
            require(e["sender_energy"] > self.state.config.energy_threshold, "Zero-energy contact")
            pairs.add((i, j)); event_ids.add(e["event_id"])
            exposures[j] += 1; sent[i].add(j); per_period_sender[(t, i)] += 1
            receipts[(t, j)].append(e)
        require(all(n <= self.dynamics.opportunities for n in per_period_sender.values()), "Contact budget exceeded")
        purchased, trial_keys = {}, set()
        for d in self.decisions:
            key = (d["period"], d["receiver"])
            require(key not in trial_keys and key in receipts, "Repeated or unexposed purchase decision")
            trial_keys.add(key)
            require(d["new_positive_messages"] == len(receipts[key]), "Incorrect batch exposure count")
            require(d["adopted"] == (d["purchase_draw"] < d["probability"]), "Purchase threshold mismatch")
            if d["adopted"]:
                j = d["receiver"]
                require(j not in purchased, "Multiple purchases")
                expected_parent = min(receipts[key], key=lambda e: (-e["sender_credibility"], e["sender"]))["sender"]
                require(d["parent"] == expected_parent, "Incorrect purchase attribution")
                purchased[j] = d
        require(trial_keys == set(receipts), "Missing purchase decisions")
        for a, original in zip(self.agents, self.initial.agents):
            a.validate()
            require(a.community == original.community and a.traits == original.traits, "Exogenous traits changed")
            require((a.initial_customer, a.initial_promoter, a.initial_detractor) ==
                    (original.initial_customer, original.initial_promoter, original.initial_detractor), "Initial roles changed")
            require(a.contacted_positive == sent[a.id] and a.positive_exposures == exposures[a.id], "Event accounting mismatch")
            require(not a.contacted_negative and a.negative_exposures == 0 and a.negative_memory == 0, "Negative WOM in M2")
            self._validate_energy(a, original)
            if a.initial_customer:
                require(a.commercial == original.commercial and a.satisfaction == original.satisfaction and
                        a.experience == original.experience, "Initial customer experience changed")
            elif a.id in purchased:
                d = purchased[a.id]
                self._validate_purchase(a, d)
            else:
                require(a.commercial == Commercial.SUSCEPTIBLE and a.purchase_time is None and a.parent is None, "Spontaneous purchase")
            if a.wom == WOM.PROMOTER_ACTIVE:
                require(bool(self.state.eligible_contacts(a.id, "positive")) and a.positive_energy > self.state.config.energy_threshold, "Ineligible active promoter")
        require(len(self.system) == self.time + 1, "Incomplete system history")
        require(sum(r["positive_events"] for r in self.system) == len(self.events), "System-event mismatch")
        require(sum(r["new_purchases"] for r in self.system) == len(purchased), "System-purchase mismatch")
        require(sum(a.commercial != Commercial.SUSCEPTIBLE for a in self.agents) == self.state.config.initial_customers + len(purchased), "Customer conservation failed")
