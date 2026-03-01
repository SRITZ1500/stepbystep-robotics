# Design Document: StepByStep Direct

## Overview

StepByStep Direct is a two-layer creative direction system that transforms screenplay scenes into production-ready vertical (9:16) short film storyboards and renders them as video clips via Amazon Bedrock's Luma Ray2 model.

The system consists of:

1. **React Frontend Artifact**: An interactive UI for loading screenplay sources, applying creative direction prompts, and exporting storyboard JSON for rendering
2. **Python CLI Render Pipeline**: An asynchronous video generation workflow that converts storyboard shots into Luma Ray2 prompts, invokes Bedrock, polls for completion, downloads clips from S3, and stitches them into a final vertical video

The frontend enables rapid creative iteration through one-word direction prompts (e.g., "Darker", "Funnier", "Operatic") that transform the entire storyboard's concept, shot descriptions, audio design, pacing, and narrative tension. The render pipeline handles the technical complexity of async video generation, cost estimation, quality selection, and FFmpeg post-processing.

## Architecture

### System Layers

**Layer 1: React Frontend Artifact**
- Source Selector: Loads screenplay scenes as structured storyboard JSON
- Direction Engine: Applies creative transformations via direction prompts or shot overrides
- Themed UI Renderer: Displays storyboard with smooth animations and brand color themes
- Export: Generates storyboard JSON for render pipeline consumption

**Layer 2: Python CLI Render Pipeline**
- Shot Builder: Constructs shot list from storyboard JSON
- Prompt Engineer: Converts FRAME descriptions to Luma Ray2-optimized prompts
- Bedrock Async Invoker: Submits video generation requests via StartAsyncInvoke
- Job Poller: Monitors render status via GetAsyncInvoke at 10-second intervals
- S3 Downloader: Retrieves completed video clips from S3 storage
- FFmpeg Stitcher: Trims clips to exact duration and concatenates in shot order

### Data Flow

```
Screenplay Scene → Storyboard Parser → Storyboard JSON
                                            ↓
                                    Direction Engine
                                            ↓
                                    Themed UI Display
                                            ↓
                                    Export Storyboard JSON
                                            ↓
                                    Render Pipeline CLI
                                            ↓
                    Shot Builder → Prompt Engineer → Bedrock Async Invoker
                                            ↓
                                    Job Poller (10s intervals)
                                            ↓
                                    S3 Downloader → FFmpeg Stitcher
                                            ↓
                                    Final 9:16 Vertical Video
```

### AWS Infrastructure

- **Video Generation**: Amazon Bedrock Runtime `luma.ray-v2:0` model in `us-west-2` region
- **Clip Storage**: S3 bucket with path structure `stepbystep/{source}/{direction}/{timestamp}/shot_NN/`
- **IAM Permissions**: `bedrock:InvokeModel`, `bedrock:StartAsyncInvoke`, `bedrock:GetAsyncInvoke`, `s3:PutObject`, `s3:GetObject`, `s3:ListBucket`
- **Async Invocation**: StartAsyncInvoke for job submission, GetAsyncInvoke for status polling

## Components and Interfaces

### 1. Storyboard Parser

**Purpose**: Parse screenplay scene files into structured Storyboard_Source objects

**Interface**:
```python
def parse_storyboard(scene_file: str) -> StoryboardSource:
    """
    Parse screenplay scene into structured storyboard.
    
    Args:
        scene_file: Path to screenplay scene file
        
    Returns:
        StoryboardSource object with concept, shots, invisible_wide, 
        storm_cloud, and platform fields
        
    Raises:
        ParseError: If scene file is malformed or missing required fields
    """
```

**Responsibilities**:
- Extract concept field describing scene's core idea
- Parse 5-8 Shot objects with FRAME, AUDIO, DURATION, VALUE_SHIFT
- Extract invisible wide field for broader context
- Parse storm cloud seed with subtlety rating (0-10)
- Extract platform notes for vertical short film distribution
- Validate all required fields are present
- Return descriptive error messages on parse failure

