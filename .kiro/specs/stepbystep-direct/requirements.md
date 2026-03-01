# Requirements Document

## Introduction

StepByStep Direct is a creative direction engine that transforms screenplay scenes into production-ready vertical (9:16) short film storyboards, then renders them as video clips via Amazon Bedrock's Luma Ray2 model. The system enables users to load source material, apply one-word creative direction prompts that transform the entire storyboard, and trigger an async render pipeline that generates 9:16 video clips stitched into a final vertical short.

## Glossary

- **Storyboard_Source**: A screenplay scene parsed into structured format containing concept, shot list, invisible wide, storm cloud seed, and platform notes
- **Shot**: A single video segment with FRAME (visual description), AUDIO (sound design), DURATION (5s or 9s), and VALUE_SHIFT (narrative purpose)
- **Direction_Prompt**: A single-word creative instruction (e.g., "Darker", "Funnier", "Operatic") that transforms storyboard elements
- **Storm_Cloud_Seed**: A narrative tension indicator with subtlety rating (0-10) representing underlying conflict
- **Invisible_Wide**: The broader context or subtext of a scene not explicitly shown
- **Luma_Ray2**: Amazon Bedrock's video generation model that creates 9:16 video clips from text prompts
- **Reference_Image**: An optional image used for image-to-video generation requests
- **Previz_Mode**: Preview quality rendering at 540p resolution costing $0.75 per second
- **Full_Quality_Mode**: Production quality rendering at 720p resolution costing $1.50 per second
- **Direction_History**: A tracked sequence of applied direction prompts forming a transformation path
- **Theme_Palette**: A UI color scheme (Flyers, Claude, or Amazon brand colors)
- **Shot_Override**: A user-specified modification to a single shot within a storyboard
- **Async_Render_Pipeline**: The asynchronous video generation workflow using StartAsyncInvoke and GetAsyncInvoke polling

## Requirements

### Requirement 1: Load Screenplay Sources

**User Story:** As a filmmaker, I want to load screenplay scenes as storyboard sources, so that I can begin the creative direction process.

#### Acceptance Criteria

1. WHEN a screenplay scene file is provided, THE Storyboard_Parser SHALL parse it into a Storyboard_Source object
2. THE Storyboard_Source SHALL contain a concept field describing the scene's core idea
3. THE Storyboard_Source SHALL contain a shot list with 5 to 8 Shot objects
4. THE Storyboard_Source SHALL contain an invisible wide field describing broader context
5. THE Storyboard_Source SHALL contain a storm cloud seed with a subtlety rating between 0 and 10
6. THE Storyboard_Source SHALL contain platform notes for vertical short film distribution
7. WHEN parsing fails, THE Storyboard_Parser SHALL return a descriptive error message

### Requirement 2: Parse Shot Structure

**User Story:** As a filmmaker, I want each shot to have structured metadata, so that the render pipeline can generate accurate video clips.

#### Acceptance Criteria

1. THE Shot_Parser SHALL extract a FRAME field containing visual description
2. THE Shot_Parser SHALL extract an AUDIO field containing sound design specifications
3. THE Shot_Parser SHALL extract a DURATION field with value of either 5 or 9 seconds
4. THE Shot_Parser SHALL extract a VALUE_SHIFT field describing narrative purpose
5. WHEN a required shot field is missing, THE Shot_Parser SHALL return a validation error

### Requirement 3: Apply Creative Direction

**User Story:** As a filmmaker, I want to apply one-word direction prompts, so that I can transform the entire storyboard's creative approach.

#### Acceptance Criteria

1. WHEN a Direction_Prompt is applied, THE Direction_Engine SHALL transform the storyboard concept
2. WHEN a Direction_Prompt is applied, THE Direction_Engine SHALL transform all Shot FRAME fields
3. WHEN a Direction_Prompt is applied, THE Direction_Engine SHALL transform all Shot AUDIO fields
4. WHEN a Direction_Prompt is applied, THE Direction_Engine SHALL adjust shot pacing and duration
5. WHEN a Direction_Prompt is applied, THE Direction_Engine SHALL update the storm cloud seed and subtlety rating
6. WHEN a Direction_Prompt is applied, THE Direction_Engine SHALL update platform notes
7. THE Direction_Engine SHALL append the Direction_Prompt to the Direction_History
8. THE Direction_Engine SHALL preserve the original shot count (5 to 8 shots)

### Requirement 4: Support Shot Overrides

