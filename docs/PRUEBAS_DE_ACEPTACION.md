# Metro Taxi — checklist manual previo a cada entrega

> Marcar únicamente lo comprobado realmente en la versión correspondiente. Los tests automatizados no sustituyen comprobaciones visuales.

## Instalación / sesiones

- [ ] Servidor iniciado en **una** instancia, carpeta correcta, `/ingresar` abre.
- [ ] Admin / operador entran a `/central` y no se redirigen en bucle.
- [ ] Conductor entra a `/conductor`, cliente a `/cliente` y cada rol no accede a la pantalla de otro.
- [ ] Cambio de contraseña e inicio de sesión de otro usuario no producen CSRF inválido persistente.

## Flujo MT-3 / ciclo completo

- [ ] Pasajero de prueba solicita taxi, comparte GPS o punto indicado explícitamente, valida precisión y referencia.
- [ ] Central ve solicitud sin depender del mapa; asigna conductor válido.
- [ ] Conductor ve MT-3 en «Servicios que me ofreció», **no** permanece «Cargando…».
- [ ] Si no hay coordenadas, muestra aviso y NO inventa navegación.
- [ ] Si hay coordenadas y acepta, ve Waze y Google Maps; las URLs contienen esas coordenadas.
- [ ] Waze se abre en Android, inicia desde ubicación del conductor y guía al punto de recogida.
- [ ] Al regresar de Waze, la carrera sigue registrada en Metro Taxi.
- [ ] Botones «Iniciar carrera» y «Finalizar carrera» actualizan estados y la central los refleja.
- [ ] Cuando falla la API, aparece explicación y **Reintentar**; no queda una carga infinita.

## Privacidad / datos / despliegue

- [ ] Cliente no puede consultar flota ni ubicación de otro conductor.
- [ ] Conductor no ve teléfono privado del pasajero ni carreras ajenas.
- [ ] QR dirige al formulario de Metro Taxi y no crea carrera automáticamente al registrarse.
- [ ] `runtime/` respaldada y conservada; credenciales no incluidas en ZIP/GitHub.
- [ ] Navegador recargado sin caché antigua (Ctrl+F5) y vista móvil revisada.
- [ ] Si no se verificaron navegador real, HTTPS, APK o GPS de fondo, reportar claramente esa limitación.

## Validación automática

```powershell
scripts\validar_entrega.bat
```

**Estado de pruebas manuales en esta entrega (20-11-2026):** pendiente de validación en el navegador y teléfono de la instalación del usuario. No marcar como aprobadas sin evidencia.


## POINT-108 — Central recupera coordenadas confirmadas (nueva comprobación manual)

- [ ] Registrar una carrera desde la central sin coordenadas; el conductor no puede iniciarla por no tener punto de recogida.
- [ ] Abrir «Marcar recogida en mapa» para esa carrera, pulsar el mapa o introducir dos coordenadas proporcionadas por el pasajero, y marcar la casilla de confirmación.
- [ ] Cancelar sin guardar: las coordenadas no cambian. Guardar con confirmación: la central y el conductor ven el punto tras actualizar.
- [ ] Sin el consentimiento del pasajero o sin dos valores numéricos válidos la API devuelve 400; el error es visible en la central.
- [ ] Dos operadores editan el mismo punto: el segundo no sobrescribe silenciosamente y recibe 409.
- [ ] Al iniciar el viaje, la recogida no se puede modificar; el destino sí hasta el final. Tras terminar/cancelar, ambos quedan bloqueados.
- [ ] Las acciones «Iniciar» y «Finalizar» siguen exigiendo GPS reciente/preciso del conductor cerca del punto; **el punto confirmado por la central no suplanta el GPS del vehículo**.
- [ ] Desactivar Internet/mapas: el formulario permite escribir coordenadas verificadas manualmente y el resto de la central carga sin quedar bloqueada.
- [ ] Confirmar que el cambio de punto no expone teléfonos ni posiciones de otros clientes al conductor; probar en Chrome y Android antes de operar en calle.

**Estado:** automatización CI pendiente de corroborar en PR; inspección manual en navegadores/teléfonos pendiente.


## DISPATCH-117 — ensayo real pendiente, tres sesiones

- [ ] Abrir perfiles/navegadores separados para pasajero, operador central y conductor. Verificar sesiones y CSRF separados.
- [ ] Pasajero solicita una carrera ficticia; central la ve y asigna una unidad disponible. El pasajero NO ve ofertas internas ni flota.
- [ ] Conductor recibe únicamente su oferta; al aceptarla el pasajero ve la unidad confirmada.
- [ ] Sin GPS preciso y cercano, intentar inicio/final desde navegador y API: ambos deben bloquearse. Nunca inventar GPS de dispositivo.
- [ ] Probar recorrido con GPS físico cerca de recogida/destino, actualización en central y cliente, navegación Waze y recuperación desde segundo plano.
- [ ] Verificar historial en pestaña independiente de conductor y cliente, sin acciones en viajes cerrados ni datos de otros usuarios.
- [ ] Probar pérdida de Internet, GPS detenido y reconexión; no utilizar clientes reales en esta etapa.

