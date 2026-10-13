"""CLI for M1–M6: dynamics and optional read-only diffusion analysis."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from .config import Config
from .export import export_initial_state, export_positive_simulation, export_experience_simulation, export_energy_simulation
from .experience import ExperienceConfig, ExperienceSimulation
from .energy import EnergyConfig, EnergySimulation
from .mixed import MixedSimulation, NegativeConfig
from .export import export_mixed_simulation
from .export import export_analyzed_simulation
from .analysis import AnalysisConfig
from .model import initialize
from .positive import PositiveConfig, PositiveSimulation


def main() -> None:
    parser = argparse.ArgumentParser(description="Article 8: M1–M5, including mixed positive/negative WOM")
    parser.add_argument("--mode", choices=("initial", "positive", "experience", "energy", "mixed"), default="initial")
    parser.add_argument("--dynamics-config", type=Path)
    parser.add_argument("--experience-config", type=Path)
    parser.add_argument("--energy-config", type=Path)
    parser.add_argument("--negative-config", type=Path)
    parser.add_argument("--negative-weight", type=float)
    parser.add_argument("--analysis", action="store_true", help="Add M6 indicators and classification to mixed mode")
    parser.add_argument("--analysis-config", type=Path)
    parser.add_argument("--periods", type=int)
    parser.add_argument("--no-agent-history", action="store_true")
    parser.add_argument("--config", type=Path, help="JSON configuration; defaults to baseline")
    parser.add_argument("--out", required=True, type=Path, help="New/empty output directory")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--share", type=float)
    parser.add_argument("--distribution", choices=("distributed", "concentrated"))
    parser.add_argument("--positive-energy", type=float)
    parser.add_argument("--negative-off", action="store_true")
    args = parser.parse_args()
    try:
        if args.analysis and args.mode != 'mixed':
            raise ValueError('--analysis requires --mode mixed')
        if args.analysis_config is not None and not args.analysis:
            raise ValueError('--analysis-config requires --analysis')
        analysis = AnalysisConfig(**({} if args.analysis_config is None else
                                    json.loads(args.analysis_config.read_text(encoding='utf-8'))))
        analysis.validate()
        if args.experience_config is not None and args.mode not in ("experience", "energy", "mixed"):
            raise ValueError("--experience-config requires --mode experience, energy or mixed")
        if args.energy_config is not None and args.mode not in ("energy", "mixed"):
            raise ValueError("--energy-config requires --mode energy or mixed")
        if (args.negative_config is not None or args.negative_weight is not None) and args.mode != "mixed":
            raise ValueError("Negative dynamic options require --mode mixed")
        payload = asdict(Config()) if args.config is None else json.loads(args.config.read_text(encoding="utf-8"))
        for name, value in (("seed", args.seed), ("promoter_share", args.share),
                            ("distribution", args.distribution), ("positive_energy", args.positive_energy)):
            if value is not None:
                payload[name] = value
        if args.negative_off:
            payload["negative_wom_enabled"] = False
        if args.negative_weight is not None:
            payload['negative_weight'] = args.negative_weight
        state = initialize(Config(**payload))
        if args.mode == "initial":
            if args.dynamics_config is not None or args.periods is not None or args.no_agent_history:
                raise ValueError("Dynamic options require --mode positive, experience or energy")
            export_initial_state(state, args.out)
            summary = {"scope": "M1, t=0 only", **state.summary()}
        else:
            options = {} if args.dynamics_config is None else json.loads(args.dynamics_config.read_text(encoding="utf-8"))
            if args.periods is not None:
                options["periods"] = args.periods
            if args.no_agent_history:
                options["record_agents"] = False
            if args.mode in ("experience", "energy", "mixed"):
                experience = ({} if args.experience_config is None else
                              json.loads(args.experience_config.read_text(encoding="utf-8")))
                if args.mode in ("energy", "mixed"):
                    energy = ({} if args.energy_config is None else
                              json.loads(args.energy_config.read_text(encoding="utf-8")))
                    if args.mode == 'mixed':
                        negative = ({} if args.negative_config is None else
                                    json.loads(args.negative_config.read_text(encoding='utf-8')))
                        simulation = MixedSimulation(state, PositiveConfig(**options), ExperienceConfig(**experience),
                                                     EnergyConfig(**energy), NegativeConfig(**negative)).run()
                        if args.analysis:
                            export_analyzed_simulation(simulation, args.out, analysis)
                        else:
                            export_mixed_simulation(simulation, args.out)
                    else:
                        simulation = EnergySimulation(state, PositiveConfig(**options), ExperienceConfig(**experience),
                                                      EnergyConfig(**energy)).run()
                        export_energy_simulation(simulation, args.out)
                else:
                    simulation = ExperienceSimulation(state, PositiveConfig(**options), ExperienceConfig(**experience)).run()
                    export_experience_simulation(simulation, args.out)
            else:
                simulation = PositiveSimulation(state, PositiveConfig(**options)).run()
                export_positive_simulation(simulation, args.out)
            summary = simulation.summary()
            if args.analysis:
                summary = json.loads((args.out/'run_summary.json').read_text(encoding='utf-8'))
    except (ValueError, TypeError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({"output": str(args.out), **summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
