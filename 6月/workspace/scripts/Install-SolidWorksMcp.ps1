param(
    [string]$RepoPath = (Join-Path $PSScriptRoot "..\SolidworksMCP-python-main"),
    [string]$SolidWorksYear = "2022",
    [string]$PartTemplate = ""
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host $Message -ForegroundColor Cyan
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Resolve-PartTemplatePath {
    param(
        [string]$Year,
        [string]$ExplicitPath
    )

    if ($ExplicitPath) {
        return $ExplicitPath
    }

    return "C:\ProgramData\SOLIDWORKS\SOLIDWORKS $Year\templates\gb_part.prtdot"
}

function Test-PythonLauncher {
    param([string[]]$Launcher)

    try {
        if ($Launcher.Count -gt 1) {
            $probe = & $Launcher[0] @($Launcher[1..($Launcher.Count - 1)] + @("-c", "import sys; print(sys.executable); print(sys.version_info[:2])")) 2>&1
        } else {
            $probe = & $Launcher[0] -c "import sys; print(sys.executable); print(sys.version_info[:2])" 2>&1
        }

        if ($LASTEXITCODE -ne 0) {
            return $null
        }

        $exe = ($probe | Select-Object -First 1).ToString().Trim()
        $versionLine = ($probe | Select-Object -Last 1).ToString().Trim()
        if (-not $exe -or -not (Test-Path $exe) -or $exe -match "WindowsApps") {
            return $null
        }

        $match = [regex]::Match($versionLine, "\((\d+),\s*(\d+)\)")
        if (-not $match.Success) {
            return $null
        }

        $major = [int]$match.Groups[1].Value
        $minor = [int]$match.Groups[2].Value
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
            return $null
        }

        return @{
            Launcher = $Launcher
            Exe = $exe
            Version = "$major.$minor"
        }
    }
    catch {
        return $null
    }
}

function Find-Python {
    $candidates = @(
        @((Join-Path $env:LOCALAPPDATA "Python\bin\python.exe")),
        @("py", "-3.13"),
        @("py", "-3.12"),
        @("py", "-3.11"),
        @("py", "-3"),
        @("python")
    )

    $wherePython = @(Get-Command python -All -ErrorAction SilentlyContinue | ForEach-Object {
        $_.Source
    } | Where-Object {
        $_ -and $_ -notmatch "WindowsApps"
    })
    foreach ($path in $wherePython) {
        $trimmed = $path.Trim()
        if ($trimmed) {
            $candidates += ,@($trimmed)
        }
    }

    foreach ($candidate in $candidates) {
        $result = Test-PythonLauncher -Launcher $candidate
        if ($result) {
            return $result
        }
    }

    return $null
}

function Invoke-ProjectPython {
    param(
        [string]$PythonPath,
        [string[]]$PythonArgs
    )

    & $PythonPath @PythonArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $PythonPath $($PythonArgs -join ' ')"
    }
}

function Write-CodexConfig {
    param(
        [string]$WorkspaceRoot,
        [string]$ResolvedRepoPath,
        [string]$Year
    )

    $codexDir = Join-Path $WorkspaceRoot ".codex"
    $vscodeDir = Join-Path $WorkspaceRoot ".vscode"
    New-Item -ItemType Directory -Force -Path $codexDir | Out-Null
    New-Item -ItemType Directory -Force -Path $vscodeDir | Out-Null

    $runScript = Join-Path $ResolvedRepoPath "run-mcp.ps1"
    $toml = @"
[mcp_servers.solidworks_mcp]
command = 'powershell'
args = [
  '-NoProfile',
  '-ExecutionPolicy',
  'Bypass',
  '-File',
  '$runScript',
  '--real',
  '--year',
  '$Year',
  '--log-level',
  'INFO'
]
startup_timeout_sec = 60
tool_timeout_sec = 300
"@
    Set-Content -Path (Join-Path $codexDir "config.toml") -Value $toml -Encoding UTF8

    $jsonConfig = [ordered]@{
        servers = [ordered]@{
            "solidworks-mcp-server" = [ordered]@{
                type = "stdio"
                command = "powershell"
                args = @(
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    $runScript,
                    "--real",
                    "--year",
                    $Year,
                    "--log-level",
                    "INFO"
                )
            }
        }
    }
    $jsonConfig | ConvertTo-Json -Depth 6 | Set-Content -Path (Join-Path $vscodeDir "mcp.json") -Encoding UTF8
}

$workspaceRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$resolvedRepo = Resolve-Path $RepoPath
$resolvedPartTemplate = Resolve-PartTemplatePath -Year $SolidWorksYear -ExplicitPath $PartTemplate

Write-Step "[1/6] Checking Windows and SolidWorks prerequisites"
if ([System.Environment]::OSVersion.Platform -ne [System.PlatformID]::Win32NT) {
    Write-Host "[ERROR] This workflow must run on native Windows. Do not use WSL for real SolidWorks COM automation." -ForegroundColor Red
    exit 1
}
Write-Host "Windows host: $([System.Environment]::OSVersion.VersionString)" -ForegroundColor Green

$comType = [type]::GetTypeFromProgID("SldWorks.Application")
if ($null -eq $comType) {
    Write-Warn "SldWorks.Application COM is not registered. Install/license SolidWorks $SolidWorksYear before real modeling."
} else {
    Write-Host "SolidWorks COM: registered" -ForegroundColor Green
}

if (Test-Path $resolvedPartTemplate) {
    Write-Host "Part template: $resolvedPartTemplate" -ForegroundColor Green
} else {
    Write-Warn "Part template not found: $resolvedPartTemplate"
}

Write-Step "[2/6] Checking repository"
if (-not (Test-Path (Join-Path $resolvedRepo "pyproject.toml"))) {
    throw "pyproject.toml not found under $resolvedRepo"
}
if (-not (Test-Path (Join-Path $resolvedRepo "run-mcp.ps1"))) {
    throw "run-mcp.ps1 not found under $resolvedRepo"
}
Write-Host "Repository: $resolvedRepo" -ForegroundColor Green

Write-Step "[3/6] Checking Python 3.11+"
$python = Find-Python
if (-not $python) {
    Write-Host "[ERROR] Python 3.11+ was not found." -ForegroundColor Red
    Write-Host "Install Python from python.org, enable 'Add python.exe to PATH', then run this script again." -ForegroundColor Yellow
    exit 1
}
Write-Host "Python: $($python.Exe) ($($python.Version))" -ForegroundColor Green

Write-Step "[4/6] Creating virtual environment"
$venvPython = Join-Path $resolvedRepo ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Push-Location $resolvedRepo
    try {
        if ($python.Launcher.Count -gt 1) {
            & $python.Launcher[0] @($python.Launcher[1..($python.Launcher.Count - 1)] + @("-m", "venv", ".venv"))
        } else {
            & $python.Launcher[0] -m venv .venv
        }
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create .venv"
        }
    }
    finally {
        Pop-Location
    }
}
Write-Host "Virtualenv: $venvPython" -ForegroundColor Green

Write-Step "[5/6] Installing core MCP dependencies"
Push-Location $resolvedRepo
try {
    Invoke-ProjectPython -PythonPath $venvPython -PythonArgs @("-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel")
    Invoke-ProjectPython -PythonPath $venvPython -PythonArgs @("-m", "pip", "install", "-e", ".")
}
finally {
    Pop-Location
}

Write-Step "[6/6] Writing Codex and VS Code MCP configs"
Write-CodexConfig -WorkspaceRoot $workspaceRoot -ResolvedRepoPath $resolvedRepo -Year $SolidWorksYear
Write-Host "Wrote .codex\config.toml and .vscode\mcp.json" -ForegroundColor Green

Write-Host ""
Write-Host "Done. Open SolidWorks, then restart Codex/VS Code MCP servers." -ForegroundColor Green
Write-Host "Run: powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Test-SolidWorksMcpEnvironment.ps1 -SolidWorksYear $SolidWorksYear -ProbeActiveInstance" -ForegroundColor Green
