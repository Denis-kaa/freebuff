import { useState, useEffect } from 'react';
import apiClient from '../services/api';

export const useCategories = () => {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        setLoading(true);
        const response = await apiClient.get('/categories');
        setCategories(response.data.categories || []);
        setError(null);
      } catch (err) {
        console.error('Error fetching categories:', err);
        setError(err.response?.data?.detail || 'Ошибка загрузки категорий');
      } finally {
        setLoading(false);
      }
    };

    fetchCategories();
  }, []);

  return { categories, loading, error };
};
