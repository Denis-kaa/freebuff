import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL;

const apiClient = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor для добавления токена к запросам
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      // Поддержка различных версий Axios для установки заголовков
      if (config.headers.set) {
        config.headers.set('Authorization', `Bearer ${token}`);
      } else {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor для обработки ошибок
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Токен истек или невалидный
      const currentPath = window.location.pathname;
      localStorage.removeItem('access_token');
      localStorage.setItem('isAuthenticated', 'false');
      
      // Редиректим только если мы не на главной странице и не на home
      // Используем проверку, чтобы не зацикливать редирект на страницах входа
      if (currentPath !== '/' && currentPath !== '/home' && !currentPath.includes('login')) {
        window.location.href = '/home';
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;

