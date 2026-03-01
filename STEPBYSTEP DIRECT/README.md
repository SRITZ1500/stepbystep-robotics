# StepByStep Direct

A creative direction engine that transforms screenplay scenes into production-ready vertical (9:16) short film storyboards, then renders them as video clips via Amazon Bedrock's Luma Ray2 model.

## Overview

StepByStep Direct consists of two main components:

1. **React Frontend Artifact** - Interactive UI for creative direction and storyboard transformation
2. **Python CLI Render Pipeline** - Async video generation via AWS Bedrock Luma Ray2

## Features

- 🎬 **Creative Direction Engine** - Transform storyboards with one-word prompts (darker, funnier, tender, surreal, minimalist, operatic)
- 🎨 **Theme System** - Switch between Flyers, Claude, and Amazon brand palettes
- 📹 **Vertical Video Generation** - Render 9:16 aspect ratio videos optimized for social platforms
- 💰 **Cost Management** - Preview costs before rendering (previz 540p @ $0.75/s, full 720p @ $1.50/s)
- 🔄 **Async Pipeline** - Efficient batch rendering with progress tracking
- 🖼️ **Image-to-Video** - Optional reference images for guided generation

## Quick Start

### Prerequisites

- **Node.js** (for React frontend)
- **Python 3.8+** (for render pipeline)
- **FFmpeg** (for video stitching)
- **AWS Account** with Bedrock access

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd stepbystep-direct
```

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Install FFmpeg**
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

4. **Configure AWS credentials**
```bash
aws configure
# Or use AWS_PROFILE environment variable
```

5. **Enable Bedrock Luma Ray2 model**
- Go to AWS Console → Bedrock → Model access
- Request access to `luma.ray-v2:0` in `us-west-2` region

## Usage

### Website (React Frontend)

The easiest way to use StepByStep Direct is through the web interface:

```bash
# Start the local web server (automatically opens browser)
python3 serve.py
```

Or simply double-click `website.html` to open in your browser.

**Features:**
- Load different screenplay sources (Jesse & The Mechanic, Changeless)
- Apply creative direction prompts
- Switch between brand themes (Flyers, Claude, Amazon)
- View transformed storyboards in real-time
- Export storyboard JSON for rendering

See `WEBSITE_INSTRUCTIONS.md` for detailed website usage.

### Python Render Pipeline

#### Dry Run (No API Calls)

Preview prompts and costs without rendering:

```bash
cd src/pipeline
python cli.py --storyboard ../../output/storyboard.json --dry-run
```

#### Render at Previz Quality (540p)

```bash
python cli.py \
  --storyboard ../../output/storyboard.json \
  --quality previz \
  --bucket my-s3-bucket \
  --output-dir ./renders
```

#### Render at Full Quality (720p)

```bash
python cli.py \
  --storyboard ../../output/storyboard.json \
  --quality full \
  --bucket my-s3-bucket \
  --output-dir ./renders
```

#### Render with Reference Images

```bash
python cli.py \
  --storyboard ../../output/storyboard.json \
  --bucket my-s3-bucket \
  --reference-dir ./reference_images
```

Reference images should be named: `shot_01.jpg`, `shot_02.png`, etc.

#### CLI Options

```
--storyboard PATH       Path to storyboard JSON file (required)
--quality {previz,full} Render quality (default: previz)
--bucket NAME           S3 bucket for output (required for live render)
--output-dir PATH       Local directory for clips (default: ./output)
--output PATH           Path for final video (default: ./output/final.mp4)
--reference-dir PATH    Directory with reference images
--region REGION         AWS region (default: us-west-2)
--profile NAME          AWS profile name
--poll-interval SEC     Polling interval (default: 10)
--dry-run               Preview without API calls
--no-stitch             Keep individual clips, skip stitching
--yes, -y               Skip confirmation prompt
```

## Project Structure

```
stepbystep-direct/
├── src/
│   ├── frontend/
│   │   └── stepbystep-direct.jsx    # React artifact
│   ├── pipeline/
│   │   ├── cli.py                   # Main CLI interface
│   │   ├── stepbystep_render.py     # Core rendering logic
│   │   ├── bedrock_client.py        # AWS Bedrock integration
│   │   └── video_processor.py       # S3 download & FFmpeg stitching
│   ├── shared/
│   │   ├── storyboard_schema.js     # JSON schema definitions
│   │   ├── resolve_direction.js     # Direction resolution logic
│   │   └── themes.js                # Theme color palettes
│   └── storyboards/
│       ├── jesse.json               # Jesse & The Mechanic source
│       └── changeless.json          # Changeless source
├── .kiro/
│   └── specs/
│       └── stepbystep-direct/       # Spec documents
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

