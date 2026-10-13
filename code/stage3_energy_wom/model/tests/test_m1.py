"""Verification against specification invariants, hand-calculated graphs and exports."""
import csv
from dataclasses import replace
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

from article8.config import Config
from article8.export import export_initial_state, verify_export, environment_fingerprint
from article8.model import (Agent, Commercial, Experience, Traits, WOM, initialize,
                           make_environment)
from article8.network import Network, make_network
from article8.randomness import COMPONENTS, component_seed, indexed_uniform


SHARES = (0, .025, .05, .075, .10, .125, .15, .175, .20, .25, .30)


class ConfigTests(unittest.TestCase):
    def test_exact_promoter_counts(self):
        self.assertEqual([replace(Config(), promoter_share=p).promoter_count() for p in SHARES],
                         [0, 3, 6, 9, 12, 15, 18, 21, 24, 30, 36])

    def test_fractional_person_rejected(self):
        with self.assertRaises(ValueError):
            replace(Config(), promoter_share=.001).validate()

    def test_invalid_settings_rejected(self):
        cases = [{"n": 601}, {"communities": 1}, {"initial_customers": 121},
                 {"initial_customers": 0}, {"initial_customers": 606},
                 {"initial_detractors": 7}, {"initial_detractors": 126},
                 {"p_within": -.01}, {"p_between": 1.01}, {"positive_energy": math.nan},
                 {"negative_energy": math.inf}, {"promoter_share": True},
                 {"seed": True}, {"seed": -1}, {"n": 600.0},
                 {"distribution": "unknown"}, {"negative_wom_enabled": 0},
                 {"negative_weight": -1}, {"energy_threshold": 2},
                 {"distribution": "concentrated", "promoter_share": .35}]
        for change in cases:
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(Config(), **change).validate()

    def test_max_concentration_with_twelve_detractors_is_feasible(self):
        state = initialize(replace(Config(), initial_detractors=12,
                                   promoter_share=.30, distribution="concentrated"))
        self.assertEqual(sum(a.initial_promoter for a in state.agents), 36)
        self.assertEqual(sum(a.initial_detractor for a in state.agents), 12)


class NetworkTests(unittest.TestCase):
    def test_two_disconnected_triangles_have_known_statistics(self):
        net = make_network(Config(n=6, communities=2, initial_customers=2,
                                  initial_detractors=0, promoter_share=.5,
                                  p_within=1, p_between=0))
        m = net.metrics()
        self.assertEqual(m["edges"], 6)
        self.assertEqual(m["mean_degree"], 2)
        self.assertEqual(m["mean_clustering_including_isolates"], 1)
        self.assertEqual(m["component_sizes"], [3, 3])
        self.assertEqual(m["assigned_community_modularity"], .5)
        self.assertEqual(m["between_community_edges"], 0)

    def test_complete_graph_statistics(self):
        net = make_network(Config(n=6, communities=2, initial_customers=2,
                                  initial_detractors=0, promoter_share=.5,
                                  p_within=1, p_between=1))
        m = net.metrics()
        self.assertEqual(m["edges"], 15)
        self.assertEqual(m["mean_degree"], 5)
        self.assertAlmostEqual(m["assigned_community_modularity"], -.1)
        self.assertEqual(m["between_community_edges"], 9)

    def test_triangle_plus_isolate_uses_all_nodes_in_clustering(self):
        net = Network((0, 0, 0, 1), (frozenset([1, 2]), frozenset([0, 2]),
                                   frozenset([0, 1]), frozenset()))
        m = net.metrics()
        self.assertEqual(m["mean_clustering_including_isolates"], .75)
        self.assertEqual(m["component_sizes"], [3, 1])

    def test_empty_graph_is_retained(self):
        net = make_network(replace(Config(), p_within=0, p_between=0))
        m = net.metrics()
        self.assertEqual(m["edges"], 0)
        self.assertEqual(m["component_count"], 600)
        self.assertIsNone(m["assigned_community_modularity"])
        self.assertEqual(m["mean_clustering_including_isolates"], 0)

    def test_invalid_graphs_rejected(self):
        graphs = [Network((0,), (frozenset([0]),)),
                  Network((0, 1), (frozenset([1]), frozenset())),
                  Network((0,), (frozenset([1]),))]
        for graph in graphs:
            with self.subTest(graph=graph), self.assertRaises(ValueError):
                graph.validate()

    def test_generated_edges_are_simple_symmetric_and_within_range(self):
        net = make_network(Config())
        self.assertEqual(len(net.edges()), len(set(net.edges())))
        self.assertEqual(sum(map(len, net.neighbors)), 2 * len(net.edges()))
        for i, j in net.edges():
            self.assertTrue(0 <= i < j < 600)
            self.assertIn(i, net.neighbors[j])


class InitializationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = make_environment(Config())

    def test_baseline_totals_and_denominators(self):
        state = initialize(Config(), self.env)
        summary = state.summary()
        self.assertEqual((summary["population"], summary["customers"], summary["susceptibles"]), (600, 120, 480))
        self.assertEqual(summary["nominal_initial_promoters"], 18)
        self.assertEqual(summary["nominal_initial_share_customers"], .15)
        self.assertEqual(summary["nominal_initial_share_population"], .03)
        self.assertEqual(sum(a.initial_detractor for a in state.agents), 6)
        self.assertEqual(sum(a.experience == Experience.NEUTRAL for a in state.agents), 96)

    def test_equal_customer_and_detractor_allocation(self):
        state = initialize(Config(), self.env)
        for c in range(6):
            self.assertEqual(sum(a.community == c and a.initial_customer for a in state.agents), 20)
            self.assertEqual(sum(a.community == c and a.initial_detractor for a in state.agents), 1)

    def test_distributed_promoters_are_balanced_and_nested_at_all_shares(self):
        previous = set()
        for share in SHARES:
            state = initialize(replace(Config(), promoter_share=share), self.env)
            current = {a.id for a in state.agents if a.initial_promoter}
            counts = [sum(a.initial_promoter and a.community == c for a in state.agents) for c in range(6)]
            self.assertLessEqual(max(counts) - min(counts), 1)
            self.assertTrue(previous <= current)
            self.assertEqual(len(current), round(120 * share))
            previous = current

    def test_concentrated_promoters_are_balanced_nested_and_in_fixed_two_communities(self):
        previous = set()
        groups = self.env.community_order[:2]
        for share in SHARES:
            state = initialize(replace(Config(), promoter_share=share, distribution="concentrated"), self.env)
            current = {a.id for a in state.agents if a.initial_promoter}
            self.assertTrue(previous <= current)
            self.assertTrue(all(a.community in groups for a in state.agents if a.initial_promoter))
            counts = [sum(a.initial_promoter and a.community == c for a in state.agents) for c in groups]
            self.assertLessEqual(abs(counts[0] - counts[1]), 1)
            previous = current

    def test_promoter_detractor_disjoint_and_all_emitters_are_customers(self):
        state = initialize(Config(), self.env)
        for a in state.agents:
            self.assertFalse(a.initial_promoter and a.initial_detractor)
            if a.initial_promoter or a.initial_detractor:
                self.assertTrue(a.initial_customer)
                self.assertEqual(a.commercial, Commercial.EXPERIENCED)

    def test_zero_promoters_preserves_base_customers(self):
        state = initialize(replace(Config(), promoter_share=0), self.env)
        self.assertEqual(state.summary()["nominal_initial_promoters"], 0)
        self.assertEqual(state.capacity("positive"), 0)
        self.assertEqual(state.summary()["customers"], 120)

    def test_zero_energy_retains_nominal_promoters_and_satisfaction(self):
        state = initialize(replace(Config(), positive_energy=0), self.env)
        self.assertEqual(state.summary()["promoter_active"], 0)
        self.assertEqual(state.summary()["nominal_initial_promoters"], 18)
        for a in state.agents:
            if a.initial_promoter:
                self.assertEqual(a.wom, WOM.PROMOTER_FATIGUED)
                self.assertEqual(a.experience, Experience.SATISFIED)
                self.assertIn("energy_exhausted", a.inactivity_reasons)

    def test_activation_threshold_is_strict(self):
        a = initialize(replace(Config(), positive_energy=.05), self.env)
        b = initialize(replace(Config(), positive_energy=.050001), self.env)
        self.assertEqual(a.summary()["promoter_active"], 0)
        self.assertEqual(b.summary()["promoter_active"], 18)

    def test_no_edges_disables_emitters_without_forcing_connectivity(self):
        state = initialize(replace(Config(), p_within=0, p_between=0))
        self.assertEqual(state.summary()["promoter_active"], 0)
        self.assertEqual(state.summary()["detractor_active"], 0)
        for a in state.agents:
            if a.initial_promoter or a.initial_detractor:
                self.assertIn("contacts_exhausted", a.inactivity_reasons)
                self.assertEqual(a.positive_energy + a.negative_energy, .6)

    def test_all_customers_means_no_susceptible_contacts(self):
        state = initialize(replace(Config(), initial_customers=600))
        self.assertEqual(state.summary()["susceptibles"], 0)
        self.assertEqual(state.capacity("positive"), 0)
        self.assertTrue(all(not state.eligible_contacts(i, "positive") for i in range(600)))

    def test_both_exhaustion_reasons_are_retained(self):
        state = initialize(replace(Config(), positive_energy=0, p_within=0, p_between=0))
        a = next(a for a in state.agents if a.initial_promoter)
        self.assertEqual(set(a.inactivity_reasons), {"contacts_exhausted", "energy_exhausted"})

    def test_negative_off_preserves_dissatisfied_customer_identities(self):
        state = initialize(replace(Config(), negative_wom_enabled=False), self.env)
        self.assertEqual(state.summary()["detractor_active"], 0)
        self.assertEqual(state.capacity("negative"), 0)
        self.assertEqual({a.id for a in state.agents if a.initial_detractor}, set(self.env.detractors))
        for a in state.agents:
            if a.initial_detractor:
                self.assertEqual(a.experience, Experience.DISSATISFIED)
                self.assertIn("negative_wom_disabled", a.inactivity_reasons)

    def test_zero_negative_weight_does_not_disable_negative_emitters(self):
        state = initialize(replace(Config(), negative_weight=0), self.env)
        self.assertEqual(state.summary()["detractor_active"], 6)
        self.assertGreater(state.capacity("negative"), 0)
        self.assertEqual(state.summary()["net_pressure"], state.capacity("positive"))

    def test_contact_eligibility_respects_edges_purchase_and_sign_history(self):
        state = initialize(Config(), self.env)
        a = next(a for a in state.agents if a.initial_promoter)
        eligible = state.eligible_contacts(a.id, "positive")
        self.assertTrue(eligible)
        for j in eligible:
            self.assertIn(j, self.env.network.neighbors[a.id])
            self.assertEqual(state.agents[j].commercial, Commercial.SUSCEPTIBLE)
        target = eligible[0]
        a.contacted_positive.add(target)
        self.assertNotIn(target, state.eligible_contacts(a.id, "positive"))
        self.assertIn(target, state.eligible_contacts(a.id, "negative"))
        with self.assertRaises(ValueError):
            state.eligible_contacts(a.id, "unknown")

    def test_hand_calculated_capacity_on_complete_six_person_graph(self):
        cfg = Config(n=6, communities=2, initial_customers=2, initial_detractors=0,
                     promoter_share=.5, p_within=1, p_between=1)
        env = make_environment(cfg)
        env = replace(env, traits=tuple(Traits(.75, .75, .75) for _ in range(6)))
        state = initialize(cfg, env)
        self.assertAlmostEqual(state.capacity("positive"), .6 * .75 * 4 / 5)

    def test_state_compatibility_rejects_unexperienced_emitter(self):
        a = Agent(0, 0, Traits(.5, .5, .6), wom=WOM.PROMOTER_ACTIVE)
        with self.assertRaises(ValueError):
            a.validate()

    def test_incompatible_or_nonfinite_states_rejected(self):
        for change in ({"wom": WOM.DETRACTOR_ACTIVE}, {"satisfaction": math.nan},
                       {"positive_energy": -1}, {"negative_eligible": True},
                       {"commercial": "bad"}, {"positive_exposures": -1}):
            state = initialize(Config(), self.env)
            a = next(a for a in state.agents if a.initial_promoter)
            for key, value in change.items():
                setattr(a, key, value)
            with self.subTest(change=change), self.assertRaises(ValueError):
                state.validate()

    def test_timestamp_and_genealogy_invariants_detect_corruption(self):
        for field in ("parent", "purchase_time", "experience_time", "activation_time", "generation"):
            state = initialize(Config(), self.env)
            a = next(a for a in state.agents if a.initial_promoter)
            setattr(a, field, 99)
            with self.subTest(field=field), self.assertRaises(ValueError):
                state.validate()

    def test_m1_outputs_do_not_claim_temporal_results(self):
        summary = initialize(Config(), self.env).summary()
        self.assertEqual(summary["time"], 0)
        self.assertEqual(summary["diffusion_class"], "not_evaluated_m1")
        self.assertIsNone(summary["reproduction_ratio"])
        self.assertIsNone(summary["replacement_ratio"])


