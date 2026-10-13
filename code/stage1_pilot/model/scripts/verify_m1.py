"""Run tests, a 220-snapshot audit and two complete worked examples."""
import argparse
import csv
from dataclasses import asdict, replace
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from article8 import __version__
from article8.config import Config
from article8.export import (community_rows, environment_fingerprint, export_initial_state,
                            write_csv, write_json, verify_export)
from article8.model import initialize, make_environment
from article8.randomness import COMPONENTS, component_seed

SHARES = (0, .025, .05, .075, .10, .125, .15, .175, .20, .25, .30)
SEEDS = tuple(20260925 + i for i in range(10))


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({"test": test.id(), "status": "passed"})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.records.append({"test": test.id(), "status": "failed"})

    def addError(self, test, err):
        super().addError(test, err)
        self.records.append({"test": test.id(), "status": "error"})


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def verify(out: Path) -> dict:
    if out.exists() and any(out.iterdir()):
        raise FileExistsError("Verification output must be new or empty")
    out.mkdir(parents=True, exist_ok=True)
    log = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_m1.py")
    result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=RecordedResult).run(suite)
    (out / "unit_tests.log").write_text(log.getvalue(), encoding="utf-8")
    write_json(out / "unit_tests.json", {"tests_run": result.testsRun, "failures": len(result.failures),
                                       "errors": len(result.errors), "skipped": len(result.skipped),
                                       "successful": result.wasSuccessful(), "tests": result.records})
    require(result.wasSuccessful(), "Unit tests failed; see unit_tests.log")

    rows, network_rows, seeds_rows, energy_rows = [], [], [], []
    for seed in SEEDS:
        cfg = replace(Config(), seed=seed)
        env = make_environment(cfg)
        m = env.network.metrics()
        network_rows.append({"seed": seed, **{k: v for k, v in m.items() if not isinstance(v, (dict, list))}})
        seeds_rows.append({"seed": seed, **{k: component_seed(seed, k) for k in COMPONENTS}})
        common_fingerprint = environment_fingerprint(initialize(cfg, env))
        for distribution in ("distributed", "concentrated"):
            previous = set()
            for share in SHARES:
                scenario = replace(cfg, distribution=distribution, promoter_share=share)
                state = initialize(scenario, env)
                state.validate()
                ids = {a.id for a in state.agents if a.initial_promoter}
                require(previous <= ids, "Promoter sets are not nested")
                previous = ids
                require(len(ids) == scenario.promoter_count(), "Incorrect promoter count")
                require(environment_fingerprint(state) == common_fingerprint, "Unpaired environment")
                communities = community_rows(state)
                counts = [r["nominal_promoters"] for r in communities]
                if distribution == "distributed":
                    require(max(counts) - min(counts) <= 1, "Unbalanced distributed promoters")
                else:
                    groups = env.community_order[:2]
                    require(all(counts[c] == 0 for c in range(6) if c not in groups), "Promoters outside concentration groups")
                    require(abs(counts[groups[0]] - counts[groups[1]]) <= 1, "Unbalanced concentrated promoters")
                rows.append({"seed": seed, "distribution": distribution, "promoter_share": share,
                             "network_sha256": m["network_sha256"], "environment_sha256": common_fingerprint,
                             "invariants_passed": True, **state.summary()})
            for energy in (.3, .6, .9):
                state = initialize(replace(cfg, distribution=distribution, positive_energy=energy), env)
                energy_rows.append({"seed": seed, "distribution": distribution, "energy": energy,
                                    "promoter_share": .15, **state.summary()})
    write_csv(out / "initialization_sweep.csv", rows)
    write_csv(out / "network_replicates.csv", network_rows)
    write_csv(out / "component_seeds.csv", seeds_rows)
    write_csv(out / "paired_energy_checks.csv", energy_rows)

    examples = {}
    for distribution in ("distributed", "concentrated"):
        state = initialize(replace(Config(), distribution=distribution))
        root = out / "examples" / distribution
        export_initial_state(state, root)
        verify_export(root)
        examples[distribution] = {"summary": state.summary(), "communities": community_rows(state)}
    base_network = initialize(Config()).environment.network.metrics()
    report = {
        "module_version": __version__, "python_version": platform.python_version(),
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "t=0 initialization; no temporal diffusion runs",
        "unit_tests": result.testsRun, "unit_test_failures": len(result.failures),
        "unit_test_errors": len(result.errors), "initialization_cases": len(rows),
        "paired_energy_snapshots": len(energy_rows), "replicates": len(SEEDS),
        "seeds": SEEDS, "baseline_network": base_network, "examples": examples,
        "network_mean_degree_min": min(r["mean_degree"] for r in network_rows),
        "network_mean_degree_max": max(r["mean_degree"] for r in network_rows),
        "network_mean_degree_mean": statistics.mean(r["mean_degree"] for r in network_rows),
        "initialization_failures": sum(not r["invariants_passed"] for r in rows),
        "completed_temporal_simulations": 0,
    }
    write_json(out / "verification_summary.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    os.chdir(ROOT)  # CLI subprocess tests must import the packaged source.
    report = verify(out)
    print(json.dumps({k: report[k] for k in ("unit_tests", "unit_test_failures", "unit_test_errors",
                                           "initialization_cases", "paired_energy_snapshots",
                                           "initialization_failures", "completed_temporal_simulations")}, indent=2))


if __name__ == "__main__":
    main()
