# Download and install OpenJDK 17
$jdkUrl = "https://download.java.net/java/GA/jdk17.0.2/dfd4a8d0985749f896bed50d7138ee7f/8/GPL/openjdk-17.0.2_windows-x64_bin.zip"
$jdkZip = "openjdk.zip"
$jdkDir = "jdk-17.0.2"

Write-Host "[INFO] Downloading OpenJDK 17..."
try {
    Invoke-WebRequest -Uri $jdkUrl -OutFile $jdkZip -UseBasicParsing
    Write-Host "[OK] Download complete"
} catch {
    Write-Host "[ERROR] Download failed: $_"
    exit 1
}

Write-Host "[INFO] Extracting JDK..."
try {
    Expand-Archive -Path $jdkZip -DestinationPath "." -Force
    Remove-Item $jdkZip
    Write-Host "[OK] Extraction complete"
} catch {
    Write-Host "[ERROR] Extraction failed: $_"
    exit 1
}

Write-Host "[INFO] Adding to PATH..."
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
$jdkBinPath = (Resolve-Path "$jdkDir\bin").Path

if ($currentPath -notlike "*$jdkBinPath*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$jdkBinPath", "User")
    $env:Path += ";$jdkBinPath"
    Write-Host "[OK] Java added to PATH"
} else {
    Write-Host "[OK] Java already in PATH"
}

Write-Host "[OK] Java installation complete"
