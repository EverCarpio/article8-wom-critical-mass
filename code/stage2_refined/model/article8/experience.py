"""M3: one-time experience, delayed promoter formation and attributed lineage.

Purchase at t -> experience at t+1 -> single activation attempt at t+2.
Negative WOM and energy decay are deliberately outside this module.
"""
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
import json
import math

from .model import Commercial, Experience, InitialState, WOM
from .positive import PositiveConfig, PositiveSimulation


@dataclass(frozen=True)
class ExperienceConfig:
    quality: float = .7
    fit_effect: float = .2
    noise_amplitude: float = .4
    satisfied_threshold: float = .75
    dissatisfied_threshold: float = .35
    promoter_disposition_probability: float = .8
    new_promoter_energy: float = .6

    def validate(self):
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be finite in [0,1]")
        if self.dissatisfied_threshold >= self.satisfied_threshold:
            raise ValueError("Experience thresholds must be strictly ordered")


def assess_experience(fit, noise_draw, config=ExperienceConfig()):
    """Pure assessment: uniform noise, clipping and inclusive extreme classes."""
    config.validate()
    if not math.isfinite(fit) or not 0 <= fit <= 1:
        raise ValueError("fit must be in [0,1]")
    if not math.isfinite(noise_draw) or not 0 <= noise_draw < 1:
        raise ValueError("noise_draw must be in [0,1)")
    noise = config.noise_amplitude * (2 * noise_draw - 1)
    raw = config.quality + config.fit_effect * (fit - .5) + noise
    satisfaction = min(1.0, max(0.0, raw))
    experience = (Experience.SATISFIED if satisfaction >= config.satisfied_threshold else
                  Experience.DISSATISFIED if satisfaction <= config.dissatisfied_threshold else
                  Experience.NEUTRAL)
    return noise, raw, satisfaction, experience


EXPERIENCE_COLUMNS = ["period", "agent", "purchase_time", "parent", "fit", "quality",
                      "noise_draw", "noise", "raw_satisfaction", "satisfaction", "experience",
                      "disposition_draw", "positive_disposition_probability", "positive_disposition",
                      "scheduled_activation_time"]
ACTIVATION_COLUMNS = ["period", "agent", "purchase_time", "experience_time", "parent",
                      "parent_generation", "generation", "positive_energy", "eligible_contacts",
                      "activated", "inactivity_reasons"]
LINEAGE_COLUMNS = ["agent", "parent", "parent_generation", "initial_root", "generation",
                   "purchase_time", "experience_time", "activation_attempt_time", "activation_time",
                   "deactivation_time", "experience", "satisfaction", "wom", "activation_status"]


def require(condition, message):
    if not condition:
        raise ValueError(message)


