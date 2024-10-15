import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { FaSun, FaMoon } from 'react-icons/fa'; // Import icons
import './App.css';

const API_ENDPOINT = `${window.location.protocol}//${window.location.hostname}:8118/api/answer`;

function formatTime(seconds) {
  const days = Math.floor(seconds / (24 * 60 * 60));
  const hours = Math.floor((seconds % (24 * 60 * 60)) / (60 * 60));
  const minutes = Math.floor((seconds % (60 * 60)) / 60);
  const secs = seconds % 60;

  let timeString = '';
  if (days > 0) timeString += `${days}d `;
  if (hours > 0) timeString += `${hours}h `;
  if (minutes > 0) timeString += `${minutes}m `;
  timeString += `${secs}s`;

  return timeString.trim();
}

export default function ResearchAssistant() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [searchTerms, setSearchTerms] = useState([]);
  const [relevantUrls, setRelevantUrls] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Initialize theme based on the data-theme attribute set by the inline script
  const getInitialTheme = () => {
    if (typeof window !== 'undefined' && window.document.documentElement) {
      return window.document.documentElement.getAttribute('data-theme') || 'light';
    }
    return 'light';
  };

  const [theme, setTheme] = useState(getInitialTheme);

  // Function to toggle theme
  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    // Optional: Update background color to prevent flash during toggle
    const backgroundColor = newTheme === 'dark' ? '#1e1e1e' : '#f0f4f8';
    document.documentElement.style.backgroundColor = backgroundColor;
  };

  // Listen for changes in localStorage (optional, for multi-tab support)
  useEffect(() => {
    const handleStorage = (event) => {
      if (event.key === 'theme') {
        const newTheme = event.newValue || 'light';
        setTheme(newTheme);
        document.documentElement.setAttribute('data-theme', newTheme);
        
        // Optional: Update background color
        const backgroundColor = newTheme === 'dark' ? '#1e1e1e' : '#f0f4f8';
        document.documentElement.style.backgroundColor = backgroundColor;
      }
    };
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setAnswer('');
    setSearchTerms([]);
    setRelevantUrls([]);

    try {
      const response = await fetch(API_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ content: question }),
      });

      if (!response.ok) {
        // Try to parse the error response once
        const errorData = await response.json();
        if (response.status === 429) {
          const retryAfterSeconds = errorData.retry_after_seconds || response.headers.get('Retry-After');
          const limitType = errorData.limit_type || 'unknown';
          
          // Convert seconds to dd:hh:mm format
          const retryTimeFormatted = formatTime(retryAfterSeconds);
  
          setError(`${limitType} Rate limit exceeded. Try again in ${retryTimeFormatted}.`);
        } else {
          setError(`Error: ${errorData.detail || response.statusText}`);
        }
      } else {
        const data = await response.json();
      
        if (data.answer) {
          setAnswer(data.answer);
          setSearchTerms(data.search_terms || []);
          setRelevantUrls(data.relevant_urls || []);
        } else if (data.status_code) {
          setError(data.status_code);
        } else {
          throw new Error('Unexpected response format');
        }
      }

      
    } catch (err) {
      console.error('Error details:', err);
      setError('An error occurred while fetching the answer. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      {/* Theme Toggle Button */}
      <button className="theme-toggle" onClick={toggleTheme} aria-label="Toggle Theme">
        {theme === 'light' ? <FaMoon /> : <FaSun />}
      </button>

      <div className="research-assistant">
        {/* OpenAnswer label above the title */}
        <span className="open-answer">OpenAnswer</span>
        <h1 className="title">Research Assistant</h1>

        <form onSubmit={handleSubmit} className="form">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Enter your question or request"
            className="input"
            required
          />
          <button 
            type="submit" 
            disabled={loading}
            className="button"
          >
            {loading ? (
              <div className="spinner"></div>
            ) : (
              'Ask'
            )}
          </button>
        </form>

        {error && (
          <div className="error">
            <p><strong>Error:</strong> {error}</p>
          </div>
        )}

        {(searchTerms.length > 0 || relevantUrls.length > 0) && (
          <div className="metadata">
            {searchTerms.length > 0 && (
              <div className="search-terms">
                <h3>Search Terms:</h3>
                <ul>
                  {searchTerms.map((term, index) => (
                    <li key={index}>{term}</li>
                  ))}
                </ul>
              </div>
            )}
            {relevantUrls.length > 0 && (
              <div className="relevant-urls">
                <h3>Relevant URLs:</h3>
                <ul>
                  {relevantUrls.map((url, index) => (
                    <li key={index}>
                      <a href={url} target="_blank" rel="noopener noreferrer">{url}</a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {answer && (
          <div className="answer">
            <h2>Answer:</h2>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({node, inline, className, children, ...props}) {
                  const match = /language-(\w+)/.exec(className || '')
                  return !inline && match ? (
                    <SyntaxHighlighter
                      style={vscDarkPlus}
                      language={match[1]}
                      PreTag="div"
                      {...props}
                    >
                      {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                  ) : (
                    <code className={className} {...props}>
                      {children}
                    </code>
                  )
                }
              }}
            >
              {answer}
            </ReactMarkdown>
          </div>
        )}
        
        <div className="powered-by">
          <p>Powered by <a href="https://github.com/Txoka/OpenAnswer" target="_blank" rel="noopener noreferrer">https://github.com/Txoka/OpenAnswer</a></p>
        </div>
      </div>
    </div>
  );
}
