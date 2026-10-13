# Article 8 — M4: desgaste de energía y fatiga

Versión **0.4.0-m4**. Simulación en Python con biblioteca estándar, sin paquetes externos. Probada en **Python 3.12.14**; requiere 3.11 o posterior. Conserva los modos M1, M2 y M3 y añade actualización de energía y fatiga al ciclo positivo de WOM, compra y formación de promotores.

## Ejecución

Descomprima el ZIP y abra una terminal en `article8_m4`:

```bash
python -m article8 --mode energy --config configs/m4_baseline.json --dynamics-config configs/m4_dynamics.json --experience-config configs/m4_experience.json --energy-config configs/m4_energy.json --out outputs/distributed
python -m article8 --mode energy --config configs/m4_baseline.json --distribution concentrated --out outputs/concentrated
python -m unittest discover -s tests -v
python scripts/verify_m4.py --out outputs/verification
```

Use directorios de salida nuevos o vacíos; no se sobrescriben resultados. El verificador ejecuta **146 pruebas** y **40 corridas diagnósticas**: diez semillas, dos distribuciones y dos condiciones de desgaste. Guarda dos ejemplos completos con desgaste base. Estas corridas no constituyen el piloto del modelo completo.

Para una corrida breve:

```bash
python -m article8 --mode energy --negative-off --periods 10 --no-agent-history --out outputs/short
```

`--mode initial`, `--mode positive` y `--mode experience` conservan sus alcances anteriores. `--energy-config` solo se acepta en modo `energy`; `--experience-config` se admite en `experience` y `energy`. Los modos dinámicos todavía requieren WOM negativo deshabilitado mediante la configuración o `--negative-off`.

## Regla implementada

Para cada promotor activo durante el período, incluso si no envía mensajes:

```text
E_cierre = max[0, (1 − delta) × E_inicio − costo × mensajes_emitidos]
delta = 0,06
costo = 0,04
```

Todas las oportunidades del período usan **E_inicio**. Los mensajes y compras se procesan como lote síncrono; después se descuenta energía y se revisan los contactos restantes. No se interrumpe una segunda oportunidad porque la primera haya consumido el presupuesto: el costo se aplica al cierre y la energía se recorta a cero.

| Caso | Actualización |
|---|---|
| Activo que envía mensajes | Desgaste temporal y costo por los mensajes realmente emitidos |
| Activo sin mensajes, incluso con cero oportunidades | Solo desgaste temporal |
| Promotor potencial que aún no se activa | Energía congelada |
| Nuevo promotor activado al inicio del período | Participa y se actualiza al cierre de ese mismo período |
| Agente que ya estaba inactivo | Energía congelada; no hay reactivación |
| Detractor inicial | Permanece inactivo; la energía negativa no cambia en M4 |

No hay costo adicional por rechazo, refuerzo por compra ni recuperación. Las compras y experiencias conservan los retrasos de M3: compra en t, experiencia en t + 1 y un único intento de activación en t + 2. La energía de nuevos potenciales es 0,6, independiente de la energía inicial de los promotores.

Un activo pasa a `promoter_fatigued` cuando su energía final es **≤ 0,05**, cuando ya no tiene contactos elegibles tras las compras o por ambas razones. La fatiga no cambia su satisfacción, disposición, padre ni generación. Un potencial que falla al intentar activarse permanece potencial; no cuenta como desactivación.

## Causas de desactivación

| Campo del flujo por período | Interpretación |
|---|---|
| `deactivated_energy_only` | Energía agotada, con contactos todavía elegibles |
| `deactivated_contacts_only` | Contactos agotados, con energía todavía superior al umbral |
| `deactivated_both` | Ambas condiciones coinciden al cierre |
| `deactivated_by_energy` | Primera categoría + ambas |
| `deactivated_by_contacts` | Segunda categoría + ambas |

Las tres primeras categorías son excluyentes y suman `deactivated_promoters`. Los dos últimos indicadores se superponen y no deben sumarse. Los campos `cumulative_*` son acumulados. Se conserva la causa observada al desactivarse; si otros agentes agotan después sus contactos restantes, no se modifica retrospectivamente.

Los promotores que comienzan inactivos en t = 0 se describen en el estado inicial y no se cuentan como nuevas desactivaciones. Se mantiene la identidad:

```text
activos(t) = activos(t−1) + nuevos_activados(t) − desactivados(t)
```

## Registros nuevos

