# Article 8 — M3: experiencia, satisfacción y nuevos promotores

Versión **0.3.0-m3**. Simulación en Python con biblioteca estándar, sin paquetes externos. Probada en Python **3.12.14**; requiere 3.11 o posterior. Conserva los modos M1 y M2 y añade M3 mediante una extensión del motor de WOM y compra.

## Ejecutar

Descomprima el ZIP y abra una terminal en `article8_m3`:

```bash
python -m article8 --mode experience --config configs/m3_baseline.json --dynamics-config configs/m3_dynamics.json --experience-config configs/m3_experience.json --out outputs/distributed
python -m article8 --mode experience --config configs/m3_baseline.json --distribution concentrated --out outputs/concentrated
python -m unittest discover -s tests -v
python scripts/verify_m3.py --out outputs/verification
```

Use salidas nuevas o vacías. Los resultados existentes no se sobrescriben. El verificador ejecuta **110 pruebas** y **20 trayectorias de diagnóstico** de 60 períodos; conserva dos ejemplos completos. Las corridas diagnósticas todavía no son el piloto del modelo completo.

Para una corrida breve:

```bash
python -m article8 --mode experience --negative-off --periods 10 --no-agent-history --out outputs/short
```

Los modos `--mode initial` y `--mode positive` mantienen el alcance previo. `--mode experience` requiere `negative_wom_enabled=false`, mediante la configuración M3 o `--negative-off`. `--experience-config` solo es válido en este modo. Los comandos también pueden ejecutarse desde Colab después de descomprimir y cambiar al directorio del paquete; Colab no se verificó en esta sesión.

## Secuencia temporal

| Momento | Regla |
|---|---|
| Compra en t | Sale de susceptibles; queda pendiente de experiencia; se registra el padre atribuido |
| Inicio de t + 1 | Se calcula una única satisfacción y se clasifica la experiencia |
| Inicio de t + 1, si satisfecho | Un sorteo de disposición con probabilidad 0,8 puede convertirlo en promotor potencial |
| Inicio de t + 2, si potencial | Se intenta activar una sola vez: energía > 0,05 y al menos un vecino susceptible elegible |
| t + 2, si se activa | Puede emitir WOM en ese período; generación = generación del padre + 1 |
| Después del lote de mensajes y compras | Se desactivan los promotores que agotaron los contactos elegibles |

Los mensajes y las decisiones de compra conservan el procesamiento síncrono de M2. Un comprador nuevo nunca emite en el mismo período de compra ni en el de evaluación de experiencia. Todos los emisores de un período usan la misma instantánea de susceptibles.

## Satisfacción y disposición

```text
satisfacción = clip[calidad + 0,2 × (ajuste − 0,5) + ruido, 0, 1]
calidad = 0,7; ruido uniforme en [−0,4, 0,4]
```

| Resultado | Experiencia | WOM en M3 |
|---|---|---|
| Satisfacción ≥ 0,75 | Satisfecho | Un único sorteo `u < 0,8` decide la disposición positiva |
| 0,35 < satisfacción < 0,75 | Neutral | Ninguno |
| Satisfacción ≤ 0,35 | Insatisfecho | Ninguno; el mecanismo negativo queda para el módulo correspondiente |

Si el satisfecho no desarrolla disposición, conserva su satisfacción y no vuelve a sortearla. El promotor potencial recibe energía **0,6**, independiente de la energía configurada para los promotores iniciales. Los clientes iniciales mantienen su experiencia ya asignada; no se reevalúan.

Una activación fallida deja al agente como `promoter_potential`, con razones `energy_exhausted`, `contacts_exhausted` o ambas. No hay reintentos. Se distingue de una activación aún pendiente al finalizar el horizonte. `deactivation_time` solo se asigna si un promotor previamente activo se desactiva, además de los casos iniciales ya definidos en M1.

## Genealogía y trazabilidad

La atribución de compra usa el emisor de mayor credibilidad en el lote; un empate se resuelve por menor ID. Es una convención contable, no una estimación causal. Los promotores iniciales tienen generación 0. La generación de un nuevo promotor se fija cuando se activa; un comprador o potencial que aún no se activó mantiene la generación sin asignar.

