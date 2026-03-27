' Orvix Lite — full path to Python (avoids "Select an app" issues)
Option Explicit

Dim fso, sh, baseDir, scriptPath, exe, cmdl, ec

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
baseDir = fso.GetParentFolderName(WScript.ScriptFullName)
scriptPath = baseDir & "\ORVIX_PRO_v24.py"

If Not fso.FileExists(scriptPath) Then
  MsgBox "Not found:" & vbCrLf & scriptPath, vbCritical, "Orvix Lite"
  WScript.Quit 1
End If

exe = FindPythonExe(fso)
If exe = "" Then
  MsgBox "Python executable not found." & vbCrLf & vbCrLf & _
         "Install from python.org and enable ""Add to PATH""." & vbCrLf & _
         "Or use ORVIX_PRO_v24.bat.", vbExclamation, "Orvix Lite"
  WScript.Quit 1
End If

' Tam yol + arqumentler — birinci soz MUTLəq .exe olsun
If LCase(Right(exe, 6)) = "py.exe" Then
  cmdl = """" & exe & """ -3 """ & scriptPath & """"
Else
  cmdl = """" & exe & """ """ & scriptPath & """"
End If

ec = sh.Run(cmdl, 0, True)
If ec = 0 Then WScript.Quit 0

MsgBox "Program exited with error (code " & ec & ").", vbExclamation, "Orvix Lite"
WScript.Quit ec

Function FindPythonExe(fso)
  Dim la, pf, v, t, cand, paths, i
  la = WshExpand("%LOCALAPPDATA%")
  pf = WshExpand("%ProgramFiles%")

  ' 1) Python Launcher (ən etibarlı)
  cand = la & "\Programs\Python\Launcher\py.exe"
  If fso.FileExists(cand) Then FindPythonExe = cand : Exit Function

  ' 2) pythonw — istifadəçi qovluğu (312, 311, ...)
  For Each v In Array("312", "311", "310", "39", "313")
    cand = la & "\Programs\Python\Python" & v & "\pythonw.exe"
    If fso.FileExists(cand) Then FindPythonExe = cand : Exit Function
  Next

  ' 3) Sizin traceback-dakı kimi C:\Python312\
  For Each v In Array("312", "311", "310")
    cand = "C:\Python" & v & "\pythonw.exe"
    If fso.FileExists(cand) Then FindPythonExe = cand : Exit Function
  Next

  ' 4) Program Files
  For Each v In Array("312", "311", "310")
    cand = pf & "\Python" & v & "\pythonw.exe"
    If fso.FileExists(cand) Then FindPythonExe = cand : Exit Function
  Next

  ' 5) python.exe (konsollu) — son çarə
  For Each v In Array("312", "311", "310")
    cand = "C:\Python" & v & "\python.exe"
    If fso.FileExists(cand) Then FindPythonExe = cand : Exit Function
  Next

  FindPythonExe = ""
End Function

Function WshExpand(s)
  Dim sh2
  Set sh2 = CreateObject("WScript.Shell")
  WshExpand = sh2.ExpandEnvironmentStrings(s)
End Function
