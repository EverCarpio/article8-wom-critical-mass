# Article 8 — M5: WOM negativo y formación de detractores

Versión **0.5.0-m5**, en Python con biblioteca estándar. Probada en **Python 3.12.14**; requiere 3.11 o posterior. Conserva M1–M4 y añade mensajes negativos, exposición mixta, memoria negativa y formación de detractores a partir de la experiencia de compra.

## Ejecutar

Descomprima y abra una terminal en `article8_m5`:

```bash
python -m article8 --mode mixed --config configs/m5_baseline.json --out outputs/base
python -m article8 --mode mixed --config configs/m5_baseline.json --negative-weight 2 --out outputs/lambda2
python -m article8 --mode mixed --config configs/m5_baseline.json --negative-off --out outputs/negative_off
python -m unittest discover -s tests -v
python scripts/verify_m5.py --out outputs/verification
```

Use directorios nuevos o vacíos: no se sobrescriben resultados. El modo `mixed` usa WOM negativo habilitado por defecto, salvo que la configuración o `--negative-off` indiquen lo contrario. Los modos `initial`, `positive`, `experience` y `energy` conservan sus alcances anteriores. `--no-agent-history` omite el historial individual sin cambiar la dinámica.

El verificador ejecuta **184 pruebas** y **80 corridas diagnósticas**: diez semillas × dos distribuciones × cuatro condiciones. Conserva dos trazas completas con lambda = 1. No es el piloto del modelo completo, pues los indicadores de reproducción y clasificación todavía están pendientes.

## Exposición y compra

Se fijan los susceptibles y emisores al inicio, después de procesar experiencias y activaciones. Todos los mensajes positivos y negativos se generan antes de comprar. Cada emisor usa su energía de inicio, dos oportunidades de base y probabilidad por oportunidad `0,8 × energía`. Se seleccionan vecinos susceptibles sin repetición por pareja dirigida y signo. Los rechazos no restauran contactos.

```text
L+(t) = 0,5 × L+(t−1) + suma de credibilidades positivas recibidas
L−(t) = 0,5 × L−(t−1) + suma de credibilidades negativas recibidas
H+ = 1 − exp(−L+)
H− = 1 − exp(−L−)
z = −2 + 1,5 × necesidad + 1,5 × ajuste + 1,2 × H+ − 1,2 × lambda × H−
probabilidad = logistic(z), solo si hay un mensaje positivo nuevo
```

Un receptor puede recibir varios mensajes de ambos signos, pero solo tiene una oportunidad de compra en ese período. Con exposición exclusivamente negativa, la probabilidad es cero y no se sortea compra, incluso si conserva memoria positiva anterior. Ambas memorias decaen mientras sigue susceptible y se congelan al comprar.

La atribución de compra siempre corresponde a un emisor **positivo** del período: mayor credibilidad y desempate por menor ID. Un emisor negativo nunca recibe crédito por una compra. La conciencia de la oferta (`aware`) puede provenir de cualquiera de los signos.

## Formación de detractores

| Momento | Regla |
|---|---|
| Compra en t | Cliente pendiente de experiencia; se conserva el padre positivo atribuido |
| Inicio de t + 1 | Una evaluación de satisfacción, con la misma fórmula de M3 |
| Satisfacción ≤ 0,35 | Una única Bernoulli de probabilidad 0,8 para disposición negativa |
| Disposición negativa favorable | Detractor potencial, con energía nueva 0,6 |
| Inicio de t + 2 | Un único intento de activación: energía > 0,05 y al menos un contacto elegible |
| Activación favorable | Puede emitir WOM negativo en ese período |
| Activación fallida | Permanece potencial con motivos registrados, sin reintentos |

Recibir WOM negativo no crea insatisfacción ni convierte al receptor en detractor. Es necesaria su propia compra y experiencia. Un insatisfecho sin disposición conserva WOM = ninguno. Los satisfechos siguen la ruta positiva y los neutrales no desarrollan disposición. Nadie es simultáneamente promotor y detractor.

Los clientes iniciales mantienen su experiencia previa impuesta. Los detractores iniciales no se vuelven a sortear ni evaluar. Los nuevos detractores reciben 0,6 de energía independientemente de las energías iniciales y positivas.

La generación sigue describiendo la cascada promotora: un nuevo promotor activo recibe generación del padre + 1. Para detractores queda sin asignar; su padre de compra y raíz inicial sí constan en `lineage.csv`. No se interpreta como transmisión de insatisfacción entre personas.

## Energía y desactivación negativas

```text
E−_cierre = max[0, (1 − 0,06) × E−_inicio − 0,04 × mensajes_negativos_enviados]
```

El costo se aplica al cierre, usando solo mensajes enviados. Los activos pierden energía temporal incluso sin mensajes; potenciales e inactivos conservan su saldo. Un detractor activo pasa a inactivo si su energía final es ≤ 0,05 o si se agotan los contactos elegibles. Se conservan ambas razones si coinciden. No hay recuperación, reactivación, costo adicional por rechazo ni refuerzo por éxito.

La energía negativa tiene sus propios parámetros en `negative_config.json`; el desgaste positivo permanece en `energy_config.json`. Los campos `negative_deactivated_energy_only`, `negative_deactivated_contacts_only` y `negative_deactivated_both` son categorías excluyentes. Suman `deactivated_detractors`. Los indicadores inclusivos por energía y por contactos se superponen cuando coinciden las causas.

## Deshabilitar no es lo mismo que lambda = 0

