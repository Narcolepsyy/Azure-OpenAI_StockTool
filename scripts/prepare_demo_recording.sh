#!/bin/bash

# Demo Video Recording Helper Script
# This script prepares your environment for demo recording

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║           🎬 Demo Video Recording Setup Helper 🎬             ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

echo "This script will:"
echo "  1. Start LocalStack"
echo "  2. Deploy Lambda function"
echo "  3. Create CloudWatch dashboard"
echo "  4. Verify all AWS resources"
echo "  5. Prepare terminal for recording"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 1: Starting LocalStack"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if LocalStack is already running
if docker compose ps localstack | grep -q "Up"; then
    print_status "LocalStack is already running"
else
    echo "Starting LocalStack..."
    docker compose up -d localstack
    sleep 10
    print_status "LocalStack started"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 2: Deploying Lambda Function"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "./scripts/deploy_lambda.sh" ]; then
    ./scripts/deploy_lambda.sh
    print_status "Lambda function deployed"
else
    print_error "Lambda deployment script not found"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 3: Creating CloudWatch Dashboard"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "./scripts/create_cloudwatch_dashboard.sh" ]; then
    ./scripts/create_cloudwatch_dashboard.sh
    print_status "CloudWatch dashboard created"
else
    print_error "Dashboard creation script not found"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 4: Verifying AWS Resources"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "./scripts/verify_aws_resources.py" ]; then
    python scripts/verify_aws_resources.py
    print_status "All resources verified"
else
    print_error "Verification script not found"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 5: Recording Environment Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
print_status "Environment is ready for recording!"
echo ""
echo "📋 Pre-Recording Checklist:"
echo ""
echo "Terminal Setup:"
echo "  □ Increase terminal font size (Ctrl + Shift + +)"
echo "  □ Set terminal to 120x30 characters"
echo "  □ Use high-contrast theme (white on black)"
echo "  □ Clear terminal history: clear"
echo ""
echo "Browser Setup:"
echo "  □ Open GitHub repository"
echo "  □ Open docs/AWS_SHOWCASE.md"
echo "  □ Zoom to 125-150% for readability"
echo "  □ Close unnecessary tabs"
echo ""
echo "Recording Software:"
echo "  □ OBS Studio / SimpleScreenRecorder / Kazam installed"
echo "  □ Set resolution: 1920x1080"
echo "  □ Set frame rate: 30 FPS"
echo "  □ Test microphone levels"
echo "  □ Close notifications (Do Not Disturb mode)"
echo ""
echo "Practice:"
echo "  □ Read through docs/DEMO_VIDEO_SCRIPT.md"
echo "  □ Do a dry run without recording"
echo "  □ Time yourself (aim for 2:00 - 2:30)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎬 Commands to run during recording:"
echo ""
echo "1. Show LocalStack status:"
echo "   docker compose ps"
echo ""
echo "2. Check LocalStack health:"
echo "   curl http://localhost:4566/_localstack/health | jq"
echo ""
echo "3. Deploy Lambda (already done, but can re-run):"
echo "   ./scripts/deploy_lambda.sh"
echo ""
echo "4. Test Lambda:"
echo "   python scripts/test_lambda.py"
echo ""
echo "5. List CloudWatch dashboards:"
echo "   aws --endpoint-url=http://localhost:4566 cloudwatch list-dashboards"
echo ""
echo "6. Verify all resources:"
echo "   python scripts/verify_aws_resources.py"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📚 Helpful Resources:"
echo "  • Full script: docs/DEMO_VIDEO_SCRIPT.md"
echo "  • AWS showcase: docs/AWS_SHOWCASE.md"
echo "  • Portfolio roadmap: docs/PORTFOLIO_ROADMAP.md"
echo ""
echo "🎙️ Recording Tips:"
echo "  • Speak clearly and confidently"
echo "  • Don't rush - pause between sentences"
echo "  • Smile while talking (sounds more energetic!)"
echo "  • Re-record sections if needed"
echo "  • Have fun - you're showcasing awesome work! 🚀"
echo ""
echo "Good luck with your recording! 🎬"
echo ""
