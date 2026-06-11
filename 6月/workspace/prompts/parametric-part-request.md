# Parametric Part Request Template

Use this prompt in Codex after the SolidWorks MCP server is connected:

```text
Use the SolidWorks MCP server to create a parametric part in small verified steps.

Part: L bracket
Units: mm
Part template: C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2022\templates\gb_part.prtdot
Base dimensions: 100 length x 60 height x 8 thickness
Features: two 6 mm mounting holes, 2 mm external fillets
Material: plain carbon steel
Output folder: outputs/solidworks

Workflow requirements:
- First produce a concise build plan.
- Use one MCP tool call at a time.
- After each mutating operation, inspect model state or export a preview image.
- Save the native SolidWorks part and export STEP plus PNG preview.
- Stop and report the exact failed operation if COM, sketch, rebuild, or export fails.
```
