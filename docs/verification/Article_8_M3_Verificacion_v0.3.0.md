# Article 8 — Verificación de M3: experiencia, satisfacción y nuevos promotores

**Versión:** 0.3.0-m3. **Fecha:** 26 de septiembre de 2026. **Runtime verificado:** Python 3.12.14.

## Resultado

Se implementó y verificó el módulo M3 en Python. Pasaron **110 pruebas automatizadas y 20 trayectorias diagnósticas de 60 períodos**, sin fallos ni errores. La población, compras, evaluaciones y activaciones se reconciliaron con sus registros. Los modos anteriores de inicialización y WOM positivo/compra conservan sus pruebas.

El modelo ahora puede generar nuevos promotores y nuevas generaciones a partir de compradores satisfechos. La entrega sigue siendo parcial: falta el desgaste energético y WOM negativo. **No se ejecutó el piloto del modelo completo ni se clasificó masa crítica, despegue o colapso.**

## Implementación

La compra en t se evalúa al inicio de t + 1 mediante la satisfacción especificada en v0.1: calidad 0,7, efecto del ajuste 0,2 y ruido uniforme de amplitud 0,4, con recorte a [0, 1]. Los umbrales 0,75 y 0,35 son inclusivos para satisfacción e insatisfacción. La zona intermedia es neutral.

Un satisfecho realiza una sola prueba de disposición positiva con probabilidad 0,8. Si la supera, queda como potencial con energía 0,6. Al inicio de t + 2 se intenta activarlo una sola vez: energía > 0,05 y al menos un contacto elegible. Los fallos permanecen potenciales, registran sus razones y no se reintentan.

Los nuevos activos pueden emitir en su período de activación, usando el motor síncrono de M2. Los compradores no emiten en el período de compra ni en el de experiencia. La energía inicial de los promotores no determina la de los nuevos. Los clientes iniciales conservan su experiencia ya definida.

La atribución por credibilidad y desempate por ID se conserva. Cada nuevo promotor activado recibe generación del padre + 1; el padre puede estar inactivo. Las compras no activadas mantienen generación vacía. Todas las compras nuevas tienen trazabilidad hasta una raíz inicial.

`experience.py` implementa el ciclo y sus registros, extendiendo el motor de WOM y compra. `positive.py` añade puntos de validación para esta extensión. La CLI incorpora `--mode experience` y `--experience-config`. El exportador añade evaluaciones, intentos y genealogía. Un error durante un período revierte sus cambios de estado y registros.

## Pruebas automatizadas

| Grupo | Pruebas | Resultado |
|---|---:|---|
| Regresión M1: red, población, estados y exportación | 42 | Todas pasan |
| Regresión M2: WOM, contactos, compra y sincronía | 31 | Todas pasan |
| M3: evaluación de satisfacción y parámetros | 5 | Todas pasan |
| M3: secuencia temporal y formación de promotores | 15 | Todas pasan |
| M3: reproducibilidad e integridad | 11 | Todas pasan |
| M3: exportación y CLI | 6 | Todas pasan |
| **Total** | **110** | **0 fallos; 0 errores** |

Las pruebas nuevas comprueban los dos umbrales exactos, el intervalo neutral, recorte a 0 y 1, fórmula calculada a mano, probabilidades extremas, sorteo único, independencia de energías, umbral energético estricto, pérdida de contactos antes de activarse, ambas razones de bloqueo y ausencia de reintentos. La disposición negativa queda fuera de M3 y no se sortea para insatisfechos.

Una red controlada en cadena fija cuatro compras en los períodos **1, 3, 5 y 7**, experiencias en **2, 4, 6 y 8**, y tres activaciones en **3, 5 y 7**. Las generaciones activadas son **1, 2 y 3**. El último comprador intenta activarse en 9 y queda potencial por falta de contactos. En esa cadena los padres ya están inactivos cuando se activan los hijos.

Se verificó que invertir el orden de emisores —incluidos los nuevos— no cambia los registros; que ejecutar por tramos o desactivar el historial individual no altera la trayectoria; que deshabilitar disposición positiva conserva exactamente los mensajes y compras de M2; y que las salidas de CLI son idénticas entre procesos con distintas semillas de hash de Python.

También se comprobaron compras al final del horizonte, rollback de un período ante sorteos inválidos, conservación del objeto inicial, detección de registros repetidos o ausentes, genealogía y satisfacción alteradas, exportaciones vacías con cabeceras, reproducción desde configuraciones y detección de archivos modificados por SHA-256.

## Corridas de diagnóstico

