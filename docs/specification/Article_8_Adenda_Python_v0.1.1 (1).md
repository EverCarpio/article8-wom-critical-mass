# Article 8 — Adenda de implementación en Python v0.1.1

**Fecha de decisión:** 25 de septiembre de 2026, Colombia.  
**Documento base:** Article_8_Especificacion_minima_v0.1.md.  
**Código asociado:** 0.1.1-m1.  
**Motivo:** instrucción del profesor coordinador de implementar las simulaciones en Python.

## Cambio de plataforma

La referencia a NetLogo y BehaviorSpace en la sección 1 de la especificación v0.1 queda sustituida por Python para el modelo, las pruebas, los experimentos y la exportación. Los conceptos y parámetros científicos de la especificación se conservan. Esta adenda acompaña al documento original, sin reescribirlo ni presentar nuevas hipótesis.

M1 usa únicamente la biblioteca estándar y fue verificado con Python 3.12.14. Se requiere al menos Python 3.11 para StrEnum, aunque la equivalencia entre versiones todavía no se ha probado. No se incorporan dependencias de Mesa o NetworkX para este módulo.

## Alcance implementado

Red, población y rasgos iniciales; clientes y detractores; selección de promotores distribuida o concentrada; estados comerciales, de experiencia y de WOM; contactos elegibles iniciales; índices de capacidad inicial; exportación y verificación. El modelo disponible genera t = 0. La evolución temporal sigue pendiente.

## Decisiones técnicas concretadas

1. Los identificadores de agentes y comunidades comienzan en cero. Cada enlace se exporta una vez con source < target.
2. Las semillas se derivan mediante SHA-256 con la versión de esquema article8-sha256-v1, la semilla maestra y el nombre del componente. Cada flujo utiliza random.Random aislado. La secuencia y las versiones se documentan en randomness.py y manifest.json.
3. Red, rasgos, clientes, detractores, orden comunitario y orden de selección se generan sin utilizar la proporción, la energía ni la política de ubicación de promotores. Las comparaciones se pueden emparejar sin compartir objetos de estado mutables.
4. Las proporciones se convierten a Decimal desde su representación textual. Se rechazan tamaños no enteros y capacidades comunitarias insuficientes; no se redondea ni se redistribuye sin avisar.
5. Los remanentes de la asignación equilibrada siguen la permutación comunitaria fija. La selección por turnos conserva el anidamiento de promotores al aumentar su número dentro de cada política.
6. Los promotores nominales que no cumplen energía/contactos al inicio se registran fatigados con activación vacía y motivo explícito. La desactivación t = 0 indica bloqueo inicial, no una trayectoria histórica simulada. La falta de energía y el agotamiento de contactos permanecen separados.
7. Deshabilitar WOM negativo mantiene las identidades y la insatisfacción de los clientes iniciales reservados, pero su estado es detractor inactivo. Poner lambda = 0 conserva el mecanismo y sus emisores; son intervenciones distintas.
8. Las fechas t = 0 de los clientes iniciales representan su presencia previa al seguimiento. No son fechas de compra empíricas. Las energías pertenecen al signo del rol; los demás agentes comienzan con energía cero.
9. Para las futuras decisiones temporales se incorpora una función uniforme indexada por semilla, agente, período, mecanismo y oportunidad. Es una implementación determinista bajo demanda de la tabla de números comunes prevista en la especificación. Su estabilidad frente al orden de consulta fue probada; la dinámica que la utilizará aún no está implementada.
10. Las razones de reproducción/reposición y la clasificación temporal se exportan como no definidas/no evaluadas en M1. No se inventan resultados de despegue, saturación ni colapso.

## Verificación y siguiente entrega

El informe Article_8_M1_Verificacion_v0.1.1.md documenta las pruebas ejecutadas y los ejemplos. La siguiente entrega implementará WOM positivo, contactos y compra, manteniendo los escenarios emparejados y la programación sincrónica prevista en v0.1.

El piloto de 150 corridas y el mínimo de 100 réplicas por condición principal permanecen como planes del modelo completo. Las comprobaciones de inicialización no se cuentan como esas simulaciones.
