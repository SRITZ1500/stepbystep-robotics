# StepByStep Direct - Quick Start

## 🚀 View the Website NOW

You have 3 options:

### Option 1: Double-Click (Easiest!)
Simply **double-click `index.html`** - it will open in your browser immediately!

### Option 2: Python Server (Full Features)
```bash
python3 serve.py
```
This starts a local server and opens your browser automatically.

### Option 3: Manual Browser Open
Right-click `index.html` → Open With → Your Browser

## ✅ What You'll See

A working demo of StepByStep Direct showing:
- Jesse & The Mechanic storyboard
- 3 sample shots with full details
- Clean, themed interface

## 🎨 Want the Full Interactive Experience?

The full version includes:
- 2 complete sources (Jesse & Changeless)
- 6 direction variants each (funnier, darker, tender, surreal, minimalist, operatic)
- Theme switcher (Flyers, Claude, Amazon)
- Real-time storyboard transformation
- Direction history tracking
- Export to JSON

To get the full version, run:
```bash
python3 serve.py
```

Then the website will load all features from the `src/` directory.

## 🎬 Next Steps

1. **Explore the demo** - Double-click index.html
2. **Try the full version** - Run `python3 serve.py`
3. **Export a storyboard** - Use the export button
4. **Render as video** - Follow README.md for AWS Bedrock setup

## ❓ Troubleshooting

**Blank page?**
- Check browser console (F12) for errors
- Try a different browser (Chrome, Firefox, Safari)
- Use Option 2 (Python server) instead

**Can't see the full features?**
- Make sure you're running `python3 serve.py`
- Check that `src/` directory exists with all files

**Port 8000 in use?**
- Edit `serve.py` and change `PORT = 8000` to `PORT = 8080`

## 📚 More Info

- Full documentation: `README.md`
- Website details: `WEBSITE_INSTRUCTIONS.md`
- Spec documents: `.kiro/specs/stepbystep-direct/`
