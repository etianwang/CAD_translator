# 涓€閿細鏋勫缓鍓嶇 鈫?PyInstaller 鈫?Inno Setup 瀹夎鍖?
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> 鏋勫缓 React 鍓嶇..." -ForegroundColor Cyan
Push-Location frontend
if (-not (Test-Path node_modules)) { npm install }
npm run build
if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }
Pop-Location

Write-Host "==> PyInstaller 鎵撳寘..." -ForegroundColor Cyan
pyinstaller Honsen_CAD_Translator_v1.11.11.spec
if ($LASTEXITCODE -ne 0) { throw "Main executable build failed" }
pyinstaller HonsenUpdateRunner.spec
if ($LASTEXITCODE -ne 0) { throw "Runner build failed" }

$exe = Join-Path $Root "dist\Honsen DrawTranslate.exe"
if (-not (Test-Path $exe)) {
    throw "鏈壘鍒?$exe锛孭yInstaller 鎵撳寘澶辫触"
}

$runner = Join-Path $Root "dist\HonsenUpdateRunner.exe"
$exeVersion = (Get-Item -LiteralPath $exe).VersionInfo.FileVersion
python (Join-Path $Root "installer\release_check.py") --exe-version $exeVersion --product-version (Get-Item -LiteralPath $exe).VersionInfo.ProductVersion
if ($LASTEXITCODE -ne 0) { throw "Release version check failed" }

if (-not (Test-Path $runner)) {
    throw "未找到 $runner；更新助手打包失败"
}

$oda = Join-Path $Root "dist\ODAFileConverter\ODAFileConverter.exe"
if (-not (Test-Path $oda)) {
    throw "ODAFileConverter.exe is required for a complete release"
}

$isccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$isccCandidates += Get-ItemProperty @(
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
) -ErrorAction SilentlyContinue |
    Where-Object { $_.DisplayName -like "Inno Setup*" -and $_.InstallLocation } |
    ForEach-Object { Join-Path $_.InstallLocation "ISCC.exe" }
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
& $iscc (Join-Path $Root "installer\Honsen_DrawTranslate_Setup.iss")
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed with exit code $LASTEXITCODE" }

$setup = Join-Path $Root "installer\Output\Honsen_DrawTranslate_v1.11.11_Setup.exe"
if (Test-Path $setup) {
    python (Join-Path $Root "installer\release_check.py") --exe-version $exeVersion --product-version (Get-Item -LiteralPath $exe).VersionInfo.ProductVersion --setup-version (Get-Item -LiteralPath $setup).VersionInfo.FileVersion
    if ($LASTEXITCODE -ne 0) { throw "Installer version check failed" }
    $hash = (Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash.ToLowerInvariant()
    [System.IO.File]::WriteAllText(($setup + ".sha256"), "$hash  $([System.IO.Path]::GetFileName($setup))`n", [System.Text.Encoding]::ASCII)
    Write-Host "瀹屾垚: $setup" -ForegroundColor Green
} else {
    throw "瀹夎鍖呮湭鐢熸垚锛岃妫€鏌?Inno Setup 杈撳嚭"
}
