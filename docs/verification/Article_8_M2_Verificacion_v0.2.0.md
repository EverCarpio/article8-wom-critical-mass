# Article 8 — Informe de verificación M2 v0.2.0

**Fecha:** 25 de septiembre de 2026, Colombia. **Código:** 0.2.0-m2. **Python probado:** 3.12.14.

## Resultado

**73 pruebas aprobadas: 42 de regresión M1 y 31 de M2. Cero fallos y cero errores.** Además se completaron 20 trayectorias de diagnóstico, de 60 períodos cada una, sin fallos de invariantes.

M2 añade WOM positivo, selección de vecinos susceptibles sin repetir parejas emisor–receptor, influencia con memoria, decisión sincrónica y compra única. El código conserva las condiciones iniciales y las reglas pertinentes de la especificación v0.1.

**Alcance:** WOM negativo deshabilitado, energía constante, compradores pendientes de experiencia y sin formación de nuevos promotores. La pérdida de contactos sí desactiva a los emisores. No se estiman despegue, reproducción ni colapso. Las veinte trayectorias son diagnósticas y no cuentan como el piloto de 150 corridas del modelo completo.

## Verificación de mecanismos

| Mecanismo | Comprobación y resultado |
|---|---|
| Contactos finitos | Cada pareja dirigida aparece como máximo una vez; se respeta el máximo de oportunidades por período |
| Compra única | Cada comprador aparece una vez en purchases.csv y sale del conjunto susceptible |
| Simultaneidad | Dos promotores pueden contactar al mismo receptor; las dos exposiciones generan una sola decisión |
| Alcance único | Dos mensajes a una persona cuentan como dos eventos y una persona alcanzada |
| Rechazo | Un rechazo no habilita otro mensaje del mismo emisor; otro emisor sí puede contactar después |
| Memoria | Se verificaron persistencia 0, 0,5 y 1; exposición antigua sin mensaje nuevo no habilita compra |
| Probabilidad | Coincide con un cálculo manual; permanece acotada y tolera coeficientes extremos de prueba |
| Atribución | Mayor credibilidad; empate por menor identificador; un único emisor recibe crédito |
| Orden de ejecución | Invertir emisores conserva exactamente eventos, decisiones, series y estados finales |
| Reproducibilidad | Mismos parámetros y semillas producen iguales registros; exportaciones idénticas entre procesos con distintos PYTHONHASHSEED |
| Ausencia de fuente | Cero promotores, energía, oportunidades o contactos producen cero mensajes y compras nuevas |
| Conservación | En todo período, clientes + susceptibles = 600; las compras conciliaron con agentes y eventos |
| Exportación | Registros recuperables, huellas comprobadas, detección de alteraciones y rechazo de sobrescritura |

## Diagnóstico emparejado

Se utilizaron diez semillas, 20260925 a 20260934, y dos distribuciones de promotores. Todas las corridas parten de 600 personas, 120 clientes, 480 susceptibles y 18 promotores nominales. La red, los clientes, los rasgos y los números correspondientes a decisiones potenciales permanecen emparejados.

El ejemplo de la primera semilla produce los siguientes registros. Es una comparación de funcionamiento del módulo parcial, no una conclusión del artículo.

| Indicador a 60 períodos | Distribuida | Concentrada |
|---|---:|---:|
| Mensajes positivos | 137 | 127 |
| Personas únicas alcanzadas | 132 | 118 |
| Nuevos compradores | 95 | 86 |
| Clientes finales, incluidos los 120 iniciales | 215 | 206 |
| Promotores activos finales | 0 | 0 |

En estos dos ejemplos, los emisores terminan sin contactos susceptibles no utilizados. Mantienen su energía y satisfacción. Esta pérdida de actividad no se etiqueta como colapso: M2 no permite formar nuevos promotores y todavía no implementa el clasificador del modelo completo.

En las veinte corridas se verificó que las compras estuvieran dentro del alcance susceptible inicial de los promotores y que los mensajes no excedieran el número inicial de parejas elegibles. Ningún nuevo comprador emitió WOM; sus fechas de experiencia y activación permanecen sin procesar.

## Registro de pruebas nuevas

Las 42 pruebas de M1 también pasaron; sus nombres y resultados completos se conservan en unit_tests.json y unit_tests.log. Las nuevas son:

