import { useState, useEffect } from 'react';
import apiClient from '../services/api';

export const usePortfolio = () => {
  const [portfolioItems, setPortfolioItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchPortfolio = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/portfolio');
      setPortfolioItems(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching portfolio:', err);
      setError(err.response?.data?.detail || 'Ошибка загрузки портфолио');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPortfolio();
  }, []);

  const addPortfolioItem = async (itemData) => {
    try {
      const response = await apiClient.post('/portfolio', itemData);
      setPortfolioItems(prev => [...prev, response.data]);
      return response.data;
    } catch (err) {
      console.error('Error adding portfolio item:', err);
      throw err;
    }
  };

  const updatePortfolioItem = async (id, itemData) => {
    try {
      const response = await apiClient.put(`/portfolio/${id}`, itemData);
      setPortfolioItems(prev => prev.map(item => item.id === id ? response.data : item));
      return response.data;
    } catch (err) {
      console.error('Error updating portfolio item:', err);
      throw err;
    }
  };

  const deletePortfolioItem = async (id) => {
    try {
      await apiClient.delete(`/portfolio/${id}`);
      setPortfolioItems(prev => prev.filter(item => item.id !== id));
    } catch (err) {
      console.error('Error deleting portfolio item:', err);
      throw err;
    }
  };

  return {
    portfolioItems,
    loading,
    error,
    addPortfolioItem,
    updatePortfolioItem,
    deletePortfolioItem,
    refetch: fetchPortfolio
  };
};
