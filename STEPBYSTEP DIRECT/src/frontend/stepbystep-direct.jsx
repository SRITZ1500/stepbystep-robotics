import React, { useState, useEffect } from 'react';
import { applyDirection } from '../shared/resolve_direction.js';
import { themes, getTheme, applyThemeToDOM, loadThemeFromStorage, saveThemeToStorage } from '../shared/themes.js';
import jesseSource from '../storyboards/jesse.json';
import changelessSource from '../storyboards/changeless.json';

// Source registry
const SOURCES = {
  jesse: jesseSource,
  changeless: changelessSource
};

export default function StepByStepDirect() {
  // State management
  const [currentTheme, setCurrentTheme] = useState('claude');
  const [currentSource, setCurrentSource] = useState('jesse');
  const [currentDirection, setCurrentDirection] = useState(null);
  const [storyboard, setStoryboard] = useState(null);
  const [directionInput, setDirectionInput] = useState('');
  const [isTransitioning, setIsTransitioning] = useState(false);

  // Load theme from localStorage on mount
  useEffect(() => {
    const savedTheme = loadThemeFromStorage();
    setCurrentTheme(savedTheme);
    applyThemeToDOM(getTheme(savedTheme));
  }, []);

  // Load initial storyboard
  useEffect(() => {
    const source = SOURCES[currentSource];
    const resolved = applyDirection(source, currentDirection);
    setStoryboard(resolved);
  }, [currentSource, currentDirection]);

  // Handle theme change
  const handleThemeChange = (themeKey) => {
    setCurrentTheme(themeKey);
    const theme = getTheme(themeKey);
    applyThemeToDOM(theme);
    saveThemeToStorage(themeKey);
  };

  // Handle source change
  const handleSourceChange = (sourceKey) => {
    setIsTransitioning(true);
    setTimeout(() => {
      setCurrentSource(sourceKey);
      setCurrentDirection(null);
      setDirectionInput('');
      window.scrollTo(0, 0);
      setIsTransitioning(false);
    }, 400);
  };

  // Handle direction application
  const handleApplyDirection = (directionKey) => {
    if (!directionKey) return;
    
    setIsTransitioning(true);
    setTimeout(() => {
      setCurrentDirection(directionKey);
      setDirectionInput('');
      window.scrollTo(0, 0);
      setIsTransitioning(false);
    }, 400);
  };

  // Handle direction input submit
  const handleDirectionSubmit = (e) => {
    e.preventDefault();
    const normalized = directionInput.toLowerCase().trim();
    if (normalized) {
      handleApplyDirection(normalized);
    }
  };

  // Get available directions for current source
  const getAvailableDirections = () => {
    const source = SOURCES[currentSource];
    return Object.keys(source.directions || {});
  };

  // Get current theme object
  const theme = getTheme(currentTheme);

  if (!storyboard) {
    return <div style={{ padding: '2rem', color: 'var(--text)' }}>Loading...</div>;
  }

  return (
    <div className="stepbystep-container">
      <style>{`
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
          background: var(--bg);
          color: var(--text);
          line-height: 1.6;
          transition: background-color 0.4s ease, color 0.4s ease;
        }

        .stepbystep-container {
          min-height: 100vh;
          padding-bottom: 120px;
        }

        /* Header */
        .header {
          background: var(--surface);
          border-bottom: 1px solid var(--border-subtle);
          padding: 1.5rem 2rem;
          position: sticky;
          top: 0;
          z-index: 100;
          transition: background-color 0.4s ease;
        }

        .header-top {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
        }

        .header-title {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .title {
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--text);
        }

        .subtitle {
          font-size: 0.875rem;
          color: var(--text-secondary);
        }

        .version-tag {
          display: inline-block;
          padding: 0.25rem 0.5rem;
          background: var(--tag);
          border: 1px solid var(--accent);
          border-radius: 4px;
          font-size: 0.75rem;
          font-weight: 600;
          color: var(--accent);
          font-family: 'Monaco', 'Courier New', monospace;
        }

        /* Theme Switcher */
        .theme-switcher {
          display: flex;
          gap: 0.5rem;
        }

        .theme-button {
          width: 40px;
          height: 40px;
          border: 2px solid transparent;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.625rem;
          font-weight: 700;
          color: white;
          font-family: 'Monaco', 'Courier New', monospace;
        }

        .theme-button:hover {
          transform: scale(1.1);
          border-color: var(--accent);
        }

        .theme-button.active {
          border-color: var(--accent);
          box-shadow: 0 0 0 2px var(--bg), 0 0 0 4px var(--accent);
        }

        .theme-button.flyers {
          background: #F74902;
        }

        .theme-button.claude {
          background: #DA7756;
        }

        .theme-button.amazon {
          background: #FF9900;
        }

        /* Source Tabs */
        .source-tabs {
          display: flex;
          gap: 0.5rem;
        }

        .source-tab {
          padding: 0.5rem 1rem;
          background: transparent;
          border: none;
          border-bottom: 2px solid transparent;
          color: var(--text-secondary);
          cursor: pointer;
          font-size: 0.875rem;
          font-weight: 500;
          transition: all 0.3s ease;
        }

        .source-tab:hover {
          color: var(--text);
          background: var(--bgAlt);
        }

        .source-tab.active {
          color: var(--accent);
          border-bottom-color: var(--accent);
          background: var(--bgAlt);
        }

        /* Main Content */
        .main-content {
          max-width: 900px;
          margin: 0 auto;
          padding: 2rem;
          opacity: 1;
          transition: opacity 0.4s ease;
        }

        .main-content.transitioning {
          opacity: 0.12;
        }

        /* Fixed Input Bar */
        .input-bar {
          position: fixed;
          bottom: 0;
          left: 0;
          right: 0;
          background: var(--surface);
          border-top: 1px solid var(--border-subtle);
          padding: 1rem 2rem;
          z-index: 100;
          transition: background-color 0.4s ease;
        }

        .input-bar::before {
          content: '';
          position: absolute;
          top: -40px;
          left: 0;
          right: 0;
          height: 40px;
          background: var(--gradient);
          pointer-events: none;
        }

        .direction-form {
          max-width: 900px;
          margin: 0 auto;
          display: flex;
          gap: 0.75rem;
          margin-bottom: 0.75rem;
        }

        .direction-input {
          flex: 1;
          padding: 0.75rem 1rem;
          background: var(--input-bg);
          border: 1px solid var(--border-subtle);
          border-radius: 6px;
          color: var(--text);
          font-size: 0.875rem;
          transition: all 0.3s ease;
        }

        .direction-input:focus {
          outline: none;
          border-color: var(--accent);
          box-shadow: 0 0 0 3px var(--border);
        }

        .direction-submit {
          padding: 0.75rem 1.5rem;
          background: var(--accent);
          border: none;
          border-radius: 6px;
          color: white;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .direction-submit:hover {
          background: var(--accent-hover);
          transform: translateY(-1px);
        }

        .direction-submit:active {
          transform: translateY(0);
        }

        /* Direction Pills */
        .direction-pills {
          max-width: 900px;
          margin: 0 auto;
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
        }

        .direction-pill {
          padding: 0.5rem 1rem;
          background: var(--pill);
          border: 1px solid var(--pill-border);
          border-radius: 20px;
          color: var(--text);
          font-size: 0.75rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
          text-transform: capitalize;
        }

        .direction-pill:hover {
          background: var(--accent);
          border-color: var(--accent);
          color: white;
          transform: translateY(-2px);
        }

        /* Direction History */
        .direction-history {
          margin-bottom: 2rem;
          padding: 1rem;
          background: var(--surface);
          border: 1px solid var(--border-subtle);
          border-radius: 6px;
          font-family: 'Monaco', 'Courier New', monospace;
          font-size: 0.75rem;
          color: var(--text-secondary);
        }

        .direction-history-path {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          flex-wrap: wrap;
        }

        .direction-history-item {
          color: var(--text-muted);
        }

        .direction-history-item.current {
          color: var(--accent);
          font-weight: 700;
        }

        .direction-history-arrow {
          color: var(--text-dim);
        }
      `}</style>

      {/* Header */}
      <header className="header">
        <div className="header-top">
          <div className="header-title">
            <h1 className="title">StepByStep Direct</h1>
            <p className="subtitle">
              {SOURCES[currentSource].label} • {SOURCES[currentSource].subtitle}
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span className="version-tag">v1.0</span>
            <div className="theme-switcher">
              {Object.keys(themes).map(key => (
                <button
                  key={key}
                  className={`theme-button ${key} ${currentTheme === key ? 'active' : ''}`}
                  onClick={() => handleThemeChange(key)}
                  title={themes[key].name}
                >
                  {themes[key].abbr}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Source Tabs */}
        <div className="source-tabs">
          {Object.keys(SOURCES).map(key => (
            <button
              key={key}
              className={`source-tab ${currentSource === key ? 'active' : ''}`}
              onClick={() => handleSourceChange(key)}
            >
              {SOURCES[key].label}
            </button>
          ))}
        </div>
      </header>

      {/* Main Content */}
      <main className={`main-content ${isTransitioning ? 'transitioning' : ''}`}>
        {/* Direction History */}
        {storyboard.directionHistory && storyboard.directionHistory.length > 0 && (
          <div className="direction-history">
            <div className="direction-history-path">
              <span className="direction-history-item">baseline</span>
              {storyboard.directionHistory.map((dir, index) => (
                <React.Fragment key={index}>
                  <span className="direction-history-arrow">→</span>
                  <span className={`direction-history-item ${index === storyboard.directionHistory.length - 1 ? 'current' : ''}`}>
                    {dir}
                  </span>
                </React.Fragment>
              ))}
            </div>
          </div>
        )}

        {/* Storyboard Content - Will be implemented in next tasks */}
        <div style={{ padding: '2rem', background: 'var(--surface)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
          <h2 style={{ marginBottom: '1rem', color: 'var(--accent)' }}>Concept</h2>
          <p style={{ marginBottom: '2rem', color: 'var(--text-secondary)' }}>{storyboard.concept}</p>

          <h2 style={{ marginBottom: '1rem', color: 'var(--accent)' }}>Shots ({storyboard.shots.length})</h2>
          {storyboard.shots.map(shot => (
            <div key={shot.id} style={{ marginBottom: '1.5rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
              <div style={{ fontFamily: 'Monaco, monospace', color: 'var(--accent)', marginBottom: '0.5rem' }}>
                Shot {shot.id} • {shot.duration}s
              </div>
              <div style={{ marginBottom: '0.5rem' }}>
                <strong style={{ color: 'var(--text)' }}>Frame:</strong> <span style={{ color: 'var(--text-secondary)' }}>{shot.frame}</span>
              </div>
              <div style={{ marginBottom: '0.5rem' }}>
                <strong style={{ color: 'var(--text)' }}>Audio:</strong> <span style={{ color: 'var(--text-secondary)' }}>{shot.audio}</span>
              </div>
              <div>
                <strong style={{ color: 'var(--text)' }}>Value Shift:</strong> <span style={{ color: 'var(--text-secondary)' }}>{shot.valueShift}</span>
              </div>
            </div>
          ))}
        </div>
      </main>

      {/* Fixed Input Bar */}
      <div className="input-bar">
        <form className="direction-form" onSubmit={handleDirectionSubmit}>
          <input
            type="text"
            className="direction-input"
            placeholder="Enter direction (e.g., darker, funnier, tender)..."
            value={directionInput}
            onChange={(e) => setDirectionInput(e.target.value)}
          />
          <button type="submit" className="direction-submit">
            Direct
          </button>
        </form>

        <div className="direction-pills">
          {getAvailableDirections()
            .filter(dir => dir !== currentDirection)
            .map(dir => (
              <button
                key={dir}
                className="direction-pill"
                onClick={() => handleApplyDirection(dir)}
              >
                {dir}
              </button>
            ))}
        </div>
      </div>
    </div>
  );
}