### 2. Direction Engine

**Purpose**: Apply creative transformations to storyboards via direction prompts or shot overrides

**Interface**:
```javascript
function applyDirection(
  storyboard: Storyboard,
  directionPrompt: string,
  shotOverrides?: ShotOverride[]
): Storyboard {
  // Returns transformed storyboard with updated concept, shots, 
  // storm_cloud, platform, and direction_history
}
```

**Responsibilities**:
- Transform storyboard concept based on direction prompt
- Transform all Shot FRAME and AUDIO fields
- Adjust shot pacing and duration
- Update storm cloud seed and subtlety rating
- Update platform notes
- Append direction prompt to direction_history
- Preserve original shot count (5-8 shots)
- Apply shot overrides to specific shots only
- Validate override target shots exist

**Direction Resolution Algorithm**:
1. If shotOverrides provided: Merge overrides onto baseline shots (override mode)
2. If full replacement shots provided: Replace entire shot list (replacement mode)
3. Otherwise: Apply direction prompt transformation to all fields

### 3. Theme System

**Purpose**: Provide brand color themes with smooth transitions

**Interface**:
```javascript
const themes = {
  flyers: ThemePalette,
  claude: ThemePalette,
  amazon: ThemePalette
};

function applyTheme(themeName: string): void {
  // Updates CSS custom properties for all UI colors
}
```

**Theme Palette Structure**:
```javascript
interface ThemePalette {
  bg: string;           // Background color
  accent: string;       // Accent/primary color
  text: string;         // Primary text color
  textSecondary: string; // Secondary text color
  textMuted: string;    // Muted text color
  border: string;       // Border color
  surface: string;      // Surface/card color
}
```

**Responsibilities**:
- Support three brand themes: Flyers (PHI), Claude (ANTH), Amazon (AMZN)
- Apply theme colors to all UI elements (background, accent, text, borders, input fields, pills, rating badges, gradient overlays)
- Animate color transitions with 300-500ms ease timing
- Persist selected theme across sessions (localStorage)

### 4. Prompt Engineering Layer

**Purpose**: Convert FRAME descriptions to Luma Ray2-optimized video prompts

**Interface**:
```python
def generate_luma_prompt(
    frame_description: str,
    shot_type: str,
    reference_image: Optional[str] = None
) -> str:
    """
    Generate Luma Ray2-optimized prompt from shot FRAME.
    
    Args:
        frame_description: Shot FRAME field content
        shot_type: Shot framing (ECU, CU, MCU, MS, WS, etc.)
        reference_image: Optional path to reference image for image-to-video
        
    Returns:
        Optimized prompt string (max 500 characters)
    """
```

**Prompt Optimization**:
- Prepend `VERTICAL_PROMPT_PREFIX`: "Cinematic vertical 9:16 aspect ratio, professional cinematography, "
- Map shot types to framing hints via `SHOT_TYPE_MAP`:
  - ECU → "extreme close-up, intimate detail"
  - CU → "close-up, facial expression focus"
  - MCU → "medium close-up, upper body"
  - MS → "medium shot, waist up"
  - WS → "wide shot, full scene"
- Truncate final prompt to 500 characters
- Format as image-to-video request if reference_image provided

### 5. Bedrock Async Pipeline

**Purpose**: Execute asynchronous video generation workflow

**Interface**:
```python
def render_storyboard(
    storyboard: Storyboard,
    quality: str,  # "previz" or "full"
    reference_dir: Optional[str] = None,
    dry_run: bool = False
) -> RenderResult:
    """
    Render storyboard as video via Bedrock Luma Ray2.
    
    Args:
        storyboard: Storyboard object with shots
        quality: "previz" (540p, $0.75/s) or "full" (720p, $1.50/s)
        reference_dir: Optional directory containing reference images
        dry_run: If True, log prompts without invoking Bedrock
        
    Returns:
        RenderResult with output_path, cost, duration, and per-shot status
    """
```

