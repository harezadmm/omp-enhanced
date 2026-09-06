# OMP Enhanced - Windows Installer
$ErrorActionPreference = "Stop"

Write-Host "=== OMP Enhanced Skills Installer ===" -ForegroundColor Cyan

# Detect Hermes profile
$profile = $env:HERMES_PROFILE
if (-not $profile) {
    $profile = "default"
}

$skillsDir = "$HOME\.hermes\profiles\$profile\skills"

Write-Host "Installing to profile: $profile" -ForegroundColor Yellow
Write-Host "Target directory: $skillsDir" -ForegroundColor Yellow

# Create skills directory if not exists
if (-not (Test-Path $skillsDir)) {
    New-Item -ItemType Directory -Path $skillsDir -Force | Out-Null
}

# Clone or update repository
$tempDir = "$env:TEMP\omp-enhanced-$(Get-Random)"
Write-Host "`nCloning repository..." -ForegroundColor Cyan
git clone --depth 1 https://github.com/harezadmm/omp-enhanced.git $tempDir

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to clone repository" -ForegroundColor Red
    exit 1
}

# Copy skills
Write-Host "Copying skills..." -ForegroundColor Cyan
$categories = Get-ChildItem -Path $tempDir -Directory | Where-Object { $_.Name -notmatch '^\.git$' }

foreach ($category in $categories) {
    $destCategory = Join-Path $skillsDir $category.Name
    if (-not (Test-Path $destCategory)) {
        New-Item -ItemType Directory -Path $destCategory -Force | Out-Null
    }
    
    Copy-Item -Path "$($category.FullName)\*" -Destination $destCategory -Recurse -Force
}

# Cleanup
Remove-Item -Path $tempDir -Recurse -Force

Write-Host "`n✓ Installation complete!" -ForegroundColor Green
Write-Host "✓ Installed to: $skillsDir" -ForegroundColor Green
Write-Host "`nUsage:" -ForegroundColor Cyan
Write-Host "  hermes skills list              # List all skills" -ForegroundColor White
Write-Host "  hermes chat                     # Start using skills" -ForegroundColor White
