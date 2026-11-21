# Metro Taxi LOCAL-121: comprobacion de acceso sin modificar servicios o datos.
# Ejecutar: powershell -ExecutionPolicy Bypass -File .\scripts\verificar_metro_local.ps1
$ErrorActionPreference = 'Stop'
$port = 8770
$base = 'http://127.0.0.1:8770'
$issues = 0

Write-Host 'METRO TAXI - Revision de acceso local (solo lectura)' -ForegroundColor Cyan
if (-not (Test-Path '.\compose.local.yaml') -or -not (Test-Path '.\metro-local.env')) {
    Write-Host 'ERROR: Ejecuta desde la carpeta metrotaxi con compose.local.yaml y metro-local.env.' -ForegroundColor Red
    exit 1
}

try {
    $listeners = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
    if ($listeners.Count -eq 0) {
        Write-Host 'ERROR: no hay servidor escuchando en 127.0.0.1:8770.' -ForegroundColor Red
        $issues++
    } else {
        foreach ($listener in $listeners) {
            $owner = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
            if ($null -ne $owner) {
                Write-Host ("Puerto 8770: PID {0}, proceso {1}, ruta {2}" -f $owner.Id,$owner.ProcessName,$owner.Path)
                if ($owner.ProcessName -eq 'python' -or $owner.ProcessName -eq 'pythonw') {
                    Write-Host 'ALERTA: un proceso Python de Windows ocupa el puerto. Puede estar mostrando la version antigua.' -ForegroundColor Yellow
                    $issues++
                }
            }
        }
    }
} catch {
    Write-Host ('AVISO: no fue posible consultar los procesos del puerto: ' + $_.Exception.Message) -ForegroundColor Yellow
}

try {
    $containers = docker compose --env-file metro-local.env -f compose.local.yaml ps --format json 2>&1
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose no pudo consultar el proyecto.' }
    Write-Host 'Estado Docker Compose:'
    $containers | Out-Host
} catch {
    Write-Host ('ERROR: ' + $_.Exception.Message) -ForegroundColor Red
    $issues++
}

try {
    $ports = docker inspect metrotaxi-app-1 --format '{{json .NetworkSettings.Ports}}' 2>&1
    if ($LASTEXITCODE -ne 0) { throw 'No se encuentra metrotaxi-app-1.' }
    $binding = $ports | ConvertFrom-Json
    $mapping = $binding.'8080/tcp'
    if ($null -eq $mapping -or -not @($mapping | Where-Object { $_.HostIp -eq '127.0.0.1' -and $_.HostPort -eq '8770' }).Count) {
        Write-Host 'ERROR: Docker NO publica 127.0.0.1:8770->8080. Comprueba la creacion del contenedor.' -ForegroundColor Red
        $issues++
    } else {
        Write-Host 'OK: Docker publica 127.0.0.1:8770->8080.' -ForegroundColor Green
    }
} catch {
    Write-Host ('ERROR al consultar el puerto publicado: ' + $_.Exception.Message) -ForegroundColor Red
    $issues++
}

try {
    $health = Invoke-RestMethod -Uri ($base + '/api/health') -TimeoutSec 8
    if ($health.ok -ne $true -or $health.database -ne 'ready') {
        throw 'API o base de datos no estan listas.'
    }
    Write-Host 'OK: API y PostgreSQL responden.' -ForegroundColor Green
} catch {
    Write-Host ('ERROR: no hay respuesta valida de la API: ' + $_.Exception.Message) -ForegroundColor Red
    $issues++
}

try {
    $page = Invoke-WebRequest -Uri ($base + '/ingresar.html?revision=local121') -Headers @{ 'Cache-Control' = 'no-cache' } -UseBasicParsing -TimeoutSec 8
    if ($page.Content.Contains('id="ver-clave"')) {
        Write-Host 'OK: Windows recibe la pagina de inicio actualizada (LOCAL-120).' -ForegroundColor Green
    } else {
        Write-Host 'ERROR: Windows recibe la pagina antigua; busca otro servidor ocupando el puerto 8770.' -ForegroundColor Red
        $issues++
    }
} catch {
    Write-Host ('ERROR al consultar la pagina: ' + $_.Exception.Message) -ForegroundColor Red
    $issues++
}

if ($issues -eq 0) {
    Write-Host 'RESULTADO: ENTORNO LOCAL CORRECTO. Ingresar en http://127.0.0.1:8770/ingresar.html' -ForegroundColor Green
    exit 0
}
Write-Host ("RESULTADO: {0} problema(s) detectado(s). No se ha modificado ningun dato." -f $issues) -ForegroundColor Yellow
exit 1
