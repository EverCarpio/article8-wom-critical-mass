"""M4: end-of-period positive-energy decay, message cost and irreversible fatigue."""
from collections import Counter, defaultdict
from dataclasses import dataclass
import json
import math

from .experience import ExperienceConfig, ExperienceSimulation, require
from .model import WOM
from .positive import PositiveConfig


@dataclass(frozen=True)
class EnergyConfig:
    decay: float = .06
    message_cost: float = .04

    def validate(self):
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be finite in [0,1]")


def energy_after(energy, messages, config=EnergyConfig()):
    """One active period; attempts without a sent message incur no message cost."""
    config.validate()
    if type(energy) not in (int, float) or not math.isfinite(energy) or not 0 <= energy <= 1:
        raise ValueError("energy must be finite in [0,1]")
    if type(messages) is not int or messages < 0:
        raise ValueError("messages must be a nonnegative integer")
    return max(0.0, (1 - config.decay) * energy - config.message_cost * messages)


ENERGY_COLUMNS = ["period", "agent", "sign", "initial_promoter", "generation", "activated_this_period",
                  "energy_before", "decay_rate", "decay_loss", "energy_after_decay", "messages_sent",
                  "message_cost", "message_cost_requested", "unclipped_energy", "energy_after", "realized_loss",
                  "remaining_contacts", "energy_exhausted", "contacts_exhausted", "deactivated", "inactivity_reasons"]


def cause_counts(rows):
    """Exclusive causes add to exits; inclusive indicators deliberately overlap."""
    energy_only = sum(r["energy_exhausted"] and not r["contacts_exhausted"] for r in rows)
    contacts_only = sum(r["contacts_exhausted"] and not r["energy_exhausted"] for r in rows)
    both = sum(r["energy_exhausted"] and r["contacts_exhausted"] for r in rows)
    return {"deactivated_energy_only": energy_only, "deactivated_contacts_only": contacts_only,
            "deactivated_both": both, "deactivated_by_energy": energy_only + both,
            "deactivated_by_contacts": contacts_only + both}


