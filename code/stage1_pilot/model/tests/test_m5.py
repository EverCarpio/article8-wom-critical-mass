"""Mechanistic tests for mixed exposure and experience-based negative WOM."""
from copy import deepcopy
from dataclasses import asdict, replace
import csv
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from article8.config import Config
from article8.energy import EnergyConfig, EnergySimulation
from article8.experience import ExperienceConfig
from article8.export import export_mixed_simulation, verify_export
from article8.mixed import MixedSimulation, NegativeConfig, mixed_adoption_probability
from article8.model import Commercial, Experience, Traits, WOM, initialize, make_environment
from article8.network import Network
from article8.positive import PositiveConfig
from test_m2 import accept
from test_m3 import chain

BAD_EXPERIENCE = ExperienceConfig(quality=.2, fit_effect=0, noise_amplitude=0)


def mixed_fixture(target_count=1, two_positive=False, weight=1, negative_on=True):
    cfg = Config(n=8, communities=2, initial_customers=4, initial_detractors=2,
                 promoter_share=.5 if two_positive else .25, positive_energy=1, negative_energy=1,
                 negative_wom_enabled=negative_on, negative_weight=weight)
    env = make_environment(cfg)
    raw = initialize(cfg,env)
    pos = [a.id for a in raw.agents if a.initial_promoter]
    neg = [a.id for a in raw.agents if a.initial_detractor]
    targets = [a.id for a in raw.agents if not a.initial_customer][:target_count]
    adj = [set() for _ in raw.agents]
    for i in pos + neg[:1]:
        for j in targets:
            adj[i].add(j); adj[j].add(i)
    env = replace(env, network=Network(env.network.community,tuple(frozenset(x) for x in adj)),
                  traits=tuple(Traits(.5,.5,1) for _ in raw.agents))
    return initialize(cfg,env),pos,neg,targets


def detractor_chain(periods=6, negative=NegativeConfig(), draw=accept, energy=EnergyConfig()):
    initial,root,targets = chain()
    initial = initialize(replace(initial.config,negative_wom_enabled=True),initial.environment)
    sim = MixedSimulation(initial,PositiveConfig(periods=periods,opportunities=1),BAD_EXPERIENCE,energy,negative,draw)
    return sim,root,targets


def project(rows, template):
    if not template:
        return rows
    return [{k:r[k] for k in template[0]} for r in rows]


class MixedProbabilityTests(unittest.TestCase):
    def test_defaults_and_invalid_negative_parameters(self):
        self.assertEqual(asdict(NegativeConfig()), {'disposition_probability':.8, 'new_detractor_energy':.6,
                         'decay':.06, 'message_cost':.04, 'influence_coefficient':1.2})
        for key in asdict(NegativeConfig()):
            for value in (-.1,math.inf,math.nan,True,'0.8'):
                with self.subTest(key=key,value=value), self.assertRaises(ValueError):
                    replace(NegativeConfig(),**{key:value}).validate()
            if key != 'influence_coefficient':
                with self.assertRaises(ValueError):
                    replace(NegativeConfig(),**{key:1.1}).validate()

    def test_hand_calculated_equal_influences(self):
        # Identical H+ and H− cancel with coefficients 1.2 and lambda=1.
        self.assertAlmostEqual(mixed_adoption_probability(.5,.5,1,1,True),1/(1+math.exp(.5)))

    def test_more_negative_influence_or_weight_reduces_probability(self):
        probabilities = [mixed_adoption_probability(.5,.5,1,x,True) for x in (0,.2,1,10)]
        self.assertEqual(probabilities,sorted(probabilities,reverse=True))
        self.assertGreater(mixed_adoption_probability(.5,.5,1,1,True,weight=1),
                           mixed_adoption_probability(.5,.5,1,1,True,weight=2))

    def test_negative_only_and_old_positive_memory_do_not_open_purchase_gate(self):
        self.assertEqual(mixed_adoption_probability(1,1,100,5,False),0)
        self.assertEqual(mixed_adoption_probability(1,1,100,5,False,weight=0),0)

    def test_probability_is_stable_at_extreme_weight(self):
        self.assertEqual(mixed_adoption_probability(.5,.5,1,1,True,weight=1e308),0)
        self.assertTrue(0 < mixed_adoption_probability(.5,.5,1,0,True,weight=1e308) < 1)