class ExperienceSimulation(PositiveSimulation):
    def __init__(self, initial=None, dynamics=PositiveConfig(),
                 experience=ExperienceConfig(), draw=None):
        experience.validate()
        self.experience_config = experience
        self.experience_events = []
        self.activation_events = []
        super().__init__(initial, dynamics, draw)

    def _advance_lifecycle(self, t):
        cfg = self.experience_config
        for a in self.agents:
            if a.commercial != Commercial.PENDING or a.purchase_time + 1 != t:
                continue
            u = self._draw(a.id, t, "experience")
            noise, raw, satisfaction, experience = assess_experience(a.traits.fit, u, cfg)
            disposition_draw = (self._draw(a.id, t, "positive_disposition")
                                if experience == Experience.SATISFIED else None)
            disposition = (disposition_draw is not None and
                           disposition_draw < cfg.promoter_disposition_probability)
            a.commercial, a.experience_time = Commercial.EXPERIENCED, t
            a.satisfaction, a.experience = satisfaction, experience
            if disposition:
                a.positive_eligible, a.wom = True, WOM.PROMOTER_POTENTIAL
                a.positive_energy = cfg.new_promoter_energy
            self.experience_events.append({
                "period": t, "agent": a.id, "purchase_time": a.purchase_time, "parent": a.parent,
                "fit": a.traits.fit, "quality": cfg.quality, "noise_draw": u, "noise": noise,
                "raw_satisfaction": raw, "satisfaction": satisfaction, "experience": experience,
                "disposition_draw": disposition_draw,
                "positive_disposition_probability": cfg.promoter_disposition_probability,
                "positive_disposition": disposition,
                "scheduled_activation_time": t + 1 if disposition else None})
        # Newly assessed customers cannot enter this batch: experience_time < t.
        attempted = {e["agent"] for e in self.activation_events}
        for a in self.agents:
            if (a.wom != WOM.PROMOTER_POTENTIAL or a.id in attempted or
                    a.experience_time + 1 != t):
                continue
            eligible = len(self.state.eligible_contacts(a.id, "positive"))
            reasons = []
            if a.positive_energy <= self.state.config.energy_threshold:
                reasons.append("energy_exhausted")
            if not eligible:
                reasons.append("contacts_exhausted")
            if not reasons:
                a.wom, a.activation_time = WOM.PROMOTER_ACTIVE, t
                a.generation = self.agents[a.parent].generation + 1
            a.inactivity_reasons = tuple(reasons)
            self.activation_events.append({
                "period": t, "agent": a.id, "purchase_time": a.purchase_time,
                "experience_time": a.experience_time, "parent": a.parent,
                "parent_generation": self.agents[a.parent].generation, "generation": a.generation,
                "positive_energy": a.positive_energy, "eligible_contacts": eligible,
                "activated": not reasons, "inactivity_reasons": json.dumps(reasons)})

    def next_sender_ids(self):
        """Sender snapshot for the next period, including scheduled activations."""
        t = self.time + 1
        return [a.id for a in self.agents if a.wom == WOM.PROMOTER_ACTIVE or
                (a.wom == WOM.PROMOTER_POTENTIAL and a.experience_time + 1 == t
                 and a.positive_energy > self.state.config.energy_threshold
                 and self.state.eligible_contacts(a.id, "positive"))]

    def _transaction_ledgers(self):
        return (self.experience_events, self.activation_events, self.events,
                self.decisions, self.system, self.agent_history)

    def step(self, sender_order=None):
        if self.time >= self.dynamics.periods:
            raise ValueError("Configured horizon already reached")
        # Work on a copy so a bad draw or sender order cannot partly commit M3.
        before = self.state
        ledgers = self._transaction_ledgers()
        lengths = [len(x) for x in ledgers]
        self.state = InitialState(before.config, before.environment, deepcopy(before.agents), before.time)
        try:
            self._advance_lifecycle(self.time + 1)
            return super().step(sender_order)
        except Exception:
            self.state = before
            for ledger, length in zip(ledgers, lengths):
                del ledger[length:]
            raise

    def _system_row(self, new_purchases, new_events, new_reach, deactivated):
        row = super()._system_row(new_purchases, new_events, new_reach, deactivated)
        new_experience = [e for e in self.experience_events if e["period"] == self.time]
        new_activation = [e for e in self.activation_events if e["period"] == self.time]
        attempted = {e["agent"] for e in self.activation_events}
        row.update({
            "new_experiences": len(new_experience),
            "new_satisfied_customers": sum(e["experience"] == Experience.SATISFIED for e in new_experience),
            "new_dissatisfied_customers": sum(e["experience"] == Experience.DISSATISFIED for e in new_experience),
            "new_potential_promoters": sum(e["positive_disposition"] for e in new_experience),
            "activation_attempts": len(new_activation),
            "blocked_activations": sum(not e["activated"] for e in new_activation),
            "new_promoters": sum(e["activated"] for e in new_activation),
            "cumulative_new_experiences": len(self.experience_events),
            "cumulative_new_promoters": sum(e["activated"] for e in self.activation_events),
            "cumulative_blocked_activations": sum(not e["activated"] for e in self.activation_events),
            "pending_activation_promoters": sum(a.wom == WOM.PROMOTER_POTENTIAL and a.id not in attempted for a in self.agents),
            "max_promoter_generation": max((a.generation for a in self.agents if a.generation is not None), default=None),
            "diffusion_class": "not_evaluated_m3"})
        return row

    def agent_rows(self):
        attempts = {e["agent"]: e for e in self.activation_events}
        rows = super().agent_rows()
        for row in rows:
            a = self.agents[row["id"]]
            attempt = attempts.get(a.id)
            row["scheduled_activation_time"] = (a.experience_time + 1
                                                if a.positive_eligible and not a.initial_customer else None)
            row["activation_attempt_time"] = attempt["period"] if attempt else None
            row["activation_status"] = ("initial" if a.initial_promoter else
                                        "activated" if attempt and attempt["activated"] else
                                        "blocked" if attempt else
                                        "pending" if a.positive_eligible else "not_scheduled")
        return rows

    def lineage_rows(self):
        rows = []
        for row in self.agent_rows():
            a = self.agents[row["id"]]
            if a.initial_customer or a.purchase_time is None:
                continue
            root = a.parent
            seen = {a.id}
            while not self.agents[root].initial_promoter:
                require(root not in seen, "Cyclic attribution lineage")
                seen.add(root)
                root = self.agents[root].parent
                require(root is not None, "Lineage missing an initial promoter root")
            rows.append({"agent": a.id, "parent": a.parent,
                         "parent_generation": self.agents[a.parent].generation, "initial_root": root,
                         **{key: row[key] for key in LINEAGE_COLUMNS if key not in
                            ("agent", "parent", "parent_generation", "initial_root")}})
        return rows

    def summary(self):
        return {**super().summary(), "scope": "M3 positive WOM, purchase, experience and promoter formation",
                "experience_dynamics_enabled": True, "new_promoter_formation_enabled": True}

    def _validate_sender(self, a, event):
        t = event["period"]
        require(a.activation_time is not None and a.activation_time <= t and
                (a.deactivation_time is None or a.deactivation_time >= t), "Message outside active interval")
        require(a.generation is not None and a.positive_eligible and
                a.experience == Experience.SATISFIED, "Ineligible sender")
        require(event["sender_energy"] == self._sender_energy_at_period(a, t), "Sender energy mismatch")

    def _sender_energy_at_period(self, agent, period):
        return agent.positive_energy

    def _validate_deactivation(self, agent):
        require(agent.inactivity_reasons == ("contacts_exhausted",) and
                not self.state.eligible_contacts(agent.id, "positive"), "Invalid promoter deactivation")

    def _validate_energy(self, a, original):
        expected = (original.positive_energy if a.initial_customer else
                    self.experience_config.new_promoter_energy if a.positive_eligible else 0.0)
        require(a.positive_energy == expected and a.negative_energy == original.negative_energy,
                "Unexpected energy change in M3")

    def _validate_purchase(self, a, d):
        require(a.purchase_time == d["period"] and a.parent == d["parent"], "Purchase-state mismatch")
        if a.purchase_time == self.time:
            require(a.commercial == Commercial.PENDING and a.experience_time is None and
                    a.experience == Experience.UNEVALUATED and a.wom == WOM.NONE and
                    a.generation is None and not a.positive_eligible, "Premature experience/promotion")
        else:
            require(a.commercial == Commercial.EXPERIENCED and a.experience_time == a.purchase_time + 1,
                    "Experience must occur exactly one period after purchase")

    def validate(self):
        super().validate()
        cfg = self.experience_config
        experiences, attempts = {}, {}
        for e in self.experience_events:
            a = self.agents[e["agent"]]
            require(a.id not in experiences and not a.initial_customer and a.purchase_time is not None,
                    "Repeated or unpurchased experience")
            experiences[a.id] = e
            require(e["period"] == a.experience_time == a.purchase_time + 1 <= self.time and
                    e["purchase_time"] == a.purchase_time and e["parent"] == a.parent,
                    "Experience schedule/parent mismatch")
            noise, raw, satisfaction, experience = assess_experience(a.traits.fit, e["noise_draw"], cfg)
            require(e["fit"] == a.traits.fit and e["quality"] == cfg.quality and
                    (e["noise"], e["raw_satisfaction"], e["satisfaction"], e["experience"]) ==
                    (noise, raw, satisfaction, experience), "Experience assessment mismatch")
            require(a.satisfaction == satisfaction and a.experience == experience, "Experience state mismatch")
            u = e["disposition_draw"]
            if experience == Experience.SATISFIED:
                require(type(u) in (int, float) and math.isfinite(u) and 0 <= u < 1,
                        "Missing/invalid disposition draw")
                disposition = u < cfg.promoter_disposition_probability
            else:
                require(u is None, "Disposition drawn for non-satisfied customer")
                disposition = False
            require(e["positive_disposition_probability"] == cfg.promoter_disposition_probability and
                    e["positive_disposition"] == a.positive_eligible == disposition and
                    e["scheduled_activation_time"] == (e["period"] + 1 if disposition else None),
                    "Disposition/schedule mismatch")
        for e in self.activation_events:
            a = self.agents[e["agent"]]
            require(a.id not in attempts and a.id in experiences and a.positive_eligible,
                    "Repeated or unscheduled activation")
            attempts[a.id] = e
            require(e["period"] == a.purchase_time + 2 <= self.time and e["experience_time"] == a.experience_time
                    and e["purchase_time"] == a.purchase_time and e["parent"] == a.parent,
                    "Activation must occur exactly two periods after purchase")
            # Susceptibles at the start of activation period, before this batch's purchases.
            eligible = sum(not self.agents[j].initial_customer and
                           (self.agents[j].purchase_time is None or self.agents[j].purchase_time >= e["period"])
                           for j in self.state.environment.network.neighbors[a.id])
            reasons = []
            activation_energy = cfg.new_promoter_energy
            if activation_energy <= self.state.config.energy_threshold:
                reasons.append("energy_exhausted")
            if not eligible:
                reasons.append("contacts_exhausted")
            require(e["eligible_contacts"] == eligible and e["positive_energy"] == activation_energy and
                    e["inactivity_reasons"] == json.dumps(reasons) and e["activated"] == (not reasons),
                    "Activation eligibility mismatch")
            parent = self.agents[a.parent]
            require(parent.generation is not None and parent.activation_time is not None and
                    parent.activation_time <= a.purchase_time, "Invalid parent chronology")
            require(e["parent_generation"] == parent.generation, "Parent generation mismatch")
            if e["activated"]:
                require(a.activation_time == e["period"] and a.generation == e["generation"] == parent.generation + 1,
                        "Activated promoter generation/time mismatch")
                require(a.wom in (WOM.PROMOTER_ACTIVE, WOM.PROMOTER_FATIGUED), "Lost activated promoter")
            else:
                require(a.wom == WOM.PROMOTER_POTENTIAL and a.activation_time is None and
                        a.generation is None and e["generation"] is None and a.deactivation_time is None and
                        a.inactivity_reasons == tuple(reasons), "Failed activation must remain potential")
        expected_experiences = {a.id for a in self.agents if not a.initial_customer and
                                a.purchase_time is not None and a.purchase_time + 1 <= self.time}
        expected_attempts = {a.id for a in self.agents if not a.initial_customer and
                             a.positive_eligible and a.purchase_time + 2 <= self.time}
        require(set(experiences) == expected_experiences, "Missing experience events")
        require(set(attempts) == expected_attempts, "Missing activation attempts")
        for a, original in zip(self.agents, self.initial.agents):
            if a.initial_customer:
                require(a.parent is None and a.generation == original.generation and
                        a.purchase_time == a.experience_time == 0 and
                        a.activation_time == original.activation_time and
                        a.positive_eligible == original.positive_eligible and
                        a.negative_eligible == original.negative_eligible, "Changed initial lifecycle")
            else:
                require(not a.negative_eligible and a.wom not in
                        (WOM.DETRACTOR_POTENTIAL, WOM.DETRACTOR_ACTIVE, WOM.DETRACTOR_INACTIVE),
                        "New negative WOM role in M3")
                if not a.positive_eligible:
                    require(a.wom == WOM.NONE and a.activation_time is None and a.generation is None and
                            a.deactivation_time is None and not a.inactivity_reasons, "Spontaneous promoter")
                elif a.id not in attempts:
                    require(a.wom == WOM.PROMOTER_POTENTIAL and a.activation_time is None and
                            a.generation is None and not a.inactivity_reasons and a.deactivation_time is None,
                            "Premature activation or blocking")
            if a.wom == WOM.PROMOTER_ACTIVE:
                require(a.deactivation_time is None and not a.inactivity_reasons, "Active promoter marked inactive")
            elif a.activation_time is not None and a.positive_eligible:
                require(a.wom == WOM.PROMOTER_FATIGUED and a.deactivation_time is not None and
                        a.activation_time <= a.deactivation_time <= self.time, "Invalid promoter deactivation time")
                self._validate_deactivation(a)
        counts = Counter(e["period"] for e in self.experience_events)
        formed = Counter(e["period"] for e in self.activation_events if e["activated"])
        blocked = Counter(e["period"] for e in self.activation_events if not e["activated"])
        bought = Counter(d["period"] for d in self.decisions if d["adopted"])
        events = Counter(e["period"] for e in self.events)
        customers = self.state.config.initial_customers
        active = sum(a.wom == WOM.PROMOTER_ACTIVE for a in self.initial.agents)
        cumulative_formed = cumulative_experienced = 0
        for t, row in enumerate(self.system):
            require(row["time"] == t and row["new_promoters"] == formed[t] and
                    row["new_experiences"] == counts[t] and row["blocked_activations"] == blocked[t] and
                    row["activation_attempts"] == formed[t] + blocked[t] and
                    row["new_purchases"] == bought[t] and row["positive_events"] == events[t],
                    "System/lifecycle ledger mismatch")
            deactivated = sum(a.positive_eligible and a.deactivation_time == t for a in self.agents) if t else 0
            require(row["deactivated_promoters"] == deactivated, "Deactivation flow mismatch")
            active += formed[t] - deactivated
            customers += bought[t]
            cumulative_formed += formed[t]
            cumulative_experienced += counts[t]
            require(row["promoter_active"] == active and row["customers"] == customers and
                    row["customers"] + row["susceptibles"] == row["population"] == len(self.agents) and
                    row["cumulative_new_promoters"] == cumulative_formed and
                    row["cumulative_new_experiences"] == cumulative_experienced, "Population/promoter conservation failed")
        require(len(self.agent_history) == ((self.time + 1) * len(self.agents) if self.dynamics.record_agents else 0),
                "Agent history length mismatch")
        self.lineage_rows()  # Every attributed purchase must reach an initial root.
