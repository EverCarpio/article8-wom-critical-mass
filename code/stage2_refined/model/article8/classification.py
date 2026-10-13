"""Finite-window operational labels from specification v0.1, section 12.

Every prefix is classified using only observations available at its end.
Historical events and terminal labels are separate. No label is causal.
"""
import json
import math
from .analysis import AnalysisConfig


def le(left, right):
    return left <= right or math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12)


def ge(left, right):
    return le(right, left)


def validate_series(rows):
    if not rows:
        raise ValueError('A time-zero observation is required')
    counts = ('new_purchases', 'promoter_active', 'new_promoters',
              'deactivated_promoters', 'external_promoters')
    for t, row in enumerate(rows):
        if type(row.get('time')) is not int or row['time'] != t:
            raise ValueError('Times must be contiguous from zero')
        for key in counts:
            if type(row.get(key)) is not int or row[key] < 0:
                raise ValueError(f'{key} must be a nonnegative integer')
        for key in ('positive_capacity', 'net_pressure', 'susceptible_fraction_initial'):
            value = row.get(key)
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError(f'{key} must be finite')
        if row['positive_capacity'] < 0 or not 0 <= row['susceptible_fraction_initial'] <= 1:
            raise ValueError('Capacity/fraction outside its domain')
        communities = row.get('purchase_communities')
        if not isinstance(communities, (tuple, list, set)) or any(type(c) is not int or c < 0 for c in communities):
            raise ValueError('purchase_communities must contain integer community IDs')
        if len(set(communities)) > row['new_purchases']:
            raise ValueError('More purchase communities than purchases')
        if t and row['susceptible_fraction_initial'] > rows[t-1]['susceptible_fraction_initial']:
            raise ValueError('Susceptible market cannot grow in the minimum model')
        if t and row['promoter_active'] - rows[t-1]['promoter_active'] != (
                row['new_promoters'] - row['deactivated_promoters'] + row['external_promoters']):
            raise ValueError('Active stock does not reconcile with entries/exits')
    if rows[0]['new_purchases'] or rows[0]['new_promoters'] or rows[0]['deactivated_promoters'] or rows[0]['external_promoters']:
        raise ValueError('Time zero is a stock, not a flow period')


def window_checks(rows, start, config, kind, first_takeoff):
    """Only called on complete windows. Return criteria and sufficient statistics."""
    duration = 2 * config.spike_block if kind == 'spike' else config.duration
    end = start + duration - 1
    block = rows[start:end+1]
    half = duration // 2
    first, second = block[:half], block[half:]
    y1 = sum(r['new_purchases'] for r in first)
    y2 = sum(r['new_purchases'] for r in second)
    stock = rows[start-1]['promoter_active']
    final = block[-1]['promoter_active']
    fractions = [r['susceptible_fraction_initial'] for r in block]
    communities = set().union(*(set(r['purchase_communities']) for r in block))
    stats = {'sales_first_half': y1, 'sales_second_half': y2,
             'stock_start': stock, 'stock_end': final,
             'minimum_remaining': min(fractions), 'purchase_communities': sorted(communities)}
    if kind == 'takeoff':
        births = sum(r['new_promoters'] for r in second)
        exits = sum(r['deactivated_promoters'] for r in second)
        stats.update(second_half_births=births, second_half_exits=exits,
                     minimum_pressure=min(r['net_pressure'] for r in block))
        checks = {'initial_sales': y1 >= config.minimum_sales,
                  'sales_growth': ge(y2, config.growth_factor*y1),
                  'active_stock': final >= stock and final > 0,
                  'endogenous_replacement': births >= 1 and births >= exits,
                  'positive_pressure': not config.require_positive_pressure or all(r['net_pressure'] > 0 for r in block),
                  'community_spread': len(communities) >= config.minimum_purchase_communities,
                  'no_external_entries': all(r['external_promoters'] == 0 for r in block)}
    elif kind == 'collapse':
        k = config.collapse_reference_periods
        has_reference = start > k
        reference = sum(r['new_purchases'] for r in rows[max(1,start-k):start])/k if has_reference else None
        peak = max(r['positive_capacity'] for r in rows[:start])
        stats.update(reference_sales=reference, capacity_peak_before_start=peak,
                     capacity_end=block[-1]['positive_capacity'], pressure_end=block[-1]['net_pressure'])
        checks = {'after_takeoff': first_takeoff is not None and start > first_takeoff,
                  'sales_decline': reference is not None and reference > 0
                      and le(y1+y2, config.collapse_sales_fraction*duration*reference) and y2 <= y1,
                  'stock_decline': stock >= 1 and le(final, config.collapse_stock_fraction*stock),
                  'capacity_decline': block[-1]['net_pressure'] <= 0
                      or le(block[-1]['positive_capacity'], config.collapse_capacity_fraction*peak),
                  'remaining_market': all(ge(f, config.collapse_remaining) for f in fractions)}
    elif kind == 'plateau':
        checks = {'remaining_market': all(f > config.saturation_remaining for f in fractions),
                  'initial_sales': y1 >= config.minimum_sales,
                  'stable_sales': le(abs(y2-y1), config.plateau_tolerance*y1),
                  'stable_stock': le(abs(final-stock), config.plateau_tolerance*max(stock,1))}
    else:
        k = config.spike_block
        has_reference = start == 1 or start > k
        previous = 0 if start == 1 else sum(r['new_purchases'] for r in rows[max(1,start-k):start])
        peak_stock = first[-1]['promoter_active']
        stats.update(previous_block_sales=previous, peak_stock=peak_stock)
        checks = {'no_takeoff': first_takeoff is None or first_takeoff > end,
                  'full_reference': has_reference,
                  'sales_spike': ge(y1, max(config.minimum_sales,config.spike_growth_factor*previous)),
                  'sales_decline': le(y2,config.spike_decline_fraction*y1),
                  'stock_decline': le(final,config.spike_decline_fraction*peak_stock),
                  'remaining_market': fractions[-1] > config.saturation_remaining}
    return checks, stats


