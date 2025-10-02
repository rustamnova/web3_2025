Param(
    [switch]$Rebuild
)

$ErrorActionPreference = 'Stop'

$venv = Join-Path $PSScriptRoot '..' '.venv'
$python = Join-Path $venv 'Scripts' 'python.exe'

if (!(Test-Path $python)) {
    Write-Host 'Создаю виртуальное окружение...'
    py -3 -m venv $venv
}

& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $PSScriptRoot '..' 'requirements.txt')

if ($Rebuild) {
    Write-Host 'Очистка кэша...'
}

Write-Host 'Запуск uvicorn...'
& $python -m uvicorn app.api:app --host 0.0.0.0 --port 8080 --reload

