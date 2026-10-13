"""M5: synchronous positive/negative WOM and experience-based detractor formation."""
from collections import Counter, defaultdict
from dataclasses import dataclass
import json
import math

from .config import Config
from .energy import EnergyConfig, EnergySimulation, ENERGY_COLUMNS, cause_counts, energy_after
from .experience import ExperienceConfig, EXPERIENCE_COLUMNS, ACTIVATION_COLUMNS, require
from .model import Commercial, Experience, WOM, initialize
from .positive import PositiveConfig, EVENT_COLUMNS, DECISION_COLUMNS


@dataclass(frozen=True)
class NegativeConfig:
    disposition_probability: float = .8
    new_detractor_energy: float = .6
    decay: float = .06
    message_cost: float = .04
    influence_coefficient: float = 1.2

    def validate(self):
        for key in self.__dataclass_fields__:
            value = getattr(self, key)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError(f"{key} must be finite and nonnegative")
            if key != 'influence_coefficient' and value > 1:
                raise ValueError(f"{key} must be in [0,1]")

    def energy_config(self):
        return EnergyConfig(self.decay, self.message_cost)


def mixed_adoption_probability(need, fit, positive_memory, negative_memory, has_positive,
                               dynamics=PositiveConfig(), negative=NegativeConfig(), weight=1.0):
    if not has_positive:
        return 0.0
    hp, hn = -math.expm1(-positive_memory), -math.expm1(-negative_memory)
    penalty = 0.0 if not hn or not weight else negative.influence_coefficient * hn * weight
    z = (dynamics.intercept + dynamics.need_coefficient * need + dynamics.fit_coefficient * fit +
         dynamics.positive_coefficient * hp - penalty)
    if z >= 0:
        return 1 / (1 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1 + ez)


MIXED_EVENT_COLUMNS = EVENT_COLUMNS + ['receiver_negative_exposures_before_period', 'first_negative_reach']
MIXED_DECISION_COLUMNS = DECISION_COLUMNS + ['new_negative_messages', 'negative_memory_before',
    'negative_memory_after', 'negative_influence', 'eligible_to_buy', 'probability_without_negative']
MIXED_EXPERIENCE_COLUMNS = EXPERIENCE_COLUMNS + ['negative_disposition_draw',
    'negative_disposition_probability', 'negative_disposition']
MIXED_ACTIVATION_COLUMNS = ACTIVATION_COLUMNS + ['sign', 'negative_energy']
MIXED_ENERGY_COLUMNS = ENERGY_COLUMNS + ['initial_detractor']
ACTIVE = {'positive': WOM.PROMOTER_ACTIVE, 'negative': WOM.DETRACTOR_ACTIVE}
POTENTIAL = {'positive': WOM.PROMOTER_POTENTIAL, 'negative': WOM.DETRACTOR_POTENTIAL}
INACTIVE = {'positive': WOM.PROMOTER_FATIGUED, 'negative': WOM.DETRACTOR_INACTIVE}