**Pipeline Sequence**:
1. **build_shot_list()**: Extract shots from storyboard JSON
2. **estimate_cost()**: Calculate total cost based on shot durations and quality
3. **submit_shot()**: Call StartAsyncInvoke for each shot with Luma Ray2 prompt
4. **poll_jobs()**: Call GetAsyncInvoke every 10 seconds until all jobs complete
5. **download_clips()**: Retrieve video clips from S3 (retry once on failure)
6. **stitch_clips()**: Use FFmpeg to trim clips to exact duration and concatenate

**Error Handling**:
- Individual shot failures: Log error, continue with remaining shots
- All shots fail: Exit with error code
- S3 download failure: Retry once, then log error
- FFmpeg missing: Exit with installation instructions
- Bedrock throttling: Exponential backoff (2s, 4s, 8s, 16s)

### 6. Cost Manager

**Purpose**: Estimate and track render costs

**Interface**:
```python
def estimate_cost(shots: List[Shot], quality: str) -> CostEstimate:
    """
    Calculate render cost estimate.
    
    Args:
        shots: List of Shot objects with DURATION fields
        quality: "previz" or "full"
        
    Returns:
        CostEstimate with previz_cost, full_cost, total_duration
    """
```

**Cost Calculation**:
- Previz Mode: 540p resolution at $0.75 per second
- Full Quality Mode: 720p resolution at $1.50 per second
- Total duration: Sum of all shot DURATION fields (5s or 9s each)
- Display both estimates before render execution
- Require explicit user confirmation (unless dry-run mode)

**Post-Render Summary**:
- Actual cost based on rendered clip durations
- Cost per shot breakdown
- Total render time (wall clock)

### 7. UI Components

**Source Switcher**:
- Dropdown or button group for loading different Storyboard_Source objects
- Displays source label and subtitle

**Direction Input**:
- Text input field for entering custom Direction_Prompt values
- Enter key or button to apply direction

**Direction Pills**:
- Clickable pill buttons for common Direction_Prompt variants (minimum 10)
- Apply direction on click
- Visual feedback on hover/active states

**Theme Switcher**:
- Toggle or dropdown for selecting Theme_Palette (Flyers, Claude, Amazon)
- Applies theme within 300ms with smooth transitions

**Storyboard Display**:
- Concept section with typewriter animation on change
- Shot list with cascade reveal animation (100ms stagger)
- Invisible wide section
- Storm cloud seed with color-coded rating badge (green 0-3, yellow 4-6, red 7-10)
- Platform notes section
- Direction history display

**Fixed Input Bar**:
- Positioned at bottom of viewport
- Contains direction input, direction pills, and theme switcher
- Remains accessible during scrolling

## Data Models

### Storyboard

```javascript
interface Storyboard {
  concept: string;              // Core scene idea
  shots: Shot[];                // 5-8 shot objects
  invisibleWide: string;        // Broader context/subtext
  stormCloud: {
    detail: string;             // Narrative tension description
    rating: number;             // Subtlety rating 0-10
  };
  platform: {
    length: string;             // Target video length
    hook: string;               // Opening hook strategy
    loop: string;               // Loop/replay strategy
    soundOff: string;           // Sound-off viewing strategy
  };
  directionHistory?: string[];  // Applied direction prompts
}
```

### Shot

```javascript
interface Shot {
  id: string;                   // Unique shot identifier
  frame: string;                // Visual description
  audio: string;                // Sound design specification
  duration: 5 | 9;              // Clip length in seconds
  valueShift: string;           // Narrative purpose
}
```

### Source

```javascript
interface Source {
  label: string;                // Source display name
  subtitle: string;             // Source description
  baseline: Storyboard;         // Original storyboard
  directions: {
    [key: string]: DirectionVariant;  // Available direction transformations
  };
}
```

### DirectionVariant

```javascript
interface DirectionVariant {
  // Override mode: Merge shot overrides onto baseline
  shotOverrides?: {
    [shotId: string]: Partial<Shot>;
  };
  
  // Replacement mode: Full shot list replacement
  shots?: Shot[];
  
  // Always present: Transformed storyboard fields
  concept?: string;
  invisibleWide?: string;
  stormCloud?: {
    detail: string;
    rating: number;
  };
  platform?: {
    length: string;
    hook: string;
    loop: string;
    soundOff: string;
  };
}
```

