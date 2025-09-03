set -e

echo "🚀 Starting NewsRagnarok Crawler..."

# Ensure script is executable
chmod +x "$0"

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found. Current directory: $(pwd)"
    ls -la
    exit 1
fi

# Check Python availability
echo "🐍 Checking Python availability..."
if command -v python3 &> /dev/null; then
    echo "✅ Python3 found: $(python3 --version)"
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    echo "✅ Python found: $(python --version)"
    PYTHON_CMD="python"
else
    echo "❌ No Python found. Available commands:"
    which python3 python || echo "No python commands found"
    exit 1
fi

# Install Python dependencies


echo "📦 Installing Python dependencies..."


if [ -f "requirements.txt" ]; then
    echo "📋 Found requirements.txt, installing packages..."
    $PYTHON_CMD -m ensurepip --upgrade
    $PYTHON_CMD -m pip install --upgrade pip
    $PYTHON_CMD -m pip install -r requirements.txt
    echo "✅ Dependencies installed successfully"
else
    echo "⚠️ No requirements.txt found, installing basic packages..."
    $PYTHON_CMD -m ensurepip --upgrade
    $PYTHON_CMD -m pip install --upgrade pip
    $PYTHON_CMD -m pip install pyyaml loguru python-dotenv
    echo "✅ Basic packages installed"
fi

# Install Playwright system dependencies
echo "🌐 Installing Playwright system dependencies..."
$PYTHON_CMD -m playwright install-deps || echo "⚠️ Could not install system dependencies"



# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
$PYTHON_CMD -m playwright install chromium || echo "⚠️ Could not install browsers, will use HTTP fallback"

# Start the main application
echo "🚀 Starting NewsRagnarok Crawler with $PYTHON_CMD..."
exec $PYTHON_CMD main.py