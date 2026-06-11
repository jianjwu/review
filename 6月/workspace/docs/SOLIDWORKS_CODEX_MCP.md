# VS Code Codex + SolidWorks MCP 配置说明

这个 workspace 实现的基础架构是：

```text
VS Code 中的 Codex -> 本地 MCP stdio server -> Python/pywin32 -> SolidWorks COM API
```

复用的 MCP 实现在 `SolidworksMCP-python-main/` 目录中。本 workspace 额外提供了 Codex/VS Code 配置、安装脚本、环境检查脚本，以及适合 AI 辅助建模的分步骤工作流程。

## 已添加内容

- `.codex/config.toml`：项目级 Codex MCP server 配置。
- `.vscode/mcp.json`：VS Code MCP 配置，供能直接读取 VS Code MCP server 的编辑器使用。
- `scripts/Install-SolidWorksMcp.ps1`：创建 `.venv`，安装核心 Python 依赖，并刷新 MCP 配置路径。
- `scripts/Test-SolidWorksMcpEnvironment.ps1`：检查仓库、虚拟环境、Python 包、COM 注册、SolidWorks 运行状态等。
- `scripts/Start-SolidWorksCodex.ps1`：SW2022 + Codex MCP 的日常一键启动与验证脚本。
- `Start-SolidWorks-Codex.bat`：双击运行的启动入口，内部调用上面的 PowerShell 脚本。
- `AGENTS.md`：Codex 持久化工作规则，用于安全、小步、可检查的 CAD 自动化。
- `outputs/solidworks/`：默认输出目录，用于保存生成的零件、截图、工程图和导出文件。

## 日常一键启动

双击：

```text
Start-SolidWorks-Codex.bat
```

或者在 PowerShell 终端中运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-SolidWorksCodex.ps1
```

启动脚本会执行这些操作：

- 为 `--real --year 2022` 刷新 `.codex/config.toml` 和 `.vscode/mcp.json`。
- 如果需要，创建或修复 MCP 的 `.venv`。
- 检查 SW2022 COM 是否已注册。
- 如果 SolidWorks 尚未运行，尝试从已知路径启动 SolidWorks。
- 等待 pywin32 能够连接到当前活动的 SolidWorks COM 实例。
- 运行最终环境检查。
- 如果系统中可用 `code` 命令，则自动用 VS Code 打开当前 workspace。

如果 VS Code/Codex 已经打开，请在脚本运行完成后执行 `Developer: Reload Window`。

## SolidWorks 电脑首次配置

1. 安装 Python 3.11+，或安装带有可用 `Python\bin\python.exe` 的 Python Manager。
2. 安装并授权 SolidWorks 2022，然后手动启动一次，完成许可、模板、启动弹窗等初始化。
3. 在本 workspace 根目录运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Install-SolidWorksMcp.ps1 -SolidWorksYear 2022
```

4. 运行环境检查：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Test-SolidWorksMcpEnvironment.ps1 -ProbeActiveInstance
```

5. 保持 SolidWorks 打开，重启 VS Code/Codex，让 Codex 重新加载项目 MCP 配置。

## 迁移到另一台电脑

如果要把这个 workspace 干净地交给另一台 Windows/SolidWorks 电脑使用，运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\New-SolidWorksCodexPackage.ps1
```

生成的 zip 包会保存在 `.generated\packages\` 下。目标电脑的安装步骤、必备软件清单、SolidWorks 版本说明和验收检查，请看：

```text
docs\TRANSFER_TO_OTHER_PC.md
```

健康的 MCP server 启动日志通常应包含：

- `Platform: Windows`
- `SolidWorks COM interface is available`
- `Registered ... SolidWorks tools`
- `Connected to SolidWorks`
- `Adapter Mode: Real SolidWorks`

## 预期 AI 建模流程

例如用户提出：

> 生成一个 100 x 60 x 8 mm 的 L 形支架，带两个安装孔和 2 mm 圆角。

Codex 应该按以下方式工作：

1. 先写出简短建模计划，包含尺寸、基准面、草图、特征和检查点。
2. 每次只调用一个 MCP 工具。
3. 每次修改模型后，都读取模型状态进行确认。
4. 将图片或 STEP 等结果导出到 `outputs/solidworks/`。
5. 如果遇到重建错误、COM 错误或几何错误，立即停止，并报告具体失败步骤。

## 常见故障

- `python` 打开 Microsoft Store 或运行失败：从 python.org 安装 Python，并关闭 Windows 的 Python 应用执行别名。
- 缺少 `SldWorks.Application` COM ProgID：SolidWorks 未安装、未注册，或当前电脑不是 SolidWorks Windows 主机。
- MCP 以 mock mode 启动：确认配置中包含 `--real --year <year>`。
- 工具返回空白图片或虚假的质量属性：server 没有运行在 real mode。
- COM 已注册但连接失败：先打开 SolidWorks，关闭启动、许可、模板等弹窗，再启动或重启 MCP server。
