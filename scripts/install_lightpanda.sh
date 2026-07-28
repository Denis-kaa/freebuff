#!/data/data/com.termux/files/usr/bin/bash
# scripts/install_lightpanda.sh
# Install Lightpanda headless browser on Termux + proot-distro Ubuntu (ARM64).
# Usage: bash scripts/install_lightpanda.sh

set -e

FREEBUFF_ROOT="/storage/emulated/0/PROJECTS/workstation/freebuff"
UBUNTU_NAME="${LIGHTPANDA_UBUNTU_DISTRO:-ubuntu***REMOVED***"
LP_BIN="/usr/local/bin/lightpanda"

echo "🐼 Lightpanda installer for Termux ARM64"
echo "========================================"

# 1. Verify Termux environment
if [ -z "$TERMUX_VERSION" ***REMOVED*** && [ ! -d "/data/data/com.termux/files" ***REMOVED***; then
    echo "❌ This script is intended for Termux."
    exit 1
fi

# 2. Install/update proot-distro
echo "📦 Installing proot-distro..."
pkg install -y proot-distro 2>/dev/null || true

# 3. Ensure Ubuntu is installed
if ! proot-distro list 2>/dev/null | grep -q "$UBUNTU_NAME"; then
    echo "️  Installing Ubuntu inside proot-distro..."
    proot-distro install "$UBUNTU_NAME"
else
    echo "✅ Ubuntu distro '$UBUNTU_NAME' already installed."
fi

# 4. Download and install Lightpanda inside proot-distro
echo "️  Downloading Lightpanda aarch64 binary..."
proot-distro login "$UBUNTU_NAME" -- bash -c "
    set -e
    apt-get update
    apt-get install -y curl ca-certificates tar xz-utils

    ARCH=\"aarch64\"
    TMPDIR=\$(mktemp -d)
    cd \\"\$TMPDIR\\"

    # Try the latest nightly release URL; fallback to a fixed pattern.
    URL=\"https://github.com/lightpanda-io/browser/releases/download/nightly/lightpanda-\${ARCH***REMOVED***-linux.tar.gz\"

    echo \\"Downloading from \$URL...\\"
    if ! curl -fsSL --retry 3 -o lightpanda.tar.gz \\"\$URL\\"; then
        echo \\"❌ Failed to download nightly build. Trying latest release...\\"
        # If the nightly tag is missing, use the GitHub latest redirect (best effort)
        URL=\\\"https://github.com/lightpanda-io/browser/releases/latest/download/lightpanda-\${ARCH***REMOVED***-linux.tar.gz\\\"
        curl -fsSL --retry 3 -o lightpanda.tar.gz \\"\$URL\\"
    fi

    echo \\"Extracting...\\"
    tar -xzf lightpanda.tar.gz

    if [ -f lightpanda ***REMOVED***; then
        mv lightpanda /usr/local/bin/lightpanda
    elif [ -f bin/lightpanda ***REMOVED***; then
        mv bin/lightpanda /usr/local/bin/lightpanda
    else
        echo \\"⚠️ Archive contents:\\"
        find . -maxdepth 2 -type f
        echo \\"❌ Could not find lightpanda binary in archive.\\"
        exit 1
    fi

    chmod +x /usr/local/bin/lightpanda
    rm -rf \\"\$TMPDIR\\"
"

# 5. Create a Termux wrapper that delegates to proot-distro
WRAPPER_DIR="$FREEBUFF_ROOT/.tools"
mkdir -p "$WRAPPER_DIR"

cat > "$WRAPPER_DIR/lightpanda" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
# Wrapper: run Lightpanda inside proot-distro Ubuntu
proot-distro login ubuntu -- /usr/local/bin/lightpanda "$@"
EOF
chmod +x "$WRAPPER_DIR/lightpanda"

echo ""
echo "✅ Lightpanda installed."
echo "   Binary inside proot: $LP_BIN"
echo "   Termux wrapper:      $WRAPPER_DIR/lightpanda"
echo ""

# 6. Verify
echo "🔍 Verifying installation..."
if "$WRAPPER_DIR/lightpanda" version 2>/dev/null || "$WRAPPER_DIR/lightpanda" --version 2>/dev/null; then
    echo ""
    echo "🚀 Lightpanda is ready."
    echo "   Add to PATH: export PATH=\"$WRAPPER_DIR:\$PATH\""
else
    echo "⚠️  Lightpanda wrapper exists, but version check failed."
    echo "   Try running manually: $WRAPPER_DIR/lightpanda version"
fi
