import { useState } from 'react';
import apiClient from '../services/api';

export const useNotes = () => {
  const [notes, setNotes] = useState({});
  const [loading, setLoading] = useState(false);

  const fetchNote = async (orderId) => {
    try {
      setLoading(true);
      const response = await apiClient.get(`/notes/orders/${orderId}/notes`);
      if (response.data && response.data.length > 0) {
        setNotes(prev => ({ ...prev, [orderId]: response.data[0].note_text }));
      }
    } catch (err) {
      console.error('Error fetching note:', err);
    } finally {
      setLoading(false);
    }
  };

  const saveNote = async (orderId, noteText) => {
    try {
      await apiClient.post(`/notes/orders/${orderId}/notes`, { note_text: noteText });
      setNotes(prev => ({ ...prev, [orderId]: noteText }));
    } catch (err) {
      console.error('Error saving note:', err);
      throw err;
    }
  };

  const getNote = (orderId) => {
    return notes[orderId] || '';
  };

  return {
    notes,
    loading,
    fetchNote,
    saveNote,
    getNote
  };
};
