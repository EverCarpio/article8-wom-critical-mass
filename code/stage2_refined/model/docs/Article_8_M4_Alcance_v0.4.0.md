# Article 8 — Alcance M4: desgaste de energía y fatiga

Fecha: 26 de septiembre de 2026, America/Bogota. Versión: **0.4.0-m4**. Lenguaje: Python. Base: especificación mínima v0.1, sección 9, y módulos M1–M3.

## Objetivo

Incorporar desgaste energético y fatiga al ciclo positivo de WOM, compra, experiencia y formación de nuevos promotores. La entrega permite distinguir la pérdida de energía del agotamiento de contactos, conservando satisfacción y trazabilidad del promotor.

## Regla operativa

Para cada promotor activo durante el período:

`E_cierre = max[0, (1 − delta) × E_inicio − c × m]`.

La base es `delta = 0,06` y `c = 0,04`. `m` cuenta mensajes realmente enviados, sin depender de que terminen en compra. Las oportunidades fallidas y los espacios del presupuesto de contactos que no se usan no tienen costo por mensaje. El desgaste temporal sí se aplica aunque el activo no envíe mensajes.

Todas las oportunidades usan la energía de inicio. El costo se aplica después del lote de mensajes y compras. Si el costo supera el saldo, la energía final es cero. La fórmula no representa un presupuesto que deba alcanzar antes de autorizar cada mensaje.

Los parámetros se concentran en `EnergyConfig`; son numéricos, finitos y pertenecen a [0, 1]. Con ambos en cero, M4 conserva exactamente las trayectorias de M3 y añade únicamente sus registros e indicadores de energía.

## Desactivación

Al cierre, un activo pasa a fatigado si la energía final es ≤ 0,05 o si no conserva contactos elegibles tras las compras. Ambas condiciones se evalúan por separado. Las razones son `energy_exhausted`, `contacts_exhausted` o ambas.

La fatiga mantiene satisfacción, disposición, padre y generación. El estado agregado `promoter_fatigued` incluye agotamiento de alcance; la causa permite distinguirlo de fatiga energética. Las razones quedan fijadas al desactivarse, sin modificarse por cambios posteriores en la red de susceptibles.

Las categorías excluyentes son energía solamente, contactos solamente y ambas. Su suma es el flujo de desactivaciones. Los indicadores inclusivos «por energía» y «por contactos» se superponen cuando coinciden las causas.

## Relación con el ciclo de experiencia

| Estado durante el período | Tratamiento |
|---|---|
| Potencial, pendiente o bloqueado | Conserva la energía asignada; no se aplica desgaste |
| Nuevo activo al inicio | Usa su energía asignada y se actualiza al cierre del mismo período |
| Activo desde períodos anteriores | Se actualiza al cierre, emita mensajes o no |
| Ya fatigado o inactivo | Conserva su energía final; no se reactiva |

La compra, experiencia e intento de activación mantienen los retrasos de M3: t, t + 1 y t + 2. Los nuevos potenciales reciben 0,6 de energía, independiente de la energía de la cohorte inicial. Un potencial bloqueado no es un activo desactivado y no entra en el flujo de fatiga.

No se incluyen costo adicional por rechazo, refuerzo por compra, recuperación ni reactivación. Estas simplificaciones corresponden a v0.1, que concreta el alcance del documento conceptual adjunto.

## Registros y balances

`energy_period.csv` contiene una fila por promotor activo durante cada período, incluso con cero mensajes. Registra energía inicial, desgaste, costo solicitado, valor previo al recorte, energía final, pérdida efectiva, contactos restantes y causas. `deactivation_events.csv` contiene el subconjunto de filas con desactivación. La energía negativa permanece congelada porque el mecanismo negativo sigue deshabilitado.

Se verifican los balances:

- Activos finales = activos anteriores + nuevas activaciones − desactivaciones.
- Energía positiva total final = total anterior + asignación a nuevos potenciales − pérdida efectiva.
- Mensajes contabilizados para costo = mensajes positivos registrados.

La pérdida efectiva respeta el recorte a cero. La energía total incluye potenciales e inactivos y se informa por separado de la energía de activos al cierre. Si no hay activos, la media activa queda sin definir. La capacidad efectiva sigue excluyendo a inactivos aunque conserven energía positiva.

Los estados iniciales inactivos conservan sus motivos de t = 0; no cuentan como nuevas desactivaciones. Las filas individuales y los registros históricos permiten comprobar la congelación posterior.

## Verificación de esta entrega

Se ejecutaron 146 pruebas: 42 de M1, 31 de M2, 37 de M3 y 36 nuevas de M4. Se verificaron límites, secuencia temporal, cargo por mensajes, ausencia de recargos o refuerzos, causas simultáneas, congelación, nuevos promotores, genealogía, conservación, reproducción y exportación.

El diagnóstico contiene 40 corridas de 60 períodos: diez semillas, dos distribuciones y dos condiciones de desgaste. Cada comparación con/sin pérdida de energía usa el mismo estado inicial y números aleatorios indexados. El control conserva agotamiento de contactos. Se entregan veinte diferencias emparejadas y dos trazas completas de la condición base.

## Trabajo pendiente

Faltan WOM negativo, formación de nuevos detractores, indicadores de reproducción y reposición y clasificación de difusión. Las corridas actuales verifican el mecanismo y no sustituyen el piloto completo ni estiman una frontera de masa crítica. El siguiente incremento corresponde a WOM negativo; no se añade un umbral de despegue prefijado.
