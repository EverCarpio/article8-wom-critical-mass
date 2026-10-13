# Article 8 — M2 en Python: WOM positivo, contactos y compra

Versión **0.2.0-m2**. Incluye M1 y añade dinámica temporal de WOM positivo y compra. Usa únicamente la biblioteca estándar. Entorno probado: **Python 3.12.14**; requiere Python 3.11 o posterior, sin garantía de huellas idénticas entre versiones no verificadas.

## Alcance

M2 incorpora oportunidades de recomendación, contactos sin repetición, exposiciones conjuntas, memoria positiva y compra única.

**WOM negativo está deshabilitado; la energía permanece constante; los compradores quedan pendientes de experiencia; no se forman nuevos promotores.** El agotamiento de contactos sí desactiva emisores. No se clasifican despegue, saturación ni colapso. Las corridas de M2 no son el piloto del modelo completo.

## Ejecución

Descomprima el paquete y abra una terminal en article8_m2:

    python -m article8 --mode positive --config configs/m2_baseline.json --dynamics-config configs/m2_dynamics.json --out outputs/distributed
    python -m article8 --mode positive --config configs/m2_baseline.json --distribution concentrated --out outputs/concentrated
    python -m unittest discover -s tests -v
    python scripts/verify_m2.py --out outputs/verification

El último comando ejecuta 73 pruebas y veinte trayectorias: diez semillas, dos distribuciones, 60 períodos y 15 % de promotores iniciales. Exporta dos ejemplos completos de la primera semilla. Use directorios de salida nuevos o vacíos; no se sobrescriben resultados.

Opciones adicionales:

    python -m article8 --mode positive --negative-off --periods 10 --no-agent-history --out outputs/short
    python -m article8 --mode initial --out outputs/initial_state
    python scripts/verify_m1.py --out outputs/m1_regression

El modo inicial conserva M1 y sus estados de detractores. El modo positivo exige m2_baseline.json o --negative-off. Una configuración que solicite WOM negativo se rechaza explícitamente.

En Colab: cargue y descomprima el ZIP, entre en article8_m2 y ejecute los mismos comandos con ! delante de python. No hay paquetes que instalar. Colab no se probó en esta sesión.

## Reglas implementadas

1. Se fija la instantánea de susceptibles y emisores activos al inicio del período.
2. Cada emisor dispone de dos oportunidades, con probabilidad 0,8 × energía por oportunidad. La energía debe ser estrictamente mayor que 0,05.
3. Se elige uniformemente un vecino susceptible no contactado antes por ese emisor. Un rechazo de compra no habilita la repetición.
4. Todos los mensajes se reúnen antes de comprar. Varios mensajes a una persona generan varias exposiciones y una sola decisión.
5. Para susceptibles: L(t) = 0,5 L(t−1) + suma de credibilidades recibidas; H(t) = 1 − exp(−L(t)).
6. Con al menos un mensaje positivo nuevo: p = logistic[−2 + 1,5 necesidad + 1,5 ajuste + 1,2 H]. Se compra si u < p. Sin mensaje nuevo, no hay compra.
7. Las compras se aplican conjuntamente. La atribución usa mayor credibilidad del emisor en ese período, con empate por menor ID. Es una convención contable.
8. Los compradores pasan a clientes pendientes de experiencia y salen del mercado susceptible.
9. Los promotores sin contactos elegibles quedan inactivos por contacts_exhausted, conservando satisfacción y energía.

## API

    from article8.config import Config
    from article8.model import initialize, make_environment
    from article8.positive import PositiveConfig, PositiveSimulation
    from article8.export import export_positive_simulation

    base = Config(seed=20260925, negative_wom_enabled=False)
    environment = make_environment(base)
    initial = initialize(base, environment)
    simulation = PositiveSimulation(initial, PositiveConfig(periods=60)).run()
    print(simulation.summary())
    export_positive_simulation(simulation, 'outputs/api_run')

La simulación copia los agentes y no modifica el objeto inicial. El entorno compartido es inmutable. run(until=10) permite detenerse al período diez y run() continuar hasta el horizonte, sin superarlo.

Las decisiones usan números indexados por semilla, agente, período, mecanismo y oportunidad: positive_opportunity, positive_target y purchase. Omitir una decisión no desplaza las restantes. Los mensajes se ordenan canónicamente antes de acumular influencias; las compras se aplican al terminar todo el lote.

La opción draw permite números controlados para pruebas. Una ejecución con esa función personalizada se marca en el manifiesto como no reproducible únicamente desde la configuración, porque la función no se serializa. Los ejemplos entregados usan el generador normal.

## Archivos

| Archivo | Unidad o contenido |
|---|---|
| initial_state/ | Red, agentes, parámetros y huellas iniciales |
| dynamics_config.json | Horizonte, oportunidades, coeficientes y memoria |
| wom_events.csv | Un mensaje por fila |
| purchase_decisions.csv | Una decisión por receptor expuesto y período, incluso sin compra |
| purchases.csv | Solo compras; un registro por comprador |
| system_period.csv | Períodos desde t = 0 |
| agent_period.csv | Agente–período; puede omitirse |
| agents_final.csv | Estado completo final |
| run_summary.json | Totales y mecanismos habilitados |
| manifest.json | Versiones, semilla, entorno y SHA-256 |

positive_events y new_purchases son flujos del período. cumulative_positive_events y cumulative_new_purchases son totales. No interprete el flujo del último mes como total de la corrida.

receiver_positive_exposures_before_period se mide antes del lote completo. first_positive_reach identifica un único evento canónico por primera persona alcanzada. receiver_bought_this_period puede ser verdadero en varios mensajes, pero credited_purchase_parent solo acredita a un emisor. El total de ventas se obtiene de purchases.csv.

scheduled_experience_time = compra + 1 indica la fecha prevista para el siguiente módulo. M2 no procesa esa experiencia: un cliente puede seguir pendiente después de dicha fecha. Las memorias de compradores se congelan; solo se actualizan las de susceptibles.

Las celdas vacías representan valores no definidos. Las razones de reproducción/reposición y la clasificación permanecen no evaluadas. El estado promoter_fatigued por agotamiento de contactos no representa fatiga energética en M2.

## Verificación y siguiente módulo

Pasaron 73 pruebas: 42 de M1 y 31 de M2. Cubren simultaneidad, compra única, contactos finitos, varios emisores sobre un receptor, memoria, ausencia de compra espontánea, atribución, casos extremos, conservación, ejecución por tramos y exportaciones idénticas entre procesos.

El paquete de evidencias conserva registros, veinte corridas diagnósticas y dos ejemplos completos. Estos resultados todavía no estiman una frontera de masa crítica.

El siguiente módulo incorporará experiencia, satisfacción y formación de nuevos promotores con retrasos explícitos. Energía temporal, WOM negativo, genealogía y clasificación deberán integrarse y verificarse antes del piloto completo.

