# Start LogiSense locally (no Docker) on Windows using PowerShell
# Prerequisites: Python 3.12 or 3.13, Node.js, npm
# Usage: .\scripts\start_app_local.ps1

$ROOT_DIR = Split-Path -Parent $PSScriptRoot
Set-Location $ROOT_DIR

Write-Host "[logisense] Starting LogiSense in local mode (Python + Node.js)..."

# Try Python 3.13 first, then 3.12
$pythonExe = $null

# Try py launcher with 3.13
if (Get-Command py -ErrorAction SilentlyContinue) {
    try {
        $version = & py -3.13 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($version -eq "3.13") {
            $pythonExe = (& py -3.13 -c "import sys; print(sys.executable)" 2>$null)
        }
    }
    catch {}
}

# Try py launcher with 3.12 if 3.13 not found
if (-not $pythonExe -and (Get-Command py -ErrorAction SilentlyContinue)) {
    try {
        $version = & py -3.12 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($version -eq "3.12") {
            $pythonExe = (& py -3.12 -c "import sys; print(sys.executable)" 2>$null)
        }
    }
    catch {}
}

# Try direct python3.13
if (-not $pythonExe -and (Get-Command python3.13 -ErrorAction SilentlyContinue)) {
    $pythonExe = (Get-Command python3.13).Source
}

# Try direct python3.12
if (-not $pythonExe -and (Get-Command python3.12 -ErrorAction SilentlyContinue)) {
    $pythonExe = (Get-Command python3.12).Source
}

# Try generic python
if (-not $pythonExe -and (Get-Command python -ErrorAction SilentlyContinue)) {
    $pythonExe = (Get-Command python).Source
}

if ($pythonExe) {
    Write-Host "[logisense] Using Python: $pythonExe"
    & $pythonExe "run.py" "local"
}
else {
    Write-Host "[logisense] Error: Python 3.12 or 3.13 not found. Install Python and try again."
    exit 1
}
