param(
    [string]$RepoPath = (Join-Path $PSScriptRoot "..\SolidworksMCP-python-main"),
    [string]$SolidWorksYear = "2022",
    [string]$PartTemplate = "",
    [switch]$ProbeActiveInstance
)

$ErrorActionPreference = "Continue"
$failed = $false

function Check {
    param(
        [string]$Name,
        [bool]$Ok,
        [string]$Detail
    )

    if ($Ok) {
        Write-Host "[OK]   $Name - $Detail" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $Name - $Detail" -ForegroundColor Red
        $script:failed = $true
    }
}

function Check-Warn {
    param(
        [string]$Name,
        [bool]$Ok,
        [string]$Detail
    )

    if ($Ok) {
        Write-Host "[OK]   $Name - $Detail" -ForegroundColor Green
    } else {
        Write-Host "[WARN] $Name - $Detail" -ForegroundColor Yellow
    }
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

$workspaceRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$resolvedRepo = $null
$resolvedPartTemplate = Resolve-PartTemplatePath -Year $SolidWorksYear -ExplicitPath $PartTemplate

Check "Native Windows host" ([System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT) ([System.Environment]::OSVersion.VersionString)

try {
    $resolvedRepo = Resolve-Path $RepoPath
    Check "Repository" $true "$resolvedRepo"
} catch {
    Check "Repository" $false "Not found: $RepoPath"
}

if ($resolvedRepo) {
    $runScript = Join-Path $resolvedRepo "run-mcp.ps1"
    Check "MCP launcher" (Test-Path $runScript) $runScript

    $venvPython = Join-Path $resolvedRepo ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        try {
            $version = & $venvPython --version 2>&1
            Check "Virtualenv Python" ($LASTEXITCODE -eq 0) "$venvPython ($version)"
        } catch {
            Check "Virtualenv Python" $false "$venvPython is not executable"
        }

        try {
            $importResult = & $venvPython -c "import solidworks_mcp, fastmcp, win32com.client; print('imports ok')" 2>&1
            Check "Python packages" ($LASTEXITCODE -eq 0) ($importResult -join " ")
        } catch {
            Check "Python packages" $false "Could not import solidworks_mcp, fastmcp, and win32com.client"
        }
    } else {
        Check "Virtualenv Python" $false "Missing .venv. Run scripts\Install-SolidWorksMcp.ps1"
    }
}

$codexConfig = Join-Path $workspaceRoot ".codex\config.toml"
$vscodeConfig = Join-Path $workspaceRoot ".vscode\mcp.json"
Check "Codex MCP config" (Test-Path $codexConfig) $codexConfig
Check "VS Code MCP config" (Test-Path $vscodeConfig) $vscodeConfig
if (Test-Path $codexConfig) {
    $codexText = Get-Content -Raw -Path $codexConfig
    Check "Codex real-mode MCP config" (($codexText -match "--real") -and ($codexText -match "solidworks_mcp") -and ($codexText -match [regex]::Escape($SolidWorksYear))) "expects --real SolidWorks $SolidWorksYear"
}
if (Test-Path $vscodeConfig) {
    $vscodeText = Get-Content -Raw -Path $vscodeConfig
    Check "VS Code real-mode MCP config" (($vscodeText -match "--real") -and ($vscodeText -match "solidworks-mcp-server") -and ($vscodeText -match [regex]::Escape($SolidWorksYear))) "expects --real SolidWorks $SolidWorksYear"
}

$codeCommand = Get-Command code -ErrorAction SilentlyContinue
if ($codeCommand) {
    Check-Warn "VS Code command" $true $codeCommand.Source
} else {
    Check-Warn "VS Code command" $false "Install VS Code or enable the 'code' command for automatic workspace opening"
}

$comType = [type]::GetTypeFromProgID("SldWorks.Application")
Check "SolidWorks COM registration" ($null -ne $comType) "ProgID SldWorks.Application"
Check-Warn "SolidWorks part template" (Test-Path $resolvedPartTemplate) $resolvedPartTemplate

$swProcess = Get-Process -Name "SLDWORKS" -ErrorAction SilentlyContinue
Check "SolidWorks process" ($null -ne $swProcess) "Open SolidWorks before starting the MCP server"

if ($ProbeActiveInstance) {
    $venvPython = if ($resolvedRepo) { Join-Path $resolvedRepo ".venv\Scripts\python.exe" } else { $null }
    if ($venvPython -and (Test-Path $venvPython)) {
        try {
            $probe = & $venvPython -c @'
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
'@ 2>&1
            Check "Active COM instance" ($LASTEXITCODE -eq 0) ($probe -join " ")
        } catch {
            Check "Active COM instance" $false "Could not attach through pywin32"
        }
    } else {
        try {
            $active = [Runtime.InteropServices.Marshal]::GetActiveObject("SldWorks.Application")
            $revisionMember = $active.RevisionNumber
            $revision = if ($revisionMember -is [scriptblock]) { $revisionMember.Invoke() } else { $revisionMember }
            Check "Active COM instance" ($null -ne $active) "Revision $revision"
        } catch {
            Check "Active COM instance" $false "Could not attach to a running SolidWorks instance"
        }
    }
}

if ($failed) {
    exit 1
}

exit 0