class EnergySimulation(ExperienceSimulation):
    def __init__(self, initial=None, dynamics=PositiveConfig(), experience=ExperienceConfig(),
                 energy=EnergyConfig(), draw=None):
        energy.validate()
        self.energy_config = energy
        self.energy_updates = []
        super().__init__(initial, dynamics, experience, draw)

    def _transaction_ledgers(self):
        return super()._transaction_ledgers() + (self.energy_updates,)

    def _close_period(self, period, active, messages):
        counts = Counter(e["sender"] for e in messages)
        cfg = self.energy_config
        deactivated = 0
        # active is the snapshot after scheduled activations and before all messages.
        for i in active:
            a = self.agents[i]
            before, sent = a.positive_energy, counts[i]
            after_decay = (1 - cfg.decay) * before
            requested_cost = cfg.message_cost * sent
            after = energy_after(before, sent, cfg)
            remaining = len(self.state.eligible_contacts(i, "positive"))
            energy_exhausted = after <= self.state.config.energy_threshold
            contacts_exhausted = remaining == 0
            reasons = []
            if energy_exhausted:
                reasons.append("energy_exhausted")
            if contacts_exhausted:
                reasons.append("contacts_exhausted")
            a.positive_energy = after
            if reasons:
                a.wom, a.deactivation_time = WOM.PROMOTER_FATIGUED, period
                a.inactivity_reasons = tuple(reasons)
                deactivated += 1
            self.energy_updates.append({
                "period": period, "agent": i, "sign": "positive", "initial_promoter": a.initial_promoter,
                "generation": a.generation, "activated_this_period": a.activation_time == period,
                "energy_before": before, "decay_rate": cfg.decay, "decay_loss": before - after_decay,
                "energy_after_decay": after_decay, "messages_sent": sent, "message_cost": cfg.message_cost,
                "message_cost_requested": requested_cost, "unclipped_energy": after_decay - requested_cost,
                "energy_after": after, "realized_loss": before - after, "remaining_contacts": remaining,
                "energy_exhausted": energy_exhausted, "contacts_exhausted": contacts_exhausted,
                "deactivated": bool(reasons), "inactivity_reasons": json.dumps(reasons)})
        return deactivated

    def _system_row(self, new_purchases, new_events, new_reach, deactivated):
        row = super()._system_row(new_purchases, new_events, new_reach, deactivated)
        current = [r for r in self.energy_updates if r["period"] == self.time]
        active = [a for a in self.agents if a.wom == WOM.PROMOTER_ACTIVE]
        row.update(cause_counts(current))
        row.update({"cumulative_" + key: value for key, value in cause_counts(self.energy_updates).items()})
        row.update({
            "energy_updated_promoters": len(current),
            "positive_energy_assigned": row["new_potential_promoters"] * self.experience_config.new_promoter_energy,
            "positive_decay_loss": math.fsum(r["decay_loss"] for r in current),
            "positive_message_cost_requested": math.fsum(r["message_cost_requested"] for r in current),
            "positive_energy_loss": math.fsum(r["realized_loss"] for r in current),
            "cumulative_positive_energy_loss": math.fsum(r["realized_loss"] for r in self.energy_updates),
            "positive_energy_total": math.fsum(a.positive_energy for a in self.agents),
            "positive_energy_active": math.fsum(a.positive_energy for a in active),
            "mean_positive_energy_active": math.fsum(a.positive_energy for a in active) / len(active) if active else None,
            "diffusion_class": "not_evaluated_m4"})
        return row

    def summary(self):
        return {**super().summary(), "scope": "M4 positive WOM, experience, promoter formation and energy fatigue",
                "energy_dynamics_enabled": True}

    def _sender_energy_at_period(self, agent, period):
        row = self._validation_energy.get((period, agent.id))
        require(row is not None, "Message missing its energy-period record")
        return row["energy_before"]

    def _validate_energy(self, agent, original):
        require(agent.positive_energy == self._validation_final_energy[agent.id] and
                agent.negative_energy == original.negative_energy, "Energy trajectory/freeze mismatch")

    def _validate_deactivation(self, agent):
        row = self._validation_energy.get((agent.deactivation_time, agent.id))
        require(row is not None and row["deactivated"] and
                tuple(json.loads(row["inactivity_reasons"])) == agent.inactivity_reasons,
                "Deactivation reason mismatch")

    def validate(self):
        cfg, threshold = self.energy_config, self.state.config.energy_threshold
        cfg.validate()
        index, by_agent, by_period = {}, defaultdict(list), defaultdict(list)
        for row in self.energy_updates:
            key = (row["period"], row["agent"])
            require(key not in index and type(key[0]) is int and 1 <= key[0] <= self.time and
                    type(key[1]) is int and 0 <= key[1] < len(self.agents), "Repeated/invalid energy-period record")
            index[key] = row
            by_agent[key[1]].append(row)
            by_period[key[0]].append(row)
        require(list(index) == sorted(index), "Energy records not in canonical order")
        expected_keys = set()
        final_energy = {}
        message_counts = Counter((e["period"], e["sender"]) for e in self.events)
        contacted_at = {(e["sender"], e["receiver"]): e["period"] for e in self.events}
        for a, original in zip(self.agents, self.initial.agents):
            expected = (original.positive_energy if a.initial_customer else
                        self.experience_config.new_promoter_energy if a.positive_eligible else 0.0)
            if a.activation_time is not None and a.positive_eligible:
                end = a.deactivation_time if a.deactivation_time is not None else self.time
                expected_keys.update((t, a.id) for t in range(max(1, a.activation_time), end + 1))
            for r in by_agent[a.id]:
                t = r["period"]
                require(r["energy_before"] == expected and expected > threshold, "Energy start/freeze mismatch")
                sent = message_counts[(t, a.id)]
                after_decay = (1 - cfg.decay) * expected
                after = max(0.0, after_decay - cfg.message_cost * sent)
                require(r["sign"] == "positive" and r["initial_promoter"] == a.initial_promoter and
                        r["generation"] == a.generation and r["activated_this_period"] == (a.activation_time == t),
                        "Energy record role mismatch")
                require((r["messages_sent"], r["decay_rate"], r["message_cost"], r["decay_loss"],
                         r["energy_after_decay"], r["message_cost_requested"], r["unclipped_energy"],
                         r["energy_after"], r["realized_loss"]) ==
                        (sent, cfg.decay, cfg.message_cost, expected - after_decay,
                         after_decay, cfg.message_cost * sent, after_decay - cfg.message_cost * sent,
                         after, expected - after), "Energy equation/message-cost mismatch")
                # Reconstruct eligible contacts at this historical close, not at final time.
                remaining = sum(not self.agents[j].initial_customer and
                                (self.agents[j].purchase_time is None or self.agents[j].purchase_time > t) and
                                contacted_at.get((a.id, j), self.time + 1) > t
                                for j in self.state.environment.network.neighbors[a.id])
                reasons = []
                if after <= threshold:
                    reasons.append("energy_exhausted")
                if remaining == 0:
                    reasons.append("contacts_exhausted")
                require(r["remaining_contacts"] == remaining and r["energy_exhausted"] == (after <= threshold) and
                        r["contacts_exhausted"] == (remaining == 0) and r["deactivated"] == bool(reasons) and
                        r["inactivity_reasons"] == json.dumps(reasons), "Historical fatigue cause mismatch")
                require(r["deactivated"] == (a.deactivation_time == t), "Fatigue transition/time mismatch")
                expected = after
            final_energy[a.id] = expected
        require(set(index) == expected_keys, "Missing active period or update of inactive agent")
        # Parent-class reconciliation now uses historical, not final, energy values.
        self._validation_energy, self._validation_final_energy = index, final_energy
        try:
            super().validate()
        finally:
            del self._validation_energy, self._validation_final_energy
        total = math.fsum(a.positive_energy for a in self.initial.agents)
        cumulative_loss = 0.0
        cumulative_causes = Counter()
        def close(left, right):
            return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-10)
        for t, row in enumerate(self.system):
            updates = by_period[t]
            causes = cause_counts(updates)
            cumulative_causes.update(causes)
            require(all(row[key] == value and row["cumulative_" + key] == cumulative_causes[key]
                        for key, value in causes.items()), "System fatigue causes mismatch")
            require(causes["deactivated_energy_only"] + causes["deactivated_contacts_only"] +
                    causes["deactivated_both"] == row["deactivated_promoters"], "Fatigue exits double-counted")
            require(row["energy_updated_promoters"] == len(updates), "System energy update count mismatch")
            assigned = sum(e["positive_disposition"] for e in self.experience_events if e["period"] == t) * self.experience_config.new_promoter_energy
            loss = math.fsum(r["realized_loss"] for r in updates)
            cumulative_loss += loss
            total += assigned - loss
            active_energies = ([a.positive_energy for a in self.initial.agents if a.wom == WOM.PROMOTER_ACTIVE]
                               if t == 0 else [r["energy_after"] for r in updates if not r["deactivated"]])
            active_total = math.fsum(active_energies)
            mean = active_total / len(active_energies) if active_energies else None
            require(row["positive_energy_assigned"] == assigned and close(row["positive_energy_loss"], loss) and
                    close(row["cumulative_positive_energy_loss"], cumulative_loss) and
                    close(row["positive_energy_total"], total) and close(row["positive_energy_active"], active_total) and
                    row["mean_positive_energy_active"] == mean and
                    close(row["positive_decay_loss"], math.fsum(r["decay_loss"] for r in updates)) and
                    close(row["positive_message_cost_requested"], math.fsum(r["message_cost_requested"] for r in updates)),
                    "System energy balance mismatch")
