"""Stable component seeds and index-addressable draws for future dynamics."""
import hashlib
import json
import random

RNG_VERSION = "article8-sha256-v1"
COMPONENTS = ("network", "traits", "customers", "detractors", "promoter_order", "community_order")


def component_seed(master_seed: int, component: str) -> int:
    payload = json.dumps([RNG_VERSION, master_seed, component], separators=(",", ":"))
    return int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest()[:8], "big")


def stream(master_seed: int, component: str) -> random.Random:
    return random.Random(component_seed(master_seed, component))


def indexed_uniform(master_seed: int, agent: int, period: int, mechanism: str, slot: int = 0) -> float:
    """A keyed draw in [0,1); calling order cannot shift other draws.

    This utility is tested but not yet used to implement temporal dynamics.
    It is a deterministic PRNG design choice, not a claim of statistical superiority.
    """
    payload = json.dumps([RNG_VERSION, master_seed, agent, period, mechanism, slot],
                         ensure_ascii=True, separators=(",", ":"))
    bits = int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "big") >> 11
    return bits / 2**53