Se ejecutaron **10 semillas enteras × 2 distribuciones = 20 trayectorias**, con 600 agentes, 120 clientes iniciales, 18 promotores iniciales —15 % de clientes— y 60 períodos. Las semillas son 20260925 a 20260934, usadas como identificadores numéricos. La distribución cambia entre repartida y concentrada; cada pareja comparte red, rasgos y población inicial, verificados mediante la misma huella del entorno.

Las comprobaciones incluyeron conservación de población y stock de promotores, cronología de experiencias y activaciones, contactos finitos, compradores alcanzables desde las fuentes iniciales y reconciliación de genealogía. Las veinte trayectorias pasaron. Los ejemplos de la primera semilla incluyen historial individual completo y manifiestos verificados.

### Ejemplos de semilla 20260925

| Medida en 60 períodos | Repartida | Concentrada |
|---|---:|---:|
| Compras nuevas | 452 | 457 |
| Clientes finales | 572 | 577 |
| Mensajes positivos | 656 | 688 |
| Receptores únicos | 471 | 473 |
| Experiencias evaluadas | 452 | 457 |
| Satisfechos nuevos | 217 | 230 |
| Neutrales nuevos | 233 | 218 |
| Insatisfechos nuevos | 2 | 9 |
| Potenciales formados | 164 | 190 |
| Intentos de activación | 164 | 190 |
| Promotores nuevos activados | 151 | 170 |
| Activaciones bloqueadas | 13 | 20 |
| Máxima generación | 9 | 10 |
| Promotores activos finales | 0 | 0 |
| Compras fuera del alcance directo inicial | 321 | 341 |
| Experiencias pendientes al cierre | 0 | 0 |
| Activaciones pendientes al cierre | 0 | 0 |

Las evaluaciones se reconcilian por categoría: satisfechos + neutrales + insatisfechos = experiencias. Los potenciales se reconcilian con activaciones exitosas, bloqueadas o pendientes. Los promotores nuevos de la tabla son **activaciones acumuladas**, no el stock activo al período 60. Un agente puede activarse, emitir y desactivarse en el mismo período.

Estos ejemplos comprueban que la transmisión continúa mediante nuevos emisores y supera el alcance directo inicial. No establecen que una distribución sea mejor que la otra ni demuestran un umbral crítico. El agotamiento de contactos, con energía constante y ausencia de WOM negativo, delimita su interpretación.

## Evidencias y reproducción

El archivo de código contiene módulos, pruebas, configuraciones, documentación y `SOURCE_SHA256.json`. El paquete de evidencias conserva `unit_tests.log`, `unit_tests.json`, `diagnostic_runs.csv`, `verification_summary.json`, la huella del código, un manifiesto de evidencias y dos ejemplos completos.

Cada ejemplo contiene red y agentes iniciales, las tres configuraciones, mensajes, decisiones, compras, evaluaciones, intentos, genealogía, estados finales, historial individual, métricas por período y su manifiesto. Los sorteos de las corridas entregadas usan el generador indexado normal; no dependen de funciones personalizadas de pruebas.

```bash
python -m unittest discover -s tests -v
python scripts/verify_m3.py --out outputs/verification_reproduction
python -m article8 --mode experience --config configs/m3_baseline.json --dynamics-config configs/m3_dynamics.json --experience-config configs/m3_experience.json --seed 20260925 --out outputs/example_reproduction
```

Ejecute desde `article8_m3` después de descomprimir. Use directorios nuevos o vacíos. La fecha del informe de verificación cambia al repetir el comando; la trayectoria normal se reproduce con el mismo runtime y configuraciones. No se garantiza identidad byte a byte entre versiones diferentes de Python. Colab no se verificó en esta sesión.

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| Article_8_M3_Python_v0.3.0.zip | 63008 | `3711eba8106824e7578cd64ac22ea9833ccd1c05852dd5e613da8ed54852db74` |
| Article_8_M3_Evidencias_v0.3.0.zip | 4232640 | `7ccdae77f957ca67b9612d873867574b2c95b67f379efa53c33fcb4f9334c6d2` |
| Article_8_M3_Alcance_v0.3.0.md | 4864 | `ee924cef323c62a1bf8ed51f8d1e19c12455f8b8f24cdfcd274fe5ae54b80db1` |

Ambos ZIP se abrieron y pasaron la comprobación de integridad. Los manifiestos de los ejemplos fueron verificados después de la exportación. La ejecución de verificación quedó registrada en UTC: `2026-09-26T09:54:06.953781+00:00`.

## Siguiente incremento

Incorporar desgaste de energía y fatiga con pruebas de actualización, umbral y desactivación. Después, integrar WOM negativo y los indicadores de reproducción, reposición y clasificación antes del piloto completo. Esta entrega no incorpora ajustes para producir un umbral prefijado.
