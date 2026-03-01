#!/usr/bin/env python3
"""
Helper script to render remaining shots one at a time with delays.
Handles AWS throttling for new accounts.
"""

import json
import time
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from pipeline.bedrock_client import BedrockClient
from pipeline.video_processor import download_clips
from pipeline.stepbystep_render import build_shot_list

def render_shot(storyboard_path, shot_index, bucket, quality, output_dir):
    """Render a single shot."""
    
    # Load storyboard
    with open(storyboard_path) as f:
        storyboard = json.load(f)
    
    # Build shot list
    shots = build_shot_list(storyboard)
    
    if shot_index >= len(shots):
        print(f"Shot {shot_index + 1} does not exist (only {len(shots)} shots)")
        return False
    
    shot = shots[shot_index]
    
    print(f"\n{'='*60}")
    print(f"RENDERING SHOT {shot_index + 1}/{len(shots)}")
    print(f"{'='*60}")
    print(f"Prompt: {shot.frame[:80]}...")
    print(f"Duration: {shot.duration}s")
    
    # Build prompt
    from pipeline.stepbystep_render import frame_to_prompt, duration_to_api
    prompt = frame_to_prompt(shot.frame)
    api_duration = duration_to_api(shot.duration)
    
    # Initialize client
    client = BedrockClient(region='us-west-2')
    
    # Submit shot
    try:
        result = client.submit_shot(
            shot_id=shot_index + 1,
            prompt=prompt,
            duration=api_duration,
            resolution=quality,
            bucket=bucket,
            prefix=f"stepbystep/{Path(storyboard_path).stem}/tender/{time.strftime('%Y%m%d_%H%M%S')}"
        )
        arn = result['invocation_arn']
        print(f"✓ Shot {shot_index + 1} submitted (ARN: {arn[:16]}...)")
    except Exception as e:
        print(f"✗ Shot {shot_index + 1} failed: {e}")
        return False
    
    # Poll for completion
    print(f"\nPolling for completion...")
    while True:
        status_result = client.get_invocation_status(arn)
        status = status_result['status']
        
        if status == 'Completed':
            print(f"✓ Shot {shot_index + 1} completed")
            output_uri = status_result['output_uri']
            break
        elif status == 'Failed':
            print(f"✗ Shot {shot_index + 1} failed: {status_result.get('error', 'Unknown error')}")
            return False
        else:
            print(f"  ⋯ Shot {shot_index + 1} in progress...")
            time.sleep(10)
    
    # Download clip
    print(f"\nDownloading clip...")
    output_path = Path(output_dir) / f"shot_{shot_index + 1}.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Parse S3 URI and download
    from urllib.parse import urlparse
    import boto3
    
    parsed = urlparse(output_uri)
    bucket_name = parsed.netloc
    prefix = parsed.path.lstrip('/')
    
    try:
        s3_client = boto3.client('s3', region_name='us-west-2')
        
        # List objects in the S3 prefix
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        
        if 'Contents' not in response:
            raise Exception(f"No files found in {output_uri}")
        
        # Find .mp4 file
        mp4_files = [obj for obj in response['Contents'] if obj['Key'].endswith('.mp4')]
        
        if not mp4_files:
            raise Exception(f"No .mp4 file found in {output_uri}")
        
        # Download the first .mp4 file
        s3_key = mp4_files[0]['Key']
        s3_client.download_file(bucket_name, s3_key, str(output_path))
        
        print(f"✓ Shot {shot_index + 1} downloaded ({output_path.stat().st_size / 1024 / 1024:.1f} MB)")
        return True
    except Exception as e:
        print(f"✗ Download failed: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 render_remaining_shots.py <shot_number>")
        print("Example: python3 render_remaining_shots.py 2")
        sys.exit(1)
    
    shot_index = int(sys.argv[1]) - 1  # Convert to 0-indexed
    
    # Configuration
    storyboard_path = "output_jesse_tender.json"
    bucket = "fishkaa-stepbystep"
    quality = "previz"
    output_dir = "renders/individual_shots"
    
    success = render_shot(storyboard_path, shot_index, bucket, quality, output_dir)
    
    if success:
        print(f"\n{'='*60}")
        print(f"SHOT {shot_index + 1} COMPLETE")
        print(f"{'='*60}")
        print(f"Output: {output_dir}/shot_{shot_index + 1}.mp4")
    else:
        print(f"\n{'='*60}")
        print(f"SHOT {shot_index + 1} FAILED")
        print(f"{'='*60}")
        sys.exit(1)

if __name__ == '__main__':
    main()
