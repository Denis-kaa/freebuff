import React, { useState, useEffect, useRef } from 'react';
import { useApp } from '../contexts/AppContext';
import apiClient from '../services/api';
import './ProfileEdit.css';

const ProfileEdit = ({ onComplete }) => {
  const { t, currentUser, refetchUser } = useApp();
  const [loading, setLoading] = useState(true);
  
  const [activeTab, setActiveTab] = useState('general');
  const [formData, setFormData] = useState({
    login: '',
    phone: '',
    email: '',
    timezone: '',
    newPassword: '',
    currentPassword: '',
    name: '',
    photo: null,
    photoPreview: null,
    specialty: '',
    about: '',
    skills: [],
    workScheduleFrom: '',
    workScheduleTo: '',
    country: '',
    city: ''
  });
  
  const photoFileRef = useRef(null);
  
  const [errors, setErrors] = useState({});
  const [skillInput, setSkillInput] = useState('');
  const [photoPreview, setPhotoPreview] = useState(null);

  // Загружаем данные профиля из API
  useEffect(() => {
    const loadProfile = async () => {
      try {
        const [userResponse, profileResponse, skillsResponse] = await Promise.all([
          apiClient.get('/users/me'),
          apiClient.get('/users/me/profile').catch(() => null),
          apiClient.get('/users/me/skills').catch(() => null)
        ]);
        
        const user = userResponse.data;
        const profile = profileResponse?.data;
        const skills = skillsResponse?.data || [];
        
        // Парсим work_schedule если есть
        let workScheduleFrom = '';
        let workScheduleTo = '';
        if (profile?.work_schedule) {
          const parts = profile.work_schedule.split(' - ');
          workScheduleFrom = parts[0] || '';
          workScheduleTo = parts[1] || '';
        }
        
        setFormData({
          login: '',
          phone: user.phone || '',
          email: user.email || '',
          timezone: '',
          newPassword: '',
          currentPassword: '',
          name: user.name || '',
          photo: null,
          photoPreview: null,
          specialty: '',
          about: profile?.about || '',
          skills: skills.map(s => s.skill_name) || [],
          workScheduleFrom,
          workScheduleTo,
          country: profile?.country || '',
          city: profile?.city || ''
        });
      } catch (error) {
        console.error('Error loading profile:', error);
      } finally {
        setLoading(false);
      }
    };
    
    loadProfile();
  }, []);

  const availableSkills = ['UX/UI', 'React', 'Tilda', 'Figma', 'Copywriting', 'Python', 'JavaScript', 'HTML/CSS', 'Photoshop', 'Illustrator', 'InDesign', 'After Effects'];
  
  const timezones = [
    'UTC+2 (Калининград)',
    'UTC+3 (Москва)',
    'UTC+4 (Самара)',
    'UTC+5 (Екатеринбург)',
    'UTC+6 (Омск)',
    'UTC+7 (Красноярск)',
    'UTC+8 (Иркутск)',
    'UTC+9 (Якутск)',
    'UTC+10 (Владивосток)',
    'UTC+11 (Магадан)',
    'UTC+12 (Камчатка)'
  ];

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
  };

  const handlePhotoChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        setErrors(prev => ({ ...prev, photo: t('profileSetup.errors.photoSize') }));
        return;
      }
      photoFileRef.current = file;
      setFormData(prev => ({ ...prev, photo: file }));
      const reader = new FileReader();
      reader.onloadend = () => {
        setPhotoPreview(reader.result);
      };
      reader.readAsDataURL(file);
      if (errors.photo) {
        setErrors(prev => ({ ...prev, photo: '' }));
      }
    }
  };

  const addSkill = (skill) => {
    if (formData.skills.length >= 12) {
      setErrors(prev => ({ ...prev, skills: t('profileSetup.errors.skillsMax') }));
      return;
    }
    if (skill && !formData.skills.includes(skill)) {
      setFormData(prev => ({
        ...prev,
        skills: [...prev.skills, skill]
      }));
      setSkillInput('');
    }
  };

  const removeSkill = (skill) => {
    setFormData(prev => ({
      ...prev,
      skills: prev.skills.filter(s => s !== skill)
    }));
  };

  const validateGeneral = () => {
    const newErrors = {};
    
    if (!formData.login.trim()) {
      newErrors.login = t('profileEdit.errors.loginRequired');
    }
    
    if (!formData.email.trim()) {
      newErrors.email = t('profileEdit.errors.emailRequired');
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = t('profileEdit.errors.emailInvalid');
    }
    
    if (formData.newPassword && !formData.currentPassword) {
      newErrors.currentPassword = t('profileEdit.errors.currentPasswordRequired');
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validateProfile = () => {
    const newErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = t('profileSetup.errors.nameRequired');
    }

    if (!formData.specialty.trim()) {
      newErrors.specialty = t('profileSetup.errors.specialtyRequired');
    } else if (formData.specialty.trim().length < 5) {
      newErrors.specialty = t('profileSetup.errors.specialtyMin');
    }

    if (!formData.about.trim()) {
      newErrors.about = t('profileSetup.errors.aboutRequired');
    } else if (formData.about.trim().length < 200) {
      newErrors.about = t('profileSetup.errors.aboutMin');
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (activeTab === 'general' && !validateGeneral()) {
      return;
    }
    
    if (activeTab === 'profile' && !validateProfile()) {
      return;
    }

    if (activeTab === 'general') {
      setActiveTab('profile');
      return;
    }

    try {
      // Обновляем профиль через API
      const profileData = {
        about: formData.about,
        country: formData.country,
        city: formData.city,
        work_schedule: `${formData.workScheduleFrom} - ${formData.workScheduleTo}`
      };
      
      await apiClient.put('/users/me/profile', profileData);
      
      // Обновляем основные данные (имя, фото) через FormData
      const userFormData = new FormData();
      userFormData.append('name', formData.name);
      
      const fileToUpload = photoFileRef.current || formData.photo;
      if (fileToUpload) {
        userFormData.append('avatar', fileToUpload);
      }
      
      await apiClient.put('/users/me', userFormData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      // Обновляем навыки
      const currentSkills = await apiClient.get('/users/me/skills').then(r => r.data.map(s => s.skill_name)).catch(() => []);
      
      // Удаляем старые навыки
      for (const skill of currentSkills) {
        if (!formData.skills.includes(skill)) {
          await apiClient.delete(`/users/me/skills/${skill}`).catch(() => {});
        }
      }
      
      // Добавляем новые навыки
      for (const skill of formData.skills) {
        if (!currentSkills.includes(skill)) {
          await apiClient.post('/users/me/skills', { skill_name: skill });
        }
      }
      
      // Обновляем данные пользователя в контексте
      if (refetchUser) {
        await refetchUser();
      }
      
      if (onComplete) {
        onComplete(profileData);
      }
    } catch (error) {
      console.error('Error updating profile:', error);
      setErrors({ submit: error.response?.data?.detail || 'Ошибка при обновлении профиля' });
    }
  };

  if (loading) {
    return (
      <div className="profile-setup-container">
        <div className="profile-setup-card">
          <div style={{ textAlign: 'center', padding: '40px' }}>Загрузка...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="profile-setup-container">
      <div className="profile-setup-card">
        <div className="profile-setup-header">
          <h2 className="profile-setup-title">{t('profileEdit.title')}</h2>
        </div>

        <div className="edit-tabs">
          <button
            type="button"
            className={`edit-tab ${activeTab === 'general' ? 'active' : ''}`}
            onClick={() => setActiveTab('general')}
          >
            {t('profileEdit.general')}
          </button>
          <button
            type="button"
            className={`edit-tab ${activeTab === 'profile' ? 'active' : ''}`}
            onClick={() => setActiveTab('profile')}
          >
            {t('profileEdit.profile')}
          </button>
        </div>

        <form onSubmit={handleSubmit} className="profile-setup-form">
          {activeTab === 'general' && (
            <>
              <div className="form-group">
                <label>{t('profileEdit.login')}</label>
                <input
                  type="text"
                  name="login"
                  value={formData.login}
                  onChange={handleChange}
                  placeholder={t('profileEdit.loginPlaceholder')}
                  className={errors.login ? 'error' : ''}
                />
                {errors.login && <span className="error-message">{errors.login}</span>}
              </div>

              <div className="form-group">
                <label>{t('profileEdit.phone')}</label>
                <input
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  placeholder={t('profileEdit.phonePlaceholder')}
                />
              </div>

              <div className="form-group">
                <label>{t('profileEdit.email')}</label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder={t('profileEdit.emailPlaceholder')}
                  className={errors.email ? 'error' : ''}
                />
                {errors.email && <span className="error-message">{errors.email}</span>}
              </div>

              <div className="form-group">
                <label>{t('profileEdit.timezone')}</label>
                <select
                  name="timezone"
                  value={formData.timezone}
                  onChange={handleChange}
                >
                  <option value="">{t('profileEdit.selectTimezone')}</option>
                  {timezones.map(tz => (
                    <option key={tz} value={tz}>{tz}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>{t('profileEdit.newPassword')}</label>
                <input
                  type="password"
                  name="currentPassword"
                  value={formData.currentPassword}
                  onChange={handleChange}
                  placeholder={t('profileEdit.currentPasswordPlaceholder')}
                  className={errors.currentPassword ? 'error' : ''}
                />
                {errors.currentPassword && <span className="error-message">{errors.currentPassword}</span>}
                <input
                  type="password"
                  name="newPassword"
                  value={formData.newPassword}
                  onChange={handleChange}
                  placeholder={t('profileEdit.newPasswordPlaceholder')}
                  style={{ marginTop: '10px' }}
                />
                {formData.newPassword && (
                  <span className="helper-text">{t('profileEdit.passwordHint')}</span>
                )}
              </div>
            </>
          )}

          {activeTab === 'profile' && (
            <>
              <div className="form-group">
                <label>{t('profileSetup.name')}</label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder={t('profileSetup.namePlaceholder')}
                  className={errors.name ? 'error' : ''}
                />
                {errors.name && <span className="error-message">{errors.name}</span>}
              </div>

              <div className="form-group">
                <label>{t('profileSetup.photo')}</label>
                <div className="photo-upload">
                  {photoPreview ? (
                    <div className="photo-preview">
                      <img src={photoPreview} alt="Preview" />
                      <button
                        type="button"
                        className="photo-remove"
                        onClick={() => {
                          setFormData(prev => ({ ...prev, photo: null }));
                          setPhotoPreview(null);
                        }}
                      >
                        ×
                      </button>
                    </div>
                  ) : (
                    <label className="photo-upload-label">
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handlePhotoChange}
                        style={{ display: 'none' }}
                      />
                      <div className="photo-upload-placeholder">
                        <span>📷</span>
                        <span>{t('profileSetup.photoUpload')}</span>
                      </div>
                    </label>
                  )}
                </div>
                {errors.photo && <span className="error-message">{errors.photo}</span>}
              </div>

              <div className="form-group">
                <label>{t('profileSetup.specialty')}</label>
                <input
                  type="text"
                  name="specialty"
                  value={formData.specialty}
                  onChange={handleChange}
                  placeholder={t('profileSetup.specialtyPlaceholder')}
                  className={errors.specialty ? 'error' : ''}
                  maxLength="50"
                />
                <div className="char-count">{formData.specialty.length}/50</div>
                {errors.specialty && <span className="error-message">{errors.specialty}</span>}
              </div>

              <div className="form-group">
                <label>{t('profileSetup.about')}</label>
                <textarea
                  name="about"
                  value={formData.about}
                  onChange={handleChange}
                  placeholder={t('profileSetup.aboutPlaceholder')}
                  rows="5"
                  className={errors.about ? 'error' : ''}
                  maxLength="1200"
                />
                <div className="char-count">{formData.about.length}/1200</div>
                {errors.about && <span className="error-message">{errors.about}</span>}
              </div>

              <div className="form-group">
                <label>{t('profileSetup.skills')} ({formData.skills.length}/12)</label>
                <div className="skills-input-group">
                  <input
                    type="text"
                    value={skillInput}
                    onChange={(e) => setSkillInput(e.target.value)}
                    placeholder={t('profileSetup.skillsPlaceholder')}
                    disabled={formData.skills.length >= 12}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        addSkill(skillInput.trim());
                      }
                    }}
                  />
                  <button
                    type="button"
                    className="btn ghost small"
                    onClick={() => addSkill(skillInput.trim())}
                    disabled={formData.skills.length >= 12}
                  >
                    {t('profileSetup.add')}
                  </button>
                </div>
                <div className="skills-suggestions">
                  {availableSkills.filter(skill => !formData.skills.includes(skill)).slice(0, 6).map(skill => (
                    <button
                      key={skill}
                      type="button"
                      className="skill-suggestion-btn"
                      onClick={() => addSkill(skill)}
                      disabled={formData.skills.length >= 12}
                    >
                      + {skill}
                    </button>
                  ))}
                </div>
                <div className="skills-tags">
                  {formData.skills.map(skill => (
                    <span key={skill} className="skill-tag">
                      {skill}
                      <button
                        type="button"
                        className="skill-remove"
                        onClick={() => removeSkill(skill)}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
                {errors.skills && <span className="error-message">{errors.skills}</span>}
              </div>

              <div className="form-group">
                <label>{t('profileSetup.workSchedule')}</label>
                <div className="schedule-inputs">
                  <div className="schedule-input-group">
                    <label className="schedule-label">{t('profileSetup.workScheduleFrom')}</label>
                    <input
                      type="text"
                      name="workScheduleFrom"
                      value={formData.workScheduleFrom}
                      onChange={handleChange}
                      placeholder={t('profileSetup.workScheduleFromPlaceholder')}
                    />
                  </div>
                  <div className="schedule-input-group">
                    <label className="schedule-label">{t('profileSetup.workScheduleTo')}</label>
                    <input
                      type="text"
                      name="workScheduleTo"
                      value={formData.workScheduleTo}
                      onChange={handleChange}
                      placeholder={t('profileSetup.workScheduleToPlaceholder')}
                    />
                  </div>
                </div>
              </div>

              <div className="form-group">
                <label>{t('profileSetup.country')}</label>
                <input
                  type="text"
                  name="country"
                  value={formData.country}
                  onChange={handleChange}
                  placeholder={t('profileSetup.countryPlaceholder')}
                />
              </div>

              <div className="form-group">
                <label>{t('profileSetup.city')}</label>
                <input
                  type="text"
                  name="city"
                  value={formData.city}
                  onChange={handleChange}
                  placeholder={t('profileSetup.cityPlaceholder')}
                />
              </div>
            </>
          )}

          <div className="form-actions">
            <button type="button" className="btn ghost" onClick={() => onComplete && onComplete(null)}>
              {t('profileSetup.cancel')}
            </button>
            {activeTab === 'general' ? (
              <button type="submit" className="btn primary">
                {t('profileEdit.next')}
              </button>
            ) : (
              <button type="submit" className="btn primary">
                {t('profileEdit.save')}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
};

export default ProfileEdit;