El padre puede estar inactivo cuando el hijo se activa. `lineage.csv` contiene todos los compradores nuevos, su padre, raíz inicial, generación si corresponde y fechas. Esta tabla permite separar compras de nuevos promotores efectivos.

| Archivo adicional a M2 | Contenido |
|---|---|
| `experience_config.json` | Calidad, ruido, umbrales, disposición y energía de nuevos promotores |
| `experience_events.csv` | Una evaluación por nuevo cliente; ruido, satisfacción y sorteo de disposición |
| `activation_events.csv` | Un intento por potencial cuando vence el retraso, incluso si falla |
| `lineage.csv` | Atribución de cada compra y estado de su posible activación |

Se conservan `initial_state/`, `dynamics_config.json`, `wom_events.csv`, `purchase_decisions.csv`, `purchases.csv`, `agents_final.csv`, `agent_period.csv`, `system_period.csv`, `run_summary.json` y `manifest.json`. El manifiesto contiene las huellas SHA-256 de todas las salidas, incluyendo las nuevas tablas. `--no-agent-history` omite solamente `agent_period.csv`.

Los campos `new_experiences`, `new_potential_promoters`, `new_promoters`, `activation_attempts`, `blocked_activations` y `deactivated_promoters` son flujos del período. Los campos `cumulative_*` son totales. `new_promoters` cuenta activaciones exitosas, incluso si el agente agota sus contactos y se desactiva en ese mismo período. El stock activo cumple:

```text
activos(t) = activos(t−1) + new_promoters(t) − deactivated_promoters(t)
```

Al terminar T, las compras en T quedan pendientes de experiencia y los potenciales creados en T quedan pendientes de activación en T + 1. No se fuerzan eventos fuera del horizonte. Las celdas vacías representan valores no definidos; `activation_status` distingue `pending`, `blocked`, `activated` y `not_scheduled` para nuevos compradores.

## API

```python
from article8.config import Config
from article8.model import initialize
from article8.positive import PositiveConfig
from article8.experience import ExperienceConfig, ExperienceSimulation
from article8.export import export_experience_simulation

initial = initialize(Config(seed=20260925, negative_wom_enabled=False))
sim = ExperienceSimulation(
    initial,
    PositiveConfig(periods=60),
    ExperienceConfig(quality=.7, new_promoter_energy=.6),
).run()
print(sim.summary())
export_experience_simulation(sim, 'outputs/api_run')
```

`run(until=10)` y luego `run()` permiten ejecución por tramos. Para variar el orden de emisores en una prueba use `step(sender_order=...)` con una permutación de `next_sender_ids()`: incluye las activaciones previstas para el período que comienza.

Los sorteos normales están indexados por semilla, agente, período, mecanismo y oportunidad. M3 añade `experience` y `positive_disposition`, sin desplazar los números usados por WOM y compra. Cambiar el orden de emisores o desactivar el historial no altera la trayectoria. Un error de sorteo o de orden revierte el período completo. La opción `draw` sirve para pruebas controladas; la función personalizada y su estado externo no se serializan ni se restauran al fallar un período. Su uso queda indicado en el manifiesto. La reproducción byte a byte se verificó con el mismo runtime; no se garantiza entre versiones distintas de Python.

## Verificación y alcance pendiente

Pasaron **42 pruebas de M1, 31 de M2 y 37 de M3**, sin fallos. Las nuevas cubren retrasos, umbrales, clipping, evaluación y disposición únicas, activación fallida sin reintentos, energía independiente, generaciones sucesivas, inactividad del padre, conservación de población y promotores, fin del horizonte, reproducción y exportaciones.

M3 clasifica insatisfacción pero mantiene WOM negativo deshabilitado. La energía permanece constante: el estado `promoter_fatigued` señala aquí agotamiento de contactos, sin fatiga energética. Las razones de reproducción y reposición y la clasificación de difusión siguen sin evaluarse. No se ha ejecutado el piloto de 150 corridas del modelo completo ni se ha estimado una frontera de masa crítica.

El siguiente módulo debe incorporar y verificar desgaste de energía y fatiga; después se integrarán WOM negativo y los indicadores del modelo completo. Los documentos históricos de M1 y M2 se conservan en `docs/` y describen sus respectivas versiones.
