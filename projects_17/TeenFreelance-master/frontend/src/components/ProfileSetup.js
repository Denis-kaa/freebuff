import React, { useState, useRef } from 'react';
import { useApp } from '../contexts/AppContext';
import apiClient from '../services/api';
import './ProfileSetup.css';

const ProfileSetup = ({ onComplete }) => {
  const { t, refetchUser } = useApp();
  const [formData, setFormData] = useState({
    login: '',
    name: '',
    photo: null,
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

  const availableSkills = ['UX/UI', 'React', 'Tilda', 'Figma', 'Copywriting', 'Python', 'JavaScript', 'HTML/CSS', 'Photoshop', 'Illustrator', 'InDesign', 'After Effects'];

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
      if (errors.skills) {
        setErrors(prev => ({ ...prev, skills: '' }));
      }
    }
  };

  const removeSkill = (skill) => {
    setFormData(prev => ({
      ...prev,
      skills: prev.skills.filter(s => s !== skill)
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const newErrors = {};

    if (!formData.login.trim()) {
      newErrors.login = t('profileSetup.errors.loginRequired');
    }

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

    if (!formData.workScheduleFrom.trim()) {
      newErrors.workScheduleFrom = t('profileSetup.errors.workScheduleFromRequired');
    }

    if (!formData.workScheduleTo.trim()) {
      newErrors.workScheduleTo = t('profileSetup.errors.workScheduleToRequired');
    }

    if (!formData.country.trim()) {
      newErrors.country = t('profileSetup.errors.countryRequired');
    }

    if (!formData.city.trim()) {
      newErrors.city = t('profileSetup.errors.cityRequired');
    }

    setErrors(newErrors);

    if (Object.keys(newErrors).length === 0) {
      try {
        // Создаем профиль через API
        const profileData = {
          about: formData.about,
          country: formData.country,
          city: formData.city,
          work_schedule: `${formData.workScheduleFrom} - ${formData.workScheduleTo}`
        };
        
        
        await apiClient.post('/users/me/profile', profileData);
        
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
        for (const skill of formData.skills) {
          await apiClient.post('/users/me/skills', { skill_name: skill });
        }
        
        // Обновляем данные пользователя в контексте
        if (refetchUser) {
          await refetchUser();
        }
        
        if (onComplete) {
          onComplete(profileData);
        }
      } catch (error) {
        console.error('Error saving profile:', error);
        setErrors({ submit: error.response?.data?.detail || 'Ошибка при сохранении профиля' });
      }
    }
  };

  return (
    <div className="profile-setup-container">
      <div className="profile-setup-card">
        <div className="profile-setup-header">
          <h2 className="profile-setup-title">{t('profileSetup.title')}</h2>
          <p className="profile-setup-subtitle">{t('profileSetup.subtitle')}</p>
        </div>

        <form onSubmit={handleSubmit} className="profile-setup-form">
          <div className="form-group">
            <label>{t('profileSetup.login')}</label>
            <input
              type="text"
              name="login"
              value={formData.login}
              onChange={handleChange}
              placeholder={t('profileSetup.loginPlaceholder')}
              className={errors.login ? 'error' : ''}
            />
            {errors.login && <span className="error-message">{errors.login}</span>}
            <span className="helper-text">{t('profileSetup.loginHint')}</span>
          </div>

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
                  className={errors.workScheduleFrom ? 'error' : ''}
                />
                {errors.workScheduleFrom && <span className="error-message">{errors.workScheduleFrom}</span>}
              </div>
              <div className="schedule-input-group">
                <label className="schedule-label">{t('profileSetup.workScheduleTo')}</label>
                <input
                  type="text"
                  name="workScheduleTo"
                  value={formData.workScheduleTo}
                  onChange={handleChange}
                  placeholder={t('profileSetup.workScheduleToPlaceholder')}
                  className={errors.workScheduleTo ? 'error' : ''}
                />
                {errors.workScheduleTo && <span className="error-message">{errors.workScheduleTo}</span>}
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
              className={errors.country ? 'error' : ''}
            />
            {errors.country && <span className="error-message">{errors.country}</span>}
          </div>

          <div className="form-group">
            <label>{t('profileSetup.city')}</label>
            <input
              type="text"
              name="city"
              value={formData.city}
              onChange={handleChange}
              placeholder={t('profileSetup.cityPlaceholder')}
              className={errors.city ? 'error' : ''}
            />
            {errors.city && <span className="error-message">{errors.city}</span>}
          </div>

          <div className="form-actions">
            <button type="button" className="btn ghost" onClick={() => onComplete && onComplete(null)}>
              {t('profileSetup.cancel')}
            </button>
            <button type="submit" className="btn primary">
              {t('profileSetup.complete')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ProfileSetup;