## Storyboard Format

Storyboards are JSON files with the following structure:

```json
{
  "concept": "Scene description (50 words max)",
  "shots": [
    {
      "id": 1,
      "frame": "ECU: Visual description",
      "audio": "Sound design description",
      "duration": 5,
      "valueShift": "Emotion A → Emotion B"
    }
  ],
  "invisibleWide": "Broader context description",
  "stormCloud": {
    "detail": "Narrative tension detail",
    "rating": "INVISIBLE | WELL-HIDDEN | TOO OBVIOUS"
  },
  "platform": {
    "length": "Target duration",
    "hook": "Opening hook strategy",
    "loop": "Loop strategy",
    "soundOff": "Sound-off viability"
  },
  "directionHistory": ["darker", "tender"]
}
```

## Creative Directions

Each source includes 6 direction variants:

- **funnier** - Comedy and absurdity
- **darker** - Tension and consequence
- **tender** - Warmth and connection
- **surreal** - Dreamlike and otherworldly
- **minimalist** - Essential elements only (reduced shot count)
- **operatic** - Epic scale and drama (extended durations)

## Cost Estimation

| Quality | Resolution | Cost per Second | 30s Video | 60s Video |
|---------|-----------|----------------|-----------|-----------|
| Previz  | 540p      | $0.75          | $22.50    | $45.00    |
| Full    | 720p      | $1.50          | $45.00    | $90.00    |

## AWS IAM Permissions

Required IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:StartAsyncInvoke",
        "bedrock:GetAsyncInvoke"
      ],
      "Resource": "arn:aws:bedrock:us-west-2::foundation-model/luma.ray-v2:0"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket-name",
        "arn:aws:s3:::your-bucket-name/*"
      ]
    }
  ]
}
```

## Troubleshooting

### FFmpeg Not Found

Install FFmpeg using your package manager:
- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt-get install ffmpeg`
- Windows: Download from https://ffmpeg.org/download.html

### Bedrock Access Denied

1. Go to AWS Console → Bedrock → Model access
2. Request access to `luma.ray-v2:0` model
3. Wait for approval (usually instant for supported regions)

### S3 Permission Errors

Ensure your IAM user/role has `s3:PutObject`, `s3:GetObject`, and `s3:ListBucket` permissions for your bucket.

### Throttling Errors

The pipeline implements exponential backoff for throttling. If you hit limits frequently:
- Increase `--poll-interval` (default: 10s)
- Reduce concurrent renders
- Request quota increase from AWS Support

## Development

### Running Tests

```bash
# Python tests
cd src/pipeline
pytest

# With coverage
pytest --cov=. --cov-report=html
```

### Adding New Sources

1. Create a new JSON file in `src/storyboards/`
2. Follow the storyboard schema
3. Include baseline + 6 direction variants
4. Register in `src/frontend/stepbystep-direct.jsx`

### Adding New Directions

Add direction variants to existing source files:

```json
{
  "directions": {
    "your_direction": {
      "label": "Your Direction",
      "concept": "Transformed concept",
      "shotOverrides": {
        "1": { "frame": "New frame description" }
      }
    }
  }
}
```

## License

[Your License Here]

## Credits

Built with:
- React for frontend
- AWS Bedrock Luma Ray2 for video generation
- FFmpeg for video processing
- boto3 for AWS integration
