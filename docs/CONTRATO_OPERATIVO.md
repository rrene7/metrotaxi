# Metro Taxi — contrato funcional innegociable

- **Relación comercial:** Metro Taxi recibe, registra y administra todas las solicitudes. Waze/Google Maps son solo herramientas externas de navegación.
- **Pasajero:** puede registrar una solicitud, compartir ubicación de forma explícita, ver su carrera y el conductor asignado cuando corresponda. No ve la flota completa ni los datos de otros clientes.
- **Conductor:** se conecta/desconecta, acepta/rechaza/oferta, inicia y termina sus carreras. Solo ve sus asignaciones y los puntos autorizados de recogida/destino; no recibe los teléfonos privados de los clientes.
- **Operador:** registra solicitudes, puede asignar y supervisar carreras de sus competencias. No suspende conductores si su rol no lo autoriza.
- **Administrador:** gestiona permisos, sedes, perfiles, suspensión y política de despacho.
- **Coordenadas:** nunca se generan desde una dirección textual sin geocodificación verificada. El GPS debe solicitar permiso; datos simulados se rotulan como simulados. Posiciones antiguas no se muestran como actuales.
- **Disponibilidad:** el conductor debe estar habilitado, en turno y disponible. No se asigna por cercanía usando GPS caducado o simulado.
- **Mensajería y QR:** registros y solicitudes llegan a Metro Taxi, no a WhatsApp privado de un conductor. No afirmar que un número quedó verificado solo porque se registró.
- **Pantallas resistentes:** si falla el mapa o la biblioteca de navegación, las carreras y botones críticos deben seguir funcionando. Si falla una API se informa y se habilita Reintentar.
- **Seguridad:** autorización en servidor, CSRF en cambios, datos secretos excluidos del repositorio, HTTPS para publicación y respaldos antes de actualizar.
- **Alcance:** el servidor Python/SQLite es una demostración local; PWA no equivale a APK Android ni GPS confiable en segundo plano.

- **Separación de versiones v0.10:** la nueva API no puede heredar ni sobrescribir automáticamente datos `runtime/` del piloto; mantener respaldo y migración explícita validada. La web cloud staging no posee aún paridad QR/mensajería/foto y NO debe anunciarse como sistema final.
