"use client";

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { ConceptMapData } from '@/components/ConceptMapPreview';

interface FirebaseConceptMap extends ConceptMapData {
  id?: string;
  userId?: string;
  createdAt?: string;
  updatedAt?: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function useFirebaseConceptMaps() {
  const { user } = useAuth();
  const [conceptMaps, setConceptMaps] = useState<FirebaseConceptMap[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastFetchTime, setLastFetchTime] = useState<number>(0);
  
  // Cache for 30 seconds to avoid redundant calls
  const CACHE_DURATION = 30000;

  const getAuthToken = useCallback(async () => {
    if (!user) return null;
    try {
      const token = await user.getIdToken();
      return token;
    } catch (error) {
      console.error('Failed to get auth token:', error);
      return null;
    }
  }, [user]);

  const fetchConceptMaps = useCallback(async (forceRefresh: boolean = false) => {
    if (!user) return;

    // Check cache validity
    const now = Date.now();
    if (!forceRefresh && (now - lastFetchTime) < CACHE_DURATION && conceptMaps.length > 0) {
      console.log('Using cached concept maps');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const token = await getAuthToken();
      if (!token) {
        throw new Error('No authentication token available');
      }

      const response = await fetch(`${API_BASE_URL}/api/firebase/concept-maps`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch concept maps: ${response.statusText}`);
      }

      const maps = await response.json();
      setConceptMaps(maps);
      setLastFetchTime(now);
    } catch (error: any) {
      console.error('Error fetching concept maps:', error);
      setError(error.message || 'Failed to fetch concept maps');
    } finally {
      setLoading(false);
    }
  }, [user, getAuthToken, lastFetchTime, CACHE_DURATION, conceptMaps.length]);

  const saveConceptMap = useCallback(async (conceptMapData: ConceptMapData): Promise<string | null> => {
    if (!user) {
      setError('User not authenticated');
      return null;
    }

    try {
      const token = await getAuthToken();
      if (!token) {
        throw new Error('No authentication token available');
      }

      const response = await fetch(`${API_BASE_URL}/api/firebase/concept-maps`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: conceptMapData.title || 'Mappa Concettuale',
          nodes: conceptMapData.nodes,
          edges: conceptMapData.edges,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to save concept map: ${response.statusText}`);
      }

      const result = await response.json();
      
      // Refresh the list of concept maps
      await fetchConceptMaps(true);
      
      return result.id;
    } catch (error: any) {
      console.error('Error saving concept map:', error);
      setError(error.message || 'Failed to save concept map');
      return null;
    }
  }, [user, getAuthToken, fetchConceptMaps]);

  const updateConceptMap = useCallback(async (mapId: string, conceptMapData: Partial<ConceptMapData>): Promise<boolean> => {
    if (!user) {
      setError('User not authenticated');
      return false;
    }

    try {
      const token = await getAuthToken();
      if (!token) {
        throw new Error('No authentication token available');
      }

      const response = await fetch(`${API_BASE_URL}/api/firebase/concept-maps/${mapId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(conceptMapData),
      });

      if (!response.ok) {
        throw new Error(`Failed to update concept map: ${response.statusText}`);
      }

      // Refresh the list of concept maps
      await fetchConceptMaps(true);
      
      return true;
    } catch (error: any) {
      console.error('Error updating concept map:', error);
      setError(error.message || 'Failed to update concept map');
      return false;
    }
  }, [user, getAuthToken, fetchConceptMaps]);

  const deleteConceptMap = useCallback(async (mapId: string): Promise<boolean> => {
    if (!user) {
      setError('User not authenticated');
      return false;
    }

    try {
      const token = await getAuthToken();
      if (!token) {
        throw new Error('No authentication token available');
      }

      const response = await fetch(`${API_BASE_URL}/api/firebase/concept-maps/${mapId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to delete concept map: ${response.statusText}`);
      }

      // Refresh the list of concept maps
      await fetchConceptMaps(true);
      
      return true;
    } catch (error: any) {
      console.error('Error deleting concept map:', error);
      setError(error.message || 'Failed to delete concept map');
      return false;
    }
  }, [user, getAuthToken, fetchConceptMaps]);

  const getUserAnalysis = useCallback(async () => {
    if (!user) return null;

    try {
      const token = await getAuthToken();
      if (!token) {
        throw new Error('No authentication token available');
      }

      const response = await fetch(`${API_BASE_URL}/api/firebase/profile/analysis`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to get user analysis: ${response.statusText}`);
      }

      const result = await response.json();
      return result.analysis;
    } catch (error: any) {
      console.error('Error getting user analysis:', error);
      setError(error.message || 'Failed to get user analysis');
      return null;
    }
  }, [user, getAuthToken]);

  // Auto-fetch concept maps when user changes
  useEffect(() => {
    if (user) {
      fetchConceptMaps();
    } else {
      setConceptMaps([]);
      setError(null);
    }
  }, [user, fetchConceptMaps]);

  return {
    conceptMaps,
    loading,
    error,
    saveConceptMap,
    updateConceptMap,
    deleteConceptMap,
    fetchConceptMaps,
    getUserAnalysis,
    clearError: () => setError(null),
  };
}