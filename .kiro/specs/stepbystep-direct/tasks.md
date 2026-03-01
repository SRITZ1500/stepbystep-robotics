# Implementation Plan: StepByStep Direct

## Overview

This implementation plan converts the StepByStep Direct design into actionable coding tasks. The system consists of two main components: a React frontend artifact for creative direction and a Python CLI render pipeline for video generation via Amazon Bedrock's Luma Ray2 model.

The implementation follows a phased approach: shared data layer, React frontend, Python render pipeline, and integration validation.

## Tasks

- [x] 1. Set up shared data layer and schemas
  - [x] 1.1 Define storyboard JSON schema
    - Create schema definition with all required fields: concept, shots (5-8), invisibleWide, stormCloud, platform
    - Define Shot schema with id, frame, audio, duration (5|9), valueShift
    - Define DirectionVariant schema with shotOverrides and replacement modes
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 2.2, 2.3, 2.4_
  
  - [x] 1.2 Create source data files
    - Create jesse.json with baseline storyboard + 6 direction variants
    - Create changeless.json with baseline storyboard + 6 direction variants
    - Validate both files against schema
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_
  
  - [ ]* 1.3 Write property test for storyboard parsing
    - **Property 1: Storyboard parsing produces complete structure**
    - **Property 2: Shot parsing produces complete structure**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 2.2, 2.3, 2.4**
  
  - [ ]* 1.4 Write property test for invalid data handling
    - **Property 3: Invalid screenplay files produce errors**
    - **Property 4: Invalid shot data produces validation errors**
    - **Validates: Requirements 1.7, 2.5**

- [x] 2. Implement direction resolution module
  - [x] 2.1 Create resolve_direction.js with applyDirection()
    - Implement direction application logic with overlay and replacement modes
    - Handle shotOverrides (merge onto baseline shots)
    - Handle full shot replacement
    - Preserve shot count (5-8 shots)
    - Append to direction_history array
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 4.1, 4.2, 4.3_
  
  - [ ]* 2.2 Write property tests for direction engine
    - **Property 5: Direction application transforms all storyboard fields**
    - **Property 6: Direction application preserves shot count**
    - **Property 7: Direction application maintains valid shot durations**
    - **Property 8: Direction history accumulates in order**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 5.1, 5.2, 5.3**
  
  - [ ]* 2.3 Write property tests for shot overrides
    - **Property 9: Shot overrides affect only targeted shots**
    - **Property 10: Full shot replacement replaces entire shot list**
    - **Property 11: Invalid shot override targets produce errors**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**

- [x] 3. Define theme token system
  - [x] 3.1 Create themes.json with color palettes
    - Define Flyers theme (PHI orange/black)
    - Define Claude theme (ANTH orange/cream)
    - Define Amazon theme (AMZN orange/dark)
    - Include all tokens: bg, accent, text, textSecondary, textMuted, border, surface
    - _Requirements: 7.1, 7.2_
  
  - [ ]* 3.2 Write unit tests for theme system
    - Test theme application updates all UI elements
    - Test theme persistence via localStorage
    - _Requirements: 7.3, 7.5_

- [ ] 4. Checkpoint - Ensure data layer is complete
  - Ensure all tests pass, ask the user if questions arise.

- [-] 5. Build React artifact core layout and theme switching
  - [x] 5.1 Create stepbystep-direct.jsx with basic structure
    - Set up React component with header, main content area, fixed input bar
    - Implement theme state management
    - Load themes from themes.json
    - _Requirements: 6.1, 7.1_
  
  - [ ] 5.2 Implement theme switcher in header
    - Add theme toggle/dropdown UI
    - Wire theme state to CSS custom properties
    - Add 300-500ms CSS transitions for color changes
    - Implement localStorage persistence
    - _Requirements: 7.2, 7.3, 7.4, 7.5_
  
  - [ ]* 5.3 Write property tests for theme system
    - **Property 12: Theme persistence round-trip**
    - **Property 13: Theme application updates all UI elements**
    - **Validates: Requirements 7.3, 7.5**

- [ ] 6. Build source tab switcher
  - [ ] 6.1 Implement source selector UI
    - Add tab buttons for jesse.json and changeless.json
    - Display source label and subtitle
    - Add active tab highlighting
    - _Requirements: 6.1_
  
  - [ ] 6.2 Wire source switching logic
    - Load storyboard data on source switch
    - Reset direction history on source switch
    - Reset scroll position on source switch
    - Add fade transition animation
    - _Requirements: 6.1, 6.2_
  
  - [ ]* 6.3 Write unit tests for source switching
    - Test source data loads correctly
    - Test direction history resets
    - _Requirements: 6.1, 6.2_

- [ ] 7. Build storyboard content renderer
  - [ ] 7.1 Implement Section component
    - Create reusable section wrapper with title and content
    - Apply theme colors to section styling
    - _Requirements: 15.5_
  
  - [ ] 7.2 Implement TypewriterText component
    - Add typewriter animation for concept field changes
    - Trigger animation on direction application
    - _Requirements: 15.1_
  
  - [ ] 7.3 Implement ShotRow component
    - Display shot id, frame, audio, duration, valueShift
    - Apply theme colors to shot styling
    - _Requirements: 15.5_
  
  - [ ] 7.4 Implement cascade shot reveal animation
    - Add 100ms stagger delay between shot reveals
    - Trigger on storyboard load and direction application
    - _Requirements: 15.2_
  
  - [ ] 7.5 Render all storyboard fields
    - Render concept with TypewriterText
    - Render shot list with ShotRow and cascade animation
    - Render invisibleWide section
    - Render stormCloud with color-coded rating badge (green 0-3, yellow 4-6, red 7-10)
    - Render platform notes (length, hook, loop, soundOff)
    - Render direction history list
    - _Requirements: 15.5, 16.4, 17.2, 17.3, 17.4, 5.4_
  
  - [ ]* 7.6 Write property tests for UI rendering
    - **Property 32: UI displays all storyboard fields**
    - **Property 33: Storm cloud badge color matches rating range**
    - **Property 34: Direction history displays in order**
    - **Validates: Requirements 15.5, 16.4, 17.2, 17.3, 17.4, 5.4**

- [ ] 8. Build direction input system
  - [ ] 8.1 Create fixed input bar at bottom
    - Position fixed at bottom of viewport
    - Add text input field for custom direction prompts
    - Add submit button
    - Apply theme colors
    - _Requirements: 6.3, 6.4_
  
  - [ ] 8.2 Implement direction pills
    - Create at least 10 clickable pill buttons for common directions
    - Add hover and active state styling
    - Wire pill clicks to apply direction
    - _Requirements: 6.3, 6.5_
  
  - [ ] 8.3 Wire direction application
    - Call applyDirection() on submit or pill click
    - Update storyboard state with transformed result
    - Trigger UI animations (typewriter, cascade reveal)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_
  
  - [ ] 8.4 Implement direction history bar
    - Display applied directions in order
    - Add transition animations on direction apply
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  
  - [ ]* 8.5 Write property test for direction pill interaction
    - **Property 35: Direction pill click applies direction**
    - **Validates: Requirements 6.3**

- [ ] 9. Add storyboard export functionality
  - [ ] 9.1 Implement export button
    - Add export button to UI
    - Generate storyboard JSON on click
    - Download JSON file with source and direction in filename
    - _Requirements: 15.3, 15.4_
  
  - [ ]* 9.2 Write unit tests for export
    - Test JSON structure matches schema
    - Test filename format
    - _Requirements: 15.3, 15.4_

- [ ] 10. Checkpoint - Ensure React artifact is complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Implement Python render pipeline shot list builder and prompt engineer
  - [x] 11.1 Create stepbystep_render.py with build_shot_list()
    - Parse storyboard JSON and extract shots array
    - Validate shot structure (id, frame, audio, duration, valueShift)
    - Return list of Shot objects
    - _Requirements: 9.1_
  
  - [x] 11.2 Implement frame_to_prompt() function
    - Prepend VERTICAL_PROMPT_PREFIX: "Cinematic vertical 9:16 aspect ratio, professional cinematography, "
    - Map shot types to framing hints (ECU, CU, MCU, MS, WS)
    - Truncate final prompt to 500 characters
    - _Requirements: 8.1, 8.2, 8.3_
  
  - [x] 11.3 Implement duration_to_api() function
    - Convert shot duration (5 or 9 seconds) to Bedrock API format
    - _Requirements: 9.3_
  
  - [x] 11.4 Implement reference image handling
    - Check for reference image files in reference_dir
    - Format as image-to-video request if reference image exists
    - Format as text-to-video request otherwise
    - Validate image format (JPEG or PNG only)
    - _Requirements: 8.4, 10.1, 10.2, 10.3, 10.4_
  
  - [ ]* 11.5 Write property tests for prompt generation
    - **Property 14: Prompt generation includes aspect ratio**
    - **Property 15: Reference image changes prompt format**
    - **Validates: Requirements 8.1, 8.2, 8.4, 10.2, 10.3**
  
  - [ ]* 11.6 Write unit tests for prompt engineering
    - Test ECU shot includes "extreme close-up" hint
    - Test prompt truncation at 500 characters
    - Test unsupported image format produces error
    - _Requirements: 8.2, 8.3, 10.4_