| Condición | Mensajes y memoria negativos | Nuevos detractores | Efecto negativo directo sobre compra |
|---|---|---|---|
| `--negative-off` | No | No | No |
| `--negative-weight 0` | Sí | Sí, si cumplen el ciclo | No |
| Peso 1 | Sí | Sí, si cumplen el ciclo | Coeficiente negativo base 1,2 |
| Peso 2 | Sí | Sí, si cumplen el ciclo | Coeficiente negativo 2,4 |

Deshabilitar preserva identidades y experiencias iniciales insatisfactorias, pero mantiene esos emisores inactivos. No hay nuevos sorteos de disposición negativa, activaciones, mensajes, memoria ni desgaste negativo. La trayectoria positiva reproduce M4.

Con peso cero el mecanismo permanece activo: emite, consume energía y forma detractores. En este modelo no comparte presupuesto con promotores y no tiene otros efectos sobre compra. Por eso mantiene la trayectoria de compras de la condición deshabilitada, aunque sus registros negativos sean distintos; esta equivalencia se verifica explícitamente.

## Archivos e interpretación

Se conservan los archivos de M4 y se añade `negative_config.json`, con probabilidad de disposición, energía nueva, desgaste, costo y coeficiente de influencia negativos.

| Registro | Extensión en M5 |
|---|---|
| `wom_events.csv` | Mensajes de ambos signos; primeras exposiciones separadas; crédito de compra solo positivo |
| `purchase_decisions.csv` | Una fila por receptor expuesto y período, también con exposición solo negativa |
| `experience_events.csv` | Sorteos y resultados de disposición de ambos signos |
| `activation_events.csv` | Signo, resultado y energía en el intento; éxito o bloqueo |
| `energy_period.csv` | Una fila por emisor activo y período, de cualquiera de los signos |
| `deactivation_events.csv` | Subconjunto de actualizaciones con salida; incluye el signo |
| `system_period.csv` | Flujos y acumulados separados para promotores y detractores |

En decisiones con exposición exclusivamente negativa, `eligible_to_buy=false`, probabilidad cero y sorteo vacío. No es una venta rechazada ni una decisión estocástica de compra. `purchases.csv` contiene únicamente compras efectivas.

`probability_without_negative` elimina el término negativo **solo del cálculo de ese estado**, manteniendo su historia. No es una corrida contrafactual completa ni identifica una venta individual causalmente bloqueada. Las comparaciones entre corridas se entregan por separado.

Para compatibilidad con M4, `activation_attempts`, `blocked_activations` y los campos de fatiga sin prefijo se refieren a promotores. Sus equivalentes negativos llevan el prefijo `negative_`. `new_detractors` cuenta activaciones exitosas, no todos los insatisfechos ni potenciales. Los stocks son `detractor_potential`, `detractor_active` y `detractor_inactive`. Los acumulados comienzan por `cumulative_`.

Los nuevos detractores pendientes al cierre se distinguen de intentos bloqueados. No se extiende el horizonte para completar experiencias o activaciones. Las celdas vacías representan valores no definidos.

## API y reproducción

```python
from article8.config import Config
from article8.model import initialize
from article8.positive import PositiveConfig
from article8.experience import ExperienceConfig
from article8.energy import EnergyConfig
from article8.mixed import MixedSimulation, NegativeConfig
from article8.export import export_mixed_simulation

sim = MixedSimulation(
    initialize(Config(seed=20260925, negative_wom_enabled=True, negative_weight=1)),
    dynamics=PositiveConfig(periods=60),
    experience=ExperienceConfig(quality=.7),
    energy=EnergyConfig(decay=.06, message_cost=.04),
    negative=NegativeConfig(disposition_probability=.8, new_detractor_energy=.6),
).run()
export_mixed_simulation(sim, 'outputs/api_run')
```

La CLI permite `--dynamics-config`, `--experience-config`, `--energy-config` y `--negative-config`. Los valores base están en `configs/m5_*.json`. El interruptor y peso del mecanismo se guardan en la configuración inicial.

Los mecanismos nuevos usan las claves aleatorias `negative_opportunity`, `negative_target` y `negative_disposition`. No desplazan los sorteos positivos, de compra o experiencia. El desgaste sigue siendo determinista. Invertir `next_sender_ids()` al llamar a `step(...)`, ejecutar por tramos con `run(until=...)` o desactivar el historial no altera las trayectorias.

La simulación conserva el estado inicial y revierte el período completo ante un error, incluidos experiencia, activación y energía. Las funciones personalizadas `draw` son para pruebas: no se serializan ni se revierte su estado externo. La reproducción byte a byte se verificó dentro del mismo runtime, no entre versiones distintas de Python. Colab no se verificó en esta entrega.

## Verificación y siguiente paso

Pasaron **184 pruebas**: 42 de M1, 31 de M2, 37 de M3, 36 de M4 y 38 de M5. Se verificaron exposición mixta, memoria, puerta positiva, disposición única, retrasos, contactos sin repetición, fatiga de ambos signos, conservación, atribución, equivalencias de control, reproducibilidad y exportación.

Las **80 corridas diagnósticas** comparan cuatro condiciones emparejadas sobre diez semillas y dos distribuciones. No se ajustaron parámetros para producir un umbral de 15 %. Los resultados no clasifican todavía despegue o colapso.

El siguiente incremento debe incorporar y verificar los indicadores de reproducción y reposición, sus ventanas temporales y la clasificación de difusión. Después podrá ejecutarse el piloto del modelo completo.
