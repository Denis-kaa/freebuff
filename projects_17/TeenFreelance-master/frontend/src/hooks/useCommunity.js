import { useState, useEffect } from 'react';
import apiClient from '../services/api';

export const useCommunity = (filter = 'all') => {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchPosts = async (userId = null) => {
    try {
      setLoading(true);
      const params = userId ? { user_id: userId } : {};
      const response = await apiClient.get('/community/posts', { params });
      setPosts(response.data.items || []);
      setError(null);
    } catch (err) {
      console.error('Error fetching posts:', err);
      setError(err.response?.data?.detail || 'Ошибка загрузки постов');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Если фильтр 'my', нужно получить user_id из контекста
    // Пока загружаем все посты
    fetchPosts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  const createPost = async (postData) => {
    try {
      const response = await apiClient.post('/community/posts', postData);
      setPosts(prev => [response.data, ...prev]);
      return response.data;
    } catch (err) {
      console.error('Error creating post:', err);
      throw err;
    }
  };

  const updatePost = async (id, postData) => {
    try {
      const response = await apiClient.put(`/community/posts/${id}`, postData);
      setPosts(prev => prev.map(post => post.id === id ? response.data : post));
      return response.data;
    } catch (err) {
      console.error('Error updating post:', err);
      throw err;
    }
  };

  const deletePost = async (id) => {
    try {
      await apiClient.delete(`/community/posts/${id}`);
      setPosts(prev => prev.filter(post => post.id !== id));
    } catch (err) {
      console.error('Error deleting post:', err);
      throw err;
    }
  };

  const toggleLike = async (postId) => {
    try {
      const response = await apiClient.post(`/community/posts/${postId}/like`);
      setPosts(prev => prev.map(post =>
        post.id === postId
          ? { ...post, is_liked: response.data.is_liked, likes_count: response.data.likes_count }
          : post
      ));
      return response.data;
    } catch (err) {
      console.error('Error toggling like:', err);
      throw err;
    }
  };

  const addComment = async (postId, text) => {
    try {
      const response = await apiClient.post(`/community/posts/${postId}/comments`, { text });
      // Обновляем счётчик комментариев локально
      setPosts(prev => prev.map(post =>
        post.id === postId
          ? { ...post, comments_count: (post.comments_count || 0) + 1 }
          : post
      ));
      return response.data;
    } catch (err) {
      console.error('Error adding comment:', err);
      throw err;
    }
  };

  const fetchComments = async (postId) => {
    try {
      const response = await apiClient.get(`/community/posts/${postId}/comments`);
      return response.data || [];
    } catch (err) {
      console.error('Error fetching comments:', err);
      return [];
    }
  };

  return {
    posts,
    loading,
    error,
    createPost,
    updatePost,
    deletePost,
    toggleLike,
    addComment,
    fetchComments,
    refetch: fetchPosts
  };
};
