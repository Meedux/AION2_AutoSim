<#
Simplified and robust installer for AIONVirtualHID driver (test/dev only).

Features:
- Runs as Admin (exits if not elevated)
- Locates built .sys and associated .inf
- Creates or reuses a temporary test certificate, exports a PFX and installs into
  TrustedPublisher/Root so test-signed drivers are trusted
- Optionally enables test-signing (bcdedit)
- Finds signtool/inf2cat from common Windows Kits locations
- Signs the .sys and (optionally) creates+signs a .cat then runs pnputil
- Attempts to extract the published OEM name and supports uninstall by published name

Usage (Admin PowerShell):
  .\install_driver.ps1 -DriverSysPath ".\AIONVirtualHID\x64\Release\AIONVirtualHID.sys"

NOTE: This is for development and testing only.
#>

param(
    [string]$DriverSysPath,
    [ValidateSet('Debug','Release')]
    [string]$Configuration = 'Release',
    [ValidateSet('x64','ARM64')]
    [string]$Platform = 'x64',
    [switch]$Uninstall,
    [bool]$CreateCatalog = $true,
    [switch]$ForceReboot
)

function Ensure-Admin {
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Error "This script must be run as Administrator"
        exit 1
    }
}

function Find-ToolPath {
    param(
        [string]$ToolName,
        [string[]]$SearchPaths
    )
    # Try Get-Command first
    $cmd = Get-Command $ToolName -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    foreach ($p in $SearchPaths) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

Ensure-Admin

# Resolve .sys path
if (-not $DriverSysPath) {
    $candidates = @(
        Join-Path $PSScriptRoot "AIONVirtualHID\$Platform\$Configuration\AIONVirtualHID.sys",
        Join-Path $PSScriptRoot "AIONVirtualHID\$Platform\$Configuration\AIONVirtualHID.sys"
    )
    $DriverSysPath = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $DriverSysPath) { Write-Error "Driver .sys not found; pass -DriverSysPath or build the driver."; exit 1 }
}

$abs = (Resolve-Path $DriverSysPath).Path
if (-not (Test-Path $abs)) { Write-Error "Driver .sys not found: $abs"; exit 1 }

# Locate INF: prefer same folder as .sys, otherwise search repo
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sysDir = Split-Path -Parent $abs
$infCandidate = Join-Path $sysDir 'AIONVirtualHID.inf'
if (Test-Path $infCandidate) { $inf = $infCandidate } else {
    $found = Get-ChildItem -Path $scriptDir -Filter 'AIONVirtualHID.inf' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) { $inf = $found.FullName } else { Write-Error "AIONVirtualHID.inf not found near .sys or in repo."; exit 1 }
}

$infDir = Split-Path -Parent $inf
Write-Host "Found INF: $inf`nINF folder: $infDir`nDriver SYS: $abs"

# Copy .sys to INF dir if needed
if ($sysDir -ne $infDir) {
    Write-Host "Copying driver to INF folder..."
    $dest = Join-Path $infDir (Split-Path -Leaf $abs)
    Copy-Item -Path $abs -Destination $dest -Force
    $abs = $dest
}

# Test certificate setup
$tsName = 'CN=AIONVirtualHID-Test'
$pfxPath = Join-Path $env:TEMP 'AIONVirtualHID_TestCert.pfx'
$securePw = ConvertTo-SecureString -String 'aiondev' -Force -AsPlainText

$cert = Get-ChildItem Cert:\LocalMachine\My | Where-Object { $_.Subject -eq $tsName } | Select-Object -First 1
if (-not $cert) {
    Write-Host "Creating test certificate ($tsName)"
    $cert = New-SelfSignedCertificate -CertStoreLocation Cert:\LocalMachine\My -Subject $tsName -KeyExportPolicy Exportable -KeyLength 2048 -KeySpec Signature -NotAfter (Get-Date).AddYears(5)
} else { Write-Host "Re-using existing certificate: $($cert.Thumbprint)" }

Export-PfxCertificate -Cert "Cert:\LocalMachine\My\$($cert.Thumbprint)" -FilePath $pfxPath -Password $securePw -Force | Out-Null
Import-PfxCertificate -FilePath $pfxPath -CertStoreLocation Cert:\LocalMachine\TrustedPublisher -Password $securePw | Out-Null
Import-PfxCertificate -FilePath $pfxPath -CertStoreLocation Cert:\LocalMachine\Root -Password $securePw | Out-Null

Write-Host "(Test-signing may require reboot to take effect; use -ForceReboot to reboot automatically)"
Start-Process -FilePath bcdedit -ArgumentList '/set','testsigning','on' -NoNewWindow -Wait