class MixedSimulation(EnergySimulation):
    def __init__(self, initial=None, dynamics=PositiveConfig(), experience=ExperienceConfig(),
                 energy=EnergyConfig(), negative=NegativeConfig(), draw=None):
        negative.validate()
        self.negative_config = negative
        if initial is None:
            initial = initialize(Config())
        super().__init__(initial, dynamics, experience, energy, draw)

    def _validate_initial_mode(self, initial):
        # Unlike M2–M4, M5 explicitly supports either value of the mechanism switch.
        pass

    def _advance_lifecycle(self, t):
        before = len(self.activation_events)
        super()._advance_lifecycle(t)  # Assess all new customers and activate positive potentials.
        enabled, cfg = self.state.config.negative_wom_enabled, self.negative_config
        for e in self.experience_events:
            if e['period'] != t:
                continue
            a = self.agents[e['agent']]
            u = self._draw(a.id, t, 'negative_disposition') if enabled and a.experience == Experience.DISSATISFIED else None
            disposition = u is not None and u < cfg.disposition_probability
            e.update(negative_disposition_draw=u, negative_disposition_probability=cfg.disposition_probability,
                     negative_disposition=disposition)
            if disposition:
                a.negative_eligible, a.wom = True, WOM.DETRACTOR_POTENTIAL
                a.negative_energy = cfg.new_detractor_energy
                e['scheduled_activation_time'] = t + 1
        for e in self.activation_events[before:]:
            e.update(sign='positive', negative_energy=0.0)
        if enabled:
            for a in self.agents:
                if a.wom != WOM.DETRACTOR_POTENTIAL or a.experience_time + 1 != t:
                    continue
                eligible = len(self.state.eligible_contacts(a.id, 'negative'))
                reasons = []
                if a.negative_energy <= self.state.config.energy_threshold:
                    reasons.append('energy_exhausted')
                if not eligible:
                    reasons.append('contacts_exhausted')
                if not reasons:
                    a.wom, a.activation_time = WOM.DETRACTOR_ACTIVE, t
                a.inactivity_reasons = tuple(reasons)
                self.activation_events.append({
                    'period': t, 'agent': a.id, 'purchase_time': a.purchase_time, 'experience_time': a.experience_time,
                    'parent': a.parent, 'parent_generation': self.agents[a.parent].generation, 'generation': None,
                    'positive_energy': 0.0, 'negative_energy': a.negative_energy, 'eligible_contacts': eligible,
                    'activated': not reasons, 'inactivity_reasons': json.dumps(reasons), 'sign': 'negative'})
        self.activation_events[before:] = sorted(self.activation_events[before:], key=lambda e: e['agent'])

    def next_sender_ids(self):
        t = self.time + 1
        ids = []
        for a in self.agents:
            for sign in ACTIVE:
                if sign == 'negative' and not self.state.config.negative_wom_enabled:
                    continue
                if a.wom == ACTIVE[sign] or (a.wom == POTENTIAL[sign] and a.experience_time + 1 == t and
                    getattr(a, sign + '_energy') > self.state.config.energy_threshold and self.state.eligible_contacts(a.id, sign)):
                    ids.append(a.id)
        return ids

    def _step_batch(self, sender_order=None):
        t = self.time + 1
        susceptible = {a.id for a in self.agents if a.commercial == Commercial.SUSCEPTIBLE}
        active = [a.id for a in self.agents if a.wom in ACTIVE.values()]
        order = active if sender_order is None else list(sender_order)
        if len(order) != len(active) or set(order) != set(active):
            raise ValueError('sender_order must permute all active positive and negative senders')
        planned = []
        for i in order:
            a = self.agents[i]
            sign = 'positive' if a.wom == WOM.PROMOTER_ACTIVE else 'negative'
            energy = getattr(a, sign + '_energy')
            candidates = sorted((self.state.environment.network.neighbors[i] & susceptible) - getattr(a, 'contacted_' + sign))
            for slot in range(self.dynamics.opportunities):
                if not candidates:
                    break
                u = self._draw(i, t, sign + '_opportunity', slot)
                if u >= self.dynamics.opportunity_factor * energy:
                    continue
                v = self._draw(i, t, sign + '_target', slot)
                j = candidates.pop(int(v * len(candidates)))
                planned.append({'event_id': f'{sign[0]}{t:04d}-s{i:06d}-k{slot:03d}', 'period': t,
                    'sign': sign, 'sender': i, 'receiver': j, 'slot': slot, 'sender_community': a.community,
                    'receiver_community': self.agents[j].community, 'sender_energy': energy,
                    'sender_credibility': a.traits.credibility, 'opportunity_draw': u, 'target_draw': v,
                    'receiver_positive_exposures_before_period': self.agents[j].positive_exposures,
                    'receiver_negative_exposures_before_period': self.agents[j].negative_exposures})
        planned.sort(key=lambda e: (e['sender'], e['slot']))
        incoming = defaultdict(list)
        for e in planned:
            incoming[(e['receiver'], e['sign'])].append(e)
        memories, trials = {}, []
        for j in sorted(susceptible):
            a = self.agents[j]
            pos, neg = incoming[(j, 'positive')], incoming[(j, 'negative')]
            lp = self.dynamics.memory_retention * a.positive_memory + math.fsum(e['sender_credibility'] for e in pos)
            ln = self.dynamics.memory_retention * a.negative_memory + math.fsum(e['sender_credibility'] for e in neg)
            memories[j] = (lp, ln)
            if not pos and not neg:
                continue
            probability = mixed_adoption_probability(a.traits.need, a.traits.fit, lp, ln, bool(pos),
                self.dynamics, self.negative_config, self.state.config.negative_weight)
            u = self._draw(j, t, 'purchase', 0) if pos else None
            adopted = u is not None and u < probability
            parent = min(pos, key=lambda e: (-e['sender_credibility'], e['sender']))['sender'] if adopted else None
            trials.append({'period': t, 'receiver': j, 'community': a.community,
                'new_positive_messages': len(pos), 'new_negative_messages': len(neg),
                'positive_memory_before': a.positive_memory, 'positive_memory_after': lp, 'positive_influence': -math.expm1(-lp),
                'negative_memory_before': a.negative_memory, 'negative_memory_after': ln, 'negative_influence': -math.expm1(-ln),
                'eligible_to_buy': bool(pos), 'probability': probability, 'probability_without_negative':
                    mixed_adoption_probability(a.traits.need, a.traits.fit, lp, ln, bool(pos), self.dynamics, self.negative_config, 0),
                'purchase_draw': u, 'adopted': adopted, 'parent': parent, 'scheduled_experience_time': t + 1 if adopted else None})
        buyers = {d['receiver']: d['parent'] for d in trials if d['adopted']}
        first_reached = {'positive': set(), 'negative': set()}
        for e in planned:
            i, j, sign = e['sender'], e['receiver'], e['sign']
            for s in ACTIVE:
                first = (s == sign and e['receiver_' + s + '_exposures_before_period'] == 0 and j not in first_reached[s])
                e['first_' + s + '_reach'] = first
                if first:
                    first_reached[s].add(j)
            e['receiver_bought_this_period'] = j in buyers
            e['credited_purchase_parent'] = sign == 'positive' and j in buyers and buyers[j] == i
            getattr(self.agents[i], 'contacted_' + sign).add(j)
            setattr(self.agents[j], sign + '_exposures', getattr(self.agents[j], sign + '_exposures') + 1)
        for j, (lp, ln) in memories.items():
            self.agents[j].positive_memory, self.agents[j].negative_memory = lp, ln
        for j, parent in buyers.items():
            a = self.agents[j]
            a.commercial, a.purchase_time, a.parent = Commercial.PENDING, t, parent
        self._close_period(t, active, planned)
        self.state.time = t
        self.events.extend(planned)
        self.decisions.extend(trials)
        self.system.append(self._system_row(0, 0, 0, 0))
        if self.dynamics.record_agents:
            self.agent_history.extend(self.agent_rows())
        return dict(self.system[-1])

    def _close_period(self, period, active, messages):
        positive = [i for i in active if self.agents[i].wom == WOM.PROMOTER_ACTIVE]
        before = len(self.energy_updates)
        super()._close_period(period, positive, [e for e in messages if e['sign'] == 'positive'])
        for r in self.energy_updates[before:]:
            r['initial_detractor'] = False
        counts = Counter(e['sender'] for e in messages if e['sign'] == 'negative')
        cfg = self.negative_config.energy_config()
        for i in active:
            a = self.agents[i]
            if i in positive:
                continue
            energy, sent = a.negative_energy, counts[i]
            after_decay = (1 - cfg.decay) * energy
            after = energy_after(energy, sent, cfg)
            remaining = len(self.state.eligible_contacts(i, 'negative'))
            reasons = []
            if after <= self.state.config.energy_threshold:
                reasons.append('energy_exhausted')
            if not remaining:
                reasons.append('contacts_exhausted')
            a.negative_energy = after
            if reasons:
                a.wom, a.deactivation_time = WOM.DETRACTOR_INACTIVE, period
                a.inactivity_reasons = tuple(reasons)
            self.energy_updates.append({'period': period, 'agent': i, 'sign': 'negative', 'initial_promoter': False,
                'initial_detractor': a.initial_detractor, 'generation': None, 'activated_this_period': a.activation_time == period,
                'energy_before': energy, 'decay_rate': cfg.decay, 'decay_loss': energy - after_decay,
                'energy_after_decay': after_decay, 'messages_sent': sent, 'message_cost': cfg.message_cost,
                'message_cost_requested': cfg.message_cost * sent, 'unclipped_energy': after_decay - cfg.message_cost * sent,
                'energy_after': after, 'realized_loss': energy - after, 'remaining_contacts': remaining,
                'energy_exhausted': after <= self.state.config.energy_threshold, 'contacts_exhausted': remaining == 0,
                'deactivated': bool(reasons), 'inactivity_reasons': json.dumps(reasons)})
        self.energy_updates[before:] = sorted(self.energy_updates[before:], key=lambda r: r['agent'])

    def agent_rows(self):
        rows = super().agent_rows()
        for row in rows:
            a = self.agents[row['id']]
            row['aware'] = a.positive_exposures + a.negative_exposures > 0
            row['remaining_negative_contacts'] = len(self.state.eligible_contacts(a.id, 'negative'))
            if a.negative_eligible and not a.initial_customer:
                row['scheduled_activation_time'] = a.experience_time + 1
                if row['activation_attempt_time'] is None:
                    row['activation_status'] = 'pending'
            if a.initial_detractor:
                row['activation_status'] = 'initial'
        return rows

    def _system_row(self, *unused):
        t = self.time
        row = self.state.summary()
        new_exp = [e for e in self.experience_events if e['period'] == t]
        row.update(new_purchases=sum(d['adopted'] and d['period'] == t for d in self.decisions),
            cumulative_new_purchases=sum(d['adopted'] for d in self.decisions),
            new_experiences=len(new_exp), cumulative_new_experiences=len(self.experience_events),
            new_satisfied_customers=sum(e['experience'] == Experience.SATISFIED for e in new_exp),
            new_dissatisfied_customers=sum(e['experience'] == Experience.DISSATISFIED for e in new_exp),
            pending_experience_customers=sum(a.commercial == Commercial.PENDING for a in self.agents),
            max_promoter_generation=max((a.generation for a in self.agents if a.generation is not None), default=None),
            diffusion_class='not_evaluated_m5')
        for sign, noun in (('positive', 'promoters'), ('negative', 'detractors')):
            prefix = '' if sign == 'positive' else 'negative_'
            events = [e for e in self.events if e['sign'] == sign]
            updates = [e for e in self.energy_updates if e['sign'] == sign]
            current = [e for e in updates if e['period'] == t]
            attempts = [e for e in self.activation_events if e['sign'] == sign]
            now = [e for e in attempts if e['period'] == t]
            attempted = {e['agent'] for e in attempts}
            active = [a for a in self.agents if a.wom == ACTIVE[sign]]
            unique = sum(getattr(a, sign + '_exposures') > 0 for a in self.agents)
            potentials = sum(e[sign + '_disposition'] for e in new_exp)
            assignment = (self.experience_config.new_promoter_energy if sign == 'positive' else self.negative_config.new_detractor_energy)
            row.update({sign + '_events': sum(e['period'] == t for e in events),
                'cumulative_' + sign + '_events': len(events), 'cumulative_unique_' + sign + '_recipients': unique,
                'new_unique_' + sign + '_recipients': sum(e['period'] == t and e['first_' + sign + '_reach'] for e in events),
                'cumulative_' + sign + '_redundancy': 1 - unique / len(events) if events else None,
                'new_potential_' + noun: potentials, 'new_' + noun: sum(e['activated'] for e in now),
                'cumulative_new_' + noun: sum(e['activated'] for e in attempts),
                prefix + 'activation_attempts': len(now), prefix + 'blocked_activations': sum(not e['activated'] for e in now),
                'cumulative_' + prefix + 'blocked_activations': sum(not e['activated'] for e in attempts),
                'pending_activation_' + noun: sum(a.wom == POTENTIAL[sign] and a.id not in attempted for a in self.agents),
                'deactivated_' + noun: sum(e['deactivated'] for e in current), 'energy_updated_' + noun: len(current),
                sign + '_energy_assigned': potentials * assignment,
                sign + '_decay_loss': math.fsum(e['decay_loss'] for e in current),
                sign + '_message_cost_requested': math.fsum(e['message_cost_requested'] for e in current),
                sign + '_energy_loss': math.fsum(e['realized_loss'] for e in current),
                'cumulative_' + sign + '_energy_loss': math.fsum(e['realized_loss'] for e in updates),
                sign + '_energy_total': math.fsum(getattr(a, sign + '_energy') for a in self.agents),
                sign + '_energy_active': math.fsum(getattr(a, sign + '_energy') for a in active),
                'mean_' + sign + '_energy_active': math.fsum(getattr(a, sign + '_energy') for a in active) / len(active) if active else None})
            row.update({prefix + k: v for k, v in cause_counts(current).items()})
            row.update({'cumulative_' + prefix + k: v for k, v in cause_counts(updates).items()})
        return row

    def summary(self):
        return {'scope': 'M5 mixed WOM, experience, promoters, detractors and energy fatigue',
            'completed_periods': self.time, 'configured_periods': self.dynamics.periods,
            'negative_wom_enabled': self.state.config.negative_wom_enabled, 'energy_dynamics_enabled': True,
            'experience_dynamics_enabled': True, 'new_promoter_formation_enabled': True,
            'new_detractor_formation_enabled': self.state.config.negative_wom_enabled,
            'custom_draw_function': self.custom_draw, **self.system[-1]}

    def validate(self):
        from .mixed_validation import validate_mixed
        validate_mixed(self)