### ShotOverride

```javascript
interface ShotOverride {
  shotId: string;               // Target shot ID
  frame?: string;               // Override FRAME field
  audio?: string;               // Override AUDIO field
  duration?: 5 | 9;             // Override DURATION field
  valueShift?: string;          // Override VALUE_SHIFT field
}
```

### RenderResult

```python
@dataclass
class RenderResult:
    output_path: str              # Path to final stitched video
    total_cost: float             # Actual render cost in USD
    total_duration: float         # Total video duration in seconds
    render_time: float            # Wall clock time in seconds
    shot_results: List[ShotResult]  # Per-shot status
```

### ShotResult

```python
@dataclass
class ShotResult:
    shot_id: str                  # Shot identifier
    status: str                   # "success", "failed", "skipped"
    clip_path: Optional[str]      # Path to downloaded clip
    cost: float                   # Cost for this shot
    error: Optional[str]          # Error message if failed
```

### CostEstimate

```python
@dataclass
class CostEstimate:
    previz_cost: float            # Cost at 540p ($0.75/s)
    full_cost: float              # Cost at 720p ($1.50/s)
    total_duration: float         # Sum of shot durations
    shot_count: int               # Number of shots
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Storyboard parsing produces complete structure

*For any* valid screenplay scene file, parsing should produce a Storyboard_Source object containing all required fields: concept, shots (5-8 items), invisibleWide, stormCloud (with rating 0-10), and platform notes.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6**

### Property 2: Shot parsing produces complete structure

*For any* valid shot data, parsing should produce a Shot object containing all required fields: id, frame, audio, duration (5 or 9), and valueShift.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

### Property 3: Invalid screenplay files produce errors

*For any* malformed screenplay scene file, parsing should return a descriptive error message rather than crashing or producing invalid output.

**Validates: Requirements 1.7**

### Property 4: Invalid shot data produces validation errors

*For any* shot data with missing required fields, parsing should return a validation error rather than creating an incomplete Shot object.

**Validates: Requirements 2.5**

### Property 5: Direction application transforms all storyboard fields

*For any* storyboard and direction prompt, applying the direction should transform the concept, all shot FRAME and AUDIO fields, storm cloud seed, and platform notes.

**Validates: Requirements 3.1, 3.2, 3.3, 3.5, 3.6**

### Property 6: Direction application preserves shot count

*For any* storyboard with N shots (where 5 ≤ N ≤ 8) and any direction prompt, applying the direction should result in a storyboard with exactly N shots.

**Validates: Requirements 3.8**

### Property 7: Direction application maintains valid shot durations

*For any* storyboard and direction prompt, applying the direction should result in all shots having duration values in {5, 9}.

**Validates: Requirements 3.4**

### Property 8: Direction history accumulates in order

*For any* sequence of direction prompts [D1, D2, ..., DN], applying them in order should result in a direction_history list containing [D1, D2, ..., DN] in that exact order.

**Validates: Requirements 3.7, 5.1, 5.2, 5.3**

### Property 9: Shot overrides affect only targeted shots

*For any* storyboard and shot override targeting shot ID X, applying the override should modify only the shot with ID X, leaving all other shots unchanged.

**Validates: Requirements 4.1, 4.2**

### Property 10: Full shot replacement replaces entire shot list

*For any* storyboard and direction variant with full shot replacement, applying the direction should result in the storyboard containing exactly the replacement shots.

**Validates: Requirements 4.3**

### Property 11: Invalid shot override targets produce errors

*For any* shot override targeting a non-existent shot ID, the direction engine should return a validation error rather than silently failing.

**Validates: Requirements 4.4**

### Property 12: Theme persistence round-trip

*For any* theme selection, setting the theme and reloading the session should restore the same theme.

**Validates: Requirements 7.5**

### Property 13: Theme application updates all UI elements

*For any* theme palette, applying the theme should update colors for all specified UI elements: background, accent, text, borders, input fields, pills, rating badges, and gradient overlays.

**Validates: Requirements 7.3**

### Property 14: Prompt generation includes aspect ratio

*For any* shot FRAME description, the generated Luma Ray2 prompt should include vertical 9:16 aspect ratio specification.

**Validates: Requirements 8.1, 8.2**

### Property 15: Reference image changes prompt format

*For any* shot with a reference image provided, the generated prompt should be formatted as an image-to-video request, while shots without reference images should be formatted as text-to-video requests.

**Validates: Requirements 8.4, 10.2, 10.3**

### Property 16: Render pipeline submits one request per shot

*For any* storyboard with N shots, triggering render should result in exactly N StartAsyncInvoke API calls to Bedrock.

**Validates: Requirements 9.2**

### Property 17: Render pipeline uses correct shot durations

*For any* shot with duration D seconds, the corresponding Bedrock API call should specify clip length D.

**Validates: Requirements 9.3**

### Property 18: Render pipeline downloads all completed clips

*For any* storyboard render where M shots complete successfully, the pipeline should download exactly M video clips from S3.

**Validates: Requirements 9.5**

### Property 19: FFmpeg trims clips to exact duration

*For any* shot with duration D seconds, the FFmpeg trim command should specify exactly D seconds.

**Validates: Requirements 9.6**

### Property 20: FFmpeg concatenates clips in shot order

*For any* storyboard with shots [S1, S2, ..., SN], the FFmpeg concat list should specify clips in the order [clip_S1, clip_S2, ..., clip_SN].

**Validates: Requirements 9.7**

### Property 21: Individual render failures don't stop pipeline

*For any* storyboard render where at least one shot fails and at least one shot succeeds, the pipeline should continue processing all shots and produce output for successful shots.

**Validates: Requirements 9.9**

### Property 22: Reference image directory triggers image checks

*For any* storyboard render with a reference image directory specified, the pipeline should check for reference image files for each shot.

**Validates: Requirements 10.1**

### Property 23: Unsupported reference image formats produce errors

*For any* reference image file with an unsupported format (not JPEG or PNG), the pipeline should return a validation error.

**Validates: Requirements 10.4**

### Property 24: Cost calculation sums shot durations

*For any* storyboard with shots having durations [D1, D2, ..., DN], the calculated total duration should equal D1 + D2 + ... + DN.

**Validates: Requirements 11.1**

### Property 25: Previz cost formula

*For any* total duration T seconds, the previz mode cost should equal T × $0.75.

**Validates: Requirements 11.2**

### Property 26: Full quality cost formula

*For any* total duration T seconds, the full quality mode cost should equal T × $1.50.

**Validates: Requirements 11.3**

### Property 27: Quality mode sets correct resolution

*For any* render request, selecting previz mode should configure Bedrock for 540p output, while selecting full quality mode should configure Bedrock for 720p output.

**Validates: Requirements 12.3, 12.4**

### Property 28: Dry-run mode skips API invocation

*For any* storyboard render in dry-run mode, the pipeline should execute all steps except StartAsyncInvoke, and should not make any actual Bedrock API calls.

**Validates: Requirements 13.1**

### Property 29: Dry-run mode logs prompts and parameters

*For any* storyboard render in dry-run mode, the pipeline should log all prompts and parameters that would be sent to Bedrock.

**Validates: Requirements 13.2**

### Property 30: Dry-run mode skips confirmation

*For any* cost estimate in dry-run mode, the cost manager should display estimates without requiring user confirmation.

**Validates: Requirements 13.3**

### Property 31: Actual cost uses rendered durations

*For any* completed render with clips having actual durations [A1, A2, ..., AM], the calculated actual cost should be based on the sum of actual durations, not the requested durations.

**Validates: Requirements 14.1**

### Property 32: UI displays all storyboard fields

*For any* storyboard, the UI should render all fields: concept, shot list, invisibleWide, stormCloud, and platform notes.

**Validates: Requirements 15.5**

### Property 33: Storm cloud badge color matches rating range

*For any* storm cloud rating R, the badge color should be green when 0 ≤ R ≤ 3, yellow when 4 ≤ R ≤ 6, and red when 7 ≤ R ≤ 10.

**Validates: Requirements 16.4, 17.2, 17.3, 17.4**

### Property 34: Direction history displays in order

*For any* direction history [D1, D2, ..., DN], the UI should display the directions in that exact order.

**Validates: Requirements 5.4**

### Property 35: Direction pill click applies direction

*For any* direction pill button, clicking it should apply that direction prompt to the current storyboard.

**Validates: Requirements 6.3**

## Error Handling

### Parse Errors

- **Malformed screenplay files**: Return descriptive error message indicating which field is missing or invalid
- **Invalid shot structure**: Return validation error specifying which required field is missing
- **Invalid storm cloud rating**: Return error if rating is outside [0, 10] range
- **Invalid shot count**: Return error if shot list contains fewer than 5 or more than 8 shots

### Direction Engine Errors

- **Invalid shot override target**: Return validation error indicating the shot ID does not exist
- **Invalid direction prompt**: Return error if direction prompt is empty or malformed
- **Transformation failure**: Log error and return original storyboard if transformation fails

### Render Pipeline Errors

- **Individual shot failure**: Log error with shot ID and error message, continue with remaining shots
- **All shots fail**: Exit with error code and summary of all failures
- **S3 download failure**: Retry once with exponential backoff, then log error and mark shot as failed
- **FFmpeg missing**: Exit with error message and installation instructions
- **Bedrock throttling**: Implement exponential backoff (2s, 4s, 8s, 16s) before retrying
- **Invalid reference image format**: Return validation error listing supported formats (JPEG, PNG)
- **Missing reference image directory**: Log warning and proceed with text-to-video mode for all shots

### Cost Manager Errors

- **Invalid quality mode**: Return error if quality is not "previz" or "full"
- **User cancellation**: Exit gracefully when user declines cost confirmation
- **Cost calculation overflow**: Handle edge cases where duration sum exceeds reasonable limits

### Theme System Errors

- **Invalid theme name**: Log warning and fall back to default theme (Claude)
- **localStorage unavailable**: Log warning and use in-memory theme storage only
- **Theme load failure**: Fall back to default theme and log error

### UI Errors

- **Missing storyboard data**: Display placeholder message indicating no storyboard loaded
- **Direction application timeout**: Display error message and allow retry
- **Network errors**: Display user-friendly error message with retry option

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests for comprehensive coverage:

- **Unit tests**: Verify specific examples, edge cases, error conditions, and integration points
- **Property tests**: Verify universal properties across all inputs using randomized test data

### Property-Based Testing Configuration

- **Library**: Use `fast-check` for JavaScript/React components, `hypothesis` for Python render pipeline
- **Iterations**: Minimum 100 iterations per property test to ensure comprehensive input coverage
- **Tagging**: Each property test must include a comment referencing the design document property
- **Tag format**: `// Feature: stepbystep-direct, Property {number}: {property_text}`

