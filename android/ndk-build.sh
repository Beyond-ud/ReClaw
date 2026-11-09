#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
#  ndk-build.sh — Cross-compile PicoClaw for Android ARM64
# ═══════════════════════════════════════════════════════════
#
#  Usage:
#    bash android/ndk-build.sh              # Build with auto-detected NDK
#    ANDROID_NDK=/path/to/ndk bash android/ndk-build.sh  # Custom NDK path
#
#  Prerequisites:
#    - Android NDK r26+ installed
#    - Go 1.22+ installed
#    - Connected Android device (for push/run targets)

set -euo pipefail

# ── Configuration ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PICOCLAW_DIR="$PROJECT_ROOT/picoclaw"
BUILD_DIR="$PICOCLAW_DIR/build"
BINARY_NAME="picoclaw-android"
ANDROID_API="${ANDROID_API:-30}"

# ── Detect NDK ──
if [ -z "${ANDROID_NDK:-}" ]; then
    # Try common NDK locations
    for candidate in \
        "$HOME/Android/Sdk/ndk/"*/  \
        "$HOME/Library/Android/sdk/ndk/"*/ \
        "/usr/local/lib/android/sdk/ndk/"*/ \
    ; do
        if [ -d "$candidate" ]; then
            ANDROID_NDK="$candidate"
            break
        fi
    done
fi

if [ -z "${ANDROID_NDK:-}" ] || [ ! -d "$ANDROID_NDK" ]; then
    echo "❌ Android NDK not found."
    echo "   Set ANDROID_NDK environment variable or install via Android Studio."
    echo "   Download: https://developer.android.com/ndk/downloads"
    exit 1
fi

echo "🦞 PicoClaw NDK Build"
echo "═══════════════════════════════════════"
echo "  NDK:       $ANDROID_NDK"
echo "  API Level: $ANDROID_API"
echo "  Source:    $PICOCLAW_DIR"
echo "  Output:    $BUILD_DIR/$BINARY_NAME"
echo "═══════════════════════════════════════"

# ── Set up toolchain ──
NDK_TOOLCHAIN="$ANDROID_NDK/toolchains/llvm/prebuilt/linux-x86_64"
export CC="$NDK_TOOLCHAIN/bin/aarch64-linux-android${ANDROID_API}-clang"
export CXX="$NDK_TOOLCHAIN/bin/aarch64-linux-android${ANDROID_API}-clang++"
export AR="$NDK_TOOLCHAIN/bin/llvm-ar"

if [ ! -f "$CC" ]; then
    echo "❌ Clang not found at: $CC"
    echo "   Check your NDK installation and API level."
    exit 1
fi

# ── Build ──
echo ""
echo "🔨 Compiling for Android ARM64..."
mkdir -p "$BUILD_DIR"

VERSION=$(git -C "$PROJECT_ROOT" describe --tags --always --dirty 2>/dev/null || echo "dev")

cd "$PICOCLAW_DIR"
CGO_ENABLED=1 \
GOOS=android \
GOARCH=arm64 \
CC="$CC" \
CXX="$CXX" \
AR="$AR" \
go build \
    -ldflags="-s -w -X main.Version=$VERSION" \
    -o "$BUILD_DIR/$BINARY_NAME" \
    ./cmd/picoclaw

echo ""
echo "✅ Build successful!"
echo "   Binary: $BUILD_DIR/$BINARY_NAME"
ls -lh "$BUILD_DIR/$BINARY_NAME"

# ── Optional: push to device ──
if [ "${1:-}" = "--push" ]; then
    echo ""
    echo "📲 Pushing to device..."
    adb push "$BUILD_DIR/$BINARY_NAME" /data/local/tmp/
    adb shell chmod +x "/data/local/tmp/$BINARY_NAME"
    echo "✅ Pushed to /data/local/tmp/$BINARY_NAME"
fi

if [ "${1:-}" = "--run" ]; then
    echo ""
    echo "📲 Pushing and running on device..."
    adb push "$BUILD_DIR/$BINARY_NAME" /data/local/tmp/
    adb shell chmod +x "/data/local/tmp/$BINARY_NAME"
    adb shell "/data/local/tmp/$BINARY_NAME" start \
        --config /data/local/tmp/picoclaw.json \
        --skills /data/local/tmp/skills/
fi
