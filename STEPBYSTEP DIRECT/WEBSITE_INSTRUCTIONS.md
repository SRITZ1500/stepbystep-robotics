# StepByStep Direct - Website Instructions

## Quick Start (No Installation Required!)

You have **two options** to view the website:

### Option 1: Simple Python Server (Recommended)

Just run this command in your terminal:

```bash
python3 serve.py
```

This will:
- Start a local web server on port 8000
- Automatically open your browser to the website
- No installation or configuration needed!

Press `Ctrl+C` to stop the server when you're done.

### Option 2: Open Directly in Browser

Simply double-click `website.html` to open it in your default browser.

Note: Some browsers may block loading local files. If you see errors, use Option 1 instead.

## What You'll See

The website includes:

- **Interactive Storyboard Viewer** - Explore two complete screenplay sources
- **Creative Direction Engine** - Transform storyboards with one-word prompts
- **Theme Switcher** - Toggle between Flyers, Claude, and Amazon brand palettes
- **Direction History** - Track your creative transformations
- **Export Functionality** - Download storyboard JSON for rendering

## Available Sources

1. **Jesse & The Mechanic** - Auto shop drama about ignoring warning signs
2. **Changeless** - Coffee shop story about breaking routines

## Available Directions

Each source has 6 creative variants:
- **funnier** - Comedy and absurdity
- **darker** - Tension and consequence
- **tender** - Warmth and connection
- **surreal** - Dreamlike and otherworldly
- **minimalist** - Essential elements only (reduced shots)
- **operatic** - Epic scale and drama (extended duration)

## Exporting for Rendering

1. Select a source (Jesse or Changeless)
2. Apply direction prompts to transform the storyboard
3. Click "Export JSON" button (when implemented)
4. Use the exported JSON with the Python render pipeline:

```bash
cd src/pipeline
python cli.py --storyboard ../../output/storyboard.json --dry-run
```

## Troubleshooting

### Browser Shows Blank Page
- Make sure you're using Option 1 (Python server)
- Check browser console for errors (F12)
- Try a different browser (Chrome, Firefox, Safari)

### Can't Load Storyboard Data
- Ensure you're running from the project root directory
- Check that `src/storyboards/` contains jesse.json and changeless.json

### Port 8000 Already in Use
Edit `serve.py` and change `PORT = 8000` to another port like `8080`

## Next Steps

After exploring the website:
1. Export a storyboard JSON
2. Follow the main README.md to set up the Python render pipeline
3. Render your storyboard as video via AWS Bedrock

## Need Help?

- Check the main README.md for full documentation
- Review the spec documents in `.kiro/specs/stepbystep-direct/`
- Ensure AWS credentials are configured for rendering
