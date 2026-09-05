import React, { useState } from 'react';
import { useApp } from '../contexts/AppContext';
import apiClient from '../services/api';
import './Register.css';

const Register = ({ onSuccess }) => {
  const { t, login } = useApp();
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    age: '',
    role: 'executor',
    phone: '',
    agreeToTerms: false
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [serverError, setServerError] = useState('');

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const validateStep1 = () => {
    const newErrors = {};
    if (!formData.name.trim()) {
      newErrors.name = t('register.errors.nameRequired');
    }
    if (!formData.email.trim()) {
      newErrors.email = t('register.errors.emailRequired');
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = t('register.errors.emailInvalid');
    }
    if (!formData.password) {
      newErrors.password = t('register.errors.passwordRequired');
    } else if (formData.password.length < 8) {
      newErrors.password = t('register.errors.passwordMin');
    }
    if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = t('register.errors.passwordMatch');
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validateStep2 = () => {
    const newErrors = {};
    if (!formData.age) {
      newErrors.age = t('register.errors.ageRequired');
    } else {
      const ageNum = parseInt(formData.age);
      if (ageNum < 14 || ageNum > 18) {
        newErrors.age = t('register.errors.ageRange');
      }
    }
    if (!formData.phone.trim()) {
      newErrors.phone = t('register.errors.phoneRequired');
    }
    if (!formData.agreeToTerms) {
      newErrors.agreeToTerms = t('register.errors.agreeRequired');
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (step === 1 && validateStep1()) {
      setStep(2);
    }
  };

  const handleBack = () => {
    setStep(step - 1);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (validateStep2()) {
      setLoading(true);
      setServerError('');
      try {
        const { confirmPassword, agreeToTerms, ...userData } = formData;
        const response = await apiClient.post('/auth/register', userData);
        
        // После успешной регистрации автоматически входим
        const loginFormData = new FormData();
        loginFormData.append('username', formData.email);
        loginFormData.append('password', formData.password);
        
        const loginResponse = await apiClient.post('/auth/login', loginFormData, {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        });
        
        await login(loginResponse.data.access_token);
        
        if (onSuccess) {
          onSuccess('registered');
        }
      } catch (error) {
        console.error('Registration error:', error);
        if (error.response?.status === 400) {
          setServerError(error.response?.data?.detail || 'Ошибка при регистрации');
        } else {
          setServerError('Ошибка при регистрации. Попробуйте снова.');
        }
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <div className="register-container">
      <div className="register-card">
        <button 
          className="register-close"
          onClick={() => onSuccess && onSuccess()}
        >
          ×
        </button>
        <div className="register-header">
          <div className="brand-mark" style={{ marginBottom: '20px' }}>ТЗ</div>
          <h1 className="register-title">{t('register.title')}</h1>
          <p className="register-subtitle">{t('register.subtitle')}</p>
        </div>

        <form onSubmit={handleSubmit} className="register-form">
          {step === 1 && (
            <>
              <div className="form-group">
                <label>{t('register.name')}</label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder={t('register.namePlaceholder')}
                  className={errors.name ? 'error' : ''}
                />
                {errors.name && <span className="error-message">{errors.name}</span>}
              </div>

              <div className="form-group">
                <label>{t('register.email')}</label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder={t('register.emailPlaceholder')}
                  className={errors.email ? 'error' : ''}
                />
                {errors.email && <span className="error-message">{errors.email}</span>}
              </div>

              <div className="form-group">
                <label>{t('register.password')}</label>
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder={t('register.passwordPlaceholder')}
                  className={errors.password ? 'error' : ''}
                />
                {errors.password && <span className="error-message">{errors.password}</span>}
              </div>

              <div className="form-group">
                <label>{t('register.confirmPassword')}</label>
                <input
                  type="password"
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder={t('register.confirmPasswordPlaceholder')}
                  className={errors.confirmPassword ? 'error' : ''}
                />
                {errors.confirmPassword && <span className="error-message">{errors.confirmPassword}</span>}
              </div>

              <button type="button" className="btn primary full" onClick={handleNext}>
                {t('register.next')}
              </button>
            </>
          )}

          {step === 2 && (
            <>
              <div className="form-group">
                <label>{t('register.age')}</label>
                <input
                  type="number"
                  name="age"
                  value={formData.age}
                  onChange={handleChange}
                  placeholder={t('register.agePlaceholder')}
                  min="14"
                  max="18"
                  className={errors.age ? 'error' : ''}
                />
                {errors.age && <span className="error-message">{errors.age}</span>}
              </div>

              <div className="form-group">
                <label>{t('register.phone')}</label>
                <input
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  placeholder={t('register.phonePlaceholder')}
                  className={errors.phone ? 'error' : ''}
                />
                {errors.phone && <span className="error-message">{errors.phone}</span>}
              </div>

              <div className="form-group">
                <label>{t('register.role')}</label>
                <div className="role-selector">
                  <button
                    type="button"
                    className={`role-btn ${formData.role === 'executor' ? 'active' : ''}`}
                    onClick={() => setFormData(prev => ({ ...prev, role: 'executor' }))}
                  >
                    <span className="role-icon">👤</span>
                    <div>
                      <div className="role-title">{t('register.executor')}</div>
                      <div className="role-desc">{t('register.executorDesc')}</div>
                    </div>
                  </button>
                  <button
                    type="button"
                    className={`role-btn ${formData.role === 'customer' ? 'active' : ''}`}
                    onClick={() => setFormData(prev => ({ ...prev, role: 'customer' }))}
                  >
                    <span className="role-icon">💼</span>
                    <div>
                      <div className="role-title">{t('register.client')}</div>
                      <div className="role-desc">{t('register.clientDesc')}</div>
                    </div>
                  </button>
                </div>
              </div>

              <div className="form-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    name="agreeToTerms"
                    checked={formData.agreeToTerms}
                    onChange={handleChange}
                    className={errors.agreeToTerms ? 'error' : ''}
                  />
                  <span>{t('register.agreeToTerms')}</span>
                </label>
                {errors.agreeToTerms && <span className="error-message">{errors.agreeToTerms}</span>}
              </div>

              {serverError && <div className="error-message" style={{ marginBottom: '16px' }}>{serverError}</div>}
              
              <div className="form-actions">
                <button type="button" className="btn ghost" onClick={handleBack} disabled={loading}>
                  {t('register.back')}
                </button>
                <button type="submit" className="btn primary" disabled={loading}>
                  {loading ? 'Регистрация...' : t('register.submit')}
                </button>
              </div>
            </>
          )}
        </form>

        <div className="register-footer">
          <p>
            {t('register.haveAccount')}{' '}
            <button className="link-btn" onClick={() => { if (onSuccess) onSuccess(false); }}>
              {t('register.login')}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Register;

