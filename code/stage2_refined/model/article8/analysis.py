"""M6: read-only indicators and delayed, direct-child cohort accounting.

Analysis never changes dynamics, agent states or random-number streams.
Full specification: docs/Article_8_M6_Alcance_v0.6.0.md.
"""
from collections import defaultdict
from dataclasses import asdict, dataclass
import json
import math


@dataclass(frozen=True)
class AnalysisConfig:
    reproduction_window: int = 6
    cohort_windows: tuple = (3, 6, 12)
    duration: int = 6
    minimum_sales: int = 3
    growth_factor: float = 1.25
    require_positive_pressure: bool = True
    minimum_purchase_communities: int = 2
    collapse_reference_periods: int = 3
    collapse_sales_fraction: float = .5
    collapse_stock_fraction: float = .5
    collapse_capacity_fraction: float = .5
    saturation_remaining: float = .10
    collapse_remaining: float = .20
    plateau_tolerance: float = .20
    spike_block: int = 3
    spike_growth_factor: float = 2.0
    spike_decline_fraction: float = .5

    def validate(self):
        for name in ('reproduction_window', 'duration', 'minimum_sales',
                     'minimum_purchase_communities', 'collapse_reference_periods', 'spike_block'):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f'{name} must be a positive integer')
        if self.duration < 2 or self.duration % 2:
            raise ValueError('duration must be even and at least two')
        if not isinstance(self.cohort_windows, (tuple, list)) or not self.cohort_windows:
            raise ValueError('cohort_windows must be a nonempty sequence')
        if any(type(w) is not int or w < 1 for w in self.cohort_windows):
            raise ValueError('cohort_windows must contain positive integers')
        if len(set(self.cohort_windows)) != len(self.cohort_windows):
            raise ValueError('cohort_windows must be unique')
        if type(self.require_positive_pressure) is not bool:
            raise ValueError('require_positive_pressure must be boolean')
        for name in ('growth_factor', 'spike_growth_factor', 'collapse_sales_fraction',
                     'collapse_stock_fraction', 'collapse_capacity_fraction', 'saturation_remaining',
                     'collapse_remaining', 'plateau_tolerance', 'spike_decline_fraction'):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError(f'{name} must be finite')
            if name in ('growth_factor', 'spike_growth_factor'):
                if value <= 1:
                    raise ValueError(f'{name} must exceed one')
            elif not 0 <= value <= 1:
                raise ValueError(f'{name} must be in [0,1]')
        if not self.saturation_remaining < self.collapse_remaining:
            raise ValueError('Saturation and collapse limits must be separated')


def ratio(numerator, denominator):
    """Undefined is None (JSON null, CSV empty), never zero or infinity."""
    return numerator / denominator if denominator else None


def active_at_close(agent, period):
    return (agent.positive_eligible and agent.activation_time is not None
            and agent.activation_time <= period
            and (agent.deactivation_time is None or agent.deactivation_time > period))


def reproduction_windows(simulation, config=AnalysisConfig()):
    """Windows start at 1; purchases through b mature at b+2.

Stock at a-1 fixes cohort membership. A child remains counted even if its
parent or the child is inactive at analysis time. Grandchildren are excluded.
"""
    config.validate()
    horizon = simulation.time
    rows = []
    widths = sorted(set(config.cohort_windows) | {config.reproduction_window})
    for width in widths:
        for start in range(1, horizon + 1):
            end = start + width - 1
            observed_end = min(end, horizon)
            members = {a.id for a in simulation.agents if active_at_close(a, start - 1)}
            denominator = len(members)
            if denominator != simulation.system[start - 1]['promoter_active']:
                raise ValueError('Historical cohort differs from active stock')
            births = sum(r['new_promoters'] for r in simulation.system[start:observed_end + 1])
            children = sorted(a.id for a in simulation.agents
                              if not a.initial_customer and a.positive_eligible
                              and a.activation_time is not None
                              and a.parent in members and start <= a.purchase_time <= end
                              and a.activation_time <= min(end + 2, horizon))
            window_complete, cohort_complete = end <= horizon, end + 2 <= horizon
            rows.append({'window_start': start, 'window_end': end, 'window_width': width,
                         'observed_end': observed_end, 'cohort_available_at': end + 2,
                         'active_at_start': denominator, 'window_births_observed': births,
                         'window_censored': not window_complete,
                         'window_ratio': ratio(births, denominator) if window_complete else None,
                         'cohort_children_observed': len(children),
                         'cohort_censored': not cohort_complete,
                         'cohort_ratio': ratio(len(children), denominator) if cohort_complete else None,
                         'zero_denominator': denominator == 0,
                         'cohort_members': json.dumps(sorted(members)),
                         'direct_children_observed': json.dumps(children)})
    return rows