class MixedExposureTests(unittest.TestCase):
    def test_same_period_positive_and_negative_messages_one_purchase_decision(self):
        initial,pos,neg,targets = mixed_fixture()
        sim = MixedSimulation(initial,PositiveConfig(periods=1),draw=accept).run()
        self.assertEqual(len(sim.events),2)
        self.assertEqual(len(sim.decisions),1)
        self.assertEqual((sim.decisions[0]['new_positive_messages'],sim.decisions[0]['new_negative_messages']),(1,1))
        self.assertEqual(sim.agents[targets[0]].parent,pos[0])
        self.assertEqual(sum(e['credited_purchase_parent'] for e in sim.events),1)
        self.assertFalse(next(e for e in sim.events if e['sign']=='negative')['credited_purchase_parent'])

    def test_simultaneous_negative_exposure_affects_purchase_not_next_period_only(self):
        def draw(agent,t,mechanism,slot):
            return .45 if mechanism=='purchase' else 0
        initial,_,_,targets = mixed_fixture()
        sim = MixedSimulation(initial,PositiveConfig(periods=1),draw=draw).run()
        d = sim.decisions[0]
        self.assertLess(d['probability'],.45)
        self.assertGreater(d['probability_without_negative'],.45)
        self.assertFalse(d['adopted'])
        self.assertEqual(sim.agents[targets[0]].commercial,Commercial.SUSCEPTIBLE)

    def test_negative_only_records_gate_zero_without_a_purchase_draw(self):
        initial,pos,_,targets = mixed_fixture()
        calls = []
        def draw(agent,t,mechanism,slot):
            calls.append(mechanism)
            return .99 if agent in pos and mechanism=='positive_opportunity' else 0
        sim = MixedSimulation(initial,PositiveConfig(periods=1),draw=draw).run()
        self.assertEqual(len(sim.events),1)
        self.assertNotIn('purchase',calls)
        self.assertIsNone(sim.decisions[0]['purchase_draw'])
        self.assertEqual(sim.decisions[0]['probability'],0)
        self.assertTrue(sim.agent_rows()[targets[0]]['aware'])

    def test_negative_memory_survives_and_decays_before_later_positive_message(self):
        initial,pos,_,targets = mixed_fixture()
        def draw(agent,t,mechanism,slot):
            return .99 if agent in pos and t==1 and mechanism=='positive_opportunity' else 0
        sim = MixedSimulation(initial,PositiveConfig(periods=2,opportunities=1),draw=draw).run()
        self.assertEqual([d['new_positive_messages'] for d in sim.decisions],[0,1])
        self.assertEqual(sim.decisions[1]['negative_memory_after'],.5)
        self.assertAlmostEqual(sim.decisions[1]['probability'],mixed_adoption_probability(.5,.5,1,.5,True))

    def test_memory_retention_extremes_and_freeze_after_purchase(self):
        for rho in (0,1):
            initial,pos,_,targets = mixed_fixture()
            def draw(agent,t,mechanism,slot):
                return .99 if agent in pos and t==1 and mechanism=='positive_opportunity' else 0
            sim = MixedSimulation(initial,PositiveConfig(periods=4,opportunities=1,memory_retention=rho),draw=draw).run()
            self.assertEqual(sim.agents[targets[0]].negative_memory,rho)
            self.assertEqual(sim.agents[targets[0]].purchase_time,2)

    def test_rejected_negative_contact_is_not_repeated_and_budget_is_finite(self):
        initial,pos,neg,targets = mixed_fixture(target_count=3)
        def draw(agent,t,mechanism,slot):
            return .99 if mechanism in ('positive_opportunity','purchase') else 0
        sim = MixedSimulation(initial,PositiveConfig(periods=4),draw=draw).run()
        events = [e for e in sim.events if e['sign']=='negative']
        self.assertEqual(len(events),3)
        self.assertEqual(len({(e['sender'],e['receiver']) for e in events}),3)
        self.assertEqual([sum(e['period']==t for e in events) for t in (1,2,3,4)],[2,1,0,0])
        self.assertTrue(all(sim.agents[j].commercial==Commercial.SUSCEPTIBLE for j in targets))

    def test_several_positive_and_negative_messages_still_one_purchase(self):
        initial,pos,_,targets = mixed_fixture(two_positive=True)
        sim = MixedSimulation(initial,PositiveConfig(periods=1),draw=accept).run()
        self.assertEqual(len(sim.events),3)
        self.assertEqual(len(sim.decisions),1)
        self.assertEqual(sim.agents[targets[0]].parent,min(pos))
        self.assertEqual(sim.system[1]['new_unique_positive_recipients'],1)
        self.assertEqual(sim.system[1]['new_unique_negative_recipients'],1)

    def test_negative_sender_cannot_be_parent_even_with_higher_credibility(self):
        initial,pos,neg,targets = mixed_fixture()
        traits = list(initial.environment.traits)
        traits[pos[0]] = replace(traits[pos[0]],credibility=.6)
        initial = initialize(initial.config,replace(initial.environment,traits=tuple(traits)))
        sim = MixedSimulation(initial,PositiveConfig(periods=1),draw=accept).run()
        self.assertEqual(sim.agents[targets[0]].parent,pos[0])


