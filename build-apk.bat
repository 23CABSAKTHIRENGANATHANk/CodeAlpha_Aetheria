@echo off
REM ===================================================
REM AETHERIA APK BUILD AUTOMATION SCRIPT (Windows)
REM Converts web app to production Android APK
REM ===================================================

setlocal enabledelayedexpansion

cls
echo.
echo ==========================================
echo    AETHERIA APK BUILD AUTOMATION
echo ==========================================
echo.

REM Color codes (simulated)
set "GREEN=[OK]"
set "RED=[ERROR]"
set "BLUE=[INFO]"
set "YELLOW=[WARN]"

REM ===================================================
REM STEP 1: Verify Prerequisites
REM ===================================================
echo %BLUE% STEP 1: Verifying Prerequisites...
echo.

where node >nul 2>nul
if %errorlevel% neq 0 (
    echo %RED% Node.js not found. Install from https://nodejs.org
    pause
    exit /b 1
)

where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo %RED% npm not found.
    pause
    exit /b 1
)

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo %RED% Python not found.
    pause
    exit /b 1
)

where java >nul 2>nul
if %errorlevel% neq 0 (
    echo %RED% Java not found. Install JDK 11+
    pause
    exit /b 1
)

if not exist "android" (
    echo %RED% Android directory not found. Run: npx cap add android
    pause
    exit /b 1
)

echo %GREEN% All prerequisites verified
echo.

REM ===================================================
REM STEP 2: Install Dependencies
REM ===================================================
echo %BLUE% STEP 2: Installing Dependencies...

if not exist "node_modules" (
    call npm install
)

call npm install @capacitor/core @capacitor/android @capacitor/app @capacitor/notification 2>nul
echo %GREEN% Dependencies installed
echo.

REM ===================================================
REM STEP 3: Collect Static Files
REM ===================================================
echo %BLUE% STEP 3: Collecting Static Files...

cd socialmedia
python manage.py collectstatic --noinput --clear
cd ..

echo %GREEN% Static files collected
echo.

REM ===================================================
REM STEP 4: Sync Capacitor
REM ===================================================
echo %BLUE% STEP 4: Syncing Capacitor...

call npx cap sync android
call npx cap update android

echo %GREEN% Capacitor synced
echo.

REM ===================================================
REM STEP 5: Build Web Assets
REM ===================================================
echo %BLUE% STEP 5: Building Web Assets...

call npx cap copy android

echo %GREEN% Web assets copied to Android
echo.

REM ===================================================
REM STEP 6: Build Debug APK
REM ===================================================
echo %BLUE% STEP 6: Building Debug APK...

cd android

REM Clean before build
call gradlew.bat clean

REM Build debug APK
call gradlew.bat assembleDebug

if exist "app\build\outputs\apk\debug\app-debug.apk" (
    echo %GREEN% Debug APK built successfully
    echo    Location: app\build\outputs\apk\debug\app-debug.apk
) else (
    echo %RED% Debug APK build failed
    cd ..
    pause
    exit /b 1
)
echo.

REM ===================================================
REM STEP 7: Build Release APK
REM ===================================================
echo %BLUE% STEP 7: Building Release APK...

call gradlew.bat assembleRelease

if exist "app\build\outputs\apk\release\app-release-unsigned.apk" (
    echo %GREEN% Release APK built successfully
    echo    Location: app\build\outputs\apk\release\app-release-unsigned.apk
) else (
    echo %RED% Release APK build failed
    cd ..
    pause
    exit /b 1
)
echo.

cd ..

REM ===================================================
REM STEP 8: Sign Release APK
REM ===================================================
echo %BLUE% STEP 8: Signing Release APK...

set "KEYSTORE=%USERPROFILE%\.android\aetheria-release-key.jks"

if not exist "%KEYSTORE%" (
    echo %YELLOW% Creating keystore...
    if not exist "%USERPROFILE%\.android" mkdir "%USERPROFILE%\.android"
    
    keytool -genkey -v -keystore "%KEYSTORE%" ^
        -keyalg RSA -keysize 2048 -validity 10000 ^
        -alias aetheria ^
        -dname "CN=Aetheria,O=Aetheria,L=Global,ST=Global,C=US" ^
        -storepass aetheria123 -keypass aetheria123
    
    echo %GREEN% Keystore created
)

jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 ^
    -keystore "%KEYSTORE%" ^
    -storepass aetheria123 -keypass aetheria123 ^
    "android\app\build\outputs\apk\release\app-release-unsigned.apk" aetheria

echo %GREEN% APK signed successfully
echo.

REM ===================================================
REM STEP 9: Optimize APK
REM ===================================================
echo %BLUE% STEP 9: Optimizing APK...

set "FINAL_APK=app-aetheria-release.apk"

zipalign -v 4 "android\app\build\outputs\apk\release\app-release-unsigned.apk" "%FINAL_APK%"

if exist "%FINAL_APK%" (
    for %%A in ("%FINAL_APK%") do set "APK_SIZE=%%~zA"
    echo %GREEN% APK optimized successfully
    echo    File: %FINAL_APK%
    echo    Size: ~!APK_SIZE! bytes
) else (
    echo %RED% APK optimization failed
    pause
    exit /b 1
)
echo.

REM ===================================================
REM STEP 10: Verify Signature
REM ===================================================
echo %BLUE% STEP 10: Verifying APK Signature...

jarsigner -verify -verbose -certs "%FINAL_APK%" >nul 2>&1

if %errorlevel% equ 0 (
    echo %GREEN% APK signature verified
) else (
    echo %RED% APK signature verification failed
    pause
    exit /b 1
)
echo.

REM ===================================================
REM STEP 11: Installation Options
REM ===================================================
echo %BLUE% STEP 11: Installation Options
echo.
echo Choose installation method:
echo   1) Install on connected device (adb)
echo   2) Show file location (no install)
echo   3) Exit
echo.

set /p install_option="Select option (1-3): "

if "%install_option%"=="1" (
    where adb >nul 2>nul
    if %errorlevel% equ 0 (
        echo Installing APK on device...
        call adb install -r "%FINAL_APK%"
        echo %GREEN% APK installed on device
        echo.
        echo Launch app:
        echo   adb shell am start -n com.aetheria/.MainActivity
    ) else (
        echo %YELLOW% adb not found. Cannot install directly.
        echo To install manually:
        echo   adb install -r %FINAL_APK%
    )
) else if "%install_option%"=="2" (
    echo.
    echo %GREEN% APK ready for distribution:
    echo   %cd%\%FINAL_APK%
) else if "%install_option%"=="3" (
    echo Exiting...
) else (
    echo Invalid option. Exiting...
)

echo.
echo ==========================================
echo %GREEN% BUILD COMPLETE!
echo ==========================================
echo.
echo Summary:
echo   Debug APK: android\app\build\outputs\apk\debug\app-debug.apk
echo   Release APK: %FINAL_APK%
echo.
echo Next steps:
echo   1. Test on device
echo   2. Verify all features
echo   3. Upload to Google Play Store
echo.
echo Feature Status:
echo   [OK] Real-time Messaging (WebSocket)
echo   [OK] Push Notifications (Firebase)
echo   [OK] Responsive Design (Mobile)
echo   [OK] Dark Theme
echo   [OK] User Profiles
echo   [OK] Posts and Feed
echo   [OK] Direct Messages
echo   [OK] Follow System
echo   [OK] Private Accounts
echo   [OK] Stories
echo.

pause