def pending_signal(rows, config, first_takeoff):
    """Conservative incomplete-window flag, not a forecast of confirmation."""
    t, d = len(rows)-1, config.duration
    for start in range(max(1,t-d+2), t-d//2+2):
        block = rows[start:]
        if len(block) < d//2 or len(block) >= d:
            continue
        first = block[:d//2]
        if (sum(r['new_purchases'] for r in first) >= config.minimum_sales
                and block[-1]['promoter_active'] > 0
                and not any(r['external_promoters'] for r in block)
                and (not config.require_positive_pressure or all(r['net_pressure'] > 0 for r in block))):
            return True
    if first_takeoff is not None:
        for start in range(max(first_takeoff+1,t-d+2),t+1):
            k = config.collapse_reference_periods
            if start <= k:
                continue
            block = rows[start:]
            ref = sum(r['new_purchases'] for r in rows[start-k:start])/k
            stock = rows[start-1]['promoter_active']
            if (ref > 0 and stock >= 1 and le(block[-1]['promoter_active'],config.collapse_stock_fraction*stock)
                    and le(sum(r['new_purchases'] for r in block),config.collapse_sales_fraction*len(block)*ref)
                    and all(ge(r['susceptible_fraction_initial'],config.collapse_remaining) for r in block)):
                return True
    # A completed peak block with an incomplete following decline block.
    k = config.spike_block
    if first_takeoff is None:
        for start in range(max(1,t-2*k+2),t-k+2):
            if start != 1 and start <= k:
                continue
            peak = rows[start:start+k]
            previous = 0 if start == 1 else sum(r['new_purchases'] for r in rows[start-k:start])
            if (len(peak) == k and ge(sum(r['new_purchases'] for r in peak),
                                     max(config.minimum_sales,config.spike_growth_factor*previous))
                    and rows[-1]['susceptible_fraction_initial'] > config.saturation_remaining):
                return True
    return False


def classify_trajectory(rows, config=AnalysisConfig()):
    config.validate()
    validate_series(rows)
    output, audit = [], []
    events = {name: [] for name in ('takeoff','collapse','plateau','spike','saturation')}
    for t, row in enumerate(rows):
        for kind in ('takeoff','collapse','plateau','spike'):
            duration = 2*config.spike_block if kind == 'spike' else config.duration
            start = t-duration+1
            if start < 1:
                continue
            first_takeoff = events['takeoff'][0][1] if events['takeoff'] else None
            checks, stats = window_checks(rows,start,config,kind,first_takeoff)
            triggered = all(checks.values())
            audit.append({'kind':kind,'window_start':start,'expected_confirmation':t,
                          'observed_end':t,'censored':False,'triggered':triggered,
                          'criteria':json.dumps(checks,sort_keys=True),
                          'statistics':json.dumps(stats,sort_keys=True)})
            if triggered:
                events[kind].append((start,t))
        if le(row['susceptible_fraction_initial'], config.saturation_remaining) and not events['saturation']:
            events['saturation'].append((t,t))
        first_takeoff = events['takeoff'][0][1] if events['takeoff'] else None
        pending = pending_signal(rows[:t+1],config,first_takeoff)
        insufficient = t < config.duration or pending
        recent_takeoff = bool(events['takeoff'] and events['takeoff'][-1][1] > t-config.duration)
        current_plateau = bool(events['plateau'] and events['plateau'][-1][1] == t)
        if events['saturation']:
            label = 'saturation'
        elif events['collapse']:
            label = 'collapse'
        elif current_plateau:
            label = 'plateau'
        elif recent_takeoff:
            label = 'sustained_takeoff'
        elif events['spike'] and not events['takeoff']:
            label = 'temporary_spike'
        elif insufficient:
            label = 'insufficient_followup'
        elif events['takeoff']:
            label = 'evolving'
        else:
            label = 'no_confirmed_takeoff'
        result = {'time':t,'diffusion_class':label,
                  'no_takeoff_confirmed':not bool(events['takeoff']),
                  'takeoff_current':recent_takeoff and not events['collapse'] and not events['saturation'] and not current_plateau,
                  'incomplete_signal':pending,'followup_insufficient':insufficient}
        for kind, records in events.items():
            result[kind+'_ever'] = bool(records)
            result[kind+'_first_start'] = records[0][0] if records else None
            result[kind+'_first_confirmation'] = records[0][1] if records else None
            result[kind+'_last_confirmation'] = records[-1][1] if records else None
        output.append(result)
    horizon = len(rows)-1
    for kind in ('takeoff','collapse','plateau','spike'):
        duration = 2*config.spike_block if kind == 'spike' else config.duration
        for start in range(max(1,horizon-duration+2),horizon+1):
            audit.append({'kind':kind,'window_start':start,'expected_confirmation':start+duration-1,
                          'observed_end':horizon,'censored':True,'triggered':False,
                          'criteria':'{}','statistics':'{}'})
    audit.sort(key=lambda r:(r['window_start'],r['kind']))
    summary = dict(output[-1])
    summary.update(terminal_class=summary['diffusion_class'],
                   takeoff_time_censored=not summary['takeoff_ever'],
                   collapse_time_at_risk=summary['takeoff_ever'],
                   collapse_time_censored=(not summary['collapse_ever']) if summary['takeoff_ever'] else None,
                   classification_censored_windows=sum(r['censored'] for r in audit))
    return output, audit, summary
