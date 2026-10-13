"""Verify M1–M3 and 20 paired M3 diagnostics; these are not the full-model pilot."""
import argparse
from datetime import datetime, timezone
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import platform
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from article8 import __version__
from article8.config import Config
from article8.experience import ExperienceSimulation
from article8.export import (environment_fingerprint, export_experience_simulation,
                            verify_export, write_csv, write_json)
from article8.model import Commercial, WOM, initialize, make_environment
from article8.positive import PositiveConfig
from verify_m1 import RecordedResult, require


def verify(out):
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise FileExistsError("Verification output must be new or empty")
    out.mkdir(parents=True, exist_ok=True)
    log = io.StringIO()
    suite = unittest.TestSuite(unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern=pattern)
                               for pattern in ("test_m1.py", "test_m2.py", "test_m3.py"))
    result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=RecordedResult).run(suite)
    (out / "unit_tests.log").write_text(log.getvalue(), encoding="utf-8")
    write_json(out / "unit_tests.json", {"tests_run": result.testsRun,
                                       "failures": len(result.failures), "errors": len(result.errors),
                                       "skipped": len(result.skipped), "successful": result.wasSuccessful(),
                                       "tests": result.records})
    require(result.wasSuccessful(), "Unit tests failed")
    seeds = list(range(20260925, 20260935))
    runs = []
    for seed in seeds:
        cfg = Config(seed=seed, negative_wom_enabled=False)
        env = make_environment(cfg)
        pair_hashes = []
        for distribution in ("distributed", "concentrated"):
            initial = initialize(replace(cfg, distribution=distribution), env)
            roots = {a.id for a in initial.agents if a.wom == WOM.PROMOTER_ACTIVE}
            initial_reach = set().union(*(set(initial.eligible_contacts(i, "positive")) for i in roots))
            # Upper bound: paths from active roots through initially susceptible nodes.
            reachable, frontier = set(roots), list(roots)
            while frontier:
                i = frontier.pop()
                for j in env.network.neighbors[i]:
                    if j not in reachable and not initial.agents[j].initial_customer:
                        reachable.add(j)
                        frontier.append(j)
            sim = ExperienceSimulation(initial, PositiveConfig(record_agents=seed == seeds[0])).run()
            buyers = {a.id for a in sim.agents if not a.initial_customer and a.commercial != Commercial.SUSCEPTIBLE}
            require(buyers <= reachable, "Purchase outside reachable susceptible paths")
            require(len(sim.events) <= len(list(env.network.edges())), "Finite network contact bound violated")
            require(all(r["population"] == 600 and r["customers"] + r["susceptibles"] == 600 for r in sim.system),
                    "Population not conserved")
            summary = sim.summary()
            fingerprint = environment_fingerprint(initial)
            pair_hashes.append(fingerprint)
            if seed == seeds[0]:
                path = out / "examples" / distribution
                export_experience_simulation(sim, path)
                verify_export(path)
            runs.append({"seed": seed, "distribution": distribution, "promoter_share": .15,
                         "initial_promoters": 18, "environment_sha256": fingerprint,
                         "periods": sim.time, "new_purchases": len(buyers),
                         "final_customers": summary["customers"], "positive_events": len(sim.events),
                         "unique_recipients": summary["cumulative_unique_positive_recipients"],
                         "initial_unique_reach": len(initial_reach),
                         "purchases_beyond_initial_reach": len(buyers - initial_reach),
                         "new_experiences": len(sim.experience_events),
                         "satisfied_new_customers": sum(e["experience"] == "satisfied" for e in sim.experience_events),
                         "neutral_new_customers": sum(e["experience"] == "neutral" for e in sim.experience_events),
                         "dissatisfied_new_customers": sum(e["experience"] == "dissatisfied" for e in sim.experience_events),
                         "new_potential_promoters": sum(e["positive_disposition"] for e in sim.experience_events),
                         "activation_attempts": len(sim.activation_events),
                         "new_promoters": summary["cumulative_new_promoters"],
                         "blocked_activations": summary["cumulative_blocked_activations"],
                         "pending_experience": summary["pending_experience_customers"],
                         "pending_activation": summary["pending_activation_promoters"],
                         "max_generation": summary["max_promoter_generation"],
                         "final_active_promoters": summary["promoter_active"],
                         "negative_events": sum(r["negative_events"] for r in sim.system),
                         "invariants_passed": True, "classification": "not_evaluated_m3"})
        require(pair_hashes[0] == pair_hashes[1], "Distribution comparison was not paired")
    write_csv(out / "diagnostic_runs.csv", runs)
    summary = {"module_version": __version__, "python_version": platform.python_version(),
               "verified_at_utc": datetime.now(timezone.utc).isoformat(),
               "unit_tests": result.testsRun,
               "m1_regression_tests": sum(x["test"].startswith("test_m1.") for x in result.records),
               "m2_regression_tests": sum(x["test"].startswith("test_m2.") for x in result.records),
               "m3_tests": sum(x["test"].startswith("test_m3.") for x in result.records),
               "failures": len(result.failures), "errors": len(result.errors),
               "diagnostic_trajectories": len(runs), "periods_per_trajectory": 60,
               "seeds": seeds, "diagnostic_failures": 0, "full_model_pilot_runs": 0,
               "first_seed_examples": [r for r in runs if r["seed"] == seeds[0]]}
    write_json(out / "verification_summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    out = parser.parse_args().out.resolve()
    os.chdir(ROOT)
    print(json.dumps(verify(out), indent=2))


if __name__ == '__main__':
    main()
