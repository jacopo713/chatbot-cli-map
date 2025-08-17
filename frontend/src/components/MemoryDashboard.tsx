"use client";

import { useState, useEffect } from 'react';

const BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

interface MemoryStats {
  total_memories: number;
  analyzed_sample: number;
  relevant_memories: number;
  by_message_type: Record<string, number>;
  by_category: Record<string, number>;  // New: categories field
  by_role: Record<string, number>;
  by_scope: Record<string, number>;
  by_conversation: Record<string, number>;
  recent_memories: Array<{
    content: string;
    type: string;
    category: string;  // New: category field in recent memories
    role: string;
    scope: string;
    timestamp: string;
  }>;
}

interface MemoryDashboardProps {
  onClose: () => void;
}

export default function MemoryDashboard({ onClose }: MemoryDashboardProps) {
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [clearing, setClearing] = useState(false);

  // Fetch memory statistics
  const fetchMemoryStats = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`${BASE_URL}/api/memory/analyze`);
      const data = await response.json();
      
      if (data.success) {
        setStats(data.stats);
      } else {
        setError(data.error || 'Errore nel caricamento delle statistiche');
      }
    } catch (err) {
      setError('Errore di connessione');
      console.error('Error fetching memory stats:', err);
    } finally {
      setLoading(false);
    }
  };

  // Clear all memories
  const clearAllMemories = async () => {
    if (!confirm('⚠️ Sei sicuro di voler cancellare TUTTE le memorie? Questa azione non può essere annullata.')) {
      return;
    }

    try {
      setClearing(true);
      
      const response = await fetch(`${BASE_URL}/api/memory/clear`, {
        method: 'DELETE'
      });
      const data = await response.json();
      
      if (data.success) {
        alert(`✅ ${data.message}`);
        // Refresh stats after clearing
        await fetchMemoryStats();
      } else {
        alert(`❌ Errore: ${data.error}`);
      }
    } catch (err) {
      alert('❌ Errore di connessione durante la cancellazione');
      console.error('Error clearing memories:', err);
    } finally {
      setClearing(false);
    }
  };

  useEffect(() => {
    fetchMemoryStats();
  }, []);

  const formatTimestamp = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleString('it-IT', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return timestamp;
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'personal': return 'bg-blue-100 text-blue-800';
      case 'chat': return 'bg-green-100 text-green-800';
      case 'chat_history': return 'bg-gray-100 text-gray-800';
      default: return 'bg-yellow-100 text-yellow-800';
    }
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'user': return 'bg-purple-100 text-purple-800';
      case 'assistant': return 'bg-orange-100 text-orange-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'personal': return 'bg-blue-100 text-blue-800';
      case 'work': return 'bg-green-100 text-green-800';
      case 'hobby': return 'bg-pink-100 text-pink-800';
      case 'health': return 'bg-red-100 text-red-800';
      case 'relationships': return 'bg-purple-100 text-purple-800';
      case 'goals': return 'bg-yellow-100 text-yellow-800';
      case 'general': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl h-5/6 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-2xl font-bold text-gray-800 flex items-center space-x-2">
            <span>🧠</span>
            <span>Dashboard Memorie</span>
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
                <p className="text-gray-600">Caricamento statistiche...</p>
              </div>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <div className="text-6xl mb-4">⚠️</div>
              <h3 className="text-xl font-semibold text-gray-800 mb-2">Errore</h3>
              <p className="text-gray-600 mb-4">{error}</p>
              <button
                onClick={fetchMemoryStats}
                className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
              >
                Riprova
              </button>
            </div>
          ) : stats ? (
            <div className="space-y-6">
              {/* Overview Stats */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <h3 className="text-sm font-medium text-blue-800 mb-1">Memorie Totali</h3>
                  <p className="text-2xl font-bold text-blue-900">{stats.total_memories.toLocaleString()}</p>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <h3 className="text-sm font-medium text-green-800 mb-1">Rilevanti</h3>
                  <p className="text-2xl font-bold text-green-900">{stats.relevant_memories.toLocaleString()}</p>
                  <p className="text-xs text-green-600">Esclusi chat_history</p>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                  <h3 className="text-sm font-medium text-purple-800 mb-1">Conversazioni</h3>
                  <p className="text-2xl font-bold text-purple-900">{Object.keys(stats.by_conversation).length}</p>
                </div>
              </div>

              {/* Charts */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* By Category */}
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="text-lg font-semibold mb-3">Per Categoria</h3>
                  <div className="space-y-2">
                    {Object.entries(stats.by_category || {}).map(([category, count]) => (
                      <div key={category} className="flex items-center justify-between">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getCategoryColor(category)}`}>
                          {category}
                        </span>
                        <span className="font-semibold">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* By Role */}
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="text-lg font-semibold mb-3">Per Ruolo</h3>
                  <div className="space-y-2">
                    {Object.entries(stats.by_role).map(([role, count]) => (
                      <div key={role} className="flex items-center justify-between">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getRoleColor(role)}`}>
                          {role}
                        </span>
                        <span className="font-semibold">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Recent Memories */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="text-lg font-semibold mb-3">Memorie Recenti</h3>
                <div className="space-y-3 max-h-64 overflow-y-auto">
                  {stats.recent_memories.map((memory, index) => (
                    <div key={index} className="bg-white p-3 rounded border">
                      <div className="flex items-center space-x-2 mb-2">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getCategoryColor(memory.category || 'uncategorized')}`}>
                          {memory.category || 'uncategorized'}
                        </span>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getRoleColor(memory.role)}`}>
                          {memory.role}
                        </span>
                        <span className="text-xs text-gray-500">
                          {formatTimestamp(memory.timestamp)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-700">{memory.content}</p>
                      <p className="text-xs text-gray-500 mt-1">Scope: {memory.scope}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Top Conversations */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="text-lg font-semibold mb-3">Conversazioni Principali</h3>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {Object.entries(stats.by_conversation).slice(0, 10).map(([convId, count]) => (
                    <div key={convId} className="flex items-center justify-between bg-white p-2 rounded">
                      <span className="text-sm font-mono text-gray-600 truncate flex-1">
                        {convId.length > 30 ? `${convId.slice(0, 30)}...` : convId}
                      </span>
                      <span className="font-semibold text-sm ml-2">{count} memorie</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="border-t p-6 bg-gray-50">
          <div className="flex items-center justify-between">
            <button
              onClick={fetchMemoryStats}
              disabled={loading}
              className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              🔄 Aggiorna
            </button>
            
            <div className="flex space-x-3">
              <button
                onClick={clearAllMemories}
                disabled={clearing || loading}
                className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                <span>{clearing ? '⏳' : '🗑️'}</span>
                <span>{clearing ? 'Cancellando...' : 'Cancella Tutte'}</span>
              </button>
              
              <button
                onClick={onClose}
                className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600"
              >
                Chiudi
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}