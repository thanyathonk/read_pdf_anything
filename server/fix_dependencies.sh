#!/bin/bash
# Fix Dependency Conflicts Script

echo "🔧 Fixing Python Dependencies..."

# Step 1: Uninstall conflicting packages
echo "📦 Uninstalling conflicting packages..."
pip uninstall -y huggingface-hub pillow pi-heif pillow-heif

# Step 2: Install correct versions
echo "📦 Installing correct versions..."
pip install "huggingface-hub>=0.34.0,<1.0"
pip install "Pillow>=11.1.0"

# Step 3: Reinstall requirements
echo "📦 Reinstalling requirements.txt..."
pip install -r requirements.txt

echo "✅ Dependencies fixed!"
echo ""
echo "⚠️  Note: If you still see errors, try:"
echo "  pip install --upgrade pip setuptools wheel"
echo "  pip install -r requirements.txt --force-reinstall"