**User Story:** As a filmmaker, I want to override individual shots, so that I can fine-tune specific moments without re-transforming the entire storyboard.

#### Acceptance Criteria

1. WHEN a Shot_Override is specified, THE Direction_Engine SHALL apply the override to the targeted shot only
2. WHEN a Shot_Override is specified, THE Direction_Engine SHALL preserve all other shots unchanged
3. THE Direction_Engine SHALL support full shot replacement including all shot fields
4. THE Direction_Engine SHALL validate that the override target shot exists in the storyboard

### Requirement 5: Track Direction History

**User Story:** As a filmmaker, I want to see the sequence of direction prompts I've applied, so that I can understand the transformation path.

#### Acceptance Criteria

1. THE Direction_Engine SHALL maintain a Direction_History list in application order
2. WHEN a Direction_Prompt is applied, THE Direction_Engine SHALL append it to Direction_History
3. THE Direction_History SHALL persist across storyboard transformations
4. THE UI SHALL display Direction_History as a readable sequence

### Requirement 6: Provide Direction Variants

**User Story:** As a filmmaker, I want to see available direction options, so that I can quickly explore creative alternatives.

#### Acceptance Criteria

1. THE Direction_Engine SHALL provide a list of available Direction_Prompt variants
2. THE UI SHALL display Direction_Prompt variants as clickable pill buttons
3. WHEN a direction pill is clicked, THE UI SHALL apply that Direction_Prompt to the storyboard
4. THE Direction_Engine SHALL support at least 10 distinct Direction_Prompt variants

### Requirement 7: Switch UI Themes

**User Story:** As a user, I want to switch between brand color themes, so that I can customize the interface appearance.

#### Acceptance Criteria

1. THE Theme_System SHALL support three Theme_Palette options: Flyers, Claude, and Amazon
2. WHEN a Theme_Palette is selected, THE Theme_System SHALL update all UI colors within 300 milliseconds
3. THE Theme_System SHALL apply the Theme_Palette to background, accent, text, borders, input fields, pills, rating badges, and gradient overlays
4. THE Theme_System SHALL use smooth CSS transitions for color changes
5. THE Theme_System SHALL persist the selected Theme_Palette across sessions

### Requirement 8: Generate Luma Ray2 Prompts

**User Story:** As a filmmaker, I want shot FRAME fields converted to optimized video prompts, so that Luma Ray2 generates accurate clips.

#### Acceptance Criteria

1. WHEN a Shot is prepared for rendering, THE Prompt_Generator SHALL convert the FRAME field into a Luma Ray2 prompt
2. THE Prompt_Generator SHALL include vertical 9:16 aspect ratio specification in the prompt
3. THE Prompt_Generator SHALL optimize prompts for Luma Ray2 model capabilities
4. WHEN a Reference_Image is provided, THE Prompt_Generator SHALL format the request as image-to-video

### Requirement 9: Invoke Async Render Pipeline

**User Story:** As a filmmaker, I want to render storyboards as video clips, so that I can produce the final vertical short film.

#### Acceptance Criteria

1. WHEN render is triggered, THE Async_Render_Pipeline SHALL invoke Amazon Bedrock's Luma Ray2 model using StartAsyncInvoke
2. THE Async_Render_Pipeline SHALL submit one render request per Shot in the storyboard
3. THE Async_Render_Pipeline SHALL use the Shot DURATION field to determine clip length (5 or 9 seconds)
4. THE Async_Render_Pipeline SHALL poll render status using GetAsyncInvoke at 10 second intervals
5. WHEN all renders complete, THE Async_Render_Pipeline SHALL download video clips from S3
6. THE Async_Render_Pipeline SHALL trim clips to exact Shot DURATION using FFmpeg
7. THE Async_Render_Pipeline SHALL concatenate clips in shot list order using FFmpeg
8. THE Async_Render_Pipeline SHALL output a single 9:16 vertical video file
9. WHEN a render fails, THE Async_Render_Pipeline SHALL log the error and continue with remaining shots

### Requirement 10: Support Reference Images

**User Story:** As a filmmaker, I want to provide reference images for shots, so that I can generate image-to-video clips with specific visual starting points.

#### Acceptance Criteria

1. WHERE a Reference_Image directory is specified, THE Async_Render_Pipeline SHALL check for matching reference images per shot
2. WHEN a Reference_Image exists for a shot, THE Async_Render_Pipeline SHALL use image-to-video mode for that shot
3. WHEN no Reference_Image exists for a shot, THE Async_Render_Pipeline SHALL use text-to-video mode for that shot
4. THE Async_Render_Pipeline SHALL validate that Reference_Image files are in supported formats (JPEG, PNG)