### Unit Test Focus Areas

**Storyboard Parser**:
- Example: Parse a valid screenplay scene and verify structure
- Edge case: Empty screenplay file
- Edge case: Screenplay with exactly 5 shots (minimum)
- Edge case: Screenplay with exactly 8 shots (maximum)
- Error: Missing concept field
- Error: Missing storm cloud rating

**Direction Engine**:
- Example: Apply "Darker" direction and verify concept changes
- Example: Apply shot override to shot 3 and verify shots 1, 2, 4+ unchanged
- Integration: Apply multiple directions in sequence and verify history
- Error: Override non-existent shot ID

**Theme System**:
- Example: Switch to Flyers theme and verify accent color is Flyers orange
- Example: Switch to Claude theme and verify accent color is Claude orange
- Example: Switch to Amazon theme and verify accent color is Amazon orange
- Integration: Theme persists after page reload

**Prompt Generator**:
- Example: Generate prompt for ECU shot and verify "extreme close-up" hint included
- Example: Generate prompt with reference image and verify image-to-video format
- Edge case: Very long FRAME description (verify truncation to 500 chars)

**Render Pipeline**:
- Example: Render 3-shot storyboard and verify 3 API calls
- Example: Dry-run mode logs prompts without API calls
- Integration: Full pipeline from storyboard JSON to stitched video
- Error: All shots fail (verify pipeline exits with error)
- Error: S3 download fails (verify retry logic)

