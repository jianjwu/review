param(
    [string]$RepoPath = (Join-Path $PSScriptRoot "..\SolidworksMCP-python-main"),
    [string]$SolidWorksYear = "2022",
    [string]$SolidWorksExe = "",
    [string]$PartTemplate = "",
    [int]$WaitSeconds = 120,
    [switch]$SkipInstall,
    [switch]$SkipVSCode,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host $Message -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Message)
    Write-Host "[OK]   $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

function Resolve-SolidWorksExe {
    param([string]$ExplicitPath)

    $candidates = @()
    if ($ExplicitPath) {
        $candidates += $ExplicitPath
    }

    $process = Get-Process -Name "SLDWORKS" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($process -and $process.Path) {
        $candidates += $process.Path
    }

    $yearRoot = "C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS $SolidWorksYear\SLDWORKS.exe"
    $yearRootAlt = "C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS ($SolidWorksYear)\SLDWORKS.exe"

    $candidates += @(
        "D:\SW\Crop\SOLIDWORKS\SLDWORKS.exe",
        $yearRoot,
        $yearRootAlt,
        "C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SLDWORKS.exe",
        "C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS (2)\SLDWORKS.exe"
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return (Resolve-Path $candidate).Path
        }
    }

    return $null
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

function Write-McpConfig {
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

function Test-Pywin32SolidWorks {
    param([string]$PythonPath)

    $code = @'
import pythoncom
import win32com.client

pythoncom.CoInitialize()
try:
    app = win32com.client.GetActiveObject('SldWorks.Application')
    revision = app.RevisionNumber() if callable(app.RevisionNumber) else app.RevisionNumber
    doc = app.ActiveDoc
    print('Revision {0}; ActiveDoc {1}'.format(revision, 'yes' if doc else 'none'))
finally:
    pythoncom.CoUninitialize()
'@

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & $PythonPath -c $code 2>&1
        $exitCode = $LASTEXITCODE
    } catch {
        $output = @($_.Exception.Message)
        $exitCode = 1
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    return [pscustomobject]@{
        Ok = ($exitCode -eq 0)
        Detail = (($output | ForEach-Object { $_.ToString() }) -join " ")
    }
}

function Wait-SolidWorksCom {
    param(
        [string]$PythonPath,
        [int]$TimeoutSeconds
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastDetail = ""

    while ((Get-Date) -lt $deadline) {
        $probe = Test-Pywin32SolidWorks -PythonPath $PythonPath
        if ($probe.Ok) {
            return $probe
        }
        $lastDetail = $probe.Detail
        Start-Sleep -Seconds 3
    }

    return [pscustomobject]@{
        Ok = $false
        Detail = if ($lastDetail) { $lastDetail } else { "Timed out waiting for SolidWorks COM." }
    }
}

$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$resolvedRepo = (Resolve-Path $RepoPath).Path
$installScript = Join-Path $workspaceRoot "scripts\Install-SolidWorksMcp.ps1"
$testScript = Join-Path $workspaceRoot "scripts\Test-SolidWorksMcpEnvironment.ps1"
$venvPython = Join-Path $resolvedRepo ".venv\Scripts\python.exe"
$resolvedPartTemplate = Resolve-PartTemplatePath -Year $SolidWorksYear -ExplicitPath $PartTemplate

Write-Step "[1/7] Checking native Windows host"
if ([System.Environment]::OSVersion.Platform -ne [System.PlatformID]::Win32NT) {
    Write-Fail "This workflow must run on native Windows. Do not use WSL for real SolidWorks COM automation."
    exit 1
}
Write-Ok "$([System.Environment]::OSVersion.VersionString)"

Write-Step "[2/7] Refreshing MCP config"
Write-McpConfig -WorkspaceRoot $workspaceRoot -ResolvedRepoPath $resolvedRepo -Year $SolidWorksYear
Write-Ok "MCP config set to SolidWorks $SolidWorksYear"

Write-Step "[3/7] Checking MCP Python environment"
if (-not (Test-Path $venvPython)) {
    if ($SkipInstall) {
        Write-Fail "Missing .venv at $venvPython"
        exit 1
    }
    if ($CheckOnly) {
        Write-Warn "Missing .venv. Run scripts\Install-SolidWorksMcp.ps1 or rerun without -CheckOnly."
    } else {
        Write-Warn "Missing .venv; installing MCP dependencies."
        & powershell -NoProfile -ExecutionPolicy Bypass -File $installScript -SolidWorksYear $SolidWorksYear -PartTemplate $resolvedPartTemplate
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
}

if (Test-Path $venvPython) {
    $importResult = & $venvPython -c "import solidworks_mcp, fastmcp, win32com.client; print('imports ok')" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "MCP packages ready: $($importResult -join ' ')"
    } elseif (-not $SkipInstall -and -not $CheckOnly) {
        Write-Warn "MCP imports failed; reinstalling dependencies."
        & powershell -NoProfile -ExecutionPolicy Bypass -File $installScript -SolidWorksYear $SolidWorksYear -PartTemplate $resolvedPartTemplate
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    } else {
        Write-Fail "MCP imports failed: $($importResult -join ' ')"
        exit 1
    }
}

Write-Step "[4/7] Checking SolidWorks installation"
$comType = [type]::GetTypeFromProgID("SldWorks.Application")
if ($null -eq $comType) {
    Write-Fail "SldWorks.Application COM is not registered. Repair or reinstall SolidWorks $SolidWorksYear."
    exit 1
}
Write-Ok "SldWorks.Application COM registered"

$swExe = Resolve-SolidWorksExe -ExplicitPath $SolidWorksExe
if ($swExe) {
    Write-Ok "SolidWorks executable: $swExe"
} else {
    Write-Warn "Could not resolve SolidWorks executable path. Start SolidWorks manually if it is not already open."
}

if (Test-Path $resolvedPartTemplate) {
    Write-Ok "Part template: $resolvedPartTemplate"
} else {
    Write-Warn "Part template not found: $resolvedPartTemplate"
}

Write-Step "[5/7] Starting or reusing SolidWorks"
$swProcess = Get-Process -Name "SLDWORKS" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($swProcess) {
    Write-Ok "SolidWorks already running (PID $($swProcess.Id))"
} elseif ($swExe -and -not $CheckOnly) {
    Start-Process -FilePath $swExe -WindowStyle Normal
    Write-Ok "Started SolidWorks; waiting for COM readiness"
} elseif ($CheckOnly) {
    Write-Warn "SolidWorks is not running."
} else {
    Write-Fail "SolidWorks is not running and executable path was not found."
    exit 1
}

Write-Step "[6/7] Waiting for SolidWorks COM"
if (Test-Path $venvPython) {
    if ($CheckOnly -and -not (Get-Process -Name "SLDWORKS" -ErrorAction SilentlyContinue)) {
        Write-Warn "Skipped COM attach because SolidWorks is not running."
    } elseif ($CheckOnly) {
        $probe = Test-Pywin32SolidWorks -PythonPath $venvPython
        if ($probe.Ok) {
            Write-Ok "Active COM instance: $($probe.Detail)"
        } else {
            Write-Warn "Active COM instance is not ready: $($probe.Detail)"
        }
    } else {
        $probe = Wait-SolidWorksCom -PythonPath $venvPython -TimeoutSeconds $WaitSeconds
        if ($probe.Ok) {
            Write-Ok "Active COM instance: $($probe.Detail)"
        } else {
            Write-Fail "Could not attach to SolidWorks COM: $($probe.Detail)"
            Write-Host "Open SolidWorks, close startup/license/template dialogs, create or open a blank part, then rerun this script." -ForegroundColor Yellow
            exit 1
        }
    }
}

Write-Step "[7/7] Final environment check"
if (Test-Path $testScript) {
    $testArgs = @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        $testScript,
        "-SolidWorksYear",
        $SolidWorksYear,
        "-PartTemplate",
        $resolvedPartTemplate
    )
    if (-not $CheckOnly) {
        $testArgs += "-ProbeActiveInstance"
    }

    & powershell @testArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not $SkipVSCode -and -not $CheckOnly) {
    $codeCommand = Get-Command code -ErrorAction SilentlyContinue
    if ($codeCommand) {
        Start-Process -FilePath $codeCommand.Source -ArgumentList "`"$workspaceRoot`""
        Write-Ok "VS Code opened at workspace"
    } else {
        Write-Warn "VS Code command 'code' was not found. Open this workspace manually."
    }
}

Write-Host ""
if ($CheckOnly) {
    Write-Host "Check-only run finished. For real modeling, keep SolidWorks open and rerun without -CheckOnly." -ForegroundColor Green
} else {
    Write-Host "Ready. In VS Code, run 'Developer: Reload Window' if Codex was already open, then start a Codex thread." -ForegroundColor Green
}
