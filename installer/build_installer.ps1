# 一键：构建前端 → PyInstaller → Inno Setup 安装包
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> 构建 React 前端..." -ForegroundColor Cyan
Push-Location frontend
if (-not (Test-Path node_modules)) { npm install }
npm run build
Pop-Location

Write-Host "==> PyInstaller 打包..." -ForegroundColor Cyan
pyinstaller Honsen_CAD_Translator_v5.5.spec

$exe = Join-Path $Root "dist\Honsen_CAD_Translator_v5.5.exe"
if (-not (Test-Path $exe)) {
    throw "未找到 $exe，PyInstaller 打包失败"
}

$oda = Join-Path $Root "dist\ODAFileConverter\ODAFileConverter.exe"
if (-not (Test-Path $oda)) {
    Write-Warning @"
未找到 dist\ODAFileConverter\ODAFileConverter.exe
安装包将不包含 ODA，用户只能翻译 DXF，或自行复制 ODA 到安装目录。

打包前可将 ODA 解压到：
  dist\ODAFileConverter\
    ODAFileConverter.exe
    （全部 DLL）
"@
}

$isccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    throw @"
未找到 Inno Setup 6。请先安装：
  https://jrsoftware.org/isinfo.php

安装后重新运行：
  .\installer\build_installer.ps1
"@
}

Write-Host "==> Inno Setup 生成安装包..." -ForegroundColor Cyan
& $iscc (Join-Path $Root "installer\Honsen_CAD_Translator_v5.5.iss")

$setup = Join-Path $Root "installer_output\Honsen_CAD_Translator_v5.5_Setup.exe"
if (Test-Path $setup) {
    Write-Host "完成: $setup" -ForegroundColor Green
} else {
    throw "安装包未生成，请检查 Inno Setup 输出"
}
