#!/usr/bin/env python3
"""
Video Processor Module
Handles S3 download and FFmpeg video stitching
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urlparse

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("ERROR: boto3 not installed. Install with: pip install boto3")
    exit(1)


def check_ffmpeg_installed() -> bool:
    """
    Check if FFmpeg is installed and available
    
    Returns:
        True if FFmpeg is available, False otherwise
    """
    return shutil.which('ffmpeg') is not None


def get_ffmpeg_install_instructions() -> str:
    """
    Get FFmpeg installation instructions for the current platform
    
    Returns:
        Installation instructions string
    """
    import platform
    system = platform.system()
    
    if system == "Darwin":  # macOS
        return """
FFmpeg is not installed. Install with Homebrew:
  brew install ffmpeg

Or download from: https://ffmpeg.org/download.html
"""
    elif system == "Linux":
        return """
FFmpeg is not installed. Install with your package manager:
  Ubuntu/Debian: sudo apt-get install ffmpeg
  Fedora:        sudo dnf install ffmpeg
  Arch:          sudo pacman -S ffmpeg

Or download from: https://ffmpeg.org/download.html
"""
    elif system == "Windows":
        return """
FFmpeg is not installed. Download from:
  https://ffmpeg.org/download.html

Add ffmpeg.exe to your PATH after installation.
"""
    else:
        return """
FFmpeg is not installed. Download from:
  https://ffmpeg.org/download.html
