"""Count-based input and read-only revised endpoint; the M6 engine stays frozen."""
from dataclasses import dataclass, asdict
import math
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'model'))
from article8.config import Config
from article8.classification import validate_series


@dataclass(frozen=True)
class CountConfig(Config):
    promoter_share: float = 0.0
    exact_promoters: int = 0

    def promoter_count(self):
        n=self.exact_promoters
        if type(n) is not int or not 0 <= n <= self.initial_customers:
            raise ValueError('exact_promoters must be an integer in [0, initial_customers]')
        if self.initial_customers <= 0 or not math.isclose(self.promoter_share,n/self.initial_customers,rel_tol=0,abs_tol=1e-15):
            raise ValueError('Reporting share does not match the exact count')
        return n


@dataclass(frozen=True)
class SustainedConfig:
    duration: int = 6
    market_fraction_in_window: float = .05
    minimum_purchase_communities: int = 2

    def validate(self):
        if type(self.duration) is not int or self.duration < 2 or self.duration % 2:
            raise ValueError('duration must be positive, even, and at least two')
        f=self.market_fraction_in_window
        if type(f) not in (int,float) or not math.isfinite(f) or not 0 < f <= 1:
            raise ValueError('market fraction must be in (0,1]')
        if type(self.minimum_purchase_communities) is not int or self.minimum_purchase_communities<1:
            raise ValueError('Invalid community requirement')


def classify_sustained(rows,initial_susceptibles,config=SustainedConfig()):
    """Finite-window sustained diffusion, not perpetual growth or acceleration.

    Windows require sales and positive net pressure in every period, end stock
    >= pre-window stock and >0, births >= exits (and >=1) in second half,
    purchases in >=2 communities, no external entries, and minimum volume.
    All inputs are available by confirmation; no retrospective future data.
    """
    config.validate(); validate_series(rows)
    if type(initial_susceptibles) is not int or initial_susceptibles<=0:
        raise ValueError('Initial susceptible population must be a positive integer')
    threshold=math.ceil(config.market_fraction_in_window*initial_susceptibles-1e-12)
    windows=[]; events=[]; d=config.duration
    for end in range(d,len(rows)):
        start=end-d+1; block=rows[start:end+1]; second=block[d//2:]
        births=sum(r['new_promoters'] for r in second)
        exits=sum(r['deactivated_promoters'] for r in second)
        total=sum(r['new_purchases'] for r in block)
        communities=sorted(set().union(*(set(r['purchase_communities']) for r in block)))
        checks={
            'purchases_every_period':all(r['new_purchases']>=1 for r in block),
            'window_volume':total>=threshold,
            'positive_pressure':all(r['net_pressure']>0 for r in block),
            'active_stock':block[-1]['promoter_active']>=rows[start-1]['promoter_active'] and block[-1]['promoter_active']>0,
            'endogenous_replacement':births>=1 and births>=exits,
            'community_spread':len(communities)>=config.minimum_purchase_communities,
            'no_external_entries':all(r['external_promoters']==0 for r in block)}
        triggered=all(checks.values())
        record={'window_start':start,'confirmation':end,'triggered':triggered,
            'purchases':total,'volume_threshold':threshold,'second_half_births':births,
            'second_half_exits':exits,'communities':communities,'criteria':checks}
        windows.append(record)
        if triggered: events.append(record)
    return {'criterion_version':'sustained-v0.2','config':asdict(config),
        'ever':bool(events),'first_start':events[0]['window_start'] if events else None,
        'first_confirmation':events[0]['confirmation'] if events else None,
        'last_confirmation':events[-1]['confirmation'] if events else None,
        'complete_windows':len(windows),'uncompleted_window_starts':min(d-1,len(rows)-1),
        'volume_threshold':threshold,'windows':windows}


def settings():
    return [(f'd{d}_f{int(f*1000):03d}',SustainedConfig(d,f))
            for d in (4,6,8) for f in (.025,.05,.10)]


def first_reach(rows,initial_susceptibles,fraction):
    threshold=math.ceil(initial_susceptibles*fraction-1e-12)
    cumulative=0
    for r in rows[1:]:
        cumulative+=r['new_purchases']
        if cumulative>=threshold:return r['time']
    return None
