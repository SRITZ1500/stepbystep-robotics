#!/bin/bash
# Example render script for StepByStep Direct

# Configuration
STORYBOARD_FILE="output/storyboard.json"
S3_BUCKET="your-bucket-name"
QUALITY="previz"  # or "full"
OUTPUT_DIR="./renders"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=================================================="
echo "StepByStep Direct - Example Render"
echo "=================================================="
echo ""

# Check if storyboard file exists
if [ ! -f "$STORYBOARD_FILE" ]; then
    echo -e "${RED}✗ Storyboard file not found: $STORYBOARD_FILE${NC}"
    echo ""
    echo "Please export a storyboard from the React frontend first."
    exit 1
fi

echo -e "${GREEN}✓ Found storyboard: $STORYBOARD_FILE${NC}"

# Check if FFmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${RED}✗ FFmpeg not found${NC}"
    echo ""
    echo "Install FFmpeg:"
    echo "  macOS:   brew install ffmpeg"
    echo "  Ubuntu:  sudo apt-get install ffmpeg"
    echo "  Windows: Download from https://ffmpeg.org/download.html"
    exit 1
fi

echo -e "${GREEN}✓ FFmpeg installed${NC}"

# Check if boto3 is installed
if ! python3 -c "import boto3" 2>/dev/null; then
    echo -e "${RED}✗ boto3 not installed${NC}"
    echo ""
    echo "Install Python dependencies:"
    echo "  pip install -r requirements.txt"
    exit 1
fi

echo -e "${GREEN}✓ boto3 installed${NC}"
echo ""

# Prompt for S3 bucket if not set
if [ "$S3_BUCKET" = "your-bucket-name" ]; then
    echo -e "${YELLOW}⚠ Please set S3_BUCKET in this script${NC}"
    echo ""
    read -p "Enter S3 bucket name: " S3_BUCKET
    
    if [ -z "$S3_BUCKET" ]; then
        echo -e "${RED}✗ S3 bucket required${NC}"
        exit 1
    fi
fi

echo "Configuration:"
echo "  Storyboard: $STORYBOARD_FILE"
echo "  S3 Bucket:  $S3_BUCKET"
echo "  Quality:    $QUALITY"
echo "  Output:     $OUTPUT_DIR"
echo ""

# Ask for confirmation
read -p "Run dry-run first? [Y/n]: " DRY_RUN

if [ "$DRY_RUN" != "n" ] && [ "$DRY_RUN" != "N" ]; then
    echo ""
    echo "=================================================="
    echo "DRY RUN - No API calls will be made"
    echo "=================================================="
    echo ""
    
    cd src/pipeline
    python3 cli.py \
        --storyboard "../../$STORYBOARD_FILE" \
        --quality "$QUALITY" \
        --dry-run
    
    cd ../..
    
    echo ""
    read -p "Proceed with actual render? [y/N]: " PROCEED
    
    if [ "$PROCEED" != "y" ] && [ "$PROCEED" != "Y" ]; then
        echo "Render cancelled."
        exit 0
    fi
fi

echo ""
echo "=================================================="
echo "STARTING RENDER"
echo "=================================================="
echo ""

cd src/pipeline
python3 cli.py \
    --storyboard "../../$STORYBOARD_FILE" \
    --quality "$QUALITY" \
    --bucket "$S3_BUCKET" \
    --output-dir "../../$OUTPUT_DIR"

cd ../..

echo ""
echo "=================================================="
echo "DONE"
echo "=================================================="
echo ""
echo "Check $OUTPUT_DIR for rendered clips and final video."
