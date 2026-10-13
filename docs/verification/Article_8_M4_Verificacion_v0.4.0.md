# Article 8 — Verificación M4: desgaste de energía y fatiga

**Versión:** 0.4.0-m4. **Fecha local:** 26 de septiembre de 2026, America/Bogota. **Runtime:** Python 3.12.14.

## Resultado

El módulo M4 quedó implementado y verificado en Python. Pasaron **146 pruebas automatizadas y 40 corridas diagnósticas**, sin fallos ni errores. Los 36 casos nuevos cubren desgaste temporal, costo por mensajes realmente enviados, fatiga, congelación y su integración con la formación de promotores.

La entrega conserva los módulos previos y añade registros de energía y desactivación. Las causas se separan en energía solamente, contactos solamente y ambas. La satisfacción y la genealogía se conservan al fatigarse.

## Reglas verificadas

La actualización al cierre es `E_final = max[0, (1 − 0,06) × E_inicio − 0,04 × mensajes]`. Todas las oportunidades del período usan la energía inicial. Por ejemplo, un activo que inicia con 0,6 y envía dos mensajes termina con 0,484. Si no envía mensajes, termina con 0,564, siempre que siga siendo un activo durante ese período.

Un activo se desactiva con energía final ≤ 0,05 o sin contactos elegibles después de las compras. Si ambas condiciones coinciden, se registran ambas sin duplicar la salida. Las razones se fijan en el período de desactivación y no se alteran por compras posteriores de otros agentes.

Los potenciales mantienen su energía hasta activarse. Los nuevos activos reciben el tratamiento energético en su primer período de actividad. Los que ya estaban fatigados o inactivos conservan su saldo; no hay recuperación ni reactivación. No se cobra por oportunidades fallidas, no hay recargo por rechazo y una compra no refuerza la energía.

La energía de nuevos potenciales sigue siendo 0,6, independiente de la cohorte inicial. Los retrasos de M3 y la atribución de padre/generación se mantienen. Un descendiente puede activarse después de que el padre haya agotado su energía.

El documento conceptual adjunto contempla mecanismos opcionales más amplios; esta implementación sigue la ecuación y las delimitaciones de la especificación mínima v0.1, sección 9.

## Cambios en el código

`energy.py` incorpora la configuración, actualización, causas, indicadores y reconciliación histórica. Extiende el motor M3 para aprovechar el mismo procesamiento de mensajes, compras, experiencia y activación. El cierre de período permite aplicar energía antes de registrar el estado final. Las validaciones usan la energía histórica de cada mensaje y de cada activación, en lugar del saldo final.

El modo nuevo es `--mode energy`, con `--energy-config`. Los modos anteriores conservan sus alcances. El exportador añade `energy_config.json`, `energy_period.csv` y `deactivation_events.csv`. Los errores de un período revierten también los registros de energía.

## Pruebas automatizadas

| Grupo | Pruebas | Resultado |
|---|---:|---|
| Regresión M1 | 42 | Todas pasan |
| Regresión M2 | 31 | Todas pasan |
| Regresión M3 | 37 | Todas pasan |
| M4: Exportación y CLI | 6 | Todas pasan |
| M4: Integridad y reproducción | 9 | Todas pasan |
| M4: Fórmula y parámetros | 4 | Todas pasan |
| M4: Secuencia y causas de fatiga | 17 | Todas pasan |
| **Total** | **146** | **0 fallos; 0 errores** |

Las pruebas emplean redes pequeñas y cálculos manuales para distinguir reglas que producirían resultados diferentes:

- Energía 0,1 y dos mensajes de costo 0,1: ambas oportunidades usan la energía de inicio; el cierre se recorta a cero. No se impone un presupuesto anticipado por mensaje.
- Cero mensajes o cero oportunidades: un activo conserva el desgaste temporal, sin costo por mensaje.
- Un solo contacto disponible con dos oportunidades: se cobra únicamente el mensaje enviado.
- Energía final exactamente 0,05: hay fatiga; justo por encima, el agente sigue activo si tiene contactos.
- Fatiga por energía y contactos a la vez: una salida y dos indicadores de causa.
- Inactivo con energía residual: el saldo queda congelado y no genera actividad.
- Nuevo potencial con energía 0,6: no pierde energía antes de activarse; con delta 0,5 y un mensaje de costo 0,04 termina su primer período activo con 0,26.
- Padre con saldo cero: el hijo puede activarse en t + 2 y continuar la cadena.
- Contactos que desaparecen después de fatigarse: no se reescribe la causa histórica.

Se verificó además la equivalencia con M3 al fijar delta = costo = 0, inversión del orden de emisores, ejecución por tramos, independencia del historial individual, estado inicial sin modificaciones, ausencia de actualizaciones de detractores inactivos, balance de energía con asignaciones a nuevos potenciales y detección de registros corruptos o faltantes. Las salidas de CLI resultaron idénticas entre procesos con distintas semillas de hash de Python.

## Diagnóstico emparejado

Se ejecutaron **10 semillas × 2 distribuciones × 2 condiciones = 40 corridas**, de 60 períodos. Cada corrida usa 600 personas, 120 clientes y 18 promotores iniciales, con energía inicial y nueva de 0,6. Las semillas enteras son 20260925 a 20260934; no representan fechas.

Las dos condiciones son desgaste base (delta 0,06; costo 0,04) y pérdida energética deshabilitada (ambos en cero). Dentro de cada pareja se reutiliza exactamente el estado inicial. La red, rasgos y población base se comparten también al comparar distribución repartida y concentrada. Los sorteos se mantienen indexados por agente, período y mecanismo.

El control sin desgaste mantiene contactos finitos y desactivación por agotamiento de contactos. Se comprobó que no registre pérdida energética ni salidas por energía. En ambas condiciones se reconciliaron mensajes y costos, energía por agente y período, entradas y salidas de promotores, población y cronología. **Las 40 corridas pasaron todas las comprobaciones.**

### Ejemplo: semilla 20260925

| Medida | Repartida, base | Repartida, sin desgaste | Concentrada, base | Concentrada, sin desgaste |
|---|---:|---:|---:|---:|
| Compras nuevas | 445 | 452 | 440 | 457 |
| Promotores nuevos activados | 160 | 151 | 162 | 170 |
| Mensajes positivos | 646 | 656 | 664 | 688 |
| Salidas: solo energía | 4 | 0 | 4 | 0 |
| Salidas: solo contactos | 167 | 169 | 172 | 188 |
| Salidas: ambas causas | 7 | 0 | 4 | 0 |
| Promotores activos finales | 0 | 0 | 0 | 0 |
| Máxima generación | 9 | 9 | 10 | 10 |

Las salidas incluyen promotores iniciales y nuevos; por ello se comparan con iniciales activos + nuevas activaciones. Por ejemplo, en la corrida repartida con desgaste, 4 + 167 + 7 = 178 salidas = 18 iniciales + 160 nuevos, con cero activos al cierre.

### Promedios descriptivos de las veinte corridas por condición

| Medida | Desgaste base | Sin pérdida energética |
|---|---:|---:|
| Compras nuevas | 433.25 | 439.95 |
| Promotores nuevos activados | 160.95 | 159.80 |
| Mensajes positivos | 661.65 | 671.10 |
| Salidas: solo energía | 4.05 | 0.00 |
| Salidas: solo contactos | 171.35 | 177.80 |
| Salidas: ambas causas | 3.55 | 0.00 |

Los promedios agrupan diez semillas y dos distribuciones por condición. Se entregan las veinte diferencias emparejadas para revisar cada caso. No son estimaciones de una frontera de masa crítica ni permiten asumir una respuesta monótona de todos los indicadores. Por ejemplo, el número medio de promotores nuevos es ligeramente mayor con desgaste en este diagnóstico, aunque hay menos compras: cambian la secuencia de contactos, las fechas de experiencia y los sorteos indexados que corresponden a esas fechas. Esta observación se conserva sin ajustar parámetros para eliminarla; no identifica por sí sola qué componente explica la diferencia.

La ausencia de activos al final no se etiqueta como colapso: todavía falta la clasificación operacional y hay agotamiento de contactos. La energía total residual de inactivos tampoco se interpreta como capacidad de emisión.

## Evidencias y reproducción

El código incluye módulos, configuraciones, 146 pruebas, verificadores y documentación. El paquete de evidencias contiene resultados por prueba, registro completo de ejecución, cuarenta resúmenes, veinte diferencias emparejadas y dos trazas completas de la condición base —repartida y concentrada—. Los controles sin desgaste quedan en los resúmenes y son reproducibles con la configuración indicada.

Cada traza conserva estado inicial, red, mensajes, decisiones de compra, compras, experiencias, intentos de activación, genealogía, energía por activo y período, desactivaciones, historial de agentes, estado final e indicadores por período. Incluye las cuatro configuraciones y un manifiesto de integridad. Los archivos `SOURCE_SHA256.json` permiten vincular las evidencias con el código entregado.

```bash
python -m unittest discover -s tests -v
python scripts/verify_m4.py --out outputs/verification_reproduction
python -m article8 --mode energy --config configs/m4_baseline.json --dynamics-config configs/m4_dynamics.json --experience-config configs/m4_experience.json --energy-config configs/m4_energy.json --seed 20260925 --out outputs/example_reproduction
```

Ejecute desde `article8_m4` después de descomprimir. Use salidas nuevas o vacías. La fecha del informe de verificación cambia al repetirlo; las trayectorias se reproducen con las mismas configuraciones y runtime. No se garantiza identidad byte a byte entre distintas versiones de Python; Colab no se probó en esta sesión.

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| Article_8_M4_Python_v0.4.0.zip | 82598 | `0aa95add43765ab9a2baef77ddc553b4ec01ab52b0d2fcd26adc959ceaea61a6` |
| Article_8_M4_Evidencias_v0.4.0.zip | 3514339 | `7d80f6c52af76e36a416b760a43f3234ac1d36f07ed48e964a6de744d8f0f4c9` |
| Article_8_M4_Alcance_v0.4.0.md | 5429 | `d11e8609b2357f29326e0d3828d03b268ba77f91f5f6227c83e5b2d18d224744` |

Ambos ZIP pasaron su comprobación de integridad y los manifiestos de las trazas completas fueron verificados. Registro de finalización en UTC: `2026-09-27T02:54:35.027189+00:00`.

## Alcance pendiente

WOM negativo y formación de nuevos detractores siguen deshabilitados. También faltan indicadores de reproducción/reposición y clasificación de difusión antes del piloto completo. Este diagnóstico no constituye el experimento principal ni prueba un umbral universal de 15 %.
