#!/usr/bin/env python3
"""
StepByStep Direct - Render Pipeline
Converts storyboard JSON to video clips via Amazon Bedrock's Luma Ray2 model
"""

import json
import os
import re
import time
import base64
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Prompt engineering constants
VERTICAL_PROMPT_PREFIX = (
    "Cinematic vertical 9:16 short film shot. "
    "Shallow depth of field. Film grain. Natural lighting. "
    "No text overlays. No UI elements. "
)

SHOT_TYPE_MAP = {
    "ECU": "Extreme close-up, filling the vertical frame edge to edge. ",
    "CU": "Close-up, face and shoulders filling the vertical frame. ",
    "MCU": "Medium close-up, waist-up in vertical frame. ",
    "MS": "Medium shot, full upper body in vertical frame. ",
    "WS": "Wide shot, full scene in vertical frame. ",
}

# Cost constants (per second of video)
COST_PREVIZ = 0.75  # 540p
COST_FULL = 1.50    # 720p


@dataclass
class Shot:
    """Represents a single shot from the storyboard"""
    id: int
    frame: str
    audio: str
    duration: int
    value_shift: str


@dataclass
class RenderJob:
    """Represents a single render job submitted to Bedrock"""
    shot_id: int
    invocation_arn: str
    s3_output_uri: str
    prompt: str
    duration: int
    status: str = "InProgress"
    error: Optional[str] = None


@dataclass
class CostEstimate:
    """Cost estimation for a render"""
    total_duration: int
    shot_count: int
    previz_cost: float
    full_cost: float


def load_storyboard_json(filepath: str) -> Dict:
    """
    Load storyboard JSON from file
    
    Args:
        filepath: Path to storyboard JSON file
        
    Returns:
        Parsed storyboard dictionary
    """
    with open(filepath, 'r') as f:
        return json.load(f)


def build_shot_list(storyboard: Dict) -> List[Shot]:
    """
    Extract shot list from storyboard JSON
    
    Args:
        storyboard: Storyboard dictionary with 'shots' array
        
    Returns:
        List of Shot objects
        
    Raises:
        ValueError: If storyboard structure is invalid
    """
    if 'shots' not in storyboard:
        raise ValueError("Storyboard missing 'shots' array")
    
    shots = []
    for shot_data in storyboard['shots']:
        # Validate required fields
        required_fields = ['id', 'frame', 'audio', 'duration', 'valueShift']
        for field in required_fields:
            if field not in shot_data:
                raise ValueError(f"Shot missing required field: {field}")
        
        # Validate duration
        if shot_data['duration'] not in [5, 9]:
            raise ValueError(f"Shot {shot_data['id']} has invalid duration: {shot_data['duration']} (must be 5 or 9)")
        
        shots.append(Shot(
            id=shot_data['id'],
            frame=shot_data['frame'],
            audio=shot_data['audio'],
            duration=shot_data['duration'],
            value_shift=shot_data['valueShift']
        ))
    
    # Validate shot count
    if len(shots) < 5 or len(shots) > 8:
        raise ValueError(f"Storyboard must have 5-8 shots, has {len(shots)}")
    
    return shots


def frame_to_prompt(frame_description: str) -> str:
    """
    Convert FRAME description to Luma Ray2-optimized prompt
    
    Args:
        frame_description: Shot FRAME field content
        
    Returns:
        Optimized prompt string (max 500 characters)
    """
    # Detect and strip shot type prefix (ECU:/CU:/MCU:/etc)
    shot_type_hint = ""
    for shot_type, hint in SHOT_TYPE_MAP.items():
        pattern = f"^{shot_type}:\\s*"
        if re.match(pattern, frame_description, re.IGNORECASE):
            shot_type_hint = hint
            frame_description = re.sub(pattern, "", frame_description, flags=re.IGNORECASE)
            break
    
    # Build optimized prompt
    prompt = VERTICAL_PROMPT_PREFIX + shot_type_hint + frame_description
    
    # Truncate to 500 characters
    if len(prompt) > 500:
        prompt = prompt[:497] + "..."
    
    return prompt


def duration_to_api(duration_seconds: int) -> str:
    """
    Convert shot duration to Bedrock API format
    
    Args:
        duration_seconds: Shot duration in seconds (5 or 9)
        
    Returns:
        API duration string ("5s" or "9s")
    """
    if duration_seconds <= 6:
        return "5s"
    else:
        return "9s"