# Discover tools
$programFilesX86 = [Environment]::GetEnvironmentVariable('ProgramFiles(x86)')
$versions = @('10.0.26100.0','10.0.22621.0','10.0.19041.0')

$signtoolPaths = @()
foreach ($v in $versions) { $signtoolPaths += Join-Path $programFilesX86 "Windows Kits\10\bin\$v\$Platform\signtool.exe" }
$signtool = Find-ToolPath -ToolName 'signtool.exe' -SearchPaths $signtoolPaths
if (-not $signtool) { Write-Error "signtool.exe not found. Install Windows SDK or put signtool on PATH."; exit 1 }
Write-Host "Using signtool: $signtool"

$inf2catPaths = @()
foreach ($v in $versions) { $inf2catPaths += Join-Path $programFilesX86 "Windows Kits\10\bin\$v\x64\inf2cat.exe" }
$inf2cat = Find-ToolPath -ToolName 'inf2cat.exe' -SearchPaths $inf2catPaths
if ($CreateCatalog -and -not $inf2cat) { Write-Warning "inf2cat.exe not found; catalog creation will be skipped." }

if ($Uninstall) {
    Write-Host "Uninstall requested: attempting to remove any published driver matching INF: $(Split-Path -Leaf $inf)"
    $enum = & pnputil.exe /enum-drivers 2>&1
    $published = @()
    for ($i=0; $i -lt $enum.Count; $i++) {
        if ($enum[$i] -match 'Published Name\s*:\s*(\S+)') {
            $pub = $Matches[1]
            $orig = $null
            for ($j = $i; $j -lt [Math]::Min($i + 12, $enum.Count); $j++) {
                if ($enum[$j] -match 'Original Name\s*:\s*(\S+)') { $orig = $Matches[1]; break }
            }
            if ($orig -and ($orig -ieq (Split-Path -Leaf $inf) -or $orig -like '*AION*' -or $pub -like '*AION*')) { $published += $pub }
        }
    }
    if ($published.Count -eq 0) { $published = @((Split-Path -Leaf $inf)) }
    $removed = $false
    foreach ($p in $published) {
        Write-Host "Deleting driver package: $p"
        $out = & pnputil.exe /delete-driver $p /uninstall /force 2>&1
        Write-Host $out
        if ($out -match 'deleted' -or $out -match 'Deleted') { $removed = $true }
    }
    if (-not $removed) { Write-Warning "No matching published driver removed. Check pnputil output above." }
    Write-Host "Uninstall finished."; exit 0
}

# Sign the .sys
Write-Host "Signing SYS: $abs"
$signOut = & $signtool sign /fd SHA256 /f $pfxPath /p aiondev $abs 2>&1
Write-Host $signOut
Write-Host "Verifying SYS signature"
$verifyOut = & $signtool verify /kp $abs 2>&1
Write-Host $verifyOut

# Optionally create + sign .cat
if ($CreateCatalog -and $inf2cat) {
    Write-Host "Creating catalog via inf2cat ($inf2cat) in folder: $infDir"
    $inf2catOut = & $inf2cat /driver:$infDir /os:10_X64,11_X64 2>&1
    Write-Host $inf2catOut
    $catName = [IO.Path]::ChangeExtension((Split-Path -Leaf $inf), '.cat')
    $catPath = Join-Path $infDir $catName
    if (Test-Path $catPath) {
        Write-Host "Signing catalog: $catPath"
        $signCat = & $signtool sign /fd SHA256 /f $pfxPath /p aiondev $catPath 2>&1
        Write-Host $signCat
        $verifyCat = & $signtool verify /kp $catPath 2>&1
        Write-Host $verifyCat
    } else { Write-Warning "Expected catalog not found: $catPath" }
}

Write-Host "Running pnputil to add driver: $inf"
$pnputilOut = & pnputil.exe /add-driver $inf /install 2>&1
Write-Host $pnputilOut

# Try to extract Published Name
$published = ($pnputilOut | Select-String -Pattern 'Published Name\s*:\s*(\S+)' | ForEach-Object { $_.Matches[0].Groups[1].Value }) | Select-Object -First 1
if ($published) { Write-Host "Driver published as: $published" } else { Write-Warning "No Published Name reported by pnputil; enumerating driver store for hints:"; & pnputil.exe /enum-drivers | Select-String -Pattern 'AION|AIONVirtualHID' | ForEach-Object { Write-Host $_ } }

Write-Host '--- Post-install checks ---'
& pnputil.exe /enum-drivers | Select-String -Pattern 'AION|AIONVirtualHID' | ForEach-Object { Write-Host $_ }

