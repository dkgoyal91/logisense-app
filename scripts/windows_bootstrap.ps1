param(
    [ValidateSet('start', 'stop')]
    [string]$Action = 'start'
)

$ErrorActionPreference = 'Stop'

function Write-Log {
    param([string]$Message)
    Write-Host "[logisense] $Message"
}

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-Python312 {
    if (-not (Test-Command 'py')) {
        return $false
    }

    & py -3.12 -V *> $null
    return $LASTEXITCODE -eq 0
}

function Ensure-Python312 {
    if (Test-Python312) {
        return
    }

    if (-not (Test-Command 'winget')) {
        throw 'Python 3.12 is required, and winget is not available to install it.'
    }

    Write-Log 'Python 3.12 is missing; installing it with winget...'
    & winget install --id Python.Python.3.12 -e --silent --accept-package-agreements --accept-source-agreements

    if (-not (Test-Python312)) {
        throw 'Python 3.12 was not available after installation.'
    }
}

function Test-DockerComposeAvailable {
    if (Test-Command 'docker') {
        & docker compose version *> $null
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
    }

    if (Test-Command 'wsl') {
        & wsl -e bash -lc 'docker compose version' *> $null
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
    }

    return $false
}

function Start-DockerDesktop {
    $desktopCandidates = @()

    if ($env:ProgramFiles) {
        $desktopCandidates += Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
    }

    if (${env:ProgramFiles(x86)}) {
        $desktopCandidates += Join-Path ${env:ProgramFiles(x86)} 'Docker\Docker\Docker Desktop.exe'
    }

    foreach ($candidate in $desktopCandidates) {
        if (Test-Path $candidate) {
            Start-Process -FilePath $candidate | Out-Null
            break
        }
    }
}

function Ensure-DockerDesktop {
    if (Test-DockerComposeAvailable) {
        return
    }

    Start-DockerDesktop

    if (Test-DockerComposeAvailable) {
        return
    }

    if (-not (Test-Command 'winget')) {
        throw 'Docker Compose is required, and winget is not available to install Docker Desktop.'
    }

    Write-Log 'Docker Compose is missing; installing Docker Desktop with winget...'
    & winget install --id Docker.DockerDesktop -e --silent --accept-package-agreements --accept-source-agreements
    Start-DockerDesktop
}

function Invoke-LogiSense {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args
    )

    & py -3.12 @Args
    return $LASTEXITCODE
}

Set-Location (Join-Path $PSScriptRoot '..')
Ensure-Python312

switch ($Action) {
    'start' {
        $exitCode = Invoke-LogiSense -Args @('run.py', 'docker')
        if ($exitCode -eq 0) {
            exit 0
        }

        if (-not (Test-DockerComposeAvailable)) {
            Ensure-DockerDesktop
            $exitCode = Invoke-LogiSense -Args @('run.py', 'docker')
            if ($exitCode -eq 0) {
                exit 0
            }
        }

        Write-Log 'Starting the local Python app instead.'
        exit (Invoke-LogiSense -Args @('run.py', 'local'))
    }
    'stop' {
        $exitCode = Invoke-LogiSense -Args @('run.py', 'stop')
        if ($exitCode -eq 0) {
            exit 0
        }

        if (-not (Test-DockerComposeAvailable)) {
            Ensure-DockerDesktop
            $exitCode = Invoke-LogiSense -Args @('run.py', 'stop')
        }

        exit $exitCode
    }
}