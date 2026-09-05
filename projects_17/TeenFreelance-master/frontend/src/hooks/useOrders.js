import { useState, useEffect, useRef } from 'react';
import apiClient from '../services/api';

export const useOrders = (filters = {}) => {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [total, setTotal] = useState(0);
  const filtersRef = useRef(filters);
  filtersRef.current = filters;

  const fetchOrders = async (params = {}) => {
    try {
      setLoading(true);
      const response = await apiClient.get('/orders', { params: { ...filtersRef.current, ...params } });
      setOrders(response.data.items || []);
      setTotal(response.data.total || 0);
      setError(null);
    } catch (err) {
      console.error('Error fetching orders:', err);
      setError(err.response?.data?.detail || 'Ошибка загрузки заказов');
    } finally {
      setLoading(false);
    }
  };

  const fetchMyOrders = async (params = {}, userRole = null) => {
    try {
      setLoading(true);
      const endpoint = (userRole === 'executor' || userRole === 'EXECUTOR')
        ? '/orders/my-executor'
        : '/orders/my';
      console.log('📦 Загрузка заказов для роли:', userRole, 'endpoint:', endpoint);
      const response = await apiClient.get(endpoint, { params });
      setOrders(response.data.items || []);
      setTotal(response.data.total || 0);
      setError(null);
    } catch (err) {
      console.error('Error fetching my orders:', err);
      setError(err.response?.data?.detail || 'Ошибка загрузки заказов');
    } finally {
      setLoading(false);
    }
  };

  // Реагируем на изменение фильтров
  useEffect(() => {
    if (filters.my === true) {
      fetchMyOrders();
    } else {
      fetchOrders();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    filters.my,
    filters.status,
    filters.category_id,
    filters.subcategory_id,
    filters.subsubcategory_id,
    filters.category_ids,
    filters.subcategory_ids,
    filters.subsubcategory_ids,
    filters.budget_from,
    filters.budget_to,
    filters.keywords,
    filters.min_hired_percent,
    filters.offers_count_from,
    filters.offers_count_to,
  ]);


  const createOrder = async (orderData) => {
    try {
      const response = await apiClient.post('/orders', orderData);
      setOrders(prev => [response.data, ...prev]);
      return response.data;
    } catch (err) {
      console.error('Error creating order:', err);
      throw err;
    }
  };

  const updateOrder = async (id, orderData) => {
    try {
      const response = await apiClient.put(`/orders/${id}`, orderData);
      setOrders(prev => prev.map(order => order.id === id ? response.data : order));
      return response.data;
    } catch (err) {
      console.error('Error updating order:', err);
      throw err;
    }
  };

  const deleteOrder = async (id) => {
    try {
      await apiClient.delete(`/orders/${id}`);
      setOrders(prev => prev.filter(order => order.id !== id));
    } catch (err) {
      console.error('Error deleting order:', err);
      throw err;
    }
  };

  return {
    orders,
    loading,
    error,
    total,
    createOrder,
    updateOrder,
    deleteOrder,
    refetch: fetchOrders,
    fetchMyOrders
  };
};
