/**
 * Direction Resolution Module
 * Applies creative direction transformations to storyboards
 */

/**
 * Apply a direction transformation to a storyboard
 * @param {Object} source - Source object containing baseline and directions
 * @param {string|null} directionKey - Direction key to apply (null for baseline)
 * @returns {Object} Resolved storyboard with direction applied
 */
export function applyDirection(source, directionKey) {
  // If no direction specified, return baseline
  if (!directionKey || directionKey === 'baseline') {
    return {
      ...source.baseline,
      directionHistory: []
    };
  }

  // Get the direction variant
  const direction = source.directions[directionKey];
  
  // If direction doesn't exist, return baseline unchanged
  if (!direction) {
    console.warn(`Direction "${directionKey}" not found, returning baseline`);
    return {
      ...source.baseline,
      directionHistory: []
    };
  }

  const baseline = source.baseline;
  let finalShots;

  // Check if this is full replacement mode (direction has its own shots array)
  if (direction.shots && Array.isArray(direction.shots)) {
    // Full replacement mode: use direction's shots entirely
    finalShots = direction.shots;
  } else if (direction.shotOverrides) {
    // Overlay mode: merge shot overrides onto baseline shots
    finalShots = baseline.shots.map(shot => {
      const override = direction.shotOverrides[shot.id];
      if (override) {
        // Merge override fields onto baseline shot
        return {
          ...shot,
          ...override
        };
      }
      return shot;
    });
  } else {
    // No shot modifications, use baseline shots
    finalShots = baseline.shots;
  }

  // Build the resolved storyboard
  return {
    concept: direction.concept ?? baseline.concept,
    shots: finalShots,
    invisibleWide: direction.invisibleWide ?? baseline.invisibleWide,
    stormCloud: direction.stormCloud ?? baseline.stormCloud,
    platform: direction.platform ?? baseline.platform,
    directionHistory: [directionKey]
  };
}

/**
 * Apply multiple directions in sequence
 * @param {Object} source - Source object containing baseline and directions
 * @param {string[]} directionKeys - Array of direction keys to apply in order
 * @returns {Object} Resolved storyboard with all directions applied
 */
export function applyDirectionSequence(source, directionKeys) {
  if (!directionKeys || directionKeys.length === 0) {
    return {
      ...source.baseline,
      directionHistory: []
    };
  }

  // For now, we only support single direction application
  // Multi-direction sequencing would require more complex merging logic
  const lastDirection = directionKeys[directionKeys.length - 1];
  const result = applyDirection(source, lastDirection);
  
  // Set full history
  result.directionHistory = directionKeys.filter(key => 
    key && key !== 'baseline' && source.directions[key]
  );
  
  return result;
}

/**
 * Validate that a storyboard has the correct structure
 * @param {Object} storyboard - Storyboard to validate
 * @returns {Object} { valid: boolean, errors: string[] }
 */
export function validateStoryboard(storyboard) {
  const errors = [];

  if (!storyboard) {
    return { valid: false, errors: ['Storyboard is null or undefined'] };
  }

  // Check required fields
  if (!storyboard.concept) errors.push('Missing concept field');
  if (!storyboard.shots) errors.push('Missing shots array');
  if (!storyboard.invisibleWide) errors.push('Missing invisibleWide field');
  if (!storyboard.stormCloud) errors.push('Missing stormCloud field');
  if (!storyboard.platform) errors.push('Missing platform field');

  // Validate shots array
  if (storyboard.shots) {
    if (!Array.isArray(storyboard.shots)) {
      errors.push('shots must be an array');
    } else {
      if (storyboard.shots.length < 5) {
        errors.push(`shots array must have at least 5 items, has ${storyboard.shots.length}`);
      }
      if (storyboard.shots.length > 8) {
        errors.push(`shots array must have at most 8 items, has ${storyboard.shots.length}`);
      }

      // Validate each shot
      storyboard.shots.forEach((shot, index) => {
        if (!shot.id) errors.push(`Shot ${index} missing id field`);
        if (!shot.frame) errors.push(`Shot ${index} missing frame field`);
        if (!shot.audio) errors.push(`Shot ${index} missing audio field`);
        if (!shot.duration) errors.push(`Shot ${index} missing duration field`);
        if (shot.duration && shot.duration !== 5 && shot.duration !== 9) {
          errors.push(`Shot ${index} duration must be 5 or 9, got ${shot.duration}`);
        }
        if (!shot.valueShift) errors.push(`Shot ${index} missing valueShift field`);
      });
    }
  }

  // Validate stormCloud
  if (storyboard.stormCloud) {
    if (!storyboard.stormCloud.detail) errors.push('stormCloud missing detail field');
    if (!storyboard.stormCloud.rating) errors.push('stormCloud missing rating field');
    if (storyboard.stormCloud.rating && 
        !['INVISIBLE', 'WELL-HIDDEN', 'TOO OBVIOUS'].includes(storyboard.stormCloud.rating)) {
      errors.push(`stormCloud rating must be INVISIBLE, WELL-HIDDEN, or TOO OBVIOUS, got ${storyboard.stormCloud.rating}`);
    }
  }

  // Validate platform
  if (storyboard.platform) {
    if (!storyboard.platform.length) errors.push('platform missing length field');
    if (!storyboard.platform.hook) errors.push('platform missing hook field');
    if (!storyboard.platform.loop) errors.push('platform missing loop field');
    if (!storyboard.platform.soundOff) errors.push('platform missing soundOff field');
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

export default {
  applyDirection,
  applyDirectionSequence,
  validateStoryboard
};
