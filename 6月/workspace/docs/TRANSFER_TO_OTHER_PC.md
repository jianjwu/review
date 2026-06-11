# SolidWorks + Codex AI modeling workspace transfer guide

This guide explains how to copy this workspace to another Windows PC and make
Codex drive SolidWorks through the local MCP server.

## Architecture

The workspace uses this local chain:

```text
Codex in VS Code -> local MCP stdio server -> Python/pywin32 -> SolidWorks COM API
```

Use native Windows for real CAD work. Do not run real SolidWorks modeling from
WSL, because the MCP server connects to the Windows SolidWorks COM instance.

## Software to install on the target PC

- Windows 10 or 11. Windows 11 is recommended.
- SolidWorks, installed, licensed, and launched once manually.
- VS Code.
- Codex extension for VS Code, signed in with ChatGPT/OpenAI or configured with
  an API key.
- Python 3.11 or newer. Python 3.12 is recommended. Enable
  `Add python.exe to PATH` during installation.
- PowerShell, which is included with Windows.
- Optional: Git, if the workspace will be updated through source control.
- Optional: Internet access for the first `pip install` and for Codex model
  access.

Node.js is not required for the current SolidWorks MCP startup path.

## Files to transfer

Keep these items when copying or packaging the workspace:

- `AGENTS.md`
- `Start-SolidWorks-Codex.bat`
- `scripts/`
- `SolidworksMCP-python-main/`
- `.codex/`
- `.vscode/`
- `docs/`
- `prompts/`
- `outputs/solidworks/`, either with examples or emptied of old generated files

Do not rely on copied absolute paths in `.codex/config.toml` or
`.vscode/mcp.json`. The install/start scripts rewrite those files for the target
PC.

Leave these out of a transfer package:

- `SolidworksMCP-python-main/.venv/`
- `__pycache__/`
- `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
- SolidWorks lock files named like `~$*`
- old generated models, drawings, exports, and preview images that are not
  useful examples

## First-time setup on the target PC

1. Copy the workspace to a native Windows path, for example:

   ```text
   C:\Codex-SolidWorks\workspace
   ```

2. Install and start SolidWorks once. Finish licensing, close startup dialogs,
   and let SolidWorks finish template initialization.

3. If using the default SolidWorks 2022 setup, confirm this template exists:

   ```text
   C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2022\templates\gb_part.prtdot
   ```

4. Open PowerShell in the workspace root and run:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Install-SolidWorksMcp.ps1 -SolidWorksYear 2022
   ```

5. Keep SolidWorks open and run:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Test-SolidWorksMcpEnvironment.ps1 -SolidWorksYear 2022 -ProbeActiveInstance
   ```

6. Start daily work by double-clicking:

   ```text
   Start-SolidWorks-Codex.bat
   ```

If VS Code or Codex was already open, run `Developer: Reload Window` after the
startup script finishes.

## Different SolidWorks versions

The workspace defaults to SolidWorks 2022 and this GB part template:

```text
C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2022\templates\gb_part.prtdot
```

For another version, pass explicit parameters:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Install-SolidWorksMcp.ps1 -SolidWorksYear 2024 -PartTemplate "C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2024\templates\gb_part.prtdot"
```

Then use the same version and template when starting or checking:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-SolidWorksCodex.ps1 -SolidWorksYear 2024 -PartTemplate "C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2024\templates\gb_part.prtdot"
```

Also update `AGENTS.md` if the shared workspace should permanently target that
SolidWorks version.

## Acceptance checks

A healthy environment should show these checks:

- `Native Windows host` is `[OK]`.
- `Virtualenv Python` is `[OK]`.
- `Python packages` is `[OK]`.
- `Codex real-mode MCP config` is `[OK]`.
- `VS Code real-mode MCP config` is `[OK]`.
- `SolidWorks COM registration` is `[OK]`.
- `SolidWorks process` is `[OK]`.
- `Active COM instance` is `[OK]` when `-ProbeActiveInstance` is used.

After that, start a Codex thread in VS Code and ask it to read SolidWorks model
state or create a small test part under `outputs/solidworks/`.

## Packaging command

To create a clean transfer zip from the current workspace:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\New-SolidWorksCodexPackage.ps1
```

The zip is written under `.generated\packages\` and excludes virtual
environments, Python caches, transient generated files, and SolidWorks lock
files.