try { Get-PnpDevice | Where-Object { $_.InstanceId -match 'AION|AIONVirtualHID' } | Format-List } catch { Write-Host 'Get-PnpDevice not available on this system.' }

if ($ForceReboot) { Restart-Computer -Force } else { Write-Host 'Done. Reboot may be required for test-signing to take effect.' }
<#
Automated helper for building & installing the AIONVirtualHID KMDF driver for testing.

Usage (Admin PowerShell):
  .\install_driver.ps1 -DriverSysPath ".\x64\Debug\driver.sys"

This script performs the following (test/dev only):
 - Generates a temporary self-signed test certificate
 - Exports certificate to a PFX and installs it into LocalMachine\TrustedPeople and TrustedPublisher
 - Enables Test Signing mode (bcdedit) so Windows accepts test-signed drivers
 - Uses signtool (from Windows SDK) to sign the driver .sys
 - Installs the INF using pnputil

NOTE: You must run PowerShell as Administrator.
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$DriverSysPath,

    [ValidateSet('Debug','Release')]
    [string]$Configuration = 'Release',

    [ValidateSet('x64','ARM64')]
    [string]$Platform = 'x64',

    [switch]$Uninstall,

    # When true the script will try to create a catalog (.cat) with inf2cat and sign it
    # Many pnputil /add-driver workflows require a signed catalog. Enabled by default to
    # make test installations work with pnputil.
    [bool]$CreateCatalog = $true,

    [switch]$ForceReboot
)

function Ensure-Admin {
    if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Error "This script must be run as Administrator"
        exit 1
    }
}


Ensure-Admin

# Resolve driver .sys path. If not provided, try to auto-discover common build locations.
if (-not $DriverSysPath) {
    $tryPaths = @(
        Join-Path $PSScriptRoot "AIONVirtualHID\$Platform\$Configuration\AIONVirtualHID.sys",
        Join-Path $PSScriptRoot "AIONVirtualHID\$Platform\$Configuration\AIONVirtualHID.sys"
    )
    $found = $tryPaths | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($found) { $DriverSysPath = $found } else {
        Write-Host "Driver path not provided and no default build output found. Please pass -DriverSysPath or build the driver first."; exit 1
    }
}

$abs = (Resolve-Path $DriverSysPath).Path
if (-not (Test-Path $abs)) { Write-Error "Driver .sys not found: $abs"; exit 1 }

# Certificate subject used for test signing
$tsName = "CN=AIONVirtualHID-Test"
Write-Host "(Will use test certificate subject: $tsName)"

$pfxPath = Join-Path $env:TEMP "AIONVirtualHID_TestCert.pfx"
$securePw = ConvertTo-SecureString -String "aiondev" -Force -AsPlainText

# Reuse an existing test cert if present, otherwise create one
$cert = Get-ChildItem Cert:\LocalMachine\My | Where-Object { $_.Subject -eq $tsName } | Select-Object -First 1
if (-not $cert) {
    Write-Host "Creating temporary test certificate ($tsName)..."
    $cert = New-SelfSignedCertificate -CertStoreLocation Cert:\LocalMachine\My -Subject $tsName -KeyExportPolicy Exportable -KeyLength 2048 -KeySpec Signature -NotAfter (Get-Date).AddYears(5)
} else {
    Write-Host "Re-using existing test certificate ($($cert.Thumbprint))"
}

Export-PfxCertificate -Cert "Cert:\LocalMachine\My\$($cert.Thumbprint)" -FilePath $pfxPath -Password $securePw -Force | Out-Null

Write-Host "Installing certificate to TrustedRoot and TrustedPublisher (needed to load test-signed drivers)"
Import-PfxCertificate -FilePath $pfxPath -CertStoreLocation Cert:\LocalMachine\TrustedPublisher -Password $securePw | Out-Null
Import-PfxCertificate -FilePath $pfxPath -CertStoreLocation Cert:\LocalMachine\Root -Password $securePw | Out-Null

Write-Host "Enabling Windows test signing mode (requires reboot)"
Start-Process -FilePath bcdedit -ArgumentList '/set', 'testsigning', 'on' -NoNewWindow -Wait

Write-Host "Locating INF for the driver (searching repository for AIONVirtualHID.inf)..."
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$inf = $null
<#
Simplified and robust installer for AIONVirtualHID driver (test/dev only).

Features:
- Runs as Admin (exits if not elevated)
- Locates built .sys and associated .inf
- Creates or reuses a temporary test certificate, exports a PFX and installs into
  TrustedPublisher/Root so test-signed drivers are trusted