def encode_reference_image(image_path: str) -> str:
    """
    Encode reference image to base64 for image-to-video requests
    
    Args:
        image_path: Path to reference image file
        
    Returns:
        Base64-encoded image string
        
    Raises:
        ValueError: If image format is not supported
    """
    # Validate image format
    ext = Path(image_path).suffix.lower()
    if ext not in ['.jpg', '.jpeg', '.png']:
        raise ValueError(f"Unsupported image format: {ext} (must be .jpg, .jpeg, or .png)")
    
    with open(image_path, 'rb') as f:
        image_data = f.read()
        return base64.b64encode(image_data).decode('utf-8')


def find_reference_image(shot_id: int, reference_dir: Optional[str]) -> Optional[str]:
    """
    Find reference image for a shot
    
    Args:
        shot_id: Shot ID to find image for
        reference_dir: Directory containing reference images
        
    Returns:
        Path to reference image if found, None otherwise
    """
    if not reference_dir:
        return None
    
    ref_dir = Path(reference_dir)
    if not ref_dir.exists():
        return None
    
    # Look for shot_NN.jpg or shot_NN.png
    for ext in ['.jpg', '.jpeg', '.png']:
        image_path = ref_dir / f"shot_{shot_id:02d}{ext}"
        if image_path.exists():
            return str(image_path)
    
    return None


def estimate_cost(shots: List[Shot], resolution: str) -> CostEstimate:
    """
    Calculate render cost estimate
    
    Args:
        shots: List of Shot objects
        resolution: "previz" (540p) or "full" (720p)
        
    Returns:
        CostEstimate object with cost breakdown
    """
    total_duration = sum(shot.duration for shot in shots)
    shot_count = len(shots)
    
    previz_cost = total_duration * COST_PREVIZ
    full_cost = total_duration * COST_FULL
    
    return CostEstimate(
        total_duration=total_duration,
        shot_count=shot_count,
        previz_cost=previz_cost,
        full_cost=full_cost
    )


def print_cost_estimate(estimate: CostEstimate, resolution: str):
    """
    Print cost estimate to console
    
    Args:
        estimate: CostEstimate object
        resolution: Selected resolution mode
    """
    print("\n" + "="*60)
    print("COST ESTIMATE")
    print("="*60)
    print(f"Shot count:      {estimate.shot_count}")
    print(f"Total duration:  {estimate.total_duration}s")
    print(f"\nPreviz (540p):   ${estimate.previz_cost:.2f}")
    print(f"Full (720p):     ${estimate.full_cost:.2f}")
    print(f"\nSelected mode:   {resolution}")
    
    if resolution == "previz":
        print(f"Estimated cost:  ${estimate.previz_cost:.2f}")
    else:
        print(f"Estimated cost:  ${estimate.full_cost:.2f}")
    
    print("="*60 + "\n")


def confirm_render() -> bool:
    """
    Prompt user to confirm render execution
    
    Returns:
        True if user confirms, False otherwise
    """
    response = input("Proceed with render? [y/N]: ").strip().lower()
    return response in ['y', 'yes']


def dry_run_render(
    storyboard: Dict,
    source_name: str,
    direction_name: str,
    resolution: str,
    reference_dir: Optional[str] = None
):
    """
    Execute dry-run mode: print all prompts and parameters without API calls
    
    Args:
        storyboard: Storyboard dictionary
        source_name: Source name for display
        direction_name: Direction name for display
        resolution: "previz" or "full"
        reference_dir: Optional reference image directory
    """
    print("\n" + "="*60)
    print("DRY RUN MODE")
    print("="*60)
    print(f"Source:      {source_name}")
    print(f"Direction:   {direction_name}")
    print(f"Model:       luma.ray-v2:0")
    print(f"Region:      us-west-2")
    print(f"Resolution:  {resolution}")
    print("="*60 + "\n")
    
    shots = build_shot_list(storyboard)
    estimate = estimate_cost(shots, resolution)
    
    print(f"Shot count:  {estimate.shot_count}")
    print(f"API seconds: {estimate.total_duration}s")
    print(f"Cost:        ${estimate.previz_cost if resolution == 'previz' else estimate.full_cost:.2f}")
    print("\n" + "="*60)
    print("SHOT PROMPTS")
    print("="*60 + "\n")
    
    for shot in shots:
        ref_image = find_reference_image(shot.id, reference_dir)
        prompt = frame_to_prompt(shot.frame)
        api_duration = duration_to_api(shot.duration)
        
        print(f"Shot {shot.id} ({shot.duration}s → {api_duration})")
        print(f"  Mode: {'image-to-video' if ref_image else 'text-to-video'}")
        if ref_image:
            print(f"  Reference: {ref_image}")
        print(f"  Prompt: {prompt}")
        print()
    
    print("="*60)
    print("Dry run complete. No API calls made.")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Basic test
    print("StepByStep Direct - Render Pipeline")
    print("Module loaded successfully")
