import React, { useState } from 'react';
import axios from 'axios';
import { Upload, Sparkles, Download, Loader } from 'lucide-react';
import './App.css';

const INDICATORS = [
  // Environmental
  { code: 'E1-1', name: 'Scope 1 GHG Emissions', unit: 'tCO₂e', category: 'Environmental' },
  { code: 'E1-2', name: 'Scope 2 GHG Emissions', unit: 'tCO₂e', category: 'Environmental' },
  { code: 'E1-3', name: 'Scope 3 GHG Emissions', unit: 'tCO₂e', category: 'Environmental' },
  { code: 'E1-4', name: 'GHG Emissions Intensity', unit: 'tCO₂e/€M', category: 'Environmental' },
  { code: 'E1-5', name: 'Total Energy Consumption', unit: 'MWh', category: 'Environmental' },
  { code: 'E1-6', name: 'Renewable Energy %', unit: '%', category: 'Environmental' },
  { code: 'E1-7', name: 'Net Zero Target Year', unit: 'year', category: 'Environmental' },
  { code: 'E1-8', name: 'Green Financing Volume', unit: '€M', category: 'Environmental' },
  // Social
  { code: 'S1-1', name: 'Total Employees', unit: 'FTE', category: 'Social' },
  { code: 'S1-2', name: 'Female Employees', unit: '%', category: 'Social' },
  { code: 'S1-3', name: 'Gender Pay Gap', unit: '%', category: 'Social' },
  { code: 'S1-4', name: 'Training Hours/Employee', unit: 'hours', category: 'Social' },
  { code: 'S1-5', name: 'Employee Turnover Rate', unit: '%', category: 'Social' },
  { code: 'S1-6', name: 'Work-Related Accidents', unit: 'count', category: 'Social' },
  { code: 'S1-7', name: 'Collective Bargaining Coverage', unit: '%', category: 'Social' },
  // Governance
  { code: 'G1-1', name: 'Board Female Representation', unit: '%', category: 'Governance' },
  { code: 'G1-2', name: 'Board Meetings', unit: 'count', category: 'Governance' },
  { code: 'G1-3', name: 'Corruption Incidents', unit: 'count', category: 'Governance' },
  { code: 'G1-4', name: 'Avg Payment Period', unit: 'days', category: 'Governance' },
  { code: 'ESRS2-1', name: 'Suppliers Screened for ESG', unit: '%', category: 'Governance' },
];