class DetractorLifecycleTests(unittest.TestCase):
    def test_purchase_then_experience_then_single_detractor_activation(self):
        sim,root,targets = detractor_chain()
        sim.run(until=1)
        self.assertEqual(sim.agents[targets[0]].commercial,Commercial.PENDING)
        sim.run(until=2)
        a = sim.agents[targets[0]]
        self.assertEqual(a.wom,WOM.DETRACTOR_POTENTIAL)
        self.assertEqual(a.negative_energy,.6)
        self.assertIsNone(a.activation_time)
        sim.run(until=3)
        self.assertEqual(sim.agents[targets[0]].activation_time,3)
        self.assertEqual(sim.system[3]['new_detractors'],1)
        self.assertEqual(next(e for e in sim.events if e['sign']=='negative')['period'],3)
        self.assertEqual(sim.agents[targets[0]].parent,root)
        self.assertIsNone(sim.agents[targets[0]].generation)
        sim.run()
        self.assertEqual(len(sim.experience_events),1)
        self.assertEqual(len(sim.activation_events),1)

    def test_receiving_negative_wom_does_not_create_detractor(self):
        sim,_,targets = detractor_chain()
        sim.run()
        a = sim.agents[targets[1]]
        self.assertEqual(a.commercial,Commercial.SUSCEPTIBLE)
        self.assertEqual(a.experience,Experience.UNEVALUATED)
        self.assertFalse(a.negative_eligible)
        self.assertEqual(a.wom,WOM.NONE)
        self.assertEqual(a.negative_exposures,1)

    def test_disposition_is_strict_and_drawn_only_once(self):
        calls=[]
        def draw(agent,t,mechanism,slot):
            calls.append(mechanism)
            return .8 if mechanism=='negative_disposition' else 0
        sim,_,targets = detractor_chain(draw=draw)
        sim.run()
        self.assertEqual(calls.count('negative_disposition'),1)
        self.assertEqual(sim.agents[targets[0]].experience,Experience.DISSATISFIED)
        self.assertEqual(sim.agents[targets[0]].wom,WOM.NONE)
        self.assertFalse(sim.activation_events)

    def test_disposition_zero_one_and_mutually_exclusive_roles(self):
        for p,expected in ((0,0),(1,1)):
            sim,_,targets = detractor_chain(negative=NegativeConfig(disposition_probability=p))
            sim.run()
            self.assertEqual(sim.summary()['cumulative_new_detractors'],expected)
            self.assertTrue(all(not(a.positive_eligible and a.negative_eligible) for a in sim.agents))

    def test_neutral_and_satisfied_do_not_draw_negative_disposition(self):
        for quality in (.5,1):
            initial,_,_ = chain()
            initial = initialize(replace(initial.config,negative_wom_enabled=True),initial.environment)
            calls=[]
            def draw(agent,t,mechanism,slot):
                calls.append(mechanism); return 0
            sim=MixedSimulation(initial,PositiveConfig(periods=3,opportunities=1),
                replace(BAD_EXPERIENCE,quality=quality),draw=draw).run()
            self.assertNotIn('negative_disposition',calls)
            self.assertEqual(sim.summary()['cumulative_new_detractors'],0)

    def test_negative_energy_independent_of_initial_and_positive_energy(self):
        sim,_,targets = detractor_chain(periods=3,negative=NegativeConfig(new_detractor_energy=.7,decay=.1,message_cost=.02))
        sim.run()
        e=next(e for e in sim.events if e['sign']=='negative')
        self.assertEqual(e['sender_energy'],.7)
        self.assertAlmostEqual(sim.agents[targets[0]].negative_energy,.61)
        self.assertEqual(sim.agents[targets[0]].positive_energy,0)

    def test_zero_and_threshold_energy_block_activation_without_retry(self):
        for energy in (0,.05):
            sim,_,targets=detractor_chain(negative=NegativeConfig(new_detractor_energy=energy))
            sim.run()
            a=sim.agents[targets[0]]
            self.assertEqual(a.wom,WOM.DETRACTOR_POTENTIAL)
            self.assertEqual(a.inactivity_reasons,('energy_exhausted',))
            self.assertEqual(len(sim.activation_events),1)
            self.assertEqual(a.negative_energy,energy)
            self.assertFalse(any(e['sign']=='negative' for e in sim.events))

    def test_no_contacts_blocks_activation(self):
        initial,_,_,targets=mixed_fixture(negative_on=False)
        # Enable mechanism while all neighbors of each buyer are initial customers.
        initial=initialize(replace(initial.config,negative_wom_enabled=True),initial.environment)
        sim=MixedSimulation(initial,PositiveConfig(periods=6),BAD_EXPERIENCE,draw=accept).run()
        a=sim.agents[targets[0]]
        self.assertEqual(a.wom,WOM.DETRACTOR_POTENTIAL)
        self.assertEqual(a.inactivity_reasons,('contacts_exhausted',))
        self.assertEqual(len([e for e in sim.activation_events if e['agent']==a.id]),1)

    def test_negative_decay_no_messages_and_inactivity_freeze(self):
        initial,_,neg,_=mixed_fixture(target_count=3)
        sim=MixedSimulation(initial,PositiveConfig(periods=7,opportunities=0),
                            negative=NegativeConfig(decay=1,message_cost=0)).run()
        a=sim.agents[neg[0]]
        self.assertEqual(a.negative_energy,0)
        self.assertEqual(a.wom,WOM.DETRACTOR_INACTIVE)
        self.assertEqual(a.inactivity_reasons,('energy_exhausted',))
        self.assertEqual(len([r for r in sim.energy_updates if r['agent']==a.id]),1)

    def test_both_negative_deactivation_causes_and_no_double_count(self):
        initial,_,neg,_=mixed_fixture()
        sim=MixedSimulation(initial,PositiveConfig(periods=2),negative=NegativeConfig(decay=0,message_cost=1),draw=accept).run()
        self.assertEqual(sim.agents[neg[0]].inactivity_reasons,('energy_exhausted','contacts_exhausted'))
        self.assertEqual(sim.system[1]['negative_deactivated_both'],1)
        self.assertEqual(sim.system[1]['deactivated_detractors'],1)

    def test_horizon_censors_experience_and_detractor_activation(self):
        one,_,_=detractor_chain(periods=1); one.run()
        self.assertEqual(one.summary()['pending_experience_customers'],1)
        two,_,targets=detractor_chain(periods=2); two.run()
        self.assertEqual(two.summary()['pending_activation_detractors'],1)
        self.assertEqual(two.summary()['cumulative_negative_blocked_activations'],0)
        self.assertEqual(two.agent_rows()[targets[0]]['activation_status'],'pending')


