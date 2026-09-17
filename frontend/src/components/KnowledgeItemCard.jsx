import React from 'react';

export default function KnowledgeItemCard({ item }) {
  const isUrl = item.source_type === 'url';
  
  return (
    <li className="p-4 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow flex flex-col gap-2">
      <div className="flex justify-between items-start">
        <h3 className="font-semibold text-gray-800 break-words">{item.title || 'Untitled'}</h3>
        <span className={`text-xs px-2 py-1 rounded-full font-medium ${isUrl ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'}`}>
          {isUrl ? 'URL' : 'Note'}
        </span>
      </div>
      
      {isUrl && item.url && (
        <a href={item.url} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline truncate max-w-full block">
          {item.url}
        </a>
      )}
      
      <div className="text-xs text-gray-500 mt-1">
        Added: {new Date(item.created_at).toLocaleString()}
      </div>
    </li>
  );
}