"""


def download_clips(
    completed_jobs: List[Dict],
    output_dir: str,
    profile: Optional[str] = None,
    max_retries: int = 1
) -> List[Dict]:
    """
    Download video clips from S3
    
    Args:
        completed_jobs: List of completed job dicts with s3_output_uri
        output_dir: Local directory to save clips
        profile: AWS profile name (optional)
        max_retries: Number of retries on download failure (default: 1)
        
    Returns:
        List of dicts with shot_id, clip_path, status
    """
    print(f"\n{'='*60}")
    print(f"DOWNLOADING CLIPS")
    print(f"{'='*60}\n")
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Create S3 client
    if profile:
        session = boto3.Session(profile_name=profile)
    else:
        session = boto3.Session()
    
    s3_client = session.client('s3')
    
    downloaded_clips = []
    
    for job in completed_jobs:
        shot_id = job['shot_id']
        
        # Skip failed jobs
        if job['status'] != 'Completed':
            print(f"  ⊘ Shot {shot_id} skipped (status: {job['status']})")
            downloaded_clips.append({
                "shot_id": shot_id,
                "clip_path": None,
                "status": "skipped",
                "error": job.get('error')
            })
            continue
        
        # Parse S3 URI
        s3_uri = job.get('output_uri') or job.get('s3_output_uri')
        if not s3_uri:
            print(f"  ✗ Shot {shot_id} missing S3 URI")
            downloaded_clips.append({
                "shot_id": shot_id,
                "clip_path": None,
                "status": "failed",
                "error": "Missing S3 URI"
            })
            continue
        
        parsed = urlparse(s3_uri)
        bucket = parsed.netloc
        prefix = parsed.path.lstrip('/')
        
        # Try to download with retries
        success = False
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                # List objects in the S3 prefix
                response = s3_client.list_objects_v2(
                    Bucket=bucket,
                    Prefix=prefix
                )
                
                if 'Contents' not in response:
                    raise Exception(f"No files found in {s3_uri}")
                
                # Find .mp4 file
                mp4_files = [obj for obj in response['Contents'] if obj['Key'].endswith('.mp4')]
                
                if not mp4_files:
                    raise Exception(f"No .mp4 file found in {s3_uri}")
                
                # Download the first .mp4 file
                s3_key = mp4_files[0]['Key']
                local_path = os.path.join(output_dir, f"shot_{shot_id:02d}.mp4")
                
                s3_client.download_file(bucket, s3_key, local_path)
                
                print(f"  ✓ Shot {shot_id} downloaded ({os.path.getsize(local_path) / 1024 / 1024:.1f} MB)")
                
                downloaded_clips.append({
                    "shot_id": shot_id,
                    "clip_path": local_path,
                    "status": "success"
                })
                
                success = True
                break
                
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    print(f"  ⚠ Shot {shot_id} download failed (attempt {attempt + 1}/{max_retries + 1}), retrying...")
                else:
                    print(f"  ✗ Shot {shot_id} download failed: {last_error}")
        
        if not success:
            downloaded_clips.append({
                "shot_id": shot_id,
                "clip_path": None,
                "status": "failed",
                "error": last_error
            })
    
    print(f"\n{'='*60}")
    print(f"DOWNLOAD COMPLETE")
    print(f"{'='*60}\n")
    
    success_count = sum(1 for c in downloaded_clips if c['status'] == 'success')
    failed_count = sum(1 for c in downloaded_clips if c['status'] == 'failed')
    skipped_count = sum(1 for c in downloaded_clips if c['status'] == 'skipped')
    
    print(f"Downloaded: {success_count}")
    print(f"Failed:     {failed_count}")
    print(f"Skipped:    {skipped_count}")
    print()
    
    return downloaded_clips


def stitch_clips(
    clips: List[Dict],
    output_path: str,
    trim_durations: Optional[Dict[int, int]] = None
) -> bool:
    """
    Stitch video clips using FFmpeg
    
    Args:
        clips: List of clip dicts with shot_id, clip_path
        output_path: Path for final stitched video
        trim_durations: Optional dict mapping shot_id to duration in seconds
        
    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"STITCHING CLIPS")
    print(f"{'='*60}\n")
    
    # Check FFmpeg
    if not check_ffmpeg_installed():
        print("✗ FFmpeg not found")
        print(get_ffmpeg_install_instructions())
        return False
    
    # Filter successful clips only
    successful_clips = [c for c in clips if c['status'] == 'success' and c['clip_path']]
    
    if not successful_clips:
        print("✗ No clips to stitch")
        return False
    
    # Sort by shot_id
    successful_clips.sort(key=lambda c: c['shot_id'])
    
    print(f"Clips to stitch: {len(successful_clips)}")
    
    # Create temp directory for trimmed clips
    temp_dir = Path(output_path).parent / "temp_trimmed"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    trimmed_paths = []
    
    # Trim clips to exact duration
    for clip in successful_clips:
        shot_id = clip['shot_id']
        clip_path = clip['clip_path']
        
        # Get trim duration if specified
        if trim_durations and shot_id in trim_durations:
            duration = trim_durations[shot_id]
            trimmed_path = temp_dir / f"shot_{shot_id:02d}_trimmed.mp4"
            
            print(f"  Trimming shot {shot_id} to {duration}s...")
            
            # Trim using FFmpeg
            cmd = [
                'ffmpeg',
                '-i', clip_path,
                '-t', str(duration),
                '-c', 'copy',
                '-y',
                str(trimmed_path)
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                trimmed_paths.append(str(trimmed_path))
                print(f"    ✓ Trimmed")
            except subprocess.CalledProcessError as e:
                print(f"    ✗ Trim failed: {e.stderr.decode()}")
                # Use original clip if trim fails
                trimmed_paths.append(clip_path)
        else:
            # No trimming needed
            trimmed_paths.append(clip_path)
    
    # Create concat file
    concat_file = temp_dir / "concat.txt"
    with open(concat_file, 'w') as f:
        for path in trimmed_paths:
            f.write(f"file '{os.path.abspath(path)}'\n")
    
    print(f"\n  Concatenating {len(trimmed_paths)} clips...")
    
    # Concatenate using FFmpeg
    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_file),
        '-c:v', 'libx264',
        '-crf', '18',
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        '-y',
        output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"    ✓ Concatenated")
        
        # Clean up temp directory
        shutil.rmtree(temp_dir)
        
        print(f"\n{'='*60}")
        print(f"STITCH COMPLETE")
        print(f"{'='*60}\n")
        print(f"Output: {output_path}")
        print(f"Size:   {os.path.getsize(output_path) / 1024 / 1024:.1f} MB")
        print()
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"    ✗ Concatenation failed: {e.stderr.decode()}")
        return False


if __name__ == "__main__":
    # Basic test
    print("Video Processor Module")
    print(f"FFmpeg installed: {check_ffmpeg_installed()}")
    
    if not check_ffmpeg_installed():
        print(get_ffmpeg_install_instructions())
