# Pruebas manuales Metro Taxi v0.8

**Entorno:** localhost, datos ficticios, navegadores Chrome/Edge recientes.

1. Arranca `iniciar_windows.bat` y comprueba que `/cliente`, `/central` y `/conductor` responden correctamente (central y conductor redirigen a login sin sesión).
2. **Cliente:** crea cuenta, GPS con permiso y una carrera; deniega GPS y prueba dirección escrita. Debe guardar ubicación solo cuando la marque o autorice. Comprueba cancelación de solicitudes pendientes.
3. **Central:** inicia admin, añade foto y datos de MT-07, selecciona Pacora, asigna carrera de prueba, verifica ofertas pendientes y turnos.
4. **Conductor:** inicia sesión conductor7, activa disponibilidad, presiona GPS (si lo desea) y acepta. Debe ver solo sus carreras y nunca los teléfonos privados del pasajero. Rechaza otra oferta con motivo.
5. **Pasajero autenticado:** mientras la oferta no se acepte ve «Pendiente de aceptación», y una vez aceptada ve foto/vehículo y SOLO la última posición reciente del conductor asignado. Otro pasajero no ve esta posición. Detén GPS y verifica que desaparezca.
6. **Vencimiento:** al superar 120 s sin aceptación, solicita una actualización en la central; debe volver a pendiente. Solo se hace en la siguiente petición API; no hay cron autónomo.
7. **Turnos:** conductor pulsa «Desconectarme» cuando no está ocupado, central revisa el historial; un conductor ocupado no puede salir de servicio sin resolver su carrera.
8. **QR:** imprimir QR del conductor para pruebas locales, recordar que los enlaces 127.0.0.1 no abren desde otro teléfono. Registrar un cliente simulado y verificar que el teléfono quede en la central.
9. **PWA:** en navegador compatible visita `/cliente` o `/conductor` bajo localhost o HTTPS; revisa opción de «Añadir a inicio». No implica APK ni GPS de fondo.
10. **Modo de despacho:** con admin activa modo auto en la central. Crea una carrera con recogida GPS y dos minutos de antigüedad en datos de prueba, confirma que un taxi con GPS real reciente de la misma sede es candidato; verifica que una posición simulada o desactualizada nunca produzca autoasignación. Vuelve a modo manual al terminar.
11. **Contraseña:** cambia la contraseña temporal desde el panel de conductor y confirma que inicia sesión con la nueva; la sesión anterior debe quedar cerrada.
12. **API:** corre `python -m unittest discover -s tests -v`; todas deben pasar.

**No validado en esta entrega:** GPS físico en múltiples teléfonos, bloqueo de pantalla, 200–300 carreras diarias reales, recepción de push, Netlify, Android APK, seguridad de producción, mapas del proveedor externo.