- [x] 12. Implement Bedrock async invoke and polling
  - [x] 12.1 Implement create_bedrock_client()
    - Create boto3 Bedrock Runtime client for us-west-2 region
    - Configure IAM permissions check
    - _Requirements: 9.2_
  
  - [x] 12.2 Implement submit_shot() with StartAsyncInvoke
    - Call StartAsyncInvoke API with luma.ray-v2:0 model
    - Pass prompt, duration, quality (540p or 720p), aspect ratio (9:16)
    - Configure S3 output location with path structure: stepbystep/{source}/{direction}/{timestamp}/shot_NN/
    - Return invocation ARN for polling
    - _Requirements: 9.2, 9.3, 12.3, 12.4_
  
  - [x] 12.3 Implement poll_jobs() with GetAsyncInvoke
    - Poll GetAsyncInvoke every 10 seconds for each job
    - Implement exponential backoff on throttling (2s, 4s, 8s, 16s)
    - Track job status (InProgress, Completed, Failed)
    - Return list of completed job results with S3 paths
    - _Requirements: 9.4_
  
  - [ ]* 12.4 Write property tests for render pipeline
    - **Property 16: Render pipeline submits one request per shot**
    - **Property 17: Render pipeline uses correct shot durations**
    - **Property 18: Render pipeline downloads all completed clips**
    - **Validates: Requirements 9.2, 9.3, 9.5**
  
  - [ ]* 12.5 Write unit tests for Bedrock integration
    - Test StartAsyncInvoke called with correct parameters
    - Test polling stops when all jobs complete
    - Test exponential backoff on throttling
    - _Requirements: 9.2, 9.4_

- [x] 13. Implement S3 download and FFmpeg stitch
  - [x] 13.1 Implement download_clips() from S3
    - Download video clips from S3 paths returned by poll_jobs()
    - Retry once on download failure
    - Log error and mark shot as failed if both attempts fail
    - _Requirements: 9.5_
  
  - [x] 13.2 Implement stitch_clips() with FFmpeg
    - Trim each clip to exact shot duration using FFmpeg -t flag
    - Create concat list file with clips in shot order
    - Concatenate clips using FFmpeg concat demuxer
    - Output final 9:16 vertical video
    - _Requirements: 9.6, 9.7_
  
  - [x] 13.3 Add FFmpeg availability check
    - Check if FFmpeg is installed on system
    - Exit with installation instructions if missing
    - _Requirements: 9.6_
  
  - [ ]* 13.4 Write property tests for FFmpeg operations
    - **Property 19: FFmpeg trims clips to exact duration**
    - **Property 20: FFmpeg concatenates clips in shot order**
    - **Validates: Requirements 9.6, 9.7**
  
  - [ ]* 13.5 Write unit tests for S3 and FFmpeg
    - Test S3 download retry logic
    - Test FFmpeg concat list format
    - _Requirements: 9.5, 9.6, 9.7_

- [ ] 14. Implement error handling and resilience
  - [ ] 14.1 Add individual shot failure handling
    - Log error with shot ID and error message
    - Continue processing remaining shots
    - Mark failed shots in final summary
    - _Requirements: 9.9_
  
  - [ ] 14.2 Add pipeline-level error handling
    - Exit with error code if all shots fail
    - Display summary of all failures
    - Handle Bedrock throttling with exponential backoff
    - Handle S3 download failures with retry
    - _Requirements: 9.9_
  
  - [ ]* 14.3 Write property test for error resilience
    - **Property 21: Individual render failures don't stop pipeline**
    - **Validates: Requirements 9.9**
  
  - [ ]* 14.4 Write unit tests for error handling
    - Test pipeline continues when one shot fails
    - Test pipeline exits when all shots fail
    - _Requirements: 9.9_

- [ ] 15. Checkpoint - Ensure render pipeline core is complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 16. Implement cost estimator
  - [x] 16.1 Implement estimate_cost() function
    - Sum all shot durations from storyboard
    - Calculate previz cost: total_duration × $0.75
    - Calculate full quality cost: total_duration × $1.50
    - Return CostEstimate object with both costs and total duration
    - _Requirements: 11.1, 11.2, 11.3_
  
  - [x] 16.2 Add cost display and confirmation
    - Display both previz and full quality cost estimates before render
    - Prompt user for confirmation (unless dry-run mode)
    - Exit gracefully if user declines
    - _Requirements: 11.4_
  
  - [x] 16.3 Implement actual cost calculation
    - Calculate actual cost based on rendered clip durations (not requested durations)
    - Display cost per shot breakdown
    - Display total actual cost in final summary
    - _Requirements: 14.1, 14.2_
  
  - [ ]* 16.4 Write property tests for cost calculation
    - **Property 24: Cost calculation sums shot durations**
    - **Property 25: Previz cost formula**
    - **Property 26: Full quality cost formula**
    - **Property 27: Quality mode sets correct resolution**
    - **Property 31: Actual cost uses rendered durations**
    - **Validates: Requirements 11.1, 11.2, 11.3, 12.3, 12.4, 14.1**
  
  - [ ]* 16.5 Write unit tests for cost manager
    - Test cost calculation: 3 shots × 5s = 15s × $0.75 = $11.25 previz
    - Test cost calculation: 3 shots × 5s = 15s × $1.50 = $22.50 full
    - _Requirements: 11.1, 11.2, 11.3_

