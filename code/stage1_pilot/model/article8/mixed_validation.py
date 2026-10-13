"""Independent ledger reconciliation for both WOM signs, lifecycle and energy."""
from collections import Counter, defaultdict
import json
import math

from .energy import cause_counts
from .experience import assess_experience, require
from .model import Commercial, Experience, WOM


def validate_mixed(sim):
    from .mixed import ACTIVE, POTENTIAL, INACTIVE, mixed_adoption_probability
    sim.initial.validate()
    sim.dynamics.validate(); sim.experience_config.validate(); sim.energy_config.validate(); sim.negative_config.validate()
    cfg, dyn, exp, neg = sim.state.config, sim.dynamics, sim.experience_config, sim.negative_config
    agents, n, end = sim.agents, sim.state.config.n, sim.time
    require(sim.state.config == sim.initial.config and sim.state.environment == sim.initial.environment, 'Environment/config changed')
    require(len(agents) == n and [a.id for a in agents] == list(range(n)), 'Population/ids changed')
    require(type(end) is int and 0 <= end <= dyn.periods, 'Invalid horizon')
    close = lambda x, y: math.isclose(x, y, rel_tol=1e-12, abs_tol=1e-10)
    def uniform(value):
        return type(value) in (int, float) and math.isfinite(value) and 0 <= value < 1

    receipts, events_t, counts, sent, contact_time = defaultdict(list), defaultdict(list), Counter(), defaultdict(set), {}
    ids, pairs, exposures, before = set(), set(), Counter(), Counter()
    last_t = 0
    require(sim.events == sorted(sim.events, key=lambda e: (e['period'], e['sender'], e['slot'])), 'Unordered WOM events')
    for e in sim.events:
        t, i, j, sign = e['period'], e['sender'], e['receiver'], e['sign']
        require(type(t) is int and 1 <= t <= end and type(i) is int and 0 <= i < n and
                type(j) is int and 0 <= j < n and sign in ACTIVE, 'Invalid event identifiers')
        a, b = agents[i], agents[j]
        require(sign == 'positive' or cfg.negative_wom_enabled, 'Negative event with mechanism off')
        require(e['event_id'] not in ids and (i,j,sign) not in pairs, 'Repeated event/contact')
        ids.add(e['event_id']); pairs.add((i,j,sign))
        require(j in sim.state.environment.network.neighbors[i], 'Contact not a neighbor')
        require(getattr(a, sign + '_eligible') and a.activation_time is not None and a.activation_time <= t and
                (a.deactivation_time is None or a.deactivation_time >= t), 'Message outside active interval')
        require(not b.initial_customer and (b.purchase_time is None or b.purchase_time >= t), 'Contact after purchase')
        require(e['sender_credibility'] == a.traits.credibility and e['sender_community'] == a.community and
                e['receiver_community'] == b.community, 'Event traits mismatch')
        require(type(e['slot']) is int and 0 <= e['slot'] < dyn.opportunities and uniform(e['target_draw']) and
                uniform(e['opportunity_draw']) and e['sender_energy'] > cfg.energy_threshold and
                e['opportunity_draw'] < dyn.opportunity_factor * e['sender_energy'], 'Invalid opportunity')
        require(e['event_id'] == f'{sign[0]}{t:04d}-s{i:06d}-k{e["slot"]:03d}', 'Event id mismatch')
        if t != last_t:
            before = exposures.copy(); last_t = t
        for s in ACTIVE:
            require(e['receiver_' + s + '_exposures_before_period'] == before[(j,s)], 'Exposure-before mismatch')
            require(e['first_' + s + '_reach'] == (s == sign and exposures[(j,s)] == 0), 'First reach mismatch')
        exposures[(j,sign)] += 1
        sent[(i,sign)].add(j); contact_time[(i,j,sign)] = t
        counts[(t,i,sign)] += 1
        receipts[(t,j)].append(e); events_t[t].append(e)
    require(all(c <= dyn.opportunities for c in counts.values()), 'Message budget exceeded')
    decisions = {}
    for d in sim.decisions:
        key = (d['period'], d['receiver'])
        require(key not in decisions and key in receipts, 'Repeated/unexposed decision')
        decisions[key] = d
    require(set(decisions) == set(receipts), 'Missing exposure decision record')
    memories = {sign: [0.0] * n for sign in ACTIVE}
    purchases = {}
    for t in range(1, end + 1):
        for a in agents:
            j = a.id
            if a.initial_customer or j in purchases:
                continue
            incoming = receipts.get((t,j), [])
            by_sign = {s: [e for e in incoming if e['sign'] == s] for s in ACTIVE}
            previous = {s: memories[s][j] for s in ACTIVE}
            for s in ACTIVE:
                memories[s][j] = dyn.memory_retention * memories[s][j] + math.fsum(e['sender_credibility'] for e in by_sign[s])
            if not incoming:
                continue
            d = decisions[(t,j)]
            eligible = bool(by_sign['positive'])
            prob = mixed_adoption_probability(a.traits.need, a.traits.fit, memories['positive'][j], memories['negative'][j],
                                             eligible, dyn, neg, cfg.negative_weight)
            p0 = mixed_adoption_probability(a.traits.need, a.traits.fit, memories['positive'][j], memories['negative'][j],
                                           eligible, dyn, neg, 0)
            for s in ACTIVE:
                require(d['new_' + s + '_messages'] == len(by_sign[s]) and d[s + '_memory_before'] == previous[s] and
                        d[s + '_memory_after'] == memories[s][j] and d[s + '_influence'] == -math.expm1(-memories[s][j]),
                        'Memory/influence ledger mismatch')
            u = d['purchase_draw']
            require(d['eligible_to_buy'] == eligible and d['probability'] == prob and
                    d['probability_without_negative'] == p0 and 0 <= prob <= p0 <= 1, 'Mixed probability mismatch')
            require(uniform(u) if eligible else u is None, 'Purchase draw without positive gate or invalid draw')
            adopted = eligible and u < prob
            parent = min(by_sign['positive'], key=lambda e: (-e['sender_credibility'],e['sender']))['sender'] if adopted else None
            require(d['adopted'] == adopted and d['parent'] == parent and d['community'] == a.community and
                    d['scheduled_experience_time'] == (t+1 if adopted else None), 'Purchase/attribution mismatch')
            if adopted:
                purchases[j] = d
            for e in incoming:
                require(e['receiver_bought_this_period'] == adopted and
                        e['credited_purchase_parent'] == (adopted and e['sign'] == 'positive' and e['sender'] == parent),
                        'Event attribution mismatch')

    experiences, attempts = {}, {}
    for e in sim.experience_events:
        j = e['agent']
        require(j in purchases and j not in experiences, 'Unpurchased/repeated experience')
        a = agents[j]; d = purchases[j]
        require(e['period'] == d['period']+1 <= end and uniform(e['noise_draw']), 'Experience delay/draw mismatch')
        noise, raw, satisfaction, category = assess_experience(a.traits.fit, e['noise_draw'], exp)
        require((e['noise'], e['raw_satisfaction'], e['satisfaction'], e['experience'], e['fit'], e['quality']) ==
                (noise, raw, satisfaction, category, a.traits.fit, exp.quality), 'Experience equation mismatch')
        require(e['purchase_time'] == d['period'] and e['parent'] == d['parent'], 'Experience attribution mismatch')
        for s, expected_category, probability, draw_key in (
            ('positive', Experience.SATISFIED, exp.promoter_disposition_probability, 'disposition_draw'),
            ('negative', Experience.DISSATISFIED, neg.disposition_probability, 'negative_disposition_draw')):
            allowed = category == expected_category and (s == 'positive' or cfg.negative_wom_enabled)
            u = e[draw_key]
            require(uniform(u) if allowed else u is None, 'Disposition draw mismatch')
            disposition = allowed and u < probability
            require(e[s + '_disposition_probability'] == probability and e[s + '_disposition'] == disposition,
                    'Disposition outcome mismatch')
        require(e['scheduled_activation_time'] == (e['period']+1 if e['positive_disposition'] or e['negative_disposition'] else None),
                'Activation schedule mismatch')
        experiences[j] = e
    require(set(experiences) == {j for j,d in purchases.items() if d['period']+1 <= end}, 'Missing experience')
    for e in sim.activation_events:
        j, sign, t = e['agent'], e['sign'], e['period']
        require(j in experiences and j not in attempts and sign in ACTIVE, 'Repeated/unscheduled activation')
        x, a = experiences[j], agents[j]
        require(x[sign + '_disposition'] and t == x['period']+1 <= end and e['experience_time'] == x['period'] and
                e['purchase_time'] == x['purchase_time'] and e['parent'] == x['parent'], 'Activation chronology mismatch')
        energy = exp.new_promoter_energy if sign == 'positive' else neg.new_detractor_energy
        other = 'negative' if sign == 'positive' else 'positive'
        eligible = sum(not agents[k].initial_customer and (agents[k].purchase_time is None or agents[k].purchase_time >= t)
                       for k in sim.state.environment.network.neighbors[j])
        reasons = []
        if energy <= cfg.energy_threshold: reasons.append('energy_exhausted')
        if not eligible: reasons.append('contacts_exhausted')
        require(e[sign + '_energy'] == energy and e[other + '_energy'] == 0 and e['eligible_contacts'] == eligible and
                e['activated'] == (not reasons) and e['inactivity_reasons'] == json.dumps(reasons), 'Activation eligibility mismatch')
        parent_generation = agents[a.parent].generation
        require(parent_generation is not None and e['parent_generation'] == parent_generation and
                e['generation'] == (parent_generation+1 if sign == 'positive' and not reasons else None), 'Activation genealogy mismatch')
        attempts[j] = e
    require(set(attempts) == {j for j,e in experiences.items() if (e['positive_disposition'] or e['negative_disposition']) and e['period']+1 <= end},
            'Missing activation attempt')

    updates, updates_t, updates_a = {}, defaultdict(list), defaultdict(list)
    for r in sim.energy_updates:
        key = (r['period'],r['agent'])
        require(key not in updates and 1 <= key[0] <= end and 0 <= key[1] < n, 'Repeated/invalid energy row')
        updates[key] = r; updates_t[key[0]].append(r); updates_a[key[1]].append(r)
    require(list(updates) == sorted(updates), 'Unordered energy rows')
    expected_updates = set()
    for a, old in zip(agents, sim.initial.agents):
        a.validate()
        require(a.community == old.community and a.traits == old.traits and
                (a.initial_customer,a.initial_promoter,a.initial_detractor) == (old.initial_customer,old.initial_promoter,old.initial_detractor),
                'Initial identity/traits changed')
        x, activation = experiences.get(a.id), attempts.get(a.id)
        if a.initial_customer:
            require((a.commercial,a.experience,a.satisfaction,a.purchase_time,a.experience_time,a.parent,a.generation,a.activation_time,
                     a.positive_eligible,a.negative_eligible) ==
                    (old.commercial,old.experience,old.satisfaction,0,0,None,old.generation,old.activation_time,
                     old.positive_eligible,old.negative_eligible), 'Initial customer lifecycle changed')
            if old.activation_time is None:
                require((a.wom,a.deactivation_time,a.inactivity_reasons) == (old.wom,old.deactivation_time,old.inactivity_reasons), 'Initial inactive role changed')
        elif a.id in purchases:
            d = purchases[a.id]
            require(a.purchase_time == d['period'] and a.parent == d['parent'], 'Purchase state mismatch')
            require(a.commercial == (Commercial.EXPERIENCED if x else Commercial.PENDING) and
                    a.experience_time == (x['period'] if x else None) and
                    a.satisfaction == (x['satisfaction'] if x else None) and
                    a.experience == (x['experience'] if x else Experience.UNEVALUATED), 'Experience state mismatch')
            require(a.positive_eligible == bool(x and x['positive_disposition']) and
                    a.negative_eligible == bool(x and x['negative_disposition']), 'Eligibility state mismatch')
            successful = activation and activation['activated']
            require(a.activation_time == (activation['period'] if successful else None) and
                    a.generation == (activation['generation'] if successful else None), 'Activation state/generation mismatch')
            if not successful:
                sign = 'positive' if a.positive_eligible else 'negative' if a.negative_eligible else None
                require(a.wom == (POTENTIAL[sign] if sign else WOM.NONE) and a.deactivation_time is None and
                        a.inactivity_reasons == (tuple(json.loads(activation['inactivity_reasons'])) if activation else ()),
                        'Potential/none state mismatch')
        else:
            require(a.commercial == Commercial.SUSCEPTIBLE and a.purchase_time is None and a.experience_time is None and
                    a.parent is None and a.generation is None and a.activation_time is None and a.deactivation_time is None and
                    not a.positive_eligible and not a.negative_eligible and not a.inactivity_reasons, 'Spontaneous lifecycle')
        energies = {s: getattr(old,s+'_energy') if a.initial_customer else
                    (exp.new_promoter_energy if s=='positive' else neg.new_detractor_energy) if getattr(a,s+'_eligible') else 0.0
                    for s in ACTIVE}
        sign = 'positive' if a.positive_eligible else 'negative' if a.negative_eligible else None
        if a.activation_time is not None:
            require(sign is not None, 'Activation without disposition')
            stop = end if a.deactivation_time is None else a.deactivation_time
            require(a.activation_time <= stop <= end, 'Invalid deactivation time')
            expected_updates.update((t,a.id) for t in range(max(1,a.activation_time),stop+1))
        for r in updates_a[a.id]:
            t = r['period']
            require(r['sign'] == sign and sign in ACTIVE, 'Energy sign mismatch')
            ec = sim.energy_config if sign == 'positive' else neg.energy_config()
            before_e, m = energies[sign], counts[(t,a.id,sign)]
            decay_end = (1-ec.decay)*before_e
            after = max(0.0,decay_end-ec.message_cost*m)
            require(before_e > cfg.energy_threshold and
                (r['energy_before'],r['messages_sent'],r['decay_rate'],r['message_cost'],r['decay_loss'],r['energy_after_decay'],
                 r['message_cost_requested'],r['unclipped_energy'],r['energy_after'],r['realized_loss']) ==
                (before_e,m,ec.decay,ec.message_cost,before_e-decay_end,decay_end,ec.message_cost*m,
                 decay_end-ec.message_cost*m,after,before_e-after), 'Energy equation/continuity mismatch')
            remain = sum(not agents[k].initial_customer and (agents[k].purchase_time is None or agents[k].purchase_time > t) and
                         contact_time.get((a.id,k,sign),end+1) > t for k in sim.state.environment.network.neighbors[a.id])
            reasons = []
            if after <= cfg.energy_threshold: reasons.append('energy_exhausted')
            if not remain: reasons.append('contacts_exhausted')
            require(r['remaining_contacts'] == remain and r['energy_exhausted'] == (after <= cfg.energy_threshold) and
                    r['contacts_exhausted'] == (remain == 0) and r['deactivated'] == bool(reasons) and
                    r['inactivity_reasons'] == json.dumps(reasons) and r['deactivated'] == (a.deactivation_time == t), 'Fatigue cause mismatch')
            require(r['initial_promoter'] == a.initial_promoter and r['initial_detractor'] == a.initial_detractor and
                    r['generation'] == a.generation and r['activated_this_period'] == (a.activation_time == t), 'Energy role mismatch')
            energies[sign] = after
        if a.activation_time is not None:
            if a.deactivation_time is None:
                require(a.wom == ACTIVE[sign] and not a.inactivity_reasons and self_contacts(sim,a.id,sign), 'Ineligible active role')
            else:
                r = updates.get((a.deactivation_time,a.id))
                require(r is not None and a.wom == INACTIVE[sign] and a.inactivity_reasons == tuple(json.loads(r['inactivity_reasons'])), 'Inactive state mismatch')
        for s in ACTIVE:
            require(getattr(a,s+'_energy') == energies[s] and getattr(a,'contacted_'+s) == sent[(a.id,s)] and
                    getattr(a,s+'_exposures') == exposures[(a.id,s)] and getattr(a,s+'_memory') == memories[s][a.id], 'Energy/contact/memory state mismatch')
    require(set(updates) == expected_updates, 'Missing active energy period or update of inactive agent')
    for e in sim.events:
        require(e['sender_energy'] == updates[(e['period'],e['sender'])]['energy_before'], 'Wrong event energy')
    if not cfg.negative_wom_enabled:
        require(not any(e['sign']=='negative' for e in sim.events+sim.activation_events+sim.energy_updates) and
                not any(a.negative_memory or a.negative_exposures or (a.negative_eligible and not a.initial_customer) for a in agents),
                'Negative mechanism not fully disabled')
    require(len(sim.system) == end+1 and len(sim.agent_history) == ((end+1)*n if dyn.record_agents else 0), 'Incomplete histories')
    totals = {s: math.fsum(getattr(a,s+'_energy') for a in sim.initial.agents) for s in ACTIVE}
    stocks = {s: sum(a.wom == ACTIVE[s] for a in sim.initial.agents) for s in ACTIVE}
    cum_buys = 0
    cumulative_causes = {s: Counter() for s in ACTIVE}
    cumulative_events = Counter()
    reached = {s: set() for s in ACTIVE}
    for t,row in enumerate(sim.system):
        bought = sum(d['period']==t for d in purchases.values()); cum_buys += bought
        require(row['time']==t and row['population']==n and row['customers']==cfg.initial_customers+cum_buys and
                row['susceptibles']==n-row['customers'] and row['new_purchases']==bought and row['cumulative_new_purchases']==cum_buys and
                row['new_experiences']==sum(e['period']==t for e in experiences.values()), 'System population/lifecycle mismatch')
        for s,noun in (('positive','promoters'),('negative','detractors')):
            sign_events = [e for e in events_t[t] if e['sign']==s]
            cumulative_events[s] += len(sign_events)
            reached[s].update(e['receiver'] for e in sign_events)
            formed = sum(e['period']==t and e['sign']==s and e['activated'] for e in attempts.values())
            rlist = [r for r in updates_t[t] if r['sign']==s]
            exits = sum(r['deactivated'] for r in rlist)
            stocks[s] += formed-exits
            assigned = sum(e['period']==t and e[s+'_disposition'] for e in experiences.values()) * (exp.new_promoter_energy if s=='positive' else neg.new_detractor_energy)
            loss = math.fsum(r['realized_loss'] for r in rlist); totals[s] += assigned-loss
            require(row[s+'_events']==sum(e['sign']==s for e in events_t[t]) and row['new_'+noun]==formed and
                    row['deactivated_'+noun]==exits and row[str(ACTIVE[s])]==stocks[s] and
                    row[s+'_energy_assigned']==assigned and close(row[s+'_energy_loss'],loss) and close(row[s+'_energy_total'],totals[s]),
                    'System sign-specific balance mismatch')
            prefix = '' if s=='positive' else 'negative_'
            causes = cause_counts(rlist)
            cumulative_causes[s].update(causes)
            require(all(row[prefix+k]==v and row['cumulative_'+prefix+k]==cumulative_causes[s][k]
                        for k,v in causes.items()), 'System fatigue categories mismatch')
            sign_attempts = [e for e in attempts.values() if e['sign']==s and e['period']<=t]
            require(row['cumulative_new_'+noun]==sum(e['activated'] for e in sign_attempts) and
                    row[prefix+'activation_attempts']==sum(e['period']==t for e in sign_attempts) and
                    row[prefix+'blocked_activations']==sum(e['period']==t and not e['activated'] for e in sign_attempts) and
                    row['cumulative_'+prefix+'blocked_activations']==sum(not e['activated'] for e in sign_attempts) and
                    row['cumulative_'+s+'_events']==cumulative_events[s] and
                    row['cumulative_unique_'+s+'_recipients']==len(reached[s]), 'System cumulative lifecycle/reach mismatch')
            if t==0:
                active = [a for a in sim.initial.agents if a.wom==ACTIVE[s]]
                active_energy = math.fsum(getattr(a,s+'_energy') for a in active)
                capacity = sim.initial.capacity(s)
            else:
                active = [r for r in rlist if not r['deactivated']]
                active_energy = math.fsum(r['energy_after'] for r in active)
                capacity = math.fsum(r['energy_after'] * agents[r['agent']].traits.credibility * r['remaining_contacts'] /
                    len(sim.state.environment.network.neighbors[r['agent']]) for r in active)
            require(close(row[s+'_energy_active'],active_energy) and close(row[s+'_capacity'],capacity) and
                    row['mean_'+s+'_energy_active']==(active_energy/len(active) if active else None), 'Effective capacity mismatch')
        require(close(row['net_pressure'],row['positive_capacity']-cfg.negative_weight*row['negative_capacity']), 'Net pressure mismatch')
    for s in ACTIVE:
        require(sim.system[-1]['cumulative_'+s+'_events']==sum(e['sign']==s for e in sim.events) and
                sim.system[-1]['cumulative_unique_'+s+'_recipients']==sum(exposures[(a.id,s)]>0 for a in agents), 'Reach totals mismatch')
    sim.lineage_rows()


def self_contacts(sim, agent, sign):
    return bool(sim.state.eligible_contacts(agent,sign))