def period_indicators(simulation):
    """Reuse verified M5 capacities; reconstruct coverage from event ledgers."""
    purchases, messages = defaultdict(set), defaultdict(set)
    for decision in simulation.decisions:
        if decision['adopted']:
            purchases[decision['period']].add(decision['community'])
    for event in simulation.events:
        messages[event['period']].add(event['receiver_community'])
    initial_susceptibles = simulation.system[0]['susceptibles']
    if initial_susceptibles <= 0:
        raise ValueError('Analysis requires an initially susceptible market')
    rows, reached, acquired = [], set(), set()
    for base in simulation.system:
        row = dict(base)
        t = row['time']
        reached.update(messages[t]); acquired.update(purchases[t])
        births, exits = row['new_promoters'], row['deactivated_promoters']
        net = births - exits
        if t and row['promoter_active'] - rows[-1]['promoter_active'] != net:
            raise ValueError('Promoter stock-flow mismatch')
        row.update(replacement_ratio=ratio(births, exits), promoter_net_change=net,
                   active_share_customers=ratio(row['promoter_active'], row['customers']),
                   active_share_population=ratio(row['promoter_active'], row['population']),
                   nominal_share_customers=ratio(sum(row[k] for k in
                       ('promoter_potential', 'promoter_active', 'promoter_fatigued')), row['customers']),
                   susceptible_fraction_initial=row['susceptibles'] / initial_susceptibles,
                   initial_market_exhaustion=1-row['susceptibles']/initial_susceptibles,
                   purchase_communities=tuple(sorted(purchases[t])),
                   message_communities=tuple(sorted(messages[t])),
                   cumulative_purchase_communities=len(acquired),
                   cumulative_message_communities=len(reached), external_promoters=0)
        rows.append(row)
    return rows


@dataclass
class AnalysisResult:
    config: dict
    system: list
    reproduction: list
    classification_windows: list
    summary: dict


def analyze_simulation(simulation, config=AnalysisConfig()):
    """Deterministic observer; accepts completed or partial M5 trajectories."""
    from .classification import classify_trajectory
    config.validate()
    simulation.validate()
    periods = period_indicators(simulation)
    windows = reproduction_windows(simulation, config)
    lookup = {(r['window_start'], r['window_width']): r for r in windows}
    width = config.reproduction_window
    for row in periods:
        t = row['time']
        entry = lookup.get((t-width+1, width))
        mature = lookup.get((t-width-1, width))
        row.update(reproduction_ratio=entry['window_ratio'] if entry else None,
                   reproduction_window=width,
                   reproduction_window_start=entry['window_start'] if entry else None,
                   reproduction_window_births=entry['window_births_observed'] if entry else None,
                   reproduction_window_stock=entry['active_at_start'] if entry else None,
                   cohort_ratio_available=mature['cohort_ratio'] if mature else None,
                   cohort_window_start=mature['window_start'] if mature else None,
                   cohort_window_end=mature['window_end'] if mature else None)
    classes, audit, summary = classify_trajectory(periods, config)
    for row, classification in zip(periods, classes):
        row.update(classification)
    summary.update(module='M6', scope='M6 indicators and observed diffusion classification',
                   completed_periods=simulation.time,
                   configured_periods=simulation.dynamics.periods,
                   partial_run=simulation.time < simulation.dynamics.periods,
                   final_replacement_ratio=periods[-1]['replacement_ratio'],
                   final_reproduction_ratio=periods[-1]['reproduction_ratio'],
                   cohort_windows=len(windows),
                   cohort_censored_windows=sum(r['cohort_censored'] for r in windows),
                   cohort_zero_denominator_windows=sum(r['zero_denominator'] for r in windows))
    return AnalysisResult(asdict(config), periods, windows, audit, summary)