class MixedRegressionTests(unittest.TestCase):
    def test_negative_off_exactly_recovers_m4_core_trajectory(self):
        cfg=Config(negative_wom_enabled=False)
        initial=initialize(cfg); dyn=PositiveConfig(periods=10,record_agents=False)
        old=EnergySimulation(initial,dyn).run(); new=MixedSimulation(initial,dyn).run()
        self.assertEqual(old.agents,new.agents)
        for name in ('events','decisions','experience_events','activation_events','energy_updates'):
            self.assertEqual(getattr(old,name),project(getattr(new,name),getattr(old,name)),name)
        for a,b in zip(old.system,new.system):
            self.assertEqual({k:v for k,v in a.items() if k!='diffusion_class'},
                             {k:b[k] for k in a if k!='diffusion_class'})

    def test_weight_zero_keeps_negative_mechanism_but_purchase_matches_off(self):
        initial,_,_,_=mixed_fixture(target_count=3,weight=0)
        off=initialize(replace(initial.config,negative_wom_enabled=False),initial.environment)
        a=MixedSimulation(initial,PositiveConfig(periods=5),BAD_EXPERIENCE,draw=accept).run()
        b=EnergySimulation(off,PositiveConfig(periods=5),BAD_EXPERIENCE,draw=accept).run()
        self.assertTrue(any(e['sign']=='negative' for e in a.events))
        self.assertTrue(any(x.negative_memory>0 for x in a.agents))
        self.assertGreater(a.summary()['cumulative_negative_energy_loss'],0)
        self.assertEqual([(d['period'],d['receiver']) for d in a.decisions if d['adopted']],
                         [(d['period'],d['receiver']) for d in b.decisions if d['adopted']])

    def test_negative_off_disables_disposition_draws_and_memory_not_identities(self):
        initial,_,dets,_=mixed_fixture(negative_on=False)
        calls=[]
        def draw(agent,t,mechanism,slot):
            calls.append(mechanism); return 0
        sim=MixedSimulation(initial,PositiveConfig(periods=6),BAD_EXPERIENCE,draw=draw).run()
        self.assertFalse(any(x.startswith('negative_') for x in calls))
        self.assertTrue(all(a.negative_memory==0 and a.negative_exposures==0 for a in sim.agents))
        self.assertTrue(all(sim.agents[i].initial_detractor and sim.agents[i].experience==Experience.DISSATISFIED for i in dets))
        self.assertFalse(any(e['sign']=='negative' for e in sim.events+sim.activation_events+sim.energy_updates))

    def test_reversed_sender_order_preserves_mixed_events_and_energy(self):
        dyn=PositiveConfig(periods=8,record_agents=False)
        a=MixedSimulation(dynamics=dyn).run(); b=MixedSimulation(dynamics=dyn)
        for _ in range(dyn.periods): b.step(list(reversed(b.next_sender_ids())))
        b.validate()
        for name in ('events','decisions','experience_events','activation_events','energy_updates','agents','system'):
            self.assertEqual(getattr(a,name),getattr(b,name),name)

    def test_chunked_execution_and_recording_do_not_change_dynamics(self):
        a,_,_=detractor_chain(); b,_,_=detractor_chain()
        b.dynamics=replace(b.dynamics,record_agents=False)
        b.agent_history=[]
        a.run(); b.run(until=1).run(until=2).run(until=3).run()
        self.assertEqual(a.agents,b.agents)
        self.assertEqual(a.system,b.system)

    def test_bad_negative_draw_rolls_back_period_and_all_ledgers(self):
        def draw(agent,t,mechanism,slot):
            return math.nan if mechanism=='negative_disposition' else 0
        sim,_,_=detractor_chain(draw=draw)
        sim.run(until=1); before=deepcopy(sim.state)
        with self.assertRaises(ValueError): sim.step()
        self.assertEqual(sim.state,before)
        self.assertFalse(sim.experience_events)
        sim.validate()

    def test_failure_after_mixed_energy_update_is_atomic(self):
        initial,_,_,_=mixed_fixture()
        sim=MixedSimulation(initial,PositiveConfig(periods=1),draw=accept)
        before=deepcopy(sim.state)
        with patch.object(sim,'_system_row',side_effect=ValueError('injected')):
            with self.assertRaises(ValueError): sim.step()
        self.assertEqual(sim.state,before)
        self.assertFalse(sim.events or sim.decisions or sim.energy_updates)
        sim.validate()

    def test_corrupt_negative_event_memory_energy_or_disposition_detected(self):
        def duplicate(s): s.events.append(dict(next(e for e in s.events if e['sign']=='negative')))
        def energy(s): next(r for r in s.energy_updates if r['sign']=='negative')['energy_after']+=.01
        def disposition(s): s.experience_events[0]['negative_disposition']=False
        def memory(s): s.agents[next(e['receiver'] for e in s.events if e['sign']=='negative')].negative_memory+=.1
        def parent(s): s.decisions[0]['parent']=next(e['sender'] for e in s.events if e['sign']=='negative')
        for corrupt in (duplicate,energy,disposition,memory,parent):
            sim,_,_=detractor_chain(); sim.run(); corrupt(sim)
            with self.subTest(corrupt=corrupt.__name__),self.assertRaises(ValueError): sim.validate()

    def test_zero_horizon_and_only_detractors_cannot_generate_customers(self):
        zero=MixedSimulation(dynamics=PositiveConfig(periods=0)).run()
        self.assertEqual(len(zero.system),1)
        cfg=Config(promoter_share=0)
        sim=MixedSimulation(initialize(cfg),PositiveConfig(periods=5,record_agents=False),draw=accept).run()
        self.assertTrue(sim.events)
        self.assertEqual(sim.summary()['customers'],120)
        self.assertFalse(sim.experience_events or sim.activation_events)


class MixedExportTests(unittest.TestCase):
    def test_export_reconciles_both_signs_and_exposure_gate(self):
        sim,_,_=detractor_chain(); sim.run()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); export_mixed_simulation(sim,root); verify_export(root)
            with (root/'wom_events.csv').open() as f: events=list(csv.DictReader(f))
            with (root/'purchase_decisions.csv').open() as f: decisions=list(csv.DictReader(f))
            self.assertEqual({e['sign'] for e in events},{'positive','negative'})
            self.assertEqual(next(d for d in decisions if d['eligible_to_buy']=='False')['purchase_draw'],'')
            self.assertIn('negative_config.json',json.loads((root/'manifest.json').read_text())['files_sha256'])

    def test_serialized_configuration_reproduces_all_ledgers(self):
        a=MixedSimulation(dynamics=PositiveConfig(periods=7,record_agents=False),negative=NegativeConfig(decay=.12)).run()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); export_mixed_simulation(a,root)
            def read(name): return json.loads((root/name).read_text())
            b=MixedSimulation(initialize(Config(**read('initial_state/config.json'))),PositiveConfig(**read('dynamics_config.json')),
                ExperienceConfig(**read('experience_config.json')),EnergyConfig(**read('energy_config.json')),
                NegativeConfig(**read('negative_config.json'))).run()
            for key in ('events','decisions','activation_events','energy_updates','system'):
                self.assertEqual(getattr(a,key),getattr(b,key))

    def test_empty_headers_no_overwrite_and_checksum(self):
        sim=MixedSimulation(dynamics=PositiveConfig(periods=0)).run()
        with tempfile.TemporaryDirectory() as tmp:
            export_mixed_simulation(sim,tmp)
            for name in ('wom_events','activation_events','energy_period'):
                self.assertEqual(len((Path(tmp)/(name+'.csv')).read_text().splitlines()),1)
            with self.assertRaises(FileExistsError): export_mixed_simulation(sim,tmp)
            (Path(tmp)/'negative_config.json').write_text('{}')
            with self.assertRaises(ValueError): verify_export(tmp)

    def test_cli_byte_identity_across_hash_seeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths=[Path(tmp)/'one',Path(tmp)/'two']
            for path,seed in zip(paths,('18','61')):
                run=subprocess.run([sys.executable,'-m','article8','--mode','mixed','--periods','5',
                    '--no-agent-history','--negative-weight','2','--out',str(path)],
                    env={**os.environ,'PYTHONHASHSEED':seed},capture_output=True,text=True,check=True)
                self.assertTrue(json.loads(run.stdout)['new_detractor_formation_enabled'])
            self.assertEqual(*[{str(p.relative_to(path)):p.read_bytes() for p in path.rglob('*') if p.is_file()} for path in paths])

    def test_cli_negative_config_and_mode_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            config=Path(tmp)/'negative.json'; config.write_text(json.dumps(asdict(NegativeConfig(disposition_probability=0))))
            args=[sys.executable,'-m','article8','--negative-config',str(config),'--periods','3',
                  '--no-agent-history','--out',str(Path(tmp)/'run')]
            bad=subprocess.run(args+['--mode','energy','--negative-off'],capture_output=True,text=True)
            self.assertNotEqual(bad.returncode,0)
            good=subprocess.run(args+['--mode','mixed','--negative-off'],capture_output=True,text=True,check=True)
            self.assertFalse(json.loads(good.stdout)['negative_wom_enabled'])


if __name__=='__main__': unittest.main(verbosity=2)
