# 涓€閿細鏋勫缓鍓嶇 鈫?PyInstaller 鈫?Inno Setup 瀹夎鍖?
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> 鏋勫缓 React 鍓嶇..." -ForegroundColor Cyan
Push-Location frontend
if (-not (Test-Path node_modules)) { npm install }
npm run build
Pop-Location

Write-Host "==> PyInstaller 鎵撳寘..." -ForegroundColor Cyan
pyinstaller Honsen_CAD_Translator_v1.8.7.spec

$exe = Join-Path $Root "dist\Honsen_CAD_Translator_v1.8.7.exe"
if (-not (Test-Path $exe)) {
    throw "鏈壘鍒?$exe锛孭yInstaller 鎵撳寘澶辫触"
}

$oda = Join-Path $Root "dist\ODAFileConverter\ODAFileConverter.exe"
if (-not (Test-Path $oda)) {
    Write-Warning @"
鏈壘鍒?dist\ODAFileConverter\ODAFileConverter.exe
瀹夎鍖呭皢涓嶅寘鍚?ODA锛岀敤鎴峰彧鑳界炕璇?DXF锛屾垨鑷澶嶅埗 ODA 鍒板畨瑁呯洰褰曘€?

鎵撳寘鍓嶅彲灏?ODA 瑙ｅ帇鍒帮細
  dist\ODAFileConverter\
    ODAFileConverter.exe
    锛堝叏閮?DLL锛?
"@
}

$isccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    throw @"
鏈壘鍒?Inno Setup 6銆傝鍏堝畨瑁咃細
  https://jrsoftware.org/isinfo.php

瀹夎鍚庨噸鏂拌繍琛岋細
  .\installer\build_installer.ps1
"@
}

Write-Host "==> Inno Setup 鐢熸垚瀹夎鍖?.." -ForegroundColor Cyan
& $iscc (Join-Path $Root "installer\Honsen_CAD_Translator_v1.8.7.iss")

$setup = Join-Path $Root "installer_output\Honsen_CAD_Translator_v1.8.7_Setup.exe"
if (Test-Path $setup) {
    Write-Host "瀹屾垚: $setup" -ForegroundColor Green
} else {
    throw "瀹夎鍖呮湭鐢熸垚锛岃妫€鏌?Inno Setup 杈撳嚭"
}

