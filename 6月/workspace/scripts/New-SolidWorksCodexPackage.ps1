param(
    [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$OutputDirectory = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..")).Path ".generated\packages"),
    [string]$PackageName = ""
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host $Message -ForegroundColor Cyan
}

function Test-ExcludedPath {
    param(
        [string]$RelativePath,
        [bool]$IsDirectory
    )

    $normalized = $RelativePath -replace "\\", "/"

    if (-not $normalized) {
        return $false
    }

    $directoryNames = @(
        ".generated",
        ".rollback_backup",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "htmlcov",
        "build",
        "dist"
    )

    foreach ($name in $directoryNames) {
        if ($normalized -eq $name -or $normalized -like "*/$name" -or $normalized -like "$name/*" -or $normalized -like "*/$name/*") {
            return $true
        }
    }

    $fileNames = @(
        "debug.log"
    )

    foreach ($name in $fileNames) {
        if ($normalized -eq $name -or $normalized -like "*/$name") {
            return $true
        }
    }

    $leaf = Split-Path -Leaf $RelativePath
    if ($leaf -like "~$*") {
        return $true
    }

    $extensions = @(
        ".pyc",
        ".pyo",
        ".log"
    )

    $extension = [System.IO.Path]::GetExtension($leaf)
    if ($extensions -contains $extension) {
        return $true
    }

    return $false
}

function Test-IncludedPath {
    param([string]$RelativePath)

    $normalized = $RelativePath -replace "\\", "/"
    $includeFiles = @(
        ".gitignore",
        "AGENTS.md",
        "Start-SolidWorks-Codex.bat"
    )

    if ($includeFiles -contains $normalized) {
        return $true
    }

    $includeDirectories = @(
        ".codex",
        ".vscode",
        "docs",
        "prompts",
        "scripts",
        "SolidworksMCP-python-main",
        "outputs/solidworks"
    )

    foreach ($directory in $includeDirectories) {
        if ($normalized -like "$directory/*") {
            return $true
        }
    }

    return $false
}

function Get-RelativePath {
    param(
        [string]$BasePath,
        [string]$TargetPath
    )

    $baseFullPath = [System.IO.Path]::GetFullPath($BasePath)
    $targetFullPath = [System.IO.Path]::GetFullPath($TargetPath)

    if (-not $baseFullPath.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $baseFullPath += [System.IO.Path]::DirectorySeparatorChar
    }

    $baseUri = New-Object System.Uri($baseFullPath)
    $targetUri = New-Object System.Uri($targetFullPath)
    $relativeUri = $baseUri.MakeRelativeUri($targetUri)
    return [System.Uri]::UnescapeDataString($relativeUri.ToString()) -replace "/", "\"
}

$resolvedWorkspace = (Resolve-Path $WorkspaceRoot).Path
if (-not $PackageName) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $PackageName = "solidworks-codex-workspace-$stamp.zip"
}

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$zipPath = Join-Path $OutputDirectory $PackageName
if (Test-Path $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

Write-Step "Collecting transfer package files"
$files = Get-ChildItem -LiteralPath $resolvedWorkspace -Recurse -File -Force | Where-Object {
    $relative = Get-RelativePath -BasePath $resolvedWorkspace -TargetPath $_.FullName
    (Test-IncludedPath -RelativePath $relative) -and -not (Test-ExcludedPath -RelativePath $relative -IsDirectory:$false)
}

if (-not $files) {
    throw "No files found to package under $resolvedWorkspace"
}

Write-Host "Workspace: $resolvedWorkspace" -ForegroundColor Green
Write-Host "Files: $($files.Count)" -ForegroundColor Green

Write-Step "Creating package"
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::Open($zipPath, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($file in $files) {
        $relative = Get-RelativePath -BasePath $resolvedWorkspace -TargetPath $file.FullName
        $entryName = $relative -replace "\\", "/"
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $zip,
            $file.FullName,
            $entryName,
            [System.IO.Compression.CompressionLevel]::Optimal
        ) | Out-Null
    }
}
finally {
    $zip.Dispose()
}

Write-Host ""
Write-Host "Created transfer package:" -ForegroundColor Green
Write-Host $zipPath -ForegroundColor Green
Write-Host ""
Write-Host "Target PC setup guide: docs\TRANSFER_TO_OTHER_PC.md" -ForegroundColor Green
