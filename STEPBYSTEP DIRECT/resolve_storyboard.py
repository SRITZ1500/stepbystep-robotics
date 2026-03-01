#!/usr/bin/env python3
"""
Helper script to resolve a storyboard with direction applied
"""

import json
import sys
from pathlib import Path

def apply_direction(source, direction_key):
    """Apply direction transformation to source"""
    if not direction_key or direction_key == 'baseline':
        result = source['baseline'].copy()
        result['directionHistory'] = []
        return result
    
    direction = source['directions'].get(direction_key)
    if not direction:
        print(f"Warning: Direction '{direction_key}' not found, using baseline")
        result = source['baseline'].copy()
        result['directionHistory'] = []
        return result
    
    baseline = source['baseline']
    
    # Check for full replacement mode
    if 'shots' in direction:
        final_shots = direction['shots']
    elif 'shotOverrides' in direction:
        # Overlay mode
        final_shots = []
        for shot in baseline['shots']:
            override = direction['shotOverrides'].get(str(shot['id']))
            if override:
                merged = shot.copy()
                merged.update(override)
                final_shots.append(merged)
            else:
                final_shots.append(shot)
    else:
        final_shots = baseline['shots']
    
    return {
        'concept': direction.get('concept', baseline['concept']),
        'shots': final_shots,
        'invisibleWide': direction.get('invisibleWide', baseline['invisibleWide']),
        'stormCloud': direction.get('stormCloud', baseline['stormCloud']),
        'platform': direction.get('platform', baseline.get('platform')),
        'directionHistory': [direction_key]
    }

def main():
    if len(sys.argv) < 3:
        print("Usage: python resolve_storyboard.py <source> <direction>")
        print("  source: jesse or changeless")
        print("  direction: baseline, darker, funnier, tender, surreal, minimalist, operatic")
        sys.exit(1)
    
    source_name = sys.argv[1]
    direction_name = sys.argv[2]
    
    # Load source file
    source_path = Path(f"src/storyboards/{source_name}.json")
    if not source_path.exists():
        print(f"Error: Source file not found: {source_path}")
        sys.exit(1)
    
    with open(source_path) as f:
        source = json.load(f)
    
    # Apply direction
    resolved = apply_direction(source, direction_name)
    
    # Write output
    output_path = Path(f"output_{source_name}_{direction_name}.json")
    with open(output_path, 'w') as f:
        json.dump(resolved, f, indent=2)
    
    print(f"✓ Resolved storyboard written to: {output_path}")
    print(f"  Source: {source_name}")
    print(f"  Direction: {direction_name}")
    print(f"  Shots: {len(resolved['shots'])}")
    print(f"  Total duration: {sum(s['duration'] for s in resolved['shots'])}s")

if __name__ == "__main__":
    main()
