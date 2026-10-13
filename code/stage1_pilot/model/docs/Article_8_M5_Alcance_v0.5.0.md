# Article 8 — Alcance M5: WOM negativo y detractores

Fecha: 27 de septiembre de 2026, America/Bogota. Versión **0.5.0-m5**, Python. Base: especificación mínima v0.1, secciones 4–10, y módulos M1–M4.

## Objetivo

Integrar el mecanismo negativo completo con el ciclo positivo ya verificado: exposición conjunta, memoria, influencia sobre compra, insatisfacción, disposición negativa, activación, energía y desactivación de detractores.

## Reglas implementadas

Los emisores de ambos signos usan la misma instantánea de susceptibles. Disponen de dos oportunidades, con probabilidad 0,8 × energía de inicio. Seleccionan uniformemente vecinos susceptibles sin repetición por emisor, receptor y signo. Los mensajes se reúnen antes de decidir las compras.

Las memorias positiva y negativa se actualizan por separado: persistencia 0,5 más suma de credibilidades de los mensajes recibidos. Cada influencia es `1 − exp(−memoria)`. Solo un mensaje positivo nuevo habilita compra. El índice de adopción añade el término `−1,2 × lambda × influencia_negativa` al índice positivo de M2. Varios mensajes generan una sola decisión por receptor y período.

Una exposición exclusivamente negativa tiene probabilidad cero y no consume sorteo de compra. Se registra como exposición no elegible, no como venta rechazada. Las memorias de compradores se congelan, como en los módulos previos.

La compra se atribuye siempre a un emisor positivo del período, por mayor credibilidad y desempate por menor ID. Los mensajes negativos no reciben crédito de compra. La atribución sigue siendo una convención contable, no una identificación causal.

## Formación de detractores

Compra en t → experiencia en t + 1 → posible activación en t + 2. Una satisfacción ≤ 0,35 habilita una única Bernoulli con probabilidad 0,8. Si es favorable, el cliente queda como detractor potencial con energía 0,6. Los neutrales y satisfechos no realizan este sorteo. Un insatisfecho sin disposición conserva WOM = ninguno.

La activación se intenta una sola vez y requiere energía > 0,05 y al menos un contacto susceptible elegible. Si falla, el agente permanece potencial con motivo registrado y sin reintentos. Si tiene éxito, puede emitir en el período de activación. No existe contagio directo de insatisfacción: recibir WOM negativo no produce un detractor sin compra y experiencia propias.

Los detractores iniciales mantienen sus identidades y experiencias previas. Su energía inicial es independiente de la energía de nuevos detractores. Los agentes no cambian de signo ni pueden ser promotores y detractores simultáneamente.

La generación sigue definida para promotores activos. Los detractores mantienen generación sin asignar, pero conservan el padre positivo de su compra y la raíz inicial en la tabla de atribución.

## Energía y causas

Al cierre de cada período activo, `E−_final = max[0, (1 − 0,06) × E−_inicial − 0,04 × mensajes_negativos]`. Todas las oportunidades usan la energía de inicio. Se cobra solo por mensajes enviados; el desgaste temporal se aplica aunque no haya mensajes. Potenciales e inactivos conservan el saldo.

Un detractor se desactiva si su energía final es ≤ 0,05, si no conserva contactos elegibles tras las compras o por ambas causas. Las causas se registran al ocurrir y no se reescriben posteriormente. Las categorías excluyentes no duplican salidas. No hay recuperación, reactivación, recargo por rechazo ni refuerzo por compra.

## Intervenciones diferenciadas

| Condición | Actividad negativa | Disposición y nuevos detractores | Influencia negativa en compra |
|---|---|---|---|
| Mecanismo deshabilitado | Ninguna: sin mensajes, memoria, actualizaciones energéticas o activaciones | Sin nuevos sorteos negativos; se conservan identidades iniciales | Cero |
| Habilitado, lambda = 0 | Activa según energía y contactos | Habilitada | Cero |
| Habilitado, lambda = 1 | Activa según energía y contactos | Habilitada | Base |
| Habilitado, lambda = 2 | Activa según energía y contactos | Habilitada | Doble coeficiente en el índice de compra |

Con el mecanismo deshabilitado se recupera M4. Con lambda cero se preserva la trayectoria de compras del control deshabilitado porque el mecanismo negativo no comparte presupuesto con los promotores ni entra por otra vía a la compra; sus registros negativos sí difieren.

## Trazabilidad y verificación

Los eventos, intentos de activación y actualizaciones energéticas incorporan signo. Se añaden columnas de memoria e influencia negativas y disposición negativa. El historial de decisiones contiene también exposiciones solo negativas, identificadas por `eligible_to_buy=false` y sorteo vacío.

Los flujos de nuevos detractores y sus desactivaciones se reconcilian con el stock activo. La energía se reconcilia por signo, incluyendo asignaciones a nuevos potenciales. Se verifican compras, padres, cronología, exposiciones, memorias, contactos utilizados, energía histórica y capacidad efectiva.

`probability_without_negative` elimina el término negativo del cálculo del estado observado, sin reconstruir una trayectoria alternativa. No debe interpretarse como número de ventas causalmente bloqueadas.

Se ejecutaron 184 pruebas y 80 corridas diagnósticas de 60 períodos. Las corridas combinan diez semillas, dos distribuciones y las cuatro condiciones anteriores, con veinte grupos emparejados y sesenta diferencias respecto del control. Dos trazas completas de lambda = 1 acompañan los resúmenes.

## Límite y siguiente paso

Las reglas dinámicas positivas y negativas quedan integradas, pero siguen pendientes los indicadores de reproducción/reposición y la clasificación de difusión. El próximo módulo debe definir y verificar sus ventanas, retrasos y censura antes del piloto completo. No se concluye una frontera de masa crítica ni se fuerza una caída monótona de ventas acumuladas al aumentar lambda.
