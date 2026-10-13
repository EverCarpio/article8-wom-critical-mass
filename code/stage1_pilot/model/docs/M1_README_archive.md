# Article 8 — M1 en Python

Versión: **0.1.1-m1**. Módulo de red, población inicial y estados para el estudio de masa crítica de promotores. Implementa el estado inicial **t = 0** de la especificación mínima v0.1, con la adaptación a Python documentada en docs/Article_8_Adenda_Python_v0.1.1.md.

## Qué contiene

- Red simple no dirigida de 600 personas y seis comunidades; probabilidades de enlace interna 0,08 y externa 0,006.
- 120 clientes iniciales, 20 por comunidad, y 480 personas susceptibles.
- Reserva de seis detractores, uno por comunidad.
- Porcentajes de promotores sin redondear personas: 15 % de los clientes equivale a 18 promotores.
- Distribución equilibrada entre seis comunidades o concentrada en dos, con selección anidada al aumentar la proporción.
- Rasgos individuales y tres dimensiones de estado: comercial, experiencia y WOM.
- Estado activo condicionado por energía y contactos susceptibles. La falta de energía y de contactos se registran por separado.
- Semillas separadas por componente, exportación con huellas SHA-256 y pruebas reproducibles.

No contiene todavía emisión temporal de WOM, compra, experiencia posterior, reproducción, fatiga mensual ni clasificación de despegue. El horizonte de 60 períodos sigue previsto para el modelo completo; M1 no ejecuta esos períodos. Las inicializaciones de verificación no son el piloto de 150 corridas.

## Requisitos y ejecución

Python 3.11 o posterior por el uso de StrEnum. La entrega fue probada con **Python 3.12.14**. No requiere pip ni paquetes externos. La reproducción exacta de las huellas entregadas debe hacerse con esa misma versión de Python y este código; otras versiones no se han verificado.

Descomprima el paquete y abra una terminal en la carpeta article8_m1:

```bash
python -m article8 --out outputs/distributed --distribution distributed --seed 20260925
python -m article8 --out outputs/concentrated --distribution concentrated --seed 20260925
python -m unittest discover -s tests -v
```

Para reproducir la verificación completa, incluyendo diez redes, 220 inicializaciones, 60 comprobaciones energéticas y dos ejemplos exportados:

```bash
python scripts/verify_m1.py --out outputs/verification
```

Los directorios de salida deben ser nuevos o estar vacíos. Para repetir, use otro nombre de salida. El programa no sobrescribe resultados existentes.

También puede partir de un JSON:

```bash
python -m article8 --config configs/baseline.json --share 0.30 --positive-energy 0.9 --out outputs/custom
python -m article8 --negative-off --out outputs/negative_off
```

Una proporción que no corresponda a un número entero de clientes es rechazada, al igual que una concentración que exceda los clientes elegibles. No se altera silenciosamente el denominador ni se redistribuyen excedentes.

En Google Colab, cargue el ZIP, descomprímalo con la biblioteca zipfile y cambie de directorio antes de ejecutar:

```python
from google.colab import files
import zipfile
uploaded = files.upload()
archive = next(iter(uploaded))
with zipfile.ZipFile(archive) as z:
    z.extractall('/content/article8_release')
```

```python
%cd /content/article8_release/article8_m1
!python -m article8 --out outputs/example
!python -m unittest discover -s tests -v
```

La ejecución en Colab no se probó en esta sesión. No requiere conexión automática a Drive; los archivos de salida se pueden descargar o copiar a la carpeta del proyecto.

## API para ampliar el modelo

```python
from dataclasses import replace
from article8.config import Config
from article8.model import make_environment, initialize

base = Config(seed=20260925)
environment = make_environment(base)
distributed = initialize(base, environment)
concentrated = initialize(replace(base, distribution='concentrated'), environment)
assert distributed.environment == concentrated.environment
print(distributed.summary())
```

La reutilización del entorno mantiene red, rasgos, clientes, detractores y ordenaciones de selección. Cada estado crea agentes y conjuntos de contactos propios: cambiar un escenario no modifica otro. El entorno es inmutable.

Los atributos parent y generation preparan el registro genealógico, pero todavía no se asignan descendientes. indexed_uniform ofrece números por agente, período, mecanismo y oportunidad sin depender del orden de llamadas; su uso en la dinámica quedará verificado en los siguientes módulos.

## Archivos exportados

| Archivo | Contenido |
|---|---|
| config.json | Parámetros exactos de esta inicialización |
| network_edges.csv | Cada enlace una vez, con source < target; IDs desde cero |
| agents_initial.csv | Un registro por persona, estados, rasgos, energías, fechas y contactos restantes |
| community_summary.csv | Clientes, susceptibles y emisores por comunidad |
| system_period.csv | Una fila t = 0; razones de reproducción vacías y clasificación no evaluada |
| network_metrics.json | Grados, clustering, modularidad de las comunidades asignadas, componentes y enlaces entre comunidades |
| manifest.json | Versión, semillas, huella del entorno y comprobación de integridad de cada archivo |

En CSV, un campo vacío representa un dato no definido. Las listas y los motivos se codifican como JSON dentro de la celda. none es un estado WOM sin actividad: incluye tanto a susceptibles como a clientes neutrales; debe interpretarse junto con el estado comercial.

El tiempo cero de compra y experiencia de los clientes iniciales es un marcador de presencia en la línea de base, no una fecha histórica observada. Un promotor inicial bloqueado conserva su pertenencia al conjunto nominal y se registra fatigado, con activation_time vacío e inactivity_reasons explícitos. No se presupone una activación anterior simulada.

La modularidad es la correspondiente a las comunidades asignadas, no el resultado de detectar comunidades. Se calcula Q = suma_c[L_c/m − (d_c/(2m))²]; se exporta null cuando no hay enlaces. El clustering medio incluye los aislados con valor cero. Ninguna red se repara o descarta para aumentar la conectividad.

## Verificación y límites

Las pruebas incluyen grafos con resultados calculables a mano, configuración inválida, compra/experiencia inicial, exclusión de roles, cero energía, ausencia de contactos, WOM negativo deshabilitado, porcentajes y conjuntos anidados, emparejamiento, exportación íntegra y comparación byte por byte entre procesos con distintos PYTHONHASHSEED.

Las 220 inicializaciones combinan once proporciones, dos distribuciones y diez semillas. Las 60 comprobaciones energéticas combinan tres energías, dos distribuciones y diez semillas al 15 %; veinte configuraciones coinciden con las del barrido principal. Son 260 configuraciones únicas de inicialización, con 280 evaluaciones dentro de esos dos barridos.

Estas pruebas verifican M1. No certifican las transiciones, las compras ni los resultados temporales del modelo completo, y no constituyen validación empírica.

## Próximo módulo

M2 incorporará oportunidades de recomendación, selección de contactos sin repetición, exposiciones simultáneas y compra única. Después se incorporarán experiencia, formación de emisores, energía temporal, WOM negativo y clasificación. Cada módulo agregará sus pruebas antes del piloto.