class ReproducibilityTests(unittest.TestCase):
    def test_identical_seed_recreates_entire_state(self):
        self.assertEqual(initialize(Config()), initialize(Config()))

    def test_alternative_seed_changes_network(self):
        self.assertNotEqual(make_network(Config()).fingerprint(), make_network(replace(Config(), seed=20260926)).fingerprint())

    def test_scenario_settings_preserve_environment_without_cache(self):
        a = initialize(Config())
        b = initialize(replace(Config(), promoter_share=.30, distribution="concentrated", positive_energy=.9, negative_wom_enabled=False))
        self.assertEqual(a.environment, b.environment)
        self.assertEqual(environment_fingerprint(a), environment_fingerprint(b))

    def test_energy_changes_capacity_not_roles(self):
        low = initialize(replace(Config(), positive_energy=.3))
        high = initialize(replace(Config(), positive_energy=.9), low.environment)
        self.assertEqual([a.id for a in low.agents if a.initial_promoter], [a.id for a in high.agents if a.initial_promoter])
        self.assertAlmostEqual(high.capacity("positive"), 3 * low.capacity("positive"))

    def test_mismatched_environment_rejected(self):
        env = make_environment(Config())
        with self.assertRaises(ValueError):
            initialize(replace(Config(), seed=123), env)

    def test_independent_scenarios_do_not_share_mutable_agents(self):
        env = make_environment(Config())
        a, b = initialize(Config(), env), initialize(Config(), env)
        a.agents[0].contacted_positive.add(1)
        self.assertFalse(b.agents[0].contacted_positive)

    def test_component_seeds_distinct_and_global_rng_untouched(self):
        self.assertEqual(len({component_seed(17, name) for name in COMPONENTS}), len(COMPONENTS))
        before = random.getstate()
        initialize(Config())
        self.assertEqual(random.getstate(), before)

    def test_keyed_draws_order_independent_bounded_and_separated(self):
        keys = [(2, t, mechanism, slot) for t in range(10) for mechanism in ("buy", "target") for slot in range(2)]
        forward = {key: indexed_uniform(17, *key) for key in keys}
        reverse = {key: indexed_uniform(17, *key) for key in reversed(keys)}
        self.assertEqual(forward, reverse)
        self.assertTrue(all(0 <= u < 1 for u in forward.values()))
        self.assertEqual(len(set(forward.values())), len(keys))


class ExportTests(unittest.TestCase):
    def test_export_rows_checksums_and_reconstruction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            state = initialize(Config())
            export_initial_state(state, root)
            verify_export(root)
            with (root / "agents_initial.csv").open() as f:
                agents = list(csv.DictReader(f))
            self.assertEqual(len(agents), 600)
            self.assertEqual(sum(a["initial_promoter"] == "True" for a in agents), 18)
            with (root / "network_edges.csv").open() as f:
                edges = list(csv.DictReader(f))
            self.assertEqual(len(edges), len(state.environment.network.edges()))
            rebuilt = initialize(Config(**json.loads((root / "config.json").read_text())))
            self.assertEqual(state, rebuilt)

    def test_tampered_export_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            export_initial_state(initialize(Config()), root)
            with (root / "agents_initial.csv").open("a") as f:
                f.write("altered\n")
            with self.assertRaises(ValueError):
                verify_export(root)

    def test_existing_results_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            state = initialize(Config())
            export_initial_state(state, root)
            before = (root / "manifest.json").read_bytes()
            with self.assertRaises(FileExistsError):
                export_initial_state(state, root)
            self.assertEqual(before, (root / "manifest.json").read_bytes())

    def test_empty_network_csv_retains_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            export_initial_state(initialize(replace(Config(), p_within=0, p_between=0)), root)
            self.assertEqual((root / "network_edges.csv").read_text(), "source,target\n")
            verify_export(root)

    def test_cli_exports_are_byte_identical_across_hash_seeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / "one", Path(tmp) / "two"]
            for path, hash_seed in zip(paths, ("1", "987")):
                result = subprocess.run([sys.executable, "-m", "article8", "--out", str(path)],
                                        env={**os.environ, "PYTHONHASHSEED": hash_seed},
                                        capture_output=True, text=True, check=True)
                self.assertEqual(json.loads(result.stdout)["time"], 0)
            self.assertEqual({p.name: p.read_bytes() for p in paths[0].iterdir()},
                             {p.name: p.read_bytes() for p in paths[1].iterdir()})


if __name__ == "__main__":
    unittest.main(verbosity=2)
