import React from 'react';
import { Route, Routes, Navigate } from 'react-router-dom';
import HomePage from './pages/HomePage';
import GraphPage from './pages/GraphPage';
import TimelinePage from './pages/TimelinePage';
import SearchPage from './pages/SearchPage';
import ConnectorsPage from './pages/ConnectorsPage';
import PluginsPage from './pages/PluginsPage';
import DocsPage from './pages/DocsPage';
import TemporalSearchPage from './pages/TemporalSearchPage';
import EntityHistoryPage from './pages/EntityHistoryPage';
import ChatPage from './pages/ChatPage';

import Layout from './components/Layout';

const App: React.FC = () => {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/graph" element={<GraphPage />} />
        <Route path="/timeline" element={<TimelinePage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/temporal" element={<TemporalSearchPage />} />
        <Route path="/entity-history" element={<EntityHistoryPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/connectors" element={<ConnectorsPage />} />
        <Route path="/plugins" element={<PluginsPage />} />
        <Route path="/docs" element={<DocsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
};

export default App;