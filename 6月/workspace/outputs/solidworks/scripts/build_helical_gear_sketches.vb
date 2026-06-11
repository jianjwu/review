Option Explicit

Const swDocPART As Long = 1

Dim swApp As Object
Dim swModel As Object
Dim firstX As Double
Dim firstY As Double
Dim prevX As Double
Dim prevY As Double
Dim hasPoint As Boolean

Sub main()
    Set swApp = Application.SldWorks
    If swApp Is Nothing Then
        Err.Raise vbObjectError + 100, , "SolidWorks application is not available."
    End If

    Set swModel = swApp.NewDocument("C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2022\templates\gb_part.prtdot", 0, 0, 0)
    If swModel Is Nothing Then
        Err.Raise vbObjectError + 101, , "Failed to create part from SW2022 gb_part.prtdot template."
    End If

    swModel.SetTitle2 "helical_gear_z20_mn1_beta20"
    BuildGearProfileSketch
    BuildSweepPathSketch
    swModel.ForceRebuild3 False
End Sub

Sub BuildGearProfileSketch()
    Dim ok As Boolean
    ok = swModel.Extension.SelectByID2("Front Plane", "PLANE", 0#, 0#, 0#, False, 0, Nothing, 0)
    If Not ok Then
        Err.Raise vbObjectError + 102, , "Could not select Front Plane for gear profile sketch."
    End If

    swModel.SketchManager.InsertSketch True
    NameActiveSketch "Gear_Profile"
    swModel.SketchManager.AddToDB = True

    hasPoint = False

    Dim z As Long
    Dim mn As Double
    Dim alphaN As Double
    Dim beta As Double
    Dim mt As Double
    Dim rp As Double
    Dim ra As Double
    Dim rf As Double
    Dim alphaT As Double
    Dim rb As Double
    Dim pitch As Double
    Dim halfTooth As Double
    Dim tp As Double
    Dim psiP As Double
    Dim ta As Double
    Dim psiA As Double
    Dim flankSegments As Long
    Dim topSegments As Long
    Dim rootSegments As Long
    Dim k As Long
    Dim j As Long
    Dim c As Double
    Dim t As Double
    Dim psi As Double
    Dim radius As Double
    Dim angle As Double
    Dim minusRoot As Double
    Dim plusRoot As Double
    Dim minusTip As Double
    Dim plusTip As Double
    Dim nextMinusRoot As Double

    z = 20
    mn = 1#
    alphaN = DegToRad(20#)
    beta = DegToRad(20#)
    mt = mn / Cos(beta)
    rp = z * mt / 2#
    ra = rp + mn
    rf = rp - 1.25 * mn
    alphaT = Atn(Tan(alphaN) / Cos(beta))
    rb = rp * Cos(alphaT)
    pitch = 2# * Pi() / z
    halfTooth = Pi() / (2# * z)
    tp = Sqr((rp / rb) * (rp / rb) - 1#)
    psiP = tp - Atn(tp)
    ta = Sqr((ra / rb) * (ra / rb) - 1#)
    psiA = ta - Atn(ta)

    flankSegments = 8
    topSegments = 3
    rootSegments = 3

    For k = 0 To z - 1
        c = k * pitch
        minusRoot = c - halfTooth - psiP
        plusRoot = c + halfTooth + psiP
        minusTip = c - halfTooth - psiP + psiA
        plusTip = c + halfTooth + psiP - psiA

        If k = 0 Then
            AddProfilePoint rf * Cos(minusRoot), rf * Sin(minusRoot)
        End If

        AddProfilePoint rb * Cos(minusRoot), rb * Sin(minusRoot)

        For j = 1 To flankSegments
            t = ta * CDbl(j) / CDbl(flankSegments)
            radius = rb * Sqr(1# + t * t)
            psi = t - Atn(t)
            angle = c - halfTooth - psiP + psi
            AddProfilePoint radius * Cos(angle), radius * Sin(angle)
        Next j

        For j = 1 To topSegments
            angle = minusTip + (plusTip - minusTip) * CDbl(j) / CDbl(topSegments)
            AddProfilePoint ra * Cos(angle), ra * Sin(angle)
        Next j

        For j = flankSegments - 1 To 0 Step -1
            t = ta * CDbl(j) / CDbl(flankSegments)
            radius = rb * Sqr(1# + t * t)
            psi = t - Atn(t)
            angle = c + halfTooth + psiP - psi
            AddProfilePoint radius * Cos(angle), radius * Sin(angle)
        Next j

        AddProfilePoint rf * Cos(plusRoot), rf * Sin(plusRoot)

        nextMinusRoot = (k + 1) * pitch - halfTooth - psiP
        For j = 1 To rootSegments
            angle = plusRoot + (nextMinusRoot - plusRoot) * CDbl(j) / CDbl(rootSegments)
            AddProfilePoint rf * Cos(angle), rf * Sin(angle)
        Next j
    Next k

    CloseProfile
    swModel.SketchManager.AddToDB = False
    swModel.SketchManager.InsertSketch True
End Sub

Sub BuildSweepPathSketch()
    Dim ok As Boolean
    ok = swModel.Extension.SelectByID2("Right Plane", "PLANE", 0#, 0#, 0#, False, 0, Nothing, 0)
    If Not ok Then
        Err.Raise vbObjectError + 103, , "Could not select Right Plane for helical sweep path sketch."
    End If

    swModel.SketchManager.InsertSketch True
    NameActiveSketch "Helix_Path"
    swModel.SketchManager.AddToDB = True
    swModel.SketchManager.CreateLine 0#, 0#, 0#, 0#, 0#, MmToM(8#)
    swModel.SketchManager.AddToDB = False
    swModel.SketchManager.InsertSketch True
End Sub

Sub AddProfilePoint(ByVal xMm As Double, ByVal yMm As Double)
    If Not hasPoint Then
        firstX = xMm
        firstY = yMm
        prevX = xMm
        prevY = yMm
        hasPoint = True
    Else
        If DistanceMm(prevX, prevY, xMm, yMm) > 0.000001 Then
            swModel.SketchManager.CreateLine MmToM(prevX), MmToM(prevY), 0#, MmToM(xMm), MmToM(yMm), 0#
            prevX = xMm
            prevY = yMm
        End If
    End If
End Sub

Sub CloseProfile()
    If hasPoint Then
        If DistanceMm(prevX, prevY, firstX, firstY) > 0.000001 Then
            swModel.SketchManager.CreateLine MmToM(prevX), MmToM(prevY), 0#, MmToM(firstX), MmToM(firstY), 0#
        End If
    End If
End Sub

Sub NameActiveSketch(ByVal sketchName As String)
    On Error Resume Next
    Dim swSketch As Object
    Set swSketch = swModel.GetActiveSketch2
    If Not swSketch Is Nothing Then
        swSketch.Name = sketchName
    End If
    On Error GoTo 0
End Sub

Function DistanceMm(ByVal x1 As Double, ByVal y1 As Double, ByVal x2 As Double, ByVal y2 As Double) As Double
    DistanceMm = Sqr((x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1))
End Function

Function MmToM(ByVal valueMm As Double) As Double
    MmToM = valueMm / 1000#
End Function

Function DegToRad(ByVal degrees As Double) As Double
    DegToRad = degrees * Pi() / 180#
End Function

Function Pi() As Double
    Pi = 4# * Atn(1#)
End Function