### Requirement 11: Estimate Render Costs

**User Story:** As a filmmaker, I want to see cost estimates before rendering, so that I can make informed decisions about quality and budget.

#### Acceptance Criteria

1. WHEN render is requested, THE Cost_Manager SHALL calculate total video duration from all Shot DURATION fields
2. THE Cost_Manager SHALL calculate Previz_Mode cost at $0.75 per second
3. THE Cost_Manager SHALL calculate Full_Quality_Mode cost at $1.50 per second
4. THE Cost_Manager SHALL display both cost estimates to the user before render execution
5. THE Cost_Manager SHALL require explicit user confirmation before proceeding with render

### Requirement 12: Select Render Quality

**User Story:** As a filmmaker, I want to choose between preview and full quality rendering, so that I can balance cost and quality needs.

#### Acceptance Criteria

1. THE Cost_Manager SHALL offer Previz_Mode at 540p resolution
2. THE Cost_Manager SHALL offer Full_Quality_Mode at 720p resolution
3. WHEN Previz_Mode is selected, THE Async_Render_Pipeline SHALL configure Luma Ray2 for 540p output
4. WHEN Full_Quality_Mode is selected, THE Async_Render_Pipeline SHALL configure Luma Ray2 for 720p output

### Requirement 13: Support Dry Run Mode

**User Story:** As a developer, I want to test the render pipeline without incurring costs, so that I can validate the workflow.

#### Acceptance Criteria

1. WHERE dry-run mode is enabled, THE Async_Render_Pipeline SHALL execute all steps except StartAsyncInvoke
2. WHERE dry-run mode is enabled, THE Async_Render_Pipeline SHALL log all prompts and parameters that would be sent
3. WHERE dry-run mode is enabled, THE Cost_Manager SHALL display cost estimates without requiring confirmation

### Requirement 14: Display Cost Summary

**User Story:** As a filmmaker, I want to see actual costs after rendering, so that I can track spending.

#### Acceptance Criteria

1. WHEN render completes, THE Cost_Manager SHALL calculate actual cost based on rendered clip durations
2. WHEN render completes, THE Cost_Manager SHALL display total cost to the user
3. THE Cost_Manager SHALL display cost per shot in the summary
4. THE Cost_Manager SHALL display total render time in the summary

### Requirement 15: Render Interactive Artifact

**User Story:** As a filmmaker, I want a React-based interface, so that I can interact with storyboards visually.

#### Acceptance Criteria

1. THE UI SHALL provide a source switcher for loading different Storyboard_Source objects
2. THE UI SHALL provide a text input field for entering Direction_Prompt values
3. THE UI SHALL provide clickable direction pill buttons for common Direction_Prompt variants
4. THE UI SHALL provide a theme switcher for selecting Theme_Palette options
5. THE UI SHALL display the current storyboard concept, shot list, invisible wide, storm cloud seed, and platform notes
6. THE UI SHALL use a fixed input bar at the bottom of the viewport

### Requirement 16: Animate Storyboard Transitions

**User Story:** As a filmmaker, I want smooth visual transitions when storyboards change, so that the interface feels polished and responsive.

#### Acceptance Criteria

1. WHEN a Direction_Prompt is applied, THE UI SHALL animate text changes using typewriter effect
2. WHEN a Direction_Prompt is applied, THE UI SHALL fade transition between old and new content over 400 milliseconds
3. WHEN shot list updates, THE UI SHALL reveal shots using cascade animation with 100 millisecond stagger
4. THE UI SHALL animate storm cloud rating badge color changes (green for 0-3, yellow for 4-6, red for 7-10)
5. THE UI SHALL complete all animations within 1 second of Direction_Prompt application

### Requirement 17: Display Storm Cloud Ratings

**User Story:** As a filmmaker, I want to see visual indicators of narrative tension, so that I can understand the emotional intensity of the scene.

#### Acceptance Criteria

1. THE UI SHALL display the storm cloud subtlety rating as a badge
2. WHEN subtlety rating is 0 to 3, THE UI SHALL display the badge in green
3. WHEN subtlety rating is 4 to 6, THE UI SHALL display the badge in yellow
4. WHEN subtlety rating is 7 to 10, THE UI SHALL display the badge in red
5. THE UI SHALL animate badge color transitions over 300 milliseconds