**Cost Manager**:
- Example: 3 shots of 5s each = 15s × $0.75 = $11.25 previz
- Example: 3 shots of 5s each = 15s × $1.50 = $22.50 full quality
- Integration: Display cost estimate before render
- Integration: Display actual cost after render

### Property Test Focus Areas

**Storyboard Parser** (Properties 1-4):
- Generate random valid screenplay files, verify complete structure
- Generate random malformed files, verify error messages
- Generate random shot counts in [5, 8], verify all parse successfully

**Direction Engine** (Properties 5-11):
- Generate random storyboards and directions, verify all fields transform
- Generate random direction sequences, verify history accumulates correctly
- Generate random shot overrides, verify only targeted shots change
- Generate random invalid shot IDs, verify validation errors

**Theme System** (Properties 12-13):
- Generate random theme selections, verify round-trip persistence
- Generate random theme switches, verify all UI elements update

**Prompt Generator** (Properties 14-15):
- Generate random shot FRAME descriptions, verify all include "9:16"
- Generate random shots with/without reference images, verify format differs

**Render Pipeline** (Properties 16-23):
- Generate random storyboards, verify API call count equals shot count
- Generate random shot durations, verify API receives correct durations
- Generate random reference image directories, verify image checks occur
- Generate random unsupported formats, verify validation errors

