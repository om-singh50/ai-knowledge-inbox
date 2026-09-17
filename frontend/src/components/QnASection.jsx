import React, { useState } from 'react';
import { Section } from '../App';

export default function QnASection() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(null);
  const [sources, setSources] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasQueried, setHasQueried] = useState(false);
  const MAX_LENGTH = 1000;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;
    
    setIsLoading(true);
    setError(null);
    setAnswer(null);
    setSources([]);
    setHasQueried(true);

    try {
      const response = await fetch(`${import.meta.env.VITE_BACKEND_URL}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question.trim() })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server error: ${response.status}`);
      }

      const data = await response.json();
      setAnswer(data.answer);
      setSources(data.sources || []);
    } catch (err) {
      setError(err.message || 'An error occurred while fetching the answer.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-8">
      <Section title="Ask a Question">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              What would you like to know?
            </label>
            <textarea 
              rows={3}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={isLoading}
              maxLength={MAX_LENGTH}
              placeholder="e.g., What are the best practices for React components?" 
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
            />
            <div className="text-right text-xs text-gray-500 mt-1">
              {question.length} / {MAX_LENGTH} characters
            </div>
          </div>
          
          {error && (
            <div className="p-3 rounded-md text-sm bg-red-50 text-red-700">
              {error}
            </div>
          )}

          <button 
            type="submit" 
            disabled={!question.trim() || isLoading}
            className={`font-medium py-2 px-4 rounded-md transition-colors self-start ${
              !question.trim() || isLoading
                ? 'bg-indigo-400 text-white cursor-not-allowed' 
                : 'bg-indigo-600 text-white hover:bg-indigo-700'
            }`}
          >
            {isLoading ? 'Asking...' : 'Ask'}
          </button>
        </form>
      </Section>

      <Section title="Answer">
        {isLoading ? (
          <div className="text-center py-8 text-gray-500 bg-gray-50 rounded-lg border border-dashed border-gray-300">
            Loading...
          </div>
        ) : hasQueried ? (
          <div className="flex flex-col gap-4">
            <div className="text-gray-800 prose max-w-none whitespace-pre-wrap">
              {answer || <span className="text-gray-500 italic">No answer was generated.</span>}
            </div>
          </div>
        ) : (
          <div className="text-gray-500 italic p-6 bg-gray-50 rounded-lg border border-dashed border-gray-300 text-center">
            Ask a question to see the AI's answer here.
          </div>
        )}
      </Section>

      {hasQueried && !isLoading && (
        <Section title="Sources">
          {sources && sources.length > 0 ? (
            <div className="grid grid-cols-1 gap-4">
              {sources.map((source, idx) => (
                <div key={idx} className="p-4 bg-white rounded-lg border border-gray-200 shadow-sm flex flex-col gap-3">
                  <div className="flex justify-between items-start gap-4">
                    <h5 className="font-semibold text-gray-800 break-words flex-1">
                      {source.title || (source.source_type === 'url' ? 'Untitled URL' : 'Untitled Note')}
                    </h5>
                    {source.relevance_score !== undefined && (
                      <span className="text-xs font-medium text-gray-600 bg-gray-100 px-2 py-1 rounded-full whitespace-nowrap">
                        Score: {Number(source.relevance_score).toFixed(2)}
                      </span>
                    )}
                  </div>
                  <div className="text-sm text-gray-600">
                    {source.source_type === 'url' && source.url ? (
                      <a href={source.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline break-all">
                        {source.url}
                      </a>
                    ) : (
                      <span>Note</span>
                    )}
                  </div>
                  {source.content && (
                    <div className="text-sm text-gray-700 bg-gray-50 p-3 rounded border border-gray-100">
                      {source.content}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-gray-500 italic text-sm text-center py-4 bg-gray-50 rounded-lg border border-dashed border-gray-300">
              No sources were returned for this query.
            </div>
          )}
        </Section>
      )}
    </div>
  );
}
