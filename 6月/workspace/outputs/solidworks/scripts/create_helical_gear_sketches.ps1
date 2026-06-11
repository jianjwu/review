$ErrorActionPreference = "Stop"

$templatePath = "C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2022\templates\gb_part.prtdot"
$partTitle = "helical_gear_z20_mn1_beta20"

function Get-SolidWorksApplication {
    try {
        return [Runtime.InteropServices.Marshal]::GetActiveObject("SldWorks.Application")
    }
    catch {
        throw "SolidWorks is not running or its COM object is unavailable: $($_.Exception.Message)"
    }
}

function To-Meters([double]$valueMm) {
    return $valueMm / 1000.0
}

function Add-ProfilePoint {
    param(
        [object]$SketchManager,
        [double]$Xmm,
        [double]$Ymm,
        [ref]$State
    )

    if (-not $State.Value.HasPoint) {
        $State.Value.FirstX = $Xmm
        $State.Value.FirstY = $Ymm
        $State.Value.PrevX = $Xmm
        $State.Value.PrevY = $Ymm
        $State.Value.HasPoint = $true
        return
    }

    $dx = $Xmm - $State.Value.PrevX
    $dy = $Ymm - $State.Value.PrevY
    $distance = [Math]::Sqrt($dx * $dx + $dy * $dy)
    if ($distance -le 0.000001) {
        return
    }

    $null = $SketchManager.CreateLine(
        (To-Meters $State.Value.PrevX),
        (To-Meters $State.Value.PrevY),
        0.0,
        (To-Meters $Xmm),
        (To-Meters $Ymm),
        0.0
    )
    $State.Value.PrevX = $Xmm
    $State.Value.PrevY = $Ymm
}

function Close-Profile {
    param(
        [object]$SketchManager,
        [ref]$State
    )

    if (-not $State.Value.HasPoint) {
        throw "No profile points were created."
    }

    $dx = $State.Value.FirstX - $State.Value.PrevX
    $dy = $State.Value.FirstY - $State.Value.PrevY
    $distance = [Math]::Sqrt($dx * $dx + $dy * $dy)
    if ($distance -gt 0.000001) {
        $null = $SketchManager.CreateLine(
            (To-Meters $State.Value.PrevX),
            (To-Meters $State.Value.PrevY),
            0.0,
            (To-Meters $State.Value.FirstX),
            (To-Meters $State.Value.FirstY),
            0.0
        )
    }
}

function Rename-ActiveSketch {
    param(
        [object]$Model,
        [string]$Name
    )

    try {
        $sketch = $Model.GetActiveSketch2()
        if ($null -ne $sketch) {
            $sketch.Name = $Name
        }
    }
    catch {
        Write-Warning "Could not rename active sketch to ${Name}: $($_.Exception.Message)"
    }
}

function Build-GearProfileSketch {
    param([object]$Model)

    $ok = $Model.Extension.SelectByID2("Front Plane", "PLANE", 0.0, 0.0, 0.0, $false, 0, $null, 0)
    if (-not $ok) {
        throw "Could not select Front Plane for gear profile sketch."
    }

    $Model.SketchManager.InsertSketch($true)
    Rename-ActiveSketch -Model $Model -Name "Gear_Profile"
    $Model.SketchManager.AddToDB = $true

    $pi = [Math]::PI
    $z = 20
    $mn = 1.0
    $alphaN = 20.0 * $pi / 180.0
    $beta = 20.0 * $pi / 180.0
    $mt = $mn / [Math]::Cos($beta)
    $rp = $z * $mt / 2.0
    $ra = $rp + $mn
    $rf = $rp - 1.25 * $mn
    $alphaT = [Math]::Atan([Math]::Tan($alphaN) / [Math]::Cos($beta))
    $rb = $rp * [Math]::Cos($alphaT)
    $pitch = 2.0 * $pi / $z
    $halfTooth = $pi / (2.0 * $z)
    $tp = [Math]::Sqrt(($rp / $rb) * ($rp / $rb) - 1.0)
    $psiP = $tp - [Math]::Atan($tp)
    $ta = [Math]::Sqrt(($ra / $rb) * ($ra / $rb) - 1.0)
    $psiA = $ta - [Math]::Atan($ta)
    $flankSegments = 8
    $topSegments = 3
    $rootSegments = 3

    $state = [pscustomobject]@{
        HasPoint = $false
        FirstX = 0.0
        FirstY = 0.0
        PrevX = 0.0
        PrevY = 0.0
    }

    for ($k = 0; $k -lt $z; $k++) {
        $c = $k * $pitch
        $minusRoot = $c - $halfTooth - $psiP
        $plusRoot = $c + $halfTooth + $psiP
        $minusTip = $c - $halfTooth - $psiP + $psiA
        $plusTip = $c + $halfTooth + $psiP - $psiA

        if ($k -eq 0) {
            Add-ProfilePoint -SketchManager $Model.SketchManager -Xmm ($rf * [Math]::Cos($minusRoot)) -Ymm ($rf * [Math]::Sin($minusRoot)) -State ([ref]$state)
        }

        Add-ProfilePoint -SketchManager $Model.SketchManager -Xmm ($rb * [Math]::Cos($minusRoot)) -Ymm ($rb * [Math]::Sin($minusRoot)) -State ([ref]$state)

        for ($j = 1; $j -le $flankSegments; $j++) {
            $t = $ta * [double]$j / [double]$flankSegments
            $radius = $rb * [Math]::Sqrt(1.0 + $t * $t)
            $psi = $t - [Math]::Atan($t)
            $angle = $c - $halfTooth - $psiP + $psi
            Add-ProfilePoint -SketchManager $Model.SketchManager -Xmm ($radius * [Math]::Cos($angle)) -Ymm ($radius * [Math]::Sin($angle)) -State ([ref]$state)
        }

        for ($j = 1; $j -le $topSegments; $j++) {
            $angle = $minusTip + ($plusTip - $minusTip) * [double]$j / [double]$topSegments
            Add-ProfilePoint -SketchManager $Model.SketchManager -Xmm ($ra * [Math]::Cos($angle)) -Ymm ($ra * [Math]::Sin($angle)) -State ([ref]$state)
        }

        for ($j = $flankSegments - 1; $j -ge 0; $j--) {
            $t = $ta * [double]$j / [double]$flankSegments
            $radius = $rb * [Math]::Sqrt(1.0 + $t * $t)
            $psi = $t - [Math]::Atan($t)
            $angle = $c + $halfTooth + $psiP - $psi
            Add-ProfilePoint -SketchManager $Model.SketchManager -Xmm ($radius * [Math]::Cos($angle)) -Ymm ($radius * [Math]::Sin($angle)) -State ([ref]$state)
        }

        Add-ProfilePoint -SketchManager $Model.SketchManager -Xmm ($rf * [Math]::Cos($plusRoot)) -Ymm ($rf * [Math]::Sin($plusRoot)) -State ([ref]$state)

        $nextMinusRoot = ($k + 1) * $pitch - $halfTooth - $psiP
        for ($j = 1; $j -le $rootSegments; $j++) {
            $angle = $plusRoot + ($nextMinusRoot - $plusRoot) * [double]$j / [double]$rootSegments
            Add-ProfilePoint -SketchManager $Model.SketchManager -Xmm ($rf * [Math]::Cos($angle)) -Ymm ($rf * [Math]::Sin($angle)) -State ([ref]$state)
        }
    }

    Close-Profile -SketchManager $Model.SketchManager -State ([ref]$state)
    $Model.SketchManager.AddToDB = $false
    $Model.SketchManager.InsertSketch($true)
}

function Build-SweepPathSketch {
    param([object]$Model)

    $ok = $Model.Extension.SelectByID2("Right Plane", "PLANE", 0.0, 0.0, 0.0, $false, 0, $null, 0)
    if (-not $ok) {
        throw "Could not select Right Plane for helical sweep path sketch."
    }

    $Model.SketchManager.InsertSketch($true)
    Rename-ActiveSketch -Model $Model -Name "Helix_Path"
    $Model.SketchManager.AddToDB = $true
    $null = $Model.SketchManager.CreateLine(0.0, 0.0, 0.0, 0.0, 0.0, (To-Meters 8.0))
    $Model.SketchManager.AddToDB = $false
    $Model.SketchManager.InsertSketch($true)
}

$swApp = Get-SolidWorksApplication
if ($null -eq $swApp) {
    throw "SolidWorks COM application is not available."
}

$swApp.Visible = $true
$model = $swApp.NewDocument($templatePath, 0, 0, 0)
if ($null -eq $model) {
    throw "Failed to create part from template: $templatePath"
}

$model.SetTitle2($partTitle)
Build-GearProfileSketch -Model $model
Build-SweepPathSketch -Model $model
$null = $model.ForceRebuild3($false)

Write-Output "Created SolidWorks part and sketches: Gear_Profile, Helix_Path"