- [x] 17. Implement CLI interface with argparse
  - [x] 17.1 Add command-line argument parsing
    - Add --storyboard argument for JSON file path
    - Add --quality argument (previz or full)
    - Add --reference-dir argument for reference images directory
    - Add --dry-run flag
    - Add --output argument for final video path
    - _Requirements: 13.1_
  
  - [x] 17.2 Wire CLI to render pipeline
    - Load storyboard JSON from --storyboard path
    - Pass quality mode to render_storyboard()
    - Pass reference_dir to render_storyboard()
    - Pass dry_run flag to render_storyboard()
    - _Requirements: 13.1_
  
  - [x] 17.3 Implement dry-run mode
    - Skip StartAsyncInvoke API calls in dry-run mode
    - Log all prompts and parameters that would be sent
    - Display cost estimates without confirmation prompt
    - Execute all other pipeline steps
    - _Requirements: 13.1, 13.2, 13.3_
  
  - [ ]* 17.4 Write property tests for dry-run mode
    - **Property 28: Dry-run mode skips API invocation**
    - **Property 29: Dry-run mode logs prompts and parameters**
    - **Property 30: Dry-run mode skips confirmation**
    - **Validates: Requirements 13.1, 13.2, 13.3**
  
  - [ ]* 17.5 Write unit tests for CLI
    - Test argument parsing
    - Test dry-run mode skips API calls
    - _Requirements: 13.1, 13.2, 13.3_

- [ ] 18. Add final summary and logging
  - [x] 18.1 Implement render summary display
    - Display total render time (wall clock)
    - Display actual total cost
    - Display cost per shot breakdown
    - Display shot success/failure status
    - Display output video path
    - _Requirements: 14.2, 14.3_
  
  - [ ]* 18.2 Write unit tests for summary
    - Test summary includes all required fields
    - _Requirements: 14.2, 14.3_

- [ ] 19. Checkpoint - Ensure render pipeline is complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 20. End-to-end validation with dry-run
  - [ ] 20.1 Run dry-run for all 14 source × direction combinations
    - Test jesse.json baseline + 6 directions (7 total)
    - Test changeless.json baseline + 6 directions (7 total)
    - Verify prompt formatting is correct
    - Verify cost estimates are accurate
    - Verify shot count matches storyboard
    - _Requirements: All acceptance criteria_
  
  - [ ]* 20.2 Write integration tests for dry-run validation
    - Test all 14 combinations produce valid output
    - _Requirements: All acceptance criteria_

- [ ] 21. Live render smoke test
  - [ ] 21.1 Execute single-shot minimalist render at 540p
    - Select minimalist direction variant
    - Use previz quality (540p)
    - Verify full pipeline execution
    - Document actual render time
    - Document actual cost
    - _Requirements: All acceptance criteria_
  
  - [ ]* 21.2 Write integration test for live render
    - Test full pipeline from JSON to video
    - _Requirements: All acceptance criteria_

- [ ] 22. Create IAM policy and deployment documentation
  - [x] 22.1 Write IAM policy document
    - Document required permissions: bedrock:InvokeModel, bedrock:StartAsyncInvoke, bedrock:GetAsyncInvoke
    - Document required S3 permissions: s3:PutObject, s3:GetObject, s3:ListBucket
    - Provide example IAM policy JSON
    - _Requirements: 9.2, 9.4, 9.5_
  
  - [ ] 22.2 Document Bedrock model enablement
    - Document how to enable luma.ray-v2:0 model in us-west-2
    - Document model access request process
    - _Requirements: 9.2_
  
  - [ ] 22.3 Document FFmpeg installation
    - Provide installation instructions for macOS, Linux, Windows
    - Document required FFmpeg version
    - _Requirements: 9.6_
  
  - [x] 22.4 Write quickstart README
    - Document React artifact usage (load source, apply direction, export JSON)
    - Document Python CLI usage (all flags and arguments)
    - Provide example commands
    - Document expected output
    - _Requirements: All acceptance criteria_

- [ ] 23. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at phase boundaries
- Property tests validate universal correctness properties from design document
- Unit tests validate specific examples and edge cases
- The React artifact uses JavaScript/JSX for frontend implementation
- The render pipeline uses Python for backend CLI implementation
- All 35 correctness properties from the design document are covered by property tests
