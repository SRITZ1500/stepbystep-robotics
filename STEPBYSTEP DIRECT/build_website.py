#!/usr/bin/env python3
"""
Build a self-contained HTML file with all assets embedded
"""

import json

# Read the source files
with open('src/storyboards/jesse.json', 'r') as f:
    jesse_data = f.read()

with open('src/storyboards/changeless.json', 'r') as f:
    changeless_data = f.read()

with open('src/shared/resolve_direction.js', 'r') as f:
    resolve_direction_code = f.read()

with open('src/shared/themes.js', 'r') as f:
    themes_code = f.read()

with open('src/frontend/stepbystep-direct.jsx', 'r') as f:
    react_component = f.read()

# Build the complete HTML
html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>StepByStep Direct</title>
  <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
  <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
</head>
<body>
  <div id="root"></div>

  <script type="text/babel">
    const {{ useState, useEffect }} = React;

    // ============================================================================
    // EMBEDDED DATA
    // ============================================================================
    
    const jesseSource = {jesse_data};
    const changelessSource = {changeless_data};

    // ============================================================================
    // THEME SYSTEM
    // ============================================================================
    
    const themes = {{
      flyers: {{
        name: "Flyers", abbr: "PHI", bg: "#1A1A1A", bgAlt: "#242424", surface: "#2A2A2A",
        accent: "#F74902", accentHover: "#FF5A1A", text: "#FFFFFF", textSecondary: "#C4C4C4",
        textMuted: "#888888", textDim: "#666666", border: "rgba(247, 73, 2, 0.15)",
        borderSubtle: "rgba(255, 255, 255, 0.1)", inputBg: "#2A2A2A",
        gradient: "linear-gradient(135deg, rgba(247, 73, 2, 0.1) 0%, rgba(247, 73, 2, 0) 100%)",
        ratingGood: "#10B981", ratingMid: "#F59E0B", ratingBad: "#EF4444",
        pill: "rgba(247, 73, 2, 0.1)", pillBorder: "rgba(247, 73, 2, 0.3)", tag: "rgba(247, 73, 2, 0.2)"
      }},
      claude: {{
        name: "Claude", abbr: "ANTH", bg: "#2D2B28", bgAlt: "#3D3A35", surface: "#3D3A35",
        accent: "#DA7756", accentHover: "#E68A6A", text: "#F5F0EB", textSecondary: "#C7BFB6",
        textMuted: "#998F84", textDim: "#7A7067", border: "rgba(218, 119, 86, 0.18)",
        borderSubtle: "rgba(245, 240, 235, 0.1)", inputBg: "#3D3A35",
        gradient: "linear-gradient(135deg, rgba(218, 119, 86, 0.1) 0%, rgba(218, 119, 86, 0) 100%)",
        ratingGood: "#10B981", ratingMid: "#F59E0B", ratingBad: "#EF4444",
        pill: "rgba(218, 119, 86, 0.1)", pillBorder: "rgba(218, 119, 86, 0.3)", tag: "rgba(218, 119, 86, 0.2)"
      }},
      amazon: {{
        name: "Amazon", abbr: "AMZN", bg: "#0F1111", bgAlt: "#1A1F23", surface: "#1A1F23",
        accent: "#FF9900", accentHover: "#FFB84D", text: "#E8EAED", textSecondary: "#A8B1BA",
        textMuted: "#6B7785", textDim: "#4D5761", border: "rgba(255, 153, 0, 0.15)",
        borderSubtle: "rgba(232, 234, 237, 0.1)", inputBg: "#1A1F23",
        gradient: "linear-gradient(135deg, rgba(255, 153, 0, 0.1) 0%, rgba(255, 153, 0, 0) 100%)",
        ratingGood: "#10B981", ratingMid: "#F59E0B", ratingBad: "#EF4444",
        pill: "rgba(255, 153, 0, 0.1)", pillBorder: "rgba(255, 153, 0, 0.3)", tag: "rgba(255, 153, 0, 0.2)"
      }}
    }};

    function getTheme(themeKey) {{
      return themes[themeKey] || themes.claude;
    }}

    function applyThemeToDOM(theme) {{
      const root = document.documentElement;
      Object.entries(theme).forEach(([key, value]) => {{
        if (key !== 'name' && key !== 'abbr') {{
          const cssVar = '--' + key.replace(/([A-Z])/g, '-$1').toLowerCase();
          root.style.setProperty(cssVar, value);
        }}
      }});
    }}

    function loadThemeFromStorage() {{
      return localStorage.getItem('stepbystep-theme') || 'claude';
    }}

    function saveThemeToStorage(themeKey) {{
      localStorage.setItem('stepbystep-theme', themeKey);
    }}

    // ============================================================================
    // DIRECTION RESOLUTION
    // ============================================================================
    
    function applyDirection(source, directionKey) {{
      if (!directionKey || directionKey === 'baseline') {{
        return {{ ...source.baseline, directionHistory: [] }};
      }}

      const direction = source.directions[directionKey];
      if (!direction) {{
        return {{ ...source.baseline, directionHistory: [] }};
      }}

      const baseline = source.baseline;
      let finalShots;

      if (direction.shots && Array.isArray(direction.shots)) {{
        finalShots = direction.shots;
      }} else if (direction.shotOverrides) {{
        finalShots = baseline.shots.map(shot => {{
          const override = direction.shotOverrides[shot.id];
          return override ? {{ ...shot, ...override }} : shot;
        }});
      }} else {{
        finalShots = baseline.shots;
      }}

      return {{
        concept: direction.concept ?? baseline.concept,
        shots: finalShots,
        invisibleWide: direction.invisibleWide ?? baseline.invisibleWide,
        stormCloud: direction.stormCloud ?? baseline.stormCloud,
        platform: direction.platform ?? baseline.platform,
        directionHistory: [directionKey]
      }};
    }}

    // ============================================================================
    // MAIN COMPONENT
    // ============================================================================
    
    const SOURCES = {{
      jesse: jesseSource,
      changeless: changelessSource
    }};

    function StepByStepDirect() {{
      const [currentTheme, setCurrentTheme] = useState('claude');
      const [currentSource, setCurrentSource] = useState('jesse');
      const [currentDirection, setCurrentDirection] = useState(null);
      const [storyboard, setStoryboard] = useState(null);
      const [directionInput, setDirectionInput] = useState('');
      const [isTransitioning, setIsTransitioning] = useState(false);

      useEffect(() => {{
        const savedTheme = loadThemeFromStorage();
        setCurrentTheme(savedTheme);
        applyThemeToDOM(getTheme(savedTheme));
      }}, []);

      useEffect(() => {{
        const source = SOURCES[currentSource];
        const resolved = applyDirection(source, currentDirection);
        setStoryboard(resolved);
      }}, [currentSource, currentDirection]);

      const handleThemeChange = (themeKey) => {{
        setCurrentTheme(themeKey);
        applyThemeToDOM(getTheme(themeKey));
        saveThemeToStorage(themeKey);
      }};

      const handleSourceChange = (sourceKey) => {{
        setIsTransitioning(true);
        setTimeout(() => {{
          setCurrentSource(sourceKey);
          setCurrentDirection(null);
          setDirectionInput('');
          window.scrollTo(0, 0);
          setIsTransitioning(false);
        }}, 400);
      }};

      const handleApplyDirection = (directionKey) => {{
        if (!directionKey) return;
        setIsTransitioning(true);
        setTimeout(() => {{
          setCurrentDirection(directionKey);
          setDirectionInput('');
          window.scrollTo(0, 0);
          setIsTransitioning(false);
        }}, 400);
      }};

      const handleDirectionSubmit = (e) => {{
        e.preventDefault();
        const normalized = directionInput.toLowerCase().trim();
        if (normalized) {{
          handleApplyDirection(normalized);
        }}
      }};

      const getAvailableDirections = () => {{
        const source = SOURCES[currentSource];
        return Object.keys(source.directions || {{}});
      }};

      const theme = getTheme(currentTheme);

      if (!storyboard) {{
        return <div style={{{{ padding: '2rem', color: 'var(--text)' }}}}>Loading...</div>;
      }}

      const totalDuration = storyboard.shots.reduce((sum, shot) => sum + shot.duration, 0);

      return (
        <div className="stepbystep-container">
          <style>{{`
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
              background: var(--bg);
              color: var(--text);
              line-height: 1.6;
              transition: background-color 0.4s ease, color 0.4s ease;
            }}
            .stepbystep-container {{ min-height: 100vh; padding-bottom: 140px; }}
            .header {{
              background: var(--surface);
              border-bottom: 1px solid var(--border-subtle);
              padding: 1.5rem 2rem;
              position: sticky;
              top: 0;
              z-index: 100;
              transition: background-color 0.4s ease;
            }}
            .header-top {{
              display: flex;
              justify-content: space-between;
              align-items: center;
              margin-bottom: 1rem;
            }}
            .header-title {{ display: flex; flex-direction: column; gap: 0.25rem; }}
            .title {{ font-size: 1.5rem; font-weight: 700; color: var(--text); }}
            .subtitle {{ font-size: 0.875rem; color: var(--text-secondary); }}
            .version-tag {{
              display: inline-block;
              padding: 0.25rem 0.5rem;
              background: var(--tag);
              border: 1px solid var(--accent);
              border-radius: 4px;
              font-size: 0.75rem;
              font-weight: 600;
              color: var(--accent);
              font-family: Monaco, monospace;
            }}
            .theme-switcher {{ display: flex; gap: 0.5rem; }}
            .theme-button {{
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
              font-family: Monaco, monospace;
            }}
            .theme-button:hover {{ transform: scale(1.1); border-color: var(--accent); }}
            .theme-button.active {{
              border-color: var(--accent);
              box-shadow: 0 0 0 2px var(--bg), 0 0 0 4px var(--accent);
            }}
            .theme-button.flyers {{ background: #F74902; }}
            .theme-button.claude {{ background: #DA7756; }}
            .theme-button.amazon {{ background: #FF9900; }}
            .source-tabs {{ display: flex; gap: 0.5rem; }}
            .source-tab {{
              padding: 0.5rem 1rem;
              background: transparent;
              border: none;
              border-bottom: 2px solid transparent;
              color: var(--text-secondary);
              cursor: pointer;
              font-size: 0.875rem;
              font-weight: 500;
              transition: all 0.3s ease;
            }}
            .source-tab:hover {{ color: var(--text); background: var(--bg-alt); }}
            .source-tab.active {{
              color: var(--accent);
              border-bottom-color: var(--accent);
              background: var(--bg-alt);
            }}
            .main-content {{
              max-width: 900px;
              margin: 0 auto;
              padding: 2rem;
              opacity: 1;
              transition: opacity 0.4s ease;
            }}
            .main-content.transitioning {{ opacity: 0.12; }}
            .input-bar {{
              position: fixed;
              bottom: 0;
              left: 0;
              right: 0;
              background: var(--surface);
              border-top: 1px solid var(--border-subtle);
              padding: 1rem 2rem;
              z-index: 100;
              transition: background-color 0.4s ease;
            }}
            .input-bar::before {{
              content: '';
              position: absolute;
              top: -40px;
              left: 0;
              right: 0;
              height: 40px;
              background: var(--gradient);
              pointer-events: none;
            }}
            .direction-form {{
              max-width: 900px;
              margin: 0 auto;
              display: flex;
              gap: 0.75rem;
              margin-bottom: 0.75rem;
            }}
            .direction-input {{
              flex: 1;
              padding: 0.75rem 1rem;
              background: var(--input-bg);
              border: 1px solid var(--border-subtle);
              border-radius: 6px;
              color: var(--text);
              font-size: 0.875rem;
              transition: all 0.3s ease;
            }}
            .direction-input:focus {{
              outline: none;
              border-color: var(--accent);
              box-shadow: 0 0 0 3px var(--border);
            }}
            .direction-submit {{
              padding: 0.75rem 1.5rem;
              background: var(--accent);
              border: none;
              border-radius: 6px;
              color: white;
              font-weight: 600;
              cursor: pointer;
              transition: all 0.2s ease;
            }}
            .direction-submit:hover {{
              background: var(--accent-hover);
              transform: translateY(-1px);
            }}
            .direction-pills {{
              max-width: 900px;
              margin: 0 auto;
              display: flex;
              flex-wrap: wrap;
              gap: 0.5rem;
            }}
            .direction-pill {{
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
            }}
            .direction-pill:hover {{
              background: var(--accent);
              border-color: var(--accent);
              color: white;
              transform: translateY(-2px);
            }}
            .direction-history {{
              margin-bottom: 2rem;
              padding: 1rem;
              background: var(--surface);
              border: 1px solid var(--border-subtle);
              border-radius: 6px;
              font-family: Monaco, monospace;
              font-size: 0.75rem;
              color: var(--text-secondary);
            }}
            .direction-history-path {{
              display: flex;
              align-items: center;
              gap: 0.5rem;
              flex-wrap: wrap;
            }}
            .direction-history-item {{ color: var(--text-muted); }}
            .direction-history-item.current {{
              color: var(--accent);
              font-weight: 700;
            }}
            .direction-history-arrow {{ color: var(--text-dim); }}
            .content-section {{
              background: var(--surface);
              border: 1px solid var(--border-subtle);
              border-radius: 8px;
              padding: 2rem;
              margin-bottom: 2rem;
            }}
            .section-title {{
              font-size: 1.25rem;
              font-weight: 700;
              color: var(--accent);
              margin-bottom: 1rem;
            }}
            .section-subtitle {{
              font-family: Monaco, monospace;
              font-size: 0.75rem;
              color: var(--text-muted);
              margin-bottom: 1.5rem;
            }}
            .concept-text {{
              color: var(--text-secondary);
              line-height: 1.8;
              margin-bottom: 2rem;
            }}
            .shot-card {{
              margin-bottom: 1.5rem;
              padding-bottom: 1.5rem;
              border-bottom: 1px solid var(--border-subtle);
            }}
            .shot-card:last-child {{ border-bottom: none; }}
            .shot-header {{
              font-family: Monaco, monospace;
              color: var(--accent);
              font-weight: 700;
              margin-bottom: 0.75rem;
              font-size: 0.875rem;
            }}
            .shot-field {{
              margin-bottom: 0.5rem;
              display: flex;
              gap: 0.5rem;
            }}
            .shot-label {{
              font-weight: 600;
              color: var(--text);
              min-width: 100px;
            }}
            .shot-value {{
              color: var(--text-secondary);
              flex: 1;
            }}
            .invisible-wide {{
              background: var(--bg-alt);
              padding: 1.5rem;
              border-radius: 6px;
              border-left: 3px solid var(--accent);
              margin-bottom: 2rem;
            }}
            .invisible-wide-title {{
              font-size: 0.875rem;
              font-weight: 700;
              color: var(--accent);
              margin-bottom: 0.5rem;
              font-style: italic;
            }}
            .invisible-wide-text {{
              color: var(--text-secondary);
              font-style: italic;
              line-height: 1.7;
            }}
            .storm-cloud {{
              background: var(--bg-alt);
              padding: 1.5rem;
              border-radius: 6px;
              margin-bottom: 2rem;
            }}
            .storm-cloud-title {{
              font-size: 0.875rem;
              font-weight: 700;
              color: var(--text);
              margin-bottom: 0.75rem;
            }}
            .storm-cloud-detail {{
              color: var(--text-secondary);
              margin-bottom: 0.75rem;
            }}
            .storm-cloud-rating {{
              display: inline-block;
              padding: 0.25rem 0.75rem;
              border-radius: 4px;
              font-size: 0.75rem;
              font-weight: 700;
              font-family: Monaco, monospace;
            }}
            .rating-INVISIBLE {{
              background: var(--rating-good);
              color: white;
            }}
            .rating-WELL-HIDDEN {{
              background: var(--rating-mid);
              color: white;
            }}
            .rating-TOO-OBVIOUS {{
              background: var(--rating-bad);
              color: white;
            }}
            .platform-grid {{
              display: grid;
              grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
              gap: 1rem;
            }}
            .platform-item {{
              background: var(--bg-alt);
              padding: 1rem;
              border-radius: 6px;
            }}
            .platform-label {{
              font-size: 0.75rem;
              font-weight: 700;
              color: var(--text-muted);
              text-transform: uppercase;
              margin-bottom: 0.5rem;
            }}
            .platform-value {{
              color: var(--text-secondary);
              font-size: 0.875rem;
            }}
          `}}</style>

          <header className="header">
            <div className="header-top">
              <div className="header-title">
                <h1 className="title">StepByStep Direct</h1>
                <p className="subtitle">
                  {{SOURCES[currentSource].label}} • {{SOURCES[currentSource].subtitle}}
                </p>
              </div>
              <div style={{{{ display: 'flex', alignItems: 'center', gap: '1rem' }}}}>
                <span className="version-tag">v1.0</span>
                <div className="theme-switcher">
                  {{Object.keys(themes).map(key => (
                    <button
                      key={{key}}
                      className={{`theme-button ${{key}} ${{currentTheme === key ? 'active' : ''}}`}}
                      onClick={{() => handleThemeChange(key)}}
                      title={{themes[key].name}}
                    >
                      {{themes[key].abbr}}
                    </button>
                  ))}}
                </div>
              </div>
            </div>

            <div className="source-tabs">
              {{Object.keys(SOURCES).map(key => (
                <button
                  key={{key}}
                  className={{`source-tab ${{currentSource === key ? 'active' : ''}}`}}
                  onClick={{() => handleSourceChange(key)}}
                >
                  {{SOURCES[key].label}}
                </button>
              ))}}
            </div>
          </header>

          <main className={{`main-content ${{isTransitioning ? 'transitioning' : ''}}`}}>
            {{storyboard.directionHistory && storyboard.directionHistory.length > 0 && (
              <div className="direction-history">
                <div className="direction-history-path">
                  <span className="direction-history-item">baseline</span>
                  {{storyboard.directionHistory.map((dir, index) => (
                    <React.Fragment key={{index}}>
                      <span className="direction-history-arrow">→</span>
                      <span className={{`direction-history-item ${{index === storyboard.directionHistory.length - 1 ? 'current' : ''}}`}}>
                        {{dir}}
                      </span>
                    </React.Fragment>
                  ))}}
                </div>
              </div>
            )}}

            <div className="content-section">
              <h2 className="section-title">Concept</h2>
              <p className="concept-text">{{storyboard.concept}}</p>

              <h2 className="section-title">Shots</h2>
              <p className="section-subtitle">
                {{storyboard.shots.length}} shots • {{totalDuration}} seconds total
              </p>

              {{storyboard.shots.map(shot => (
                <div key={{shot.id}} className="shot-card">
                  <div className="shot-header">
                    Shot {{shot.id}} • {{shot.duration}}s
                  </div>
                  <div className="shot-field">
                    <span className="shot-label">Frame:</span>
                    <span className="shot-value">{{shot.frame}}</span>
                  </div>
                  <div className="shot-field">
                    <span className="shot-label">Audio:</span>
                    <span className="shot-value">{{shot.audio}}</span>
                  </div>
                  <div className="shot-field">
                    <span className="shot-label">Value Shift:</span>
                    <span className="shot-value">{{shot.valueShift}}</span>
                  </div>
                </div>
              ))}}
            </div>

            <div className="invisible-wide">
              <div className="invisible-wide-title">Invisible Wide</div>
              <div className="invisible-wide-text">{{storyboard.invisibleWide}}</div>
            </div>

            <div className="storm-cloud">
              <div className="storm-cloud-title">Storm Cloud</div>
              <div className="storm-cloud-detail">{{storyboard.stormCloud.detail}}</div>
              <span className={{`storm-cloud-rating rating-${{storyboard.stormCloud.rating.replace(/-/g, '-')}}`}}>
                {{storyboard.stormCloud.rating}}
              </span>
            </div>

            {{storyboard.platform && (
              <div className="content-section">
                <h2 className="section-title">Platform Notes</h2>
                <div className="platform-grid">
                  <div className="platform-item">
                    <div className="platform-label">Length</div>
                    <div className="platform-value">{{storyboard.platform.length}}</div>
                  </div>
                  <div className="platform-item">
                    <div className="platform-label">Hook</div>
                    <div className="platform-value">{{storyboard.platform.hook}}</div>
                  </div>
                  <div className="platform-item">
                    <div className="platform-label">Loop</div>
                    <div className="platform-value">{{storyboard.platform.loop}}</div>
                  </div>
                  <div className="platform-item">
                    <div className="platform-label">Sound Off</div>
                    <div className="platform-value">{{storyboard.platform.soundOff}}</div>
                  </div>
                </div>
              </div>
            )}}
          </main>

          <div className="input-bar">
            <form className="direction-form" onSubmit={{handleDirectionSubmit}}>
              <input
                type="text"
                className="direction-input"
                placeholder="Enter direction (e.g., darker, funnier, tender)..."
                value={{directionInput}}
                onChange={{(e) => setDirectionInput(e.target.value)}}
              />
              <button type="submit" className="direction-submit">
                Direct
              </button>
            </form>

            <div className="direction-pills">
              {{getAvailableDirections()
                .filter(dir => dir !== currentDirection)
                .map(dir => (
                  <button
                    key={{dir}}
                    className="direction-pill"
                    onClick={{() => handleApplyDirection(dir)}}
                  >
                    {{dir}}
                  </button>
                ))}}
            </div>
          </div>
        </div>
      );
    }}

    // Render the app
    const root = ReactDOM.createRoot(document.getElementById('root'));
    root.render(<StepByStepDirect />);
  </script>
</body>
</html>'''

# Write the file
with open('website.html', 'w') as f:
    f.write(html_content)

print("✓ Created website.html - a complete self-contained HTML file")
print("✓ Double-click website.html to open it in your browser")
print("✓ All features included: theme switching, source switching, direction transformations")