**La prueba automatizada DISPATCH-117 no marca estas casillas:** requieren navegadores y teléfonos reales.


## LOCAL-118 — Comprobación manual del piloto Docker

- [ ] Ejecutar `docker compose --env-file metro-local.env -f compose.local.yaml ps` en Windows y verificar web en `127.0.0.1:8770`, sin PostgreSQL publicado.
- [ ] Confirmar `/api/health` conectado a PostgreSQL; entrar con admin, operador, conductor y cliente ficticios en perfiles separados.
- [ ] Reiniciar contenedores con `stop/start`; verificar que carreras y cuentas siguen en volumen persistente (sin borrar datos).
- [ ] Comprobar que una petición desde host no local es rechazada y que otros teléfonos en LAN NO acceden al piloto HTTP.
- [ ] Completar flujo ficticio de tres roles y geocerca, y documentar limitaciones del GPS de escritorio.

Estas casillas permanecen pendientes hasta disponer de pruebas reales en el equipo.


## LOCAL-119 — comprobación del CI Docker antes de instalar

- [ ] Confirmar que el PR correspondiente muestra ambos trabajos `pruebas` y `docker-local-smoke` en verde, con bootstrap/login/reinicio sin errores.
- [ ] En el equipo Windows, revisar el puerto 8770, cuentas ficticias, sesión después de reiniciar y datos de prueba persistidos, sin eliminar volúmenes.

No se marcan estas comprobaciones como ejecutadas en Windows solo porque CI pase.

## LIVE-122 — Control de actualización automática por rol

- [ ] Pasajero: observar carrera activa mientras central asigna y conductor acepta, sin recargar página; el historial permanece en su pestaña.
- [ ] Central: mantener enfocado el selector de unidad o expediente mientras llegan consultas periódicas; no perder campos en edición.
- [ ] Conductor: mantener visible una oferta durante sondeos sin parpadeos; probar Aceptar e Historial sin cambio automático de pestaña.
- [ ] Recorrer estados `pending`, `offered`, `accepted`, `inprogress`, `done` con tres sesiones independientes y confirmar que los cambios llegan sin exponer teléfonos ni flota al pasajero o conductor.
- [ ] Verificar controles GPS de inicio y finalización lejos/cerca del punto con ubicación real, nunca simulada; probar pérdida de señal.
- [ ] Verificar que un error de API muestra Reintentar y que el panel se recupera cuando vuelve a responder.

**Pendiente:** evaluación manual en Chrome y Android físicos; pruebas automatizadas no equivalen a uso comercial.

## ALERTS-123 — Avisos de carreras

- [ ] Al abrir conductor con ofertas existentes, no se anuncian todas como nuevas; el primer sondeo establece línea base.
- [ ] Central asigna una nueva carrera ficticia: conductor conectado ve aviso de nueva oferta sin recargar ni perder GPS o pestaña de historial.
- [ ] Una carrera nueva en estado pendiente avisa únicamente a la central, no al conductor ni a pasajeros ajenos.
- [ ] Con la pestaña abierta, llega un aviso una vez; sondeos posteriores no repiten sonido para la misma oferta.
- [ ] Activar/desactivar avisos sonoros mediante control explícito, respetar rechazo de permisos de notificaciones y comprobar con varios navegadores.
- [ ] GPS, llegada obligatoria a recogida/destino, CSRF, privacidad y acciones de carrera permanecen funcionales.

**Limitación:** no es push en segundo plano ni funciona con la página cerrada. Prueba real en Android pendiente.

## SESSION-124 — Verificación de navegación sin saltos

- [ ] Con sesión de pasajero del mismo perfil Chrome, abrir `/ingresar.html`: no redirige automáticamente a central; muestra aviso y permite iniciar sesión como personal.
- [ ] Con sesión de pasajero abrir `/central.html`: navegación a cliente, sin bucle central/login.
- [ ] Con sesión de conductor abrir central: abre conductor; con admin abrir conductor: abre central.
- [ ] Sin sesión, abrir central o conductor: muestra acceso de personal sin múltiples saltos.
- [ ] Usar perfiles de Chrome independientes (no dos pestañas ni dos ventanas de incógnito compartidas) para validar pasajero/central/conductor al mismo tiempo.
- [ ] El mapa y listas continúan operando, no se pierden formularios en edición y nadie accede a datos de otro rol.

**Pendiente de comprobar presencialmente en el equipo Windows del usuario.**
