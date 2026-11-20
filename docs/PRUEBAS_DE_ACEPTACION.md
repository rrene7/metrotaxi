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
