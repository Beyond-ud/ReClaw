#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
#  proot-setup.sh — Bootstrap proot Linux distro on Android
# ═══════════════════════════════════════════════════════════
#
#  For advanced PicoClaw usage: full Linux package management
#  without requiring root access.
#
#  Run this INSIDE Termux on the target Android device.
#
#  Usage:
#    bash proot-setup.sh           # Install and configure
#    bash proot-setup.sh --enter   # Enter the proot environment
#
#  What this script does:
#    1. Installs proot-distro in Termux
#    2. Installs Alpine Linux (lightweight ~8MB)
#    3. Sets up Python and essential tools inside proot
#    4. Copies PicoClaw binary and skills into proot
#    5. Creates a launch script for easy startup

set -euo pipefail

echo "🐧 PicoClaw proot Setup"
echo "═══════════════════════════════════════"

# ── Step 1: Install proot-distro ──
if ! command -v proot-distro &>/dev/null; then
    echo "📦 Installing proot-distro..."
    pkg update -y
    pkg install -y proot-distro
else
    echo "✅ proot-distro already installed"
fi

# ── Step 2: Install Alpine Linux ──
if ! proot-distro list | grep -q "alpine.*installed"; then
    echo "📦 Installing Alpine Linux..."
    proot-distro install alpine
else
    echo "✅ Alpine Linux already installed"
fi

# ── Step 3: Set up environment inside proot ──
echo "🔧 Configuring proot environment..."

proot-distro login alpine -- sh -c '
    echo "📦 Installing packages..."
    apk update
    apk add python3 py3-pip git curl wget bash jq

    # Create PicoClaw directory structure
    mkdir -p /opt/picoclaw/skills
    mkdir -p /opt/picoclaw/config
    mkdir -p /opt/picoclaw/model

    echo "✅ proot environment configured"
    echo "   Python: $(python3 --version)"
'

# ── Step 4: Copy PicoClaw files into proot ──
PROOT_HOME="$PREFIX/var/lib/proot-distro/installed-rootfs/alpine/opt/picoclaw"

if [ -f "/data/local/tmp/picoclaw-android" ]; then
    echo "📋 Copying PicoClaw binary..."
    cp /data/local/tmp/picoclaw-android "$PROOT_HOME/"
    chmod +x "$PROOT_HOME/picoclaw-android"
fi

if [ -d "/data/local/tmp/skills" ]; then
    echo "📋 Copying skills..."
    cp -r /data/local/tmp/skills/* "$PROOT_HOME/skills/"
fi

if [ -f "/data/local/tmp/picoclaw.json" ]; then
    echo "📋 Copying config..."
    cp /data/local/tmp/picoclaw.json "$PROOT_HOME/config/"
fi

# ── Step 5: Create launch script ──
cat > "$PROOT_HOME/start.sh" << 'LAUNCH_EOF'
#!/bin/bash
# PicoClaw launch script (inside proot)
echo "🦞 Starting PicoClaw (proot mode)..."
cd /opt/picoclaw
./picoclaw-android start \
    --config ./config/picoclaw.json \
    --skills ./skills/
LAUNCH_EOF
chmod +x "$PROOT_HOME/start.sh"

echo ""
echo "═══════════════════════════════════════"
echo "✅ proot setup complete!"
echo ""
echo "To enter the environment:"
echo "  proot-distro login alpine"
echo ""
echo "To start PicoClaw inside proot:"
echo "  proot-distro login alpine -- /opt/picoclaw/start.sh"
echo ""
echo "Benefits of proot mode:"
echo "  • Full Linux filesystem without root"
echo "  • apt/apk package management"
echo "  • Python, Node, and any Linux tool available"
echo "  • Isolated from Android system"
echo "═══════════════════════════════════════"

# Handle --enter flag
if [ "${1:-}" = "--enter" ]; then
    proot-distro login alpine
fi
