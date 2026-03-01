#!/bin/bash
# Render all remaining shots with delays to avoid throttling

echo "Starting batch render of shots 2-6..."
echo "This will take 1.5-4.5 hours total"
echo ""

# Shot 2
echo "=== SHOT 2 ==="
python3 render_remaining_shots.py 2
if [ $? -ne 0 ]; then
    echo "Shot 2 failed, stopping"
    exit 1
fi
echo "Shot 2 complete, waiting 60s before Shot 3..."
sleep 60

# Shot 3
echo "=== SHOT 3 ==="
python3 render_remaining_shots.py 3
if [ $? -ne 0 ]; then
    echo "Shot 3 failed, stopping"
    exit 1
fi
echo "Shot 3 complete, waiting 60s before Shot 4..."
sleep 60

# Shot 4
echo "=== SHOT 4 ==="
python3 render_remaining_shots.py 4
if [ $? -ne 0 ]; then
    echo "Shot 4 failed, stopping"
    exit 1
fi
echo "Shot 4 complete, waiting 60s before Shot 5..."
sleep 60

# Shot 5
echo "=== SHOT 5 ==="
python3 render_remaining_shots.py 5
if [ $? -ne 0 ]; then
    echo "Shot 5 failed, stopping"
    exit 1
fi
echo "Shot 5 complete, waiting 60s before Shot 6..."
sleep 60

# Shot 6
echo "=== SHOT 6 ==="
python3 render_remaining_shots.py 6
if [ $? -ne 0 ]; then
    echo "Shot 6 failed, stopping"
    exit 1
fi

echo ""
echo "=== ALL SHOTS COMPLETE ==="
echo "Now stitching final video..."

# Stitch all shots together
python3 -c "
import sys
sys.path.insert(0, 'src')
from pathlib import Path
from pipeline.video_processor import stitch_clips

clips = []
for i in range(1, 7):
    clip_path = f'renders/individual_shots/shot_{i}.mp4'
    if Path(clip_path).exists():
        clips.append({'shot_id': i, 'clip_path': clip_path, 'status': 'success'})

output_path = 'renders/jesse_tender_final.mp4'
Path(output_path).parent.mkdir(parents=True, exist_ok=True)

# Trim durations (all 5s for tender)
trim_durations = {1: 5, 2: 5, 3: 5, 4: 5, 5: 5, 6: 5}

success = stitch_clips(clips, output_path, trim_durations)
if success:
    print(f'\n✓ Final video ready: {output_path}')
else:
    print('\n✗ Stitching failed')
    sys.exit(1)
"

echo ""
echo "=== RENDER COMPLETE ==="
echo "Final video: renders/jesse_tender_final.mp4"