**Cost Manager** (Properties 24-27, 31):
- Generate random shot duration lists, verify sum equals calculated duration
- Generate random durations, verify previz cost = duration × $0.75
- Generate random durations, verify full cost = duration × $1.50
- Generate random quality selections, verify correct resolution configured

**Dry-Run Mode** (Properties 28-30):
- Generate random storyboards in dry-run, verify no API calls made
- Generate random storyboards in dry-run, verify prompts logged
- Generate random costs in dry-run, verify no confirmation required

**UI Rendering** (Properties 32-35):
- Generate random storyboards, verify all fields appear in rendered output
- Generate random storm cloud ratings, verify badge colors match ranges
- Generate random direction histories, verify display order matches
- Simulate random pill clicks, verify directions apply

### Test Data Generators

**Screenplay Generator**:
- Random concept strings (50-200 chars)
- Random shot counts in [5, 8]
- Random shot FRAME descriptions (100-500 chars)
- Random shot AUDIO descriptions (50-200 chars)
- Random shot durations from {5, 9}
- Random storm cloud ratings in [0, 10]

**Direction Generator**:
- Random direction prompts from predefined list
- Random shot override targets (valid and invalid IDs)
- Random shot override fields (partial and complete)

**Storyboard Generator**:
- Random valid storyboards with all required fields
- Random malformed storyboards with missing fields
- Random storyboards with edge case shot counts (5, 8)

### Integration Test Scenarios

1. **End-to-end creative workflow**: Load source → Apply 3 directions → Export JSON → Verify history
2. **End-to-end render workflow**: Load storyboard JSON → Estimate cost → Render (dry-run) → Verify logs
3. **Theme persistence**: Set theme → Reload page → Verify theme restored
4. **Error recovery**: Trigger render with invalid reference images → Verify graceful error handling

### Performance Considerations

- Theme transitions should complete within 300-500ms (visual inspection, not unit tested)
- UI animations should complete within 1 second (visual inspection, not unit tested)
- Render pipeline polling should occur at 10-second intervals (integration test, not unit tested)
- Property tests should complete within reasonable time (< 10 seconds per property)

