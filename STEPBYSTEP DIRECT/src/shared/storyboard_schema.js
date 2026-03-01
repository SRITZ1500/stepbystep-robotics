/**
 * StepByStep Direct Storyboard Schema
 * JSON Schema definitions for screenplay storyboards with creative direction variants
 */

export const schema = {
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "StepByStep Direct Storyboard Schema",
  "description": "Schema for screenplay storyboards with creative direction variants",
  
  "definitions": {
    "Shot": {
      "type": "object",
      "required": ["id", "frame", "audio", "duration", "valueShift"],
      "properties": {
        "id": {
          "type": "integer",
          "minimum": 1,
          "description": "Unique shot identifier"
        },
        "frame": {
          "type": "string",
          "minLength": 1,
          "description": "Visual description of what fills the 9:16 frame"
        },
        "audio": {
          "type": "string",
          "minLength": 1,
          "description": "Sound design specification - dialogue, ambient, music, silence"
        },
        "duration": {
          "type": "integer",
          "enum": [5, 9],
          "description": "Clip length in seconds (5 or 9)"
        },
        "valueShift": {
          "type": "string",
          "minLength": 1,
          "description": "Narrative purpose - emotional transformation"
        }
      }
    },
    
    "StormCloud": {
      "type": "object",
      "required": ["detail", "rating"],
      "properties": {
        "detail": {
          "type": "string",
          "minLength": 1,
          "description": "The planted detail that pays off"
        },
        "rating": {
          "type": "string",
          "enum": ["INVISIBLE", "WELL-HIDDEN", "TOO OBVIOUS"],
          "description": "Subtlety rating of the storm cloud seed"
        }
      }
    },
    
    "Platform": {
      "type": "object",
      "required": ["length", "hook", "loop", "soundOff"],
      "properties": {
        "length": {
          "type": "string",
          "description": "Target video length"
        },
        "hook": {
          "type": "string",
          "description": "First 1.5 seconds description"
        },
        "loop": {
          "type": "string",
          "description": "Loop/replay strategy with reasoning"
        },
        "soundOff": {
          "type": "string",
          "description": "Sound-off viewing viability assessment"
        }
      }
    },
    
    "Storyboard": {
      "type": "object",
      "required": ["concept", "shots", "invisibleWide", "stormCloud", "platform"],
      "properties": {
        "concept": {
          "type": "string",
          "maxLength": 300,
          "description": "Logline text, 50 words max"
        },
        "shots": {
          "type": "array",
          "minItems": 5,
          "maxItems": 8,
          "items": { "$ref": "#/definitions/Shot" },
          "description": "5-8 shot objects"
        },
        "invisibleWide": {
          "type": "string",
          "minLength": 1,
          "description": "Description of the off-frame world"
        },
        "stormCloud": {
          "$ref": "#/definitions/StormCloud"
        },
        "platform": {
          "$ref": "#/definitions/Platform"
        }
      }
    },
    
    "DirectionVariant": {
      "type": "object",
      "properties": {
        "label": {
          "type": "string",
          "description": "Display name for this direction"
        },
        "concept": {
          "type": "string",
          "description": "Replacement concept text"
        },
        "shotOverrides": {
          "type": "object",
          "patternProperties": {
            "^[0-9]+$": {
              "type": "object",
              "properties": {
                "frame": { "type": "string" },
                "audio": { "type": "string" },
                "duration": { "type": "integer", "enum": [5, 9] },
                "valueShift": { "type": "string" }
              }
            }
          },
          "description": "Shot overrides by shot ID (overlay mode)"
        },
        "shots": {
          "type": "array",
          "minItems": 5,
          "maxItems": 8,
          "items": { "$ref": "#/definitions/Shot" },
          "description": "Full shot replacement (replacement mode)"
        },
        "invisibleWide": {
          "type": "string",
          "description": "Replacement invisible wide text"
        },
        "stormCloud": {
          "$ref": "#/definitions/StormCloud"
        },
        "platform": {
          "$ref": "#/definitions/Platform"
        }
      }
    },
    
    "Source": {
      "type": "object",
      "required": ["label", "subtitle", "baseline", "directions"],
      "properties": {
        "label": {
          "type": "string",
          "minLength": 1,
          "description": "Display name"
        },
        "subtitle": {
          "type": "string",
          "minLength": 1,
          "description": "Scene location / context"
        },
        "baseline": {
          "$ref": "#/definitions/Storyboard",
          "description": "Original storyboard"
        },
        "directions": {
          "type": "object",
          "patternProperties": {
            "^[a-z]+$": {
              "$ref": "#/definitions/DirectionVariant"
            }
          },
          "description": "Available direction transformations"
        }
      }
    }
  },
  
  "oneOf": [
    { "$ref": "#/definitions/Source" },
    { "$ref": "#/definitions/Storyboard" },
    { "$ref": "#/definitions/DirectionVariant" }
  ]
};

export default schema;
