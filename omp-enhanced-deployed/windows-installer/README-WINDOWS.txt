# OMP-Enhanced Windows Installation Guide

## Quick Install (Recommended)
1. Open CMD or PowerShell as Administrator
2. Navigate to omp-enhanced directory:
   cd path\to\omp-enhanced
3. Run installer:
   windows-installer\install.bat
4. Restart terminal after installation
5. Verify installation:
   java -version
   gradle -v
   hermes --version

## What Gets Installed
- Java JDK 21 → %USERPROFILE%\.omp-enhanced\jdk-21
- Android SDK → %USERPROFILE%\.omp-enhanced\android-sdk
- Gradle 9.7.1 → %USERPROFILE%\.omp-enhanced\gradle-9.7.1
- Environment variables: JAVA_HOME, ANDROID_HOME, PATH

## Manual Installation

### 1. Install Java JDK 21
Download from: https://www.oracle.com/java/technologies/downloads/#java21
- Extract to C:\Program Files\Java\jdk-21
- Set JAVA_HOME environment variable:
  setx JAVA_HOME "C:\Program Files\Java\jdk-21"
- Add to PATH:
  setx PATH "%PATH%;%JAVA_HOME%\bin"

### 2. Install Android SDK
Download command-line tools: https://developer.android.com/studio#command-tools
- Extract to C:\Android\sdk
- Move cmdline-tools to C:\Android\sdk\cmdline-tools\latest
- Set ANDROID_HOME:
  setx ANDROID_HOME "C:\Android\sdk"
- Add to PATH:
  setx PATH "%PATH%;%ANDROID_HOME%\cmdline-tools\latest\bin;%ANDROID_HOME%\platform-tools"

### 3. Install Gradle 9.7.1
Download from: https://services.gradle.org/distributions/gradle-9.7.1-bin.zip
- Extract to C:\Gradle\gradle-9.7.1
- Add to PATH:
  setx PATH "%PATH%;C:\Gradle\gradle-9.7.1\bin"

### 4. Install Hermes Agent
Follow official guide: https://hermes-agent.nousresearch.com/docs/installation

## Troubleshooting

### "Java not found" after installation
- Restart terminal/CMD completely
- Verify JAVA_HOME: echo %JAVA_HOME%
- Verify PATH: echo %PATH% | findstr Java

### "ANDROID_HOME not set"
- Run: setx ANDROID_HOME "%USERPROFILE%\.omp-enhanced\android-sdk"
- Restart terminal

### "Gradle command not found"
- Verify Gradle installed: dir %USERPROFILE%\.omp-enhanced\gradle-9.7.1
- Add to PATH manually:
  setx PATH "%PATH%;%USERPROFILE%\.omp-enhanced\gradle-9.7.1\bin"

### Permission Errors
- Run installer as Administrator
- Or install to user directory without admin privileges

## Requirements
- Windows 10/11
- PowerShell (included by default)
- Internet connection
- ~2GB free disk space

## System Requirements
- OS: Windows 10 (64-bit) or newer
- RAM: 8GB minimum, 16GB recommended
- CPU: Multi-core processor
- Disk: 10GB free space (SDK + tools)

## Next Steps After Installation
1. Restart terminal
2. Verify all tools: java -version && gradle -v && hermes --version
3. Build OMP-Enhanced:
   cd omp-enhanced
   gradle build
4. Run Hermes Agent:
   hermes run

## Support
- GitHub Issues: https://github.com/harezadmm/omp-enhanced/issues
- Telegram: @sisuryaofficialkuu
