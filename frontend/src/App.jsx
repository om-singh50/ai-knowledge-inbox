import React, { useState } from 'react';
import AddKnowledgeForm from './components/AddKnowledgeForm';
import SavedKnowledgeList from './components/SavedKnowledgeList';
import QnASection from './components/QnASection';

export function Section({ title, children }) {
  return (
    <section className="mb-8">
      <h2 className="text-xl font-semibold text-gray-800 mb-4">{title}</h2>
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        {children}
      </div>
    </section>
  );
}

function App() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleIngestSuccess = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans p-4 md:p-8">
      <div className="max-w-5xl mx-auto">
        {/* 1. Header */}
        <header className="mb-8 text-center md:text-left border-b border-gray-200 pb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">AI Knowledge Inbox</h1>
          <p className="text-gray-600">
            Save notes and URLs, and ask AI questions about your personal knowledge base.
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column: Knowledge Base Management */}
          <div>
            {/* 2. Add Knowledge */}
            <Section title="Add Knowledge">
              <AddKnowledgeForm onIngestSuccess={handleIngestSuccess} />
            </Section>

            {/* 3. Saved Knowledge */}
            <Section title="Saved Knowledge">
              <SavedKnowledgeList refreshTrigger={refreshTrigger} />
            </Section>
          </div>

          {/* Right Column: Q&A */}
          <div>
            <QnASection />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
