Option Explicit

Dim shell, fs, appDir, targetPath, folder

If WScript.Arguments.Count <> 2 Then WScript.Quit 1
appDir = LCase(WScript.Arguments(0))
targetPath = WScript.Arguments(1)
Set shell = CreateObject("WScript.Shell")
Set fs = CreateObject("Scripting.FileSystemObject")

For Each folder In Array(shell.SpecialFolders("Desktop"), _
  shell.SpecialFolders("AppData") & "\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar")
  RetargetLegacyLinks folder
Next

Sub RetargetLegacyLinks(folderPath)
  Dim folder, file, link, oldTarget
  If Not fs.FolderExists(folderPath) Then Exit Sub
  Set folder = fs.GetFolder(folderPath)
  For Each file In folder.Files
    If LCase(fs.GetExtensionName(file.Name)) = "lnk" Then
      On Error Resume Next
      Set link = shell.CreateShortcut(file.Path)
      oldTarget = LCase(link.TargetPath)
      If oldTarget Like appDir & "\honsen drawtranslate v*.exe" Or _
         oldTarget Like appDir & "\honsen_cad_translator_v*.exe" Then
        link.TargetPath = targetPath
        link.WorkingDirectory = WScript.Arguments(0)
        link.Save
      End If
      Err.Clear
      On Error GoTo 0
    End If
  Next
End Sub