| Prueba | Resultado |
|---|---|
| test_m2.BoundaryAndReproducibilityTests.test_chunked_run_matches_contiguous_run | passed |
| test_m2.BoundaryAndReproducibilityTests.test_corrupted_event_or_state_detected | passed |
| test_m2.BoundaryAndReproducibilityTests.test_horizon_zero_and_invalid_orders | passed |
| test_m2.BoundaryAndReproducibilityTests.test_independent_run_recreates_same_ledger | passed |
| test_m2.BoundaryAndReproducibilityTests.test_initial_state_is_not_mutated | passed |
| test_m2.BoundaryAndReproducibilityTests.test_no_intercommunity_contacts_when_bridges_absent | passed |
| test_m2.BoundaryAndReproducibilityTests.test_recording_agent_history_does_not_change_dynamics | passed |
| test_m2.BoundaryAndReproducibilityTests.test_reversed_sender_order_gives_identical_events_decisions_states | passed |
| test_m2.BoundaryAndReproducibilityTests.test_zero_sources_energy_opportunities_and_contacts | passed |
| test_m2.ContactAndPurchaseTests.test_equal_credibility_attribution_uses_smallest_id | passed |
| test_m2.ContactAndPurchaseTests.test_higher_credibility_attribution_precedes_id_tiebreak | passed |
| test_m2.ContactAndPurchaseTests.test_invalid_random_draw_fails_without_partial_commit | passed |
| test_m2.ContactAndPurchaseTests.test_later_message_from_other_sender_can_trigger_purchase | passed |
| test_m2.ContactAndPurchaseTests.test_memory_zero_and_one_extremes | passed |
| test_m2.ContactAndPurchaseTests.test_new_customer_stays_pending_and_never_emits | passed |
| test_m2.ContactAndPurchaseTests.test_opportunity_budget_without_replacement | passed |
| test_m2.ContactAndPurchaseTests.test_positive_memory_decays_without_spontaneous_purchase | passed |
| test_m2.ContactAndPurchaseTests.test_purchase_blocks_all_later_contacts | passed |
| test_m2.ContactAndPurchaseTests.test_rejected_purchase_does_not_restore_sender_contact | passed |
| test_m2.ContactAndPurchaseTests.test_strict_purchase_threshold | passed |
| test_m2.ContactAndPurchaseTests.test_two_messages_one_receiver_one_purchase | passed |
| test_m2.PositiveConfigTests.test_adoption_probability_matches_hand_calculation | passed |
| test_m2.PositiveConfigTests.test_invalid_dynamics_rejected | passed |
| test_m2.PositiveConfigTests.test_negative_mechanism_must_be_explicitly_disabled | passed |
| test_m2.PositiveConfigTests.test_old_influence_cannot_open_purchase_gate | passed |
| test_m2.PositiveConfigTests.test_probability_bounded_monotone_and_numerically_stable | passed |
| test_m2.PositiveExportTests.test_cli_results_byte_identical_across_process_hash_seeds | passed |
| test_m2.PositiveExportTests.test_empty_ledgers_have_headers_and_undefined_ratios | passed |
| test_m2.PositiveExportTests.test_no_overwrite_and_nested_checksum_validation | passed |
| test_m2.PositiveExportTests.test_recover_csv_ledgers_and_reconcile | passed |
| test_m2.PositiveExportTests.test_serialized_configuration_reproduces_dynamics | passed |

## Entregables y reproducción

- Article_8_M2_Python_v0.2.0.zip: código M1+M2, 73 pruebas, configuraciones, instrucciones y documentos de alcance.
- Article_8_M2_Evidencias_v0.2.0.zip: veinte resúmenes diagnósticos, registros de pruebas y dos ejemplos completos con eventos, compras y agentes por período.
- Article_8_M2_Alcance_v0.2.0.md: reglas implementadas, condiciones temporales del módulo parcial y próximos mecanismos.

Desde article8_m2, después de descomprimir:

    python -m unittest discover -s tests -v
    python scripts/verify_m2.py --out outputs/verification

Use una carpeta de salida nueva o vacía. No se requieren paquetes externos. La reproducción exacta se verificó en Python 3.12.14. Las instrucciones para Colab se incluyen como procedimiento; Colab no se ejecutó en esta sesión.

| Paquete | SHA-256 |
|---|---|
| Article_8_M2_Python_v0.2.0.zip | b0688332e3764fc9f73ac73a8dbd1c03c58e09038d5b1da31079c6c691b4a16c |
| Article_8_M2_Evidencias_v0.2.0.zip | f252970515b9d49ac0531bcd6dcfe4097de835bba692b0fa4445bd6fe3d9a01d |

## Próximo paso

Incorporar experiencia posterior a compra, satisfacción, disposición a recomendar y activación de nuevos promotores con los retrasos de la especificación. Después se integrarán energía/fatiga, WOM negativo, genealogía y clasificación antes del piloto completo.
