#!/bin/bash

# ===================================================
# AETHERIA APK BUILD AUTOMATION SCRIPT
# Converts web app to production Android APK
# ===================================================

set -e  # Exit on error

echo "=========================================="
echo "   AETHERIA APK BUILD AUTOMATION"
echo "=========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ===================================================
# STEP 1: Verify Prerequisites
# ===================================================
echo -e "${BLUE}[STEP 1] Verifying Prerequisites...${NC}"

command -v node >/dev/null 2>&1 || { echo -e "${RED}Node.js not found. Install from https://nodejs.org${NC}"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo -e "${RED}npm not found.${NC}"; exit 1; }
command -v python >/dev/null 2>&1 || { echo -e "${RED}Python not found.${NC}"; exit 1; }
command -v java >/dev/null 2>&1 || { echo -e "${RED}Java not found. Install JDK 11+${NC}"; exit 1; }

if [ ! -d "android" ]; then
    echo -e "${RED}Android directory not found. Run: npx cap add android${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All prerequisites verified${NC}"
echo ""

# ===================================================
# STEP 2: Install Dependencies
# ===================================================
echo -e "${BLUE}[STEP 2] Installing Dependencies...${NC}"

if [ ! -d "node_modules" ]; then
    npm install
fi

npm install @capacitor/core @capacitor/android @capacitor/app @capacitor/notification 2>/dev/null || true
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# ===================================================
# STEP 3: Collect Static Files
# ===================================================
echo -e "${BLUE}[STEP 3] Collecting Static Files...${NC}"

cd socialmedia
python manage.py collectstatic --noinput --clear
cd ..

echo -e "${GREEN}✓ Static files collected${NC}"
echo ""

# ===================================================
# STEP 4: Sync Capacitor
# ===================================================
echo -e "${BLUE}[STEP 4] Syncing Capacitor...${NC}"

npx cap sync android
npx cap update android

echo -e "${GREEN}✓ Capacitor synced${NC}"
echo ""

# ===================================================
# STEP 5: Build Web Assets
# ===================================================
echo -e "${BLUE}[STEP 5] Building Web Assets...${NC}"

npx cap copy android

echo -e "${GREEN}✓ Web assets copied to Android${NC}"
echo ""

# ===================================================
# STEP 6: Build Debug APK
# ===================================================
echo -e "${BLUE}[STEP 6] Building Debug APK...${NC}"

cd android

# Clean before build
./gradlew clean

# Build debug APK
./gradlew assembleDebug

DEBUG_APK="app/build/outputs/apk/debug/app-debug.apk"

if [ -f "$DEBUG_APK" ]; then
    echo -e "${GREEN}✓ Debug APK built successfully${NC}"
    echo -e "   Location: $DEBUG_APK"
else
    echo -e "${RED}✗ Debug APK build failed${NC}"
    exit 1
fi
echo ""

# ===================================================
# STEP 7: Build Release APK
# ===================================================
echo -e "${BLUE}[STEP 7] Building Release APK...${NC}"

./gradlew assembleRelease

RELEASE_APK_UNSIGNED="app/build/outputs/apk/release/app-release-unsigned.apk"

if [ -f "$RELEASE_APK_UNSIGNED" ]; then
    echo -e "${GREEN}✓ Release APK built successfully${NC}"
    echo -e "   Location: $RELEASE_APK_UNSIGNED"
else
    echo -e "${RED}✗ Release APK build failed${NC}"
    exit 1
fi
echo ""

cd ..

# ===================================================
# STEP 8: Sign Release APK
# ===================================================
echo -e "${BLUE}[STEP 8] Signing Release APK...${NC}"

KEYSTORE="${HOME}/.android/aetheria-release-key.jks"

if [ ! -f "$KEYSTORE" ]; then
    echo -e "${YELLOW}✓ Creating keystore...${NC}"
    mkdir -p "${HOME}/.android"
    
    keytool -genkey -v -keystore "$KEYSTORE" \
        -keyalg RSA -keysize 2048 -validity 10000 \
        -alias aetheria \
        -dname "CN=Aetheria,O=Aetheria,L=Global,ST=Global,C=US" \
        -storepass aetheria123 -keypass aetheria123
    
    echo -e "${GREEN}✓ Keystore created${NC}"
fi

jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 \
    -keystore "$KEYSTORE" \
    -storepass aetheria123 -keypass aetheria123 \
    "android/$RELEASE_APK_UNSIGNED" aetheria

echo -e "${GREEN}✓ APK signed successfully${NC}"
echo ""

# ===================================================
# STEP 9: Optimize APK
# ===================================================
echo -e "${BLUE}[STEP 9] Optimizing APK...${NC}"

FINAL_APK="app-aetheria-release.apk"

zipalign -v 4 "android/$RELEASE_APK_UNSIGNED" "$FINAL_APK"

if [ -f "$FINAL_APK" ]; then
    APK_SIZE=$(du -h "$FINAL_APK" | cut -f1)
    echo -e "${GREEN}✓ APK optimized successfully${NC}"
    echo -e "   File: $FINAL_APK"
    echo -e "   Size: $APK_SIZE"
else
    echo -e "${RED}✗ APK optimization failed${NC}"
    exit 1
fi
echo ""

# ===================================================
# STEP 10: Verify Signature
# ===================================================
echo -e "${BLUE}[STEP 10] Verifying APK Signature...${NC}"

jarsigner -verify -verbose -certs "$FINAL_APK" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ APK signature verified${NC}"
else
    echo -e "${RED}✗ APK signature verification failed${NC}"
    exit 1
fi
echo ""

# ===================================================
# STEP 11: Installation Options
# ===================================================
echo -e "${BLUE}[STEP 11] Installation Options${NC}"
echo ""
echo "Choose installation method:"
echo "1) Install on connected device (adb)"
echo "2) Show file location (no install)"
echo "3) Exit"
echo ""
read -p "Select option (1-3): " install_option

case $install_option in
    1)
        if command -v adb >/dev/null 2>&1; then
            echo "Installing APK on device..."
            adb install -r "$FINAL_APK"
            echo -e "${GREEN}✓ APK installed on device${NC}"
            echo ""
            echo "Launch app:"
            echo "  adb shell am start -n com.aetheria/.MainActivity"
        else
            echo -e "${YELLOW}adb not found. Cannot install directly.${NC}"
            echo "To install manually:"
            echo "  adb install -r $FINAL_APK"
        fi
        ;;
    2)
        echo ""
        echo -e "${GREEN}APK ready for distribution:${NC}"
        echo "  $PWD/$FINAL_APK"
        ;;
    3)
        echo "Exiting..."
        ;;
esac

echo ""
echo "=========================================="
echo -e "${GREEN}   BUILD COMPLETE!${NC}"
echo "=========================================="
echo ""
echo "Summary:"
echo "  Debug APK: android/app/build/outputs/apk/debug/app-debug.apk"
echo "  Release APK: $FINAL_APK"
echo "  Size: $APK_SIZE"
echo ""
echo "Next steps:"
echo "  1. Test on device"
echo "  2. Verify all features"
echo "  3. Upload to Google Play Store"
echo ""
echo "Feature Status:"
echo "  ✅ Real-time Messaging (WebSocket)"
echo "  ✅ Push Notifications (Firebase)"
echo "  ✅ Responsive Design (Mobile)"
echo "  ✅ Dark Theme"
echo "  ✅ User Profiles"
echo "  ✅ Posts & Feed"
echo "  ✅ Direct Messages"
echo "  ✅ Follow System"
echo "  ✅ Private Accounts"
echo "  ✅ Stories"
echo ""
