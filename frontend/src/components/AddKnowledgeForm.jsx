import React, { useState } from 'react';

export default function AddKnowledgeForm({ onIngestSuccess }) {
  const [mode, setMode] = useState('note');
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [url, setUrl] = useState('');
  const [message, setMessage] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage(null);

    if (mode === 'note' && !content.trim()) {
      setMessage({ type: 'error', text: 'Note content cannot be empty.' });
      return;
    }

    if (mode === 'url' && !url.trim()) {
      setMessage({ type: 'error', text: 'URL cannot be empty.' });
      return;
    }

    setIsLoading(true);
    const payload = mode === 'note'
      ? { source_type: 'note', title: title.trim(), content: content.trim() }
      : { source_type: 'url', title: title.trim(), url: url.trim() };

    try {
      const response = await fetch(`${import.meta.env.VITE_BACKEND_URL}/ingest`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server error: ${response.status}`);
      }

      setMessage({ type: 'success', text: `Saved ${mode} successfully!` });
      setTitle('');
      setContent('');
      setUrl('');
      if (onIngestSuccess) {
        onIngestSuccess();
      }
    } catch (error) {
      setMessage({ type: 'error', text: error.message || 'Failed to save knowledge.' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex bg-gray-100 p-1 rounded-lg w-fit">
        <button
          type="button"
          disabled={isLoading}
          onClick={() => { setMode('note'); setMessage(null); }}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            mode === 'note' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Note
        </button>
        <button
          type="button"
          disabled={isLoading}
          onClick={() => { setMode('url'); setMessage(null); }}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            mode === 'url' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          URL
        </button>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Title (optional)</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            disabled={isLoading}
            placeholder="e.g., 'Meeting Notes'"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
          />
        </div>

        {mode === 'note' ? (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Content</label>
            <textarea
              rows={4}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              disabled={isLoading}
              placeholder="Paste note content here..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
            />
          </div>
        ) : (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">URL</label>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={isLoading}
              placeholder="https://example.com"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
            />
          </div>
        )}

        {message && (
          <div className={`p-3 rounded-md text-sm ${message.type === 'error' ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
            {message.text}
          </div>
        )}

        <button
          type="submit"
          disabled={isLoading}
          className={`font-medium py-2 px-4 rounded-md transition-colors self-start ${isLoading ? 'bg-blue-400 text-white cursor-not-allowed' : 'bg-blue-600 text-white hover:bg-blue-700'}`}
        >
          {isLoading ? 'Saving...' : 'Save Knowledge'}
        </button>
      </form>
    </div>
  );
}
