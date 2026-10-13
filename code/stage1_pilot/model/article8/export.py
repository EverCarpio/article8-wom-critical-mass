"""Deterministic CSV/JSON exports and content checksums; never overwrite runs."""
from collections import Counter
from dataclasses import asdict
import csv
import hashlib
import json
from pathlib import Path
import platform
from . import __version__
from .model import InitialState, WOM
from .randomness import COMPONENTS, RNG_VERSION, component_seed


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict], columns: list[str] | None = None) -> None:
    if columns is None:
        if not rows:
            raise ValueError("Columns are required for an empty table")
        columns = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def environment_fingerprint(state: InitialState) -> str:
    e = state.environment
    payload = [e.key, e.network.fingerprint(), [asdict(t) for t in e.traits],
               sorted(e.customers), sorted(e.detractors), e.promoter_order, e.community_order]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def community_rows(state: InitialState) -> list[dict]:
    rows = []
    for c in range(state.config.communities):
        agents = [a for a in state.agents if a.community == c]
        counts = Counter(a.wom for a in agents)
        rows.append({"community": c, "population": len(agents),
                     "customers": sum(a.initial_customer for a in agents),
                     "susceptibles": sum(not a.initial_customer for a in agents),
                     "nominal_promoters": sum(a.initial_promoter for a in agents),
                     "nominal_detractors": sum(a.initial_detractor for a in agents),
                     "active_promoters": counts[WOM.PROMOTER_ACTIVE],
                     "active_detractors": counts[WOM.DETRACTOR_ACTIVE]})
    return rows


def export_initial_state(state: InitialState, directory: str | Path) -> dict:
    state.validate()
    root = Path(directory)
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise FileExistsError(f"Output must be a new or empty directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "config.json", asdict(state.config))
    write_json(root / "network_metrics.json", state.environment.network.metrics())
    write_csv(root / "network_edges.csv", [{"source": i, "target": j} for i, j in state.environment.network.edges()], ["source", "target"])
    rows = []
    for a in state.agents:
        row = asdict(a)
        row.update(row.pop("traits"))
        for key in ("contacted_positive", "contacted_negative"):
            row[key] = json.dumps(sorted(row[key]))
        row["inactivity_reasons"] = json.dumps(row["inactivity_reasons"])
        row["degree"] = len(state.environment.network.neighbors[a.id])
        row["remaining_positive_contacts"] = len(state.eligible_contacts(a.id, "positive"))
        row["remaining_negative_contacts"] = len(state.eligible_contacts(a.id, "negative"))
        rows.append(row)
    write_csv(root / "agents_initial.csv", rows)
    write_csv(root / "community_summary.csv", community_rows(state))
    write_csv(root / "system_period.csv", [state.summary()])
    manifest = {
        "module_version": __version__, "scope": "M1 initialization only; t=0",
        "python_version": platform.python_version(), "rng_version": RNG_VERSION,
        "master_seed": state.config.seed,
        "component_seeds": {name: component_seed(state.config.seed, name) for name in COMPONENTS},
        "community_order": state.environment.community_order,
        "network_sha256": state.environment.network.fingerprint(),
        "environment_sha256": environment_fingerprint(state),
        "files_sha256": {p.name: sha256_file(p) for p in sorted(root.iterdir()) if p.is_file()},
    }
    write_json(root / "manifest.json", manifest)
    return manifest


def verify_export(directory: str | Path) -> None:
    root = Path(directory)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["files_sha256"].items():
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()) or not path.is_file() or sha256_file(path) != expected:
            raise ValueError(f"Missing or altered export: {name}")


