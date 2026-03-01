#!/usr/bin/env python3
"""
StepByStep Direct - CLI Interface
Main command-line interface for the render pipeline
"""

import argparse
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

from stepbystep_render import (
    load_storyboard_json,
    build_shot_list,
    frame_to_prompt,
    duration_to_api,
    find_reference_image,
    encode_reference_image,
    estimate_cost,
    print_cost_estimate,
    confirm_render,
    dry_run_render
)
from bedrock_client import create_bedrock_client
from video_processor import download_clips, stitch_clips


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="StepByStep Direct - Render storyboards as vertical video via AWS Bedrock Luma Ray2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to see prompts and cost
  python cli.py --storyboard output.json --dry-run

  # Render at previz quality (540p)
  python cli.py --storyboard output.json --quality previz --bucket my-bucket

  # Render at full quality (720p) with reference images
  python cli.py --storyboard output.json --quality full --bucket my-bucket --reference-dir ./refs

  # Render without stitching (keep individual clips)
  python cli.py --storyboard output.json --bucket my-bucket --no-stitch
"""
    )
    
    # Required arguments
    parser.add_argument(
        '--storyboard',
        required=True,
        help='Path to storyboard JSON file'
    )
    
    # Optional arguments
    parser.add_argument(
        '--quality',
        choices=['previz', 'full'],
        default='previz',
        help='Render quality: previz (540p, $0.75/s) or full (720p, $1.50/s) [default: previz]'
    )
    
    parser.add_argument(
        '--bucket',
        help='S3 bucket name for output (required for live render)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='./output',
        help='Local directory for downloaded clips [default: ./output]'
    )
    
    parser.add_argument(
        '--output',
        help='Path for final stitched video [default: ./output/final.mp4]'
    )
    
    parser.add_argument(
        '--reference-dir',
        help='Directory containing reference images (shot_01.jpg, shot_02.png, etc.)'
    )
    
    parser.add_argument(
        '--region',
        default='us-west-2',
        help='AWS region [default: us-west-2]'
    )
    
    parser.add_argument(
        '--profile',
        help='AWS profile name'
    )
    
    parser.add_argument(
        '--poll-interval',
        type=int,
        default=10,
        help='Polling interval in seconds [default: 10]'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print prompts and cost without making API calls'
    )
    
    parser.add_argument(
        '--no-stitch',
        action='store_true',
        help='Skip stitching, keep individual clips only'
    )
    
    parser.add_argument(
        '--yes',
        '-y',
        action='store_true',
        help='Skip confirmation prompt'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.dry_run and not args.bucket:
        parser.error("--bucket is required for live render (or use --dry-run)")
    
    # Load storyboard
    print(f"\n{'='*60}")
    print("STEPBYSTEP DIRECT - RENDER PIPELINE")
    print(f"{'='*60}\n")
    
    try:
        storyboard = load_storyboard_json(args.storyboard)
        print(f"✓ Loaded storyboard: {args.storyboard}")
    except Exception as e:
        print(f"✗ Failed to load storyboard: {e}")
        sys.exit(1)
    
    # Extract metadata
    source_name = Path(args.storyboard).stem
    direction_name = storyboard.get('directionHistory', ['baseline'])[-1] if storyboard.get('directionHistory') else 'baseline'
    
    # Build shot list
    try:
        shots = build_shot_list(storyboard)
        print(f"✓ Parsed {len(shots)} shots")
    except Exception as e:
        print(f"✗ Failed to parse shots: {e}")
        sys.exit(1)
    
    # Estimate cost
    estimate = estimate_cost(shots, args.quality)
    print_cost_estimate(estimate, args.quality)
    
    # Dry run mode
    if args.dry_run:
        dry_run_render(
            storyboard=storyboard,
            source_name=source_name,
            direction_name=direction_name,
            resolution=args.quality,
            reference_dir=args.reference_dir
        )
        sys.exit(0)
    
    # Confirm render
    if not args.yes:
        if not confirm_render():
            print("Render cancelled.")
            sys.exit(0)
    
    # Start render
    start_time = time.time()
    
    print(f"\n{'='*60}")
    print("STARTING RENDER")
    print(f"{'='*60}\n")
    
    # Create Bedrock client
    try:
        client = create_bedrock_client(region=args.region, profile=args.profile)
    except Exception as e:
        print(f"✗ Failed to create Bedrock client: {e}")
        sys.exit(1)
    
    # Generate S3 prefix
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    s3_prefix = f"stepbystep/{source_name}/{direction_name}/{timestamp}"
    
    print(f"S3 prefix: s3://{args.bucket}/{s3_prefix}/\n")
    
    # Submit shots
    jobs = []
    for shot in shots:
        try:
            # Generate prompt
            prompt = frame_to_prompt(shot.frame)
            api_duration = duration_to_api(shot.duration)
            
            # Check for reference image
            ref_image_path = find_reference_image(shot.id, args.reference_dir)
            ref_image_b64 = None
            
            if ref_image_path:
                print(f"  Using reference image: {ref_image_path}")
                try:
                    ref_image_b64 = encode_reference_image(ref_image_path)
                except Exception as e:
                    print(f"  ⚠ Failed to encode reference image: {e}")
                    print(f"  Falling back to text-to-video mode")
            
            # Submit shot
            job = client.submit_shot(
                shot_id=shot.id,
                prompt=prompt,
                duration=api_duration,
                resolution=args.quality,
                bucket=args.bucket,
                prefix=s3_prefix,
                reference_image_b64=ref_image_b64
            )
            
            jobs.append(job)
            
        except Exception as e:
            print(f"  ✗ Shot {shot.id} submission failed: {e}")
            # Continue with remaining shots
    
    if not jobs:
        print("\n✗ No shots submitted successfully")
        sys.exit(1)
    
    print(f"\n✓ Submitted {len(jobs)} shots")
    
    # Poll jobs
    completed_jobs = client.poll_jobs(jobs, poll_interval=args.poll_interval)
    
    # Download clips
    output_dir = Path(args.output_dir) / f"{source_name}_{direction_name}_{timestamp}"
    clips = download_clips(
        completed_jobs=completed_jobs,
        output_dir=str(output_dir),
        profile=args.profile
    )
    
    # Stitch clips
    if not args.no_stitch:
        output_path = args.output or str(output_dir / "final.mp4")
        
        # Build trim durations map
        trim_durations = {shot.id: shot.duration for shot in shots}
        
        success = stitch_clips(
            clips=clips,
            output_path=output_path,
            trim_durations=trim_durations
        )
        
        if not success:
            print("⚠ Stitching failed, but individual clips are available")
    
    # Final summary
    end_time = time.time()
    elapsed = end_time - start_time
    
    print(f"\n{'='*60}")
    print("RENDER COMPLETE")
    print(f"{'='*60}\n")
    
    success_count = sum(1 for c in clips if c['status'] == 'success')
    failed_count = sum(1 for c in clips if c['status'] == 'failed')
    
    print(f"Render time:     {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"Clips rendered:  {success_count}/{len(shots)}")
    print(f"Clips failed:    {failed_count}")
    print(f"Output dir:      {output_dir}")
    
    if not args.no_stitch and success_count > 0:
        output_path = args.output or str(output_dir / "final.mp4")
        if Path(output_path).exists():
            print(f"Final video:     {output_path}")
    
    # Calculate actual cost
    actual_duration = sum(shot.duration for shot in shots if any(c['shot_id'] == shot.id and c['status'] == 'success' for c in clips))
    actual_cost = actual_duration * (COST_PREVIZ if args.quality == 'previz' else COST_FULL)
    
    print(f"\nActual cost:     ${actual_cost:.2f}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