- Optionally enables test-signing (bcdedit)
- Finds signtool/inf2cat from common Windows Kits locations
- Signs the .sys and (optionally) creates+signs a .cat then runs pnputil
- Attempts to extract the published OEM name and supports uninstall by published name

Usage (Admin PowerShell):
  .\install_driver.ps1 -DriverSysPath ".\AIONVirtualHID\x64\Release\AIONVirtualHID.sys"

NOTE: This is for development and testing only.
#>

param(
    [string]$DriverSysPath,
    [ValidateSet('Debug','Release')][string]$Configuration = 'Release',
    [ValidateSet('x64','ARM64')][string]$Platform = 'x64',
    [switch]$Uninstall,
    [bool]$CreateCatalog = $true,
    [switch]$ForceReboot
)

function Ensure-Admin {
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Error "This script must be run as Administrator"
        exit 1
    }
}

function Find-ToolPath {
    param(
        [string]$ToolName,
        [string[]]$SearchPaths
    )
    # Try Get-Command first
    $cmd = Get-Command $ToolName -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    foreach ($p in $SearchPaths) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

Ensure-Admin

# Resolve .sys path
if (-not $DriverSysPath) {
    $candidates = @(
        Join-Path $PSScriptRoot "AIONVirtualHID\$Platform\$Configuration\AIONVirtualHID.sys",
        Join-Path $PSScriptRoot "AIONVirtualHID\$Platform\$Configuration\AIONVirtualHID.sys"
    )
    $DriverSysPath = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $DriverSysPath) { Write-Error "Driver .sys not found; pass -DriverSysPath or build the driver."; exit 1 }
}

$abs = (Resolve-Path $DriverSysPath).Path
if (-not (Test-Path $abs)) { Write-Error "Driver .sys not found: $abs"; exit 1 }

# Locate INF: prefer same folder as .sys, otherwise search repo
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sysDir = Split-Path -Parent $abs
$infCandidate = Join-Path $sysDir 'AIONVirtualHID.inf'
if (Test-Path $infCandidate) { $inf = $infCandidate } else {
    $found = Get-ChildItem -Path $scriptDir -Filter 'AIONVirtualHID.inf' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) { $inf = $found.FullName } else { Write-Error "AIONVirtualHID.inf not found near .sys or in repo."; exit 1 }
}

$infDir = Split-Path -Parent $inf
Write-Host "Found INF: $inf`nINF folder: $infDir`nDriver SYS: $abs"

# Copy .sys to INF dir if needed
if ($sysDir -ne $infDir) {
    Write-Host "Copying driver to INF folder..."
    $dest = Join-Path $infDir (Split-Path -Leaf $abs)
    Copy-Item -Path $abs -Destination $dest -Force
    $abs = $dest
}

# Test certificate setup
$tsName = 'CN=AIONVirtualHID-Test'
$pfxPath = Join-Path $env:TEMP 'AIONVirtualHID_TestCert.pfx'
$securePw = ConvertTo-SecureString -String 'aiondev' -Force -AsPlainText

$cert = Get-ChildItem Cert:\LocalMachine\My | Where-Object { $_.Subject -eq $tsName } | Select-Object -First 1
if (-not $cert) {
    Write-Host "Creating test certificate ($tsName)"
    $cert = New-SelfSignedCertificate -CertStoreLocation Cert:\LocalMachine\My -Subject $tsName -KeyExportPolicy Exportable -KeyLength 2048 -KeySpec Signature -NotAfter (Get-Date).AddYears(5)
} else { Write-Host "Re-using existing certificate: $($cert.Thumbprint)" }

Export-PfxCertificate -Cert "Cert:\LocalMachine\My\$($cert.Thumbprint)" -FilePath $pfxPath -Password $securePw -Force | Out-Null
Import-PfxCertificate -FilePath $pfxPath -CertStoreLocation Cert:\LocalMachine\TrustedPublisher -Password $securePw | Out-Null
Import-PfxCertificate -FilePath $pfxPath -CertStoreLocation Cert:\LocalMachine\Root -Password $securePw | Out-Null

Write-Host "(Test-signing may require reboot to take effect; use -ForceReboot to reboot automatically)"
Start-Process -FilePath bcdedit -ArgumentList '/set','testsigning','on' -NoNewWindow -Wait

# Discover tools
$programFilesX86 = [Environment]::GetEnvironmentVariable('ProgramFiles(x86)')
$versions = @('10.0.26100.0','10.0.22621.0','10.0.19041.0')

