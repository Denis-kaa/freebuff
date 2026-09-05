import React, { createContext, useContext, useState, useEffect } from 'react';
import apiClient from '../services/api';
import ru from '../locales/ru.json';
import en from '../locales/en.json';

const translations = { ru, en };

const AppContext = createContext();

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within AppProvider');
  }
  return context;
};

export const AppProvider = ({ children }) => {
  const [language, setLanguage] = useState(() => {
    return localStorage.getItem('language') || 'ru';
  });

  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'dark';
  });

  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    return localStorage.getItem('isAuthenticated') === 'true' || !!localStorage.getItem('access_token');
  });

  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Проверка аутентификации при загрузке
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('access_token');
      if (token) {
        try {
          const response = await apiClient.get('/users/me');
          setCurrentUser(response.data);
          setIsAuthenticated(true);
        } catch (error) {
          // Токен невалидный
          localStorage.removeItem('access_token');
          setIsAuthenticated(false);
          setCurrentUser(null);
        }
      }
      setLoading(false);
    };
    checkAuth();
  }, []);

  useEffect(() => {
    localStorage.setItem('language', language);
    document.documentElement.setAttribute('data-language', language);
  }, [language]);

  useEffect(() => {
    localStorage.setItem('theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
  }, []);

  const t = (key) => {
    const keys = key.split('.');
    let value = translations[language];
    for (const k of keys) {
      value = value?.[k];
    }
    return value || key;
  };

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  const changeLanguage = (lang) => {
    setLanguage(lang);
  };

  const login = async (token, userData = null) => {
    if (!token) return;
    
    // Сначала сохраняем токен, чтобы перехватчик Axios мог его использовать
    localStorage.setItem('access_token', token);
    localStorage.setItem('isAuthenticated', 'true');
    
    // Затем обновляем состояние, чтобы вызвать ререндеринг
    setIsAuthenticated(true);
    
    if (userData) {
      setCurrentUser(userData);
    } else {
      try {
        // Теперь запрос должен уйти с токеном
        const response = await apiClient.get('/users/me');
        setCurrentUser(response.data);
      } catch (error) {
        console.error('Failed to fetch user data after login:', error);
        // Если не удалось получить данные пользователя, возможно токен неверный
        if (error.response?.status === 401) {
          logout();
        }
      }
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.setItem('isAuthenticated', 'false');
    setIsAuthenticated(false);
    setCurrentUser(null);
  };

  const refreshUser = async () => {
    try {
      const response = await apiClient.get('/users/me');
      setCurrentUser(response.data);
      return response.data;
    } catch (error) {
      console.error('Failed to refresh user data:', error);
      return null;
    }
  };

  const refetchUser = async () => {
    try {
      const response = await apiClient.get('/users/me');
      setCurrentUser(response.data);
    } catch (error) {
      console.error('Failed to refetch user:', error);
    }
  };

  return (
    <AppContext.Provider value={{
      language,
      theme,
      isAuthenticated,
      currentUser,
      loading,
      t,
      toggleTheme,
      changeLanguage,
      login,
      logout,
      refreshUser,
      refetchUser
    }}>
      {children}
    </AppContext.Provider>
  );
};