| Archivo | Contenido |
|---|---|
| `energy_config.json` | Desgaste y costo por mensaje |
| `energy_period.csv` | Una fila por promotor activo durante el período, incluso sin mensajes |
| `deactivation_events.csv` | Subconjunto de actualizaciones que terminan en desactivación |

Cada actualización contiene energía inicial, pérdida temporal, número de mensajes, costo solicitado, valor sin recorte, energía final, pérdida efectiva, contactos restantes y ambas causas. Los agentes ya inactivos no generan filas en `energy_period.csv`; sus valores siguen disponibles en `agents_final.csv` y en `agent_period.csv` cuando este historial está habilitado.

`sender_energy` en `wom_events.csv` es la energía usada al comienzo del período, no la energía final. `positive_energy_total` suma energía positiva de todos los agentes, incluidos potenciales e inactivos; `positive_energy_active` suma solo la de los activos al cierre. La media activa queda vacía cuando no hay activos. La energía congelada de un inactivo no representa capacidad de emitir.

El balance total incorpora la energía asignada al crear potenciales:

```text
energía_total(t) = energía_total(t−1) + energía_asignada(t) − pérdida_efectiva(t)
```

El costo solicitado puede superar la energía disponible. Por eso `positive_energy_loss` usa la pérdida efectiva después del recorte; no se sustituye por la suma de desgaste y costo solicitado. Por ejemplo, energía 0,1 y dos mensajes de costo 0,1 producen costo solicitado 0,2, energía final 0 y pérdida efectiva 0,1 si delta = 0.

Se conservan todos los registros de M3: red y población iniciales, mensajes, decisiones de compra, compras, experiencias, intentos de activación, genealogía, estados e indicadores por período. El manifiesto incluye las nuevas tablas y configuración.

## API

```python
from article8.config import Config
from article8.model import initialize
from article8.positive import PositiveConfig
from article8.experience import ExperienceConfig
from article8.energy import EnergyConfig, EnergySimulation
from article8.export import export_energy_simulation

initial = initialize(Config(seed=20260925, negative_wom_enabled=False))
sim = EnergySimulation(
    initial,
    dynamics=PositiveConfig(periods=60),
    experience=ExperienceConfig(new_promoter_energy=.6),
    energy=EnergyConfig(decay=.06, message_cost=.04),
).run()
export_energy_simulation(sim, 'outputs/api_run')
```

Los dos parámetros de energía son finitos en [0, 1]. Con `EnergyConfig(decay=0, message_cost=0)` se recuperan exactamente los mensajes, compras, experiencias, activaciones y estados de M3; M4 añade sus registros de energía y etiqueta de alcance.

`run(until=10)` permite detenerse y continuar con `run()`. Invertir `next_sender_ids()` al llamar a `step(...)` no altera la trayectoria. Los sorteos siguen indexados por semilla, agente, período, mecanismo y oportunidad; el desgaste es determinista y no añade sorteos. Desactivar el historial individual no cambia la dinámica.

Una excepción revierte los cambios y registros del período, incluida la tabla de energía. Las funciones personalizadas `draw` se destinan a pruebas: no se serializan ni se revierte su estado externo; su uso se indica en el manifiesto. La identidad byte a byte de resultados se verificó con el mismo runtime; no se garantiza entre versiones de Python distintas. Colab no se verificó en esta entrega.

## Verificación y siguientes módulos

Pasaron **42 pruebas de M1, 31 de M2, 37 de M3 y 36 de M4**. Se verificaron fórmula, extremos, recorte, energía de inicio en todas las oportunidades, cargo exclusivo por mensajes enviados, desgaste sin mensajes, umbral inclusivo de fatiga, causas simultáneas, congelación, nuevos promotores, balance de energía, regresión sin desgaste, orden de emisores, exportación y CLI.

Las 40 corridas comparan desgaste base con pérdida energética deshabilitada (`delta = costo = 0`) sobre veinte estados iniciales emparejados. Los contactos finitos y la desactivación por agotamiento de contactos permanecen activos en ambas condiciones. La comparación es un diagnóstico del mecanismo, no un experimento principal ni una prueba de un porcentaje crítico.

WOM negativo, formación de nuevos detractores, indicadores de reproducción/reposición y clasificación de difusión siguen pendientes. El siguiente incremento corresponde a WOM negativo; después se integrarán los indicadores antes del piloto completo. Los documentos de versiones anteriores quedan en `docs/` como antecedentes.