$signtoolPaths = @()
foreach ($v in $versions) { $signtoolPaths += Join-Path $programFilesX86 "Windows Kits\10\bin\$v\$Platform\signtool.exe" }
$signtool = Find-ToolPath -ToolName 'signtool.exe' -SearchPaths $signtoolPaths
if (-not $signtool) { Write-Error "signtool.exe not found. Install Windows SDK or put signtool on PATH."; exit 1 }
Write-Host "Using signtool: $signtool"

$inf2catPaths = @()
foreach ($v in $versions) { $inf2catPaths += Join-Path $programFilesX86 "Windows Kits\10\bin\$v\x64\inf2cat.exe" }
$inf2cat = Find-ToolPath -ToolName 'inf2cat.exe' -SearchPaths $inf2catPaths
if ($CreateCatalog -and -not $inf2cat) { Write-Warning "inf2cat.exe not found; catalog creation will be skipped." }

if ($Uninstall) {
    Write-Host "Uninstall requested: attempting to remove any published driver matching INF: $(Split-Path -Leaf $inf)"
    $enum = & pnputil.exe /enum-drivers 2>&1
    $published = @()
    for ($i=0; $i -lt $enum.Count; $i++) {
        if ($enum[$i] -match 'Published Name\s*:\s*(\S+)') {
            $pub = $Matches[1]
            $orig = $null
            for ($j = $i; $j -lt [Math]::Min($i + 12, $enum.Count); $j++) {
                if ($enum[$j] -match 'Original Name\s*:\s*(\S+)') { $orig = $Matches[1]; break }
            }
            if ($orig -and ($orig -ieq (Split-Path -Leaf $inf) -or $orig -like '*AION*' -or $pub -like '*AION*')) { $published += $pub }
        }
    }
    if ($published.Count -eq 0) { $published = @((Split-Path -Leaf $inf)) }
    $removed = $false
    foreach ($p in $published) {
        Write-Host "Deleting driver package: $p"
        $out = & pnputil.exe /delete-driver $p /uninstall /force 2>&1
        Write-Host $out
        if ($out -match 'deleted' -or $out -match 'Deleted') { $removed = $true }
    }
    if (-not $removed) { Write-Warning "No matching published driver removed. Check pnputil output above." }
    Write-Host "Uninstall finished."; exit 0
}

# Sign the .sys
Write-Host "Signing SYS: $abs"
$signOut = & $signtool sign /fd SHA256 /f $pfxPath /p aiondev $abs 2>&1
Write-Host $signOut
Write-Host "Verifying SYS signature"
$verifyOut = & $signtool verify /kp $abs 2>&1
Write-Host $verifyOut

# Optionally create + sign .cat
if ($CreateCatalog -and $inf2cat) {
    Write-Host "Creating catalog via inf2cat ($inf2cat) in folder: $infDir"
    $inf2catOut = & $inf2cat /driver:$infDir /os:10_X64,11_X64 2>&1
    Write-Host $inf2catOut
    $catName = [IO.Path]::ChangeExtension((Split-Path -Leaf $inf), '.cat')
    $catPath = Join-Path $infDir $catName
    if (Test-Path $catPath) {
        Write-Host "Signing catalog: $catPath"
        $signCat = & $signtool sign /fd SHA256 /f $pfxPath /p aiondev $catPath 2>&1
        Write-Host $signCat
        $verifyCat = & $signtool verify /kp $catPath 2>&1
        Write-Host $verifyCat
    } else { Write-Warning "Expected catalog not found: $catPath" }
}

Write-Host "Running pnputil to add driver: $inf"
$pnputilOut = & pnputil.exe /add-driver $inf /install 2>&1
Write-Host $pnputilOut

# Try to extract Published Name
$published = ($pnputilOut | Select-String -Pattern 'Published Name\s*:\s*(\S+)' | ForEach-Object { $_.Matches[0].Groups[1].Value }) | Select-Object -First 1
if ($published) { Write-Host "Driver published as: $published" } else { Write-Warning "No Published Name reported by pnputil; enumerating driver store for hints:"; & pnputil.exe /enum-drivers | Select-String -Pattern 'AION|AIONVirtualHID' | ForEach-Object { Write-Host $_ } }

Write-Host '--- Post-install checks ---'
& pnputil.exe /enum-drivers | Select-String -Pattern 'AION|AIONVirtualHID' | ForEach-Object { Write-Host $_ }

try { Get-PnpDevice | Where-Object { $_.InstanceId -match 'AION|AIONVirtualHID' } | Format-List } catch { Write-Host 'Get-PnpDevice not available on this system.' }

if ($ForceReboot) { Restart-Computer -Force } else { Write-Host 'Done. Reboot may be required for test-signing to take effect.' }