def export_positive_simulation(simulation, directory: str | Path) -> dict:
    from .positive import EVENT_COLUMNS, DECISION_COLUMNS
    simulation.validate()
    root = Path(directory)
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise FileExistsError(f"Output must be a new or empty directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    export_initial_state(simulation.initial, root / "initial_state")
    write_json(root / "dynamics_config.json", asdict(simulation.dynamics))
    write_json(root / "run_summary.json", simulation.summary())
    write_csv(root / "system_period.csv", simulation.system)
    write_csv(root / "wom_events.csv", simulation.events, EVENT_COLUMNS)
    write_csv(root / "purchase_decisions.csv", simulation.decisions, DECISION_COLUMNS)
    write_csv(root / "purchases.csv", [d for d in simulation.decisions if d["adopted"]], DECISION_COLUMNS)
    write_csv(root / "agents_final.csv", simulation.agent_rows())
    if simulation.dynamics.record_agents:
        write_csv(root / "agent_period.csv", simulation.agent_history)
    manifest = {
        "module_version": __version__, "scope": simulation.summary()["scope"],
        "python_version": platform.python_version(), "rng_version": RNG_VERSION,
        "master_seed": simulation.state.config.seed,
        "custom_draw_function": simulation.custom_draw,
        "reproducibility_note": ("Custom test function not serialized" if simulation.custom_draw else
                                  "Recreate with initial_state/config.json and dynamics_config.json"),
        "environment_sha256": environment_fingerprint(simulation.initial),
        "completed_periods": simulation.time,
        "files_sha256": {str(p.relative_to(root)): sha256_file(p) for p in sorted(root.rglob("*")) if p.is_file()},
    }
    write_json(root / "manifest.json", manifest)
    return manifest


def export_experience_simulation(simulation, directory: str | Path) -> dict:
    from .experience import EXPERIENCE_COLUMNS, ACTIVATION_COLUMNS, LINEAGE_COLUMNS
    manifest = export_positive_simulation(simulation, directory)
    root = Path(directory)
    write_json(root / "experience_config.json", asdict(simulation.experience_config))
    write_csv(root / "experience_events.csv", simulation.experience_events, EXPERIENCE_COLUMNS)
    write_csv(root / "activation_events.csv", simulation.activation_events, ACTIVATION_COLUMNS)
    write_csv(root / "lineage.csv", simulation.lineage_rows(), LINEAGE_COLUMNS)
    if not simulation.custom_draw:
        manifest["reproducibility_note"] = (
            "Recreate with initial_state/config.json, dynamics_config.json and experience_config.json")
    manifest["files_sha256"] = {
        str(p.relative_to(root)): sha256_file(p) for p in sorted(root.rglob("*"))
        if p.is_file() and p != root / "manifest.json"}
    write_json(root / "manifest.json", manifest)
    return manifest


def export_energy_simulation(simulation, directory: str | Path) -> dict:
    from .energy import ENERGY_COLUMNS
    manifest = export_experience_simulation(simulation, directory)
    root = Path(directory)
    write_json(root / "energy_config.json", asdict(simulation.energy_config))
    write_csv(root / "energy_period.csv", simulation.energy_updates, ENERGY_COLUMNS)
    write_csv(root / "deactivation_events.csv", [r for r in simulation.energy_updates if r["deactivated"]], ENERGY_COLUMNS)
    if not simulation.custom_draw:
        manifest["reproducibility_note"] = (
            "Recreate with initial_state/config.json, dynamics_config.json, experience_config.json and energy_config.json")
    manifest["files_sha256"] = {
        str(p.relative_to(root)): sha256_file(p) for p in sorted(root.rglob("*"))
        if p.is_file() and p != root / "manifest.json"}
    write_json(root / "manifest.json", manifest)
    return manifest


def export_mixed_simulation(simulation, directory: str | Path) -> dict:
    from .mixed import (MIXED_EVENT_COLUMNS, MIXED_DECISION_COLUMNS, MIXED_EXPERIENCE_COLUMNS,
                        MIXED_ACTIVATION_COLUMNS, MIXED_ENERGY_COLUMNS)
    from .experience import LINEAGE_COLUMNS
    simulation.validate()
    root = Path(directory)
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise FileExistsError(f'Output must be a new or empty directory: {root}')
    root.mkdir(parents=True, exist_ok=True)
    export_initial_state(simulation.initial, root / 'initial_state')
    for name, config in (('dynamics',simulation.dynamics), ('experience',simulation.experience_config),
                         ('energy',simulation.energy_config), ('negative',simulation.negative_config)):
        write_json(root / (name + '_config.json'), asdict(config))
    write_json(root / 'run_summary.json', simulation.summary())
    for name, rows, columns in (
        ('wom_events',simulation.events,MIXED_EVENT_COLUMNS),
        ('purchase_decisions',simulation.decisions,MIXED_DECISION_COLUMNS),
        ('purchases',[d for d in simulation.decisions if d['adopted']],MIXED_DECISION_COLUMNS),
        ('experience_events',simulation.experience_events,MIXED_EXPERIENCE_COLUMNS),
        ('activation_events',simulation.activation_events,MIXED_ACTIVATION_COLUMNS),
        ('energy_period',simulation.energy_updates,MIXED_ENERGY_COLUMNS),
        ('deactivation_events',[r for r in simulation.energy_updates if r['deactivated']],MIXED_ENERGY_COLUMNS),
        ('lineage',simulation.lineage_rows(),LINEAGE_COLUMNS)):
        write_csv(root / (name + '.csv'), rows, columns)
    write_csv(root / 'system_period.csv', simulation.system)
    write_csv(root / 'agents_final.csv', simulation.agent_rows())
    if simulation.dynamics.record_agents:
        write_csv(root / 'agent_period.csv', simulation.agent_history)
    manifest = {'module_version': __version__, 'scope': simulation.summary()['scope'],
        'python_version': platform.python_version(), 'rng_version': RNG_VERSION,
        'master_seed': simulation.state.config.seed, 'custom_draw_function': simulation.custom_draw,
        'reproducibility_note': ('Custom test function not serialized' if simulation.custom_draw else
            'Recreate with initial_state/config.json and the four *_config.json files'),
        'environment_sha256': environment_fingerprint(simulation.initial), 'completed_periods': simulation.time,
        'files_sha256': {str(p.relative_to(root)): sha256_file(p) for p in sorted(root.rglob('*')) if p.is_file()}}
    write_json(root / 'manifest.json', manifest)
    return manifest


def export_analyzed_simulation(simulation, directory, config=None):
    """Export M5 dynamics plus M6 observation, without mutating the simulation."""
    from .analysis import AnalysisConfig, analyze_simulation
    analysis = analyze_simulation(simulation, config or AnalysisConfig())
    manifest = export_mixed_simulation(simulation, directory)
    root = Path(directory)
    write_json(root / 'analysis_config.json', analysis.config)
    write_json(root / 'analysis_summary.json', analysis.summary)
    write_json(root / 'run_summary.json', {**simulation.summary(), **analysis.summary})
    rows = []
    for original in analysis.system:
        row = dict(original)
        for name in ('purchase_communities', 'message_communities'):
            row[name] = json.dumps(row[name])
        rows.append(row)
    write_csv(root / 'system_period.csv', rows)
    reproduction_columns = ['window_start', 'window_end', 'window_width', 'observed_end',
        'cohort_available_at', 'active_at_start', 'window_births_observed', 'window_censored',
        'window_ratio', 'cohort_children_observed', 'cohort_censored', 'cohort_ratio',
        'zero_denominator', 'cohort_members', 'direct_children_observed']
    classification_columns = ['kind', 'window_start', 'expected_confirmation', 'observed_end',
                              'censored', 'triggered', 'criteria', 'statistics']
    write_csv(root / 'reproduction_windows.csv', analysis.reproduction, reproduction_columns)
    write_csv(root / 'classification_windows.csv', analysis.classification_windows, classification_columns)
    manifest.update(scope=analysis.summary['scope'], analysis_enabled=True)
    if not simulation.custom_draw:
        manifest['reproducibility_note'] = 'Recreate with --mode mixed --analysis, initial_state/config.json and five *_config.json files'
    manifest['files_sha256'] = {str(p.relative_to(root)):sha256_file(p) for p in sorted(root.rglob('*'))
                               if p.is_file() and p != root/'manifest.json'}
    write_json(root / 'manifest.json', manifest)
    return manifest