function App() {
  const [file, setFile] = useState(null);
  const [companyName, setCompanyName] = useState('');
  const [reportYear, setReportYear] = useState(new Date().getFullYear());
  const [selectedIndicators, setSelectedIndicators] = useState([]);
  const [extracting, setExtracting] = useState(false);
  const [extractionMode, setExtractionMode] = useState('fast'); // NEW: fast, agent, or simple
  const [results, setResults] = useState(null);
  const [logs, setLogs] = useState([]);
  const [currentIndicator, setCurrentIndicator] = useState(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
    } else {
      alert('Please select a PDF file');
    }
  };

  const toggleIndicator = (code) => {
    setSelectedIndicators(prev =>
      prev.includes(code)
        ? prev.filter(c => c !== code)
        : [...prev, code]
    );
  };

  const selectCategory = (category) => {
    const categoryIndicators = INDICATORS.filter(i => i.category === category).map(i => i.code);
    const allSelected = categoryIndicators.every(code => selectedIndicators.includes(code));
    
    if (allSelected) {
      setSelectedIndicators(prev => prev.filter(code => !categoryIndicators.includes(code)));
    } else {
      setSelectedIndicators(prev => [...new Set([...prev, ...categoryIndicators])]);
    }
  };

  const handleExtract = async () => {
    if (!file || !companyName) {
      alert('Please provide company name and PDF file');
      return;
    }

    setExtracting(true);
    setLogs([]);
    setResults(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('company_name', companyName);
    formData.append('report_year', reportYear);
    formData.append('mode', extractionMode); // NEW: Pass extraction mode
    if (selectedIndicators.length > 0) {
      formData.append('indicators', JSON.stringify(selectedIndicators));
    }

    try {
      // Simulate log streaming (in production, use WebSocket or SSE)
      const logInterval = setInterval(() => {
        const indicators = selectedIndicators.length > 0 ? selectedIndicators : INDICATORS.map(i => i.code);
        const randomIndicator = indicators[Math.floor(Math.random() * indicators.length)];
        setCurrentIndicator(randomIndicator);
        setLogs(prev => [...prev, {
          time: new Date().toLocaleTimeString(),
          message: `🔍 Searching for ${randomIndicator}...`
        }]);
      }, 2000);

      const response = await axios.post('/api/extract', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      clearInterval(logInterval);
      setResults(response.data);
      setLogs(prev => [...prev, {
        time: new Date().toLocaleTimeString(),
        message: `✅ Extraction complete! Found ${response.data.extracted_values.length} indicators`
      }]);
    } catch (error) {
      console.error('Extraction error:', error);
      setLogs(prev => [...prev, {
        time: new Date().toLocaleTimeString(),
        message: `❌ Error: ${error.response?.data?.detail || error.message}`
      }]);
    } finally {
      setExtracting(false);
      setCurrentIndicator(null);
    }
  };

  const downloadCSV = () => {
    if (results?.csv_path) {
      window.open(`/api/download/${results.csv_path}`, '_blank');
    }
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.7) return '#10b981';
    if (confidence >= 0.4) return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <Sparkles size={32} />
          <h1>ESG Data Extraction</h1>
          <p>Autonomous AI Agent for Sustainability Reports</p>
        </div>
      </header>

      <div className="container">
        {/* Input Section */}
        <div className="card">
          <h2>📄 Upload Report</h2>
          
          <div className="input-group">
            <label>Company Name</label>
            <input
              type="text"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="e.g., AIB Bank"
              disabled={extracting}
            />
          </div>

          <div className="input-group">
            <label>Report Year</label>
            <input
              type="number"
              value={reportYear}
              onChange={(e) => setReportYear(parseInt(e.target.value))}
              placeholder="2024"
              disabled={extracting}
            />
          </div>

          <div className="file-upload">
            <input
              type="file"
              id="file-input"
              accept=".pdf"
              onChange={handleFileChange}
              disabled={extracting}
              style={{ display: 'none' }}
            />
            <label htmlFor="file-input" className="file-label">
              <Upload size={24} />
              {file ? file.name : 'Choose PDF File'}
            </label>
          </div>

          {/* Extraction Mode Selection */}
          <div className="input-group">
            <label>Extraction Mode</label>
            <select
              value={extractionMode}
              onChange={(e) => setExtractionMode(e.target.value)}
              disabled={extracting}
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '2px solid #e2e8f0',
                borderRadius: '8px',
                fontSize: '1rem',
                backgroundColor: 'white',
                cursor: 'pointer'
              }}
            >
              <option value="fast">⚡ Fast Mode (Vector Search - Recommended)</option>
              <option value="agent">🤖 Agent Mode (Autonomous AI - Slower)</option>
              <option value="simple">📋 Simple Mode (Basic Extraction)</option>
            </select>
            <small style={{ color: '#64748b', marginTop: '0.5rem', display: 'block' }}>
              {extractionMode === 'fast' && '⚡ Uses semantic search + 1 LLM call per indicator (~30-60s for 20 indicators)'}
              {extractionMode === 'agent' && '🤖 AI agent autonomously searches document (~3-5 min for 20 indicators)'}
              {extractionMode === 'simple' && '📋 Basic keyword matching (~1-2 min)'}
            </small>
          </div>

          {/* Indicator Selection */}
          <div className="indicators-section">
            <h3>Select Indicators (leave empty for all 20)</h3>
            
            <div className="category-buttons">
              <button onClick={() => selectCategory('Environmental')} className="category-btn environmental">
                Environmental ({INDICATORS.filter(i => i.category === 'Environmental').length})
              </button>
              <button onClick={() => selectCategory('Social')} className="category-btn social">
                Social ({INDICATORS.filter(i => i.category === 'Social').length})
              </button>
              <button onClick={() => selectCategory('Governance')} className="category-btn governance">
                Governance ({INDICATORS.filter(i => i.category === 'Governance').length})
              </button>
            </div>

            <div className="indicators-grid">
              {INDICATORS.map(indicator => (
                <label key={indicator.code} className="indicator-checkbox">
                  <input
                    type="checkbox"
                    checked={selectedIndicators.includes(indicator.code)}
                    onChange={() => toggleIndicator(indicator.code)}
                    disabled={extracting}
                  />
                  <span>{indicator.code}: {indicator.name}</span>
                </label>
              ))}
            </div>
          </div>

          <button
            className="extract-btn"
            onClick={handleExtract}
            disabled={extracting || !file || !companyName}
          >
            {extracting ? (
              <>
                <Loader className="spinner" size={20} />
                Extracting with AI Agent...
              </>
            ) : (
              <>
                <Sparkles size={20} />
                Extract Data
              </>
            )}
          </button>
        </div>

        {/* Logs Section */}
        {logs.length > 0 && (
          <div className="card logs-card">
            <h2>🤖 Agent Activity</h2>
            {currentIndicator && (
              <div className="current-indicator">
                Processing: <strong>{currentIndicator}</strong>
              </div>
            )}
            <div className="logs">
              {logs.map((log, idx) => (
                <div key={idx} className="log-entry">
                  <span className="log-time">{log.time}</span>
                  <span className="log-message">{log.message}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Results Section */}
        {results && (
          <div className="card results-card">
            <div className="results-header">
              <h2>✨ Extraction Results</h2>
              <button onClick={downloadCSV} className="download-btn">
                <Download size={18} />
                Download CSV
              </button>
            </div>

            <div className="results-stats">
              <div className="stat">
                <span className="stat-label">Total Indicators</span>
                <span className="stat-value">{results.total_indicators}</span>
              </div>
              <div className="stat success">
                <span className="stat-label">High Confidence (>70%)</span>
                <span className="stat-value">
                  {results.extracted_values.filter(v => v.confidence >= 0.7).length}
                </span>
              </div>
              <div className="stat warning">
                <span className="stat-label">Medium Confidence</span>
                <span className="stat-value">
                  {results.extracted_values.filter(v => v.confidence >= 0.4 && v.confidence < 0.7).length}
                </span>
              </div>
              <div className="stat error">
                <span className="stat-label">Low Confidence</span>
                <span className="stat-value">
                  {results.extracted_values.filter(v => v.confidence < 0.4).length}
                </span>
              </div>
            </div>

            {/* CSV Table View */}
            <div className="csv-table-container">
              <table className="csv-table">
                <thead>
                  <tr>
                    <th>Indicator Code</th>
                    <th>Indicator Name</th>
                    <th>Value</th>
                    <th>Unit</th>
                    <th>Confidence</th>
                    <th>Source Page</th>
                    <th>Category</th>
                  </tr>
                </thead>
                <tbody>
                  {results.extracted_values.map((item, idx) => {
                    const indicator = INDICATORS.find(i => i.code === item.indicator_code);
                    const confidencePercent = (item.confidence * 100).toFixed(0);
                    const confidenceClass = item.confidence >= 0.7 ? 'confidence-high' : 
                                          item.confidence >= 0.4 ? 'confidence-medium' : 'confidence-low';
                    
                    return (
                      <tr key={idx}>
                        <td><strong>{item.indicator_code}</strong></td>
                        <td>{indicator?.name || 'Unknown'}</td>
                        <td><strong>{item.value || 'Not found'}</strong></td>
                        <td>{item.unit || '-'}</td>
                        <td>
                          <span className={`confidence-badge ${confidenceClass}`}>
                            {confidencePercent}%
                          </span>
                        </td>
                        <td>{item.source_page ? `Page ${item.source_page}` : '-'}</td>
                        <td>{indicator?.category || '-'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
