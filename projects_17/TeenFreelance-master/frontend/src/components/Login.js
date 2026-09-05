import React, { useState } from 'react';
import { useApp } from '../contexts/AppContext';
import apiClient from '../services/api';
import './Login.css';

const Login = ({ onSuccess }) => {
  const { t, login } = useApp();
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [serverError, setServerError] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
    if (serverError) {
      setServerError('');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const newErrors = {};
    
    if (!formData.email.trim()) {
      newErrors.email = t('login.errors.emailRequired');
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = t('login.errors.emailInvalid');
    }
    
    if (!formData.password) {
      newErrors.password = t('login.errors.passwordRequired');
    }
    
    setErrors(newErrors);
    
    if (Object.keys(newErrors).length === 0) {
      setLoading(true);
      setServerError('');
      try {
        // Используем FormData для OAuth2PasswordRequestForm
        const formDataToSend = new FormData();
        formDataToSend.append('username', formData.email);
        formDataToSend.append('password', formData.password);
        
        const response = await apiClient.post('/auth/login', formDataToSend, {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        });
        
        // Сохраняем токен и вызываем login
        await login(response.data.access_token);
        
        if (onSuccess) {
          onSuccess('logged_in');
        }
      } catch (error) {
        console.error('Login error:', error);
        if (error.response?.status === 401) {
          setServerError(t('login.errors.invalidCredentials') || 'Неверный email или пароль');
        } else {
          setServerError(error.response?.data?.detail || 'Ошибка при входе. Попробуйте снова.');
        }
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <button 
          className="login-close"
          onClick={() => onSuccess && onSuccess(false)}
        >
          ×
        </button>
        <div className="login-header">
          <div className="brand-mark" style={{ marginBottom: '20px' }}>ТЗ</div>
          <h1 className="login-title">{t('login.title')}</h1>
          <p className="login-subtitle">{t('login.subtitle')}</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label>{t('login.email')}</label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder={t('login.emailPlaceholder')}
              className={errors.email ? 'error' : ''}
            />
            {errors.email && <span className="error-message">{errors.email}</span>}
          </div>

          <div className="form-group">
            <label>{t('login.password')}</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder={t('login.passwordPlaceholder')}
              className={errors.password ? 'error' : ''}
            />
            {errors.password && <span className="error-message">{errors.password}</span>}
          </div>

          {serverError && <div className="error-message" style={{ marginBottom: '16px' }}>{serverError}</div>}
          
          <button type="submit" className="btn primary full" disabled={loading}>
            {loading ? 'Вход...' : t('login.submit')}
          </button>
        </form>

        <div className="login-footer">
          <p>
            {t('login.noAccount')}{' '}
            <button className="link-btn" onClick={() => { if (onSuccess) onSuccess('register'); }}>
              {t('login.register')}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;

