# AI 辅助 SolidWorks 建模探索记录

记录时间：2026-06-05 16:50（UTC+08:00）  
项目状态：进行中  
角色定位：硬件实习生，探索 AI 辅助 SolidWorks 建模与工程图生成流程

## 项目简介

本项目用于记录我在硬件实习阶段对 **AI 辅助 SolidWorks 建模** 的探索。当前重点是把 VS Code/Codex、MCP 本地服务、Python/pywin32 和 SolidWorks 2022 COM API 串联起来，让 AI 能够在真实 SolidWorks 环境中执行建模、检查、导出和迭代，而不是停留在文字方案或离线脚本层面。

本仓库当前只上传 README 项目记录，用于后续整理实习经历和简历表述；模型、脚本、截图和导出文件暂时保留在本地工作区，后续会根据需要再脱敏整理。

## 当前已完成工作

1. 搭建了 VS Code Codex 到 SolidWorks 的本地调用链路：
   `Codex in VS Code -> MCP stdio server -> Python/pywin32 -> SolidWorks COM API`。

2. 完成 SolidWorks 2022 真实环境配置：
   - 配置 Codex MCP 启动参数；
   - 配置 VS Code MCP 服务入口；
   - 指定 real mode、SolidWorks 2022 和 GB 零件模板；
   - 验证 SolidWorks COM 注册和运行实例连接。

3. 编写/整理本地自动化辅助脚本：
   - 一键安装与修复 SolidWorks MCP Python 环境；
   - 环境检查脚本，验证虚拟环境、Python 包、COM 注册和 SolidWorks 运行状态；
   - 一键启动脚本，用于启动 SolidWorks、刷新 MCP 配置并打开工作区；
   - 双击启动的 bat 包装脚本，降低日常使用门槛。

4. 建立 AI 建模工作规范：
   - 使用毫米作为默认单位；
   - 按“基准/主实体/二级特征/切除孔位/阵列/倒角圆角”的顺序建模；
   - 每次修改模型后读取 SolidWorks 状态；
   - 图纸建模前先整理尺寸和特征提取表；
   - 对孔位、PCD、方向、切除/凸台等拓扑关键信息不清楚时先确认，不盲猜。

5. 建立 SolidWorks 输出目录结构：
   - `scripts/`：Python、PowerShell、VBA 建模和导出脚本；
   - `models/`：SolidWorks 零件模型；
   - `drawings/`：SolidWorks 工程图；
   - `images/`：模型预览图；
   - `exports/`：PDF、DWG 等评审/交换格式。

6. 完成多类样例模型与导出验证：
   - 直齿轮参数化建模样例；
   - GB 标准工程图生成与 PDF/DWG 导出；
   - 法兰盘类图纸建模样例；
   - 连杆/法兰连接件类图纸建模样例；
   - 斜齿轮建模脚本与预览导出探索。

## 技术栈

- SolidWorks 2022
- SolidWorks COM API
- Python / pywin32
- PowerShell
- VS Code
- Codex
- MCP（Model Context Protocol）
- Git / GitHub

## 项目收获

通过这个阶段的实践，我初步打通了 AI 与真实 CAD 软件之间的工程自动化链路，理解了自然语言建模请求需要先转化为稳定的尺寸、基准、特征顺序和验证步骤。相比单纯手工建模，这个流程更强调可复现、可检查和可迭代，也更适合后续扩展到标准件、图纸重建、工程图自动生成和批量导出场景。

## 后续计划

- 整理更多图纸到模型的案例，并形成尺寸提取模板；
- 增加参数化零件库，例如齿轮、法兰、支架、轴套等；
- 完善建模后自动校验，包括质量属性、关键尺寸、特征树和导出文件检查；
- 将本地样例成果脱敏后分批上传，形成可展示的实习项目作品集；
- 总结为简历项目经历，突出硬件工程、CAD 自动化和 AI 工具链能力。

## 简历表述草稿

硬件实习期间，探索 AI 辅助 SolidWorks 建模流程，搭建 VS Code/Codex、MCP、本地 Python/pywin32 与 SolidWorks 2022 COM API 的调用链路；编写环境安装、启动和检查脚本，建立小步建模、状态回读、图纸尺寸提取和模型导出规范；完成直齿轮、法兰盘、连接件等样例的自动化建模与工程图/PDF/DWG 导出验证。
