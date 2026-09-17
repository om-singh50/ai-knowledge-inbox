import React, { useState, useEffect } from 'react';
import KnowledgeItemCard from './KnowledgeItemCard';

export default function SavedKnowledgeList({ refreshTrigger }) {
  const [items, setItems] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchItems = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch(`${import.meta.env.VITE_BACKEND_URL}/items`);
        if (!response.ok) {
          throw new Error(`Failed to fetch items: ${response.statusText}`);
        }
        const data = await response.json();
        setItems(data);
      } catch (err) {
        setError(err.message || 'An error occurred while fetching items.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchItems();
  }, [refreshTrigger]);

  if (isLoading) {
    return (
      <div className="text-center py-8 text-gray-500 bg-gray-50 rounded-lg border border-dashed border-gray-300">
        Loading items...
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8 text-red-500 bg-red-50 rounded-lg border border-red-200">
        {error}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 bg-gray-50 rounded-lg border border-dashed border-gray-300">
        <p>No knowledge saved yet.</p>
        <p className="text-sm mt-1">Add a note or URL above to get started.</p>
      </div>
    );
  }

  return (
    <ul className="grid grid-cols-1 gap-4 max-h-96 overflow-y-auto pr-2">
      {items.map(item => (
        <KnowledgeItemCard key={item.id} item={item} />
      ))}
    </ul>
  );
}
