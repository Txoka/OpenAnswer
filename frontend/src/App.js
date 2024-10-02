import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import './App.css';

const API_ENDPOINT = 'http://localhost:8000/api/answer';

// Custom components for footnotes
const FootnoteReference = ({ identifier }) => <sup>[{identifier}]</sup>;
const FootnoteBackReference = ({ identifier }) => <a href={`#fnref-${identifier}`} className="footnote-backref">↩</a>;

export default function ResearchAssistant() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [searchTerms, setSearchTerms] = useState([]);
  const [relevantUrls, setRelevantUrls] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

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
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.answer) {
        setAnswer(data.answer);
        setSearchTerms(data.search_terms || []);
        setRelevantUrls(data.relevant_urls || []);
      } else {
        throw new Error('Unexpected response format');
      }
    } catch (err) {
      console.error('Error details:', err);
      setError('An error occurred while fetching the answer. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
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
            {loading ? 'Loading...' : 'Ask'}
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
                },
                footnoteReference: FootnoteReference,
                footnoteBackReference: FootnoteBackReference
              }}
            >
              {answer}
            </ReactMarkdown>
          </div>
        )}
        {/* Powered by OpenAnswer */}
        <div className="powered-by">
          <p>Powered by <a href="https://github.com/Txoka/OpenAnswer" target="_blank" rel="noopener noreferrer">https://github.com/Txoka/OpenAnswer</a></p>
        </div>
      </div>
    </div>
  );
}