import React, { useMemo, useState, useEffect, useRef, useCallback } from 'react';
import { useApp } from './contexts/AppContext';
import { useNavigate, useLocation } from 'react-router-dom';
import Register from './components/Register';
import Login from './components/Login';
import ProfileSetup from './components/ProfileSetup';
import ProfileEdit from './components/ProfileEdit';
import { ORDERS_CATEGORIES } from './ordersCategories';
import { usePortfolio } from './hooks/usePortfolio';
import { useCommunity } from './hooks/useCommunity';
import { useOrders } from './hooks/useOrders';
import { useNotes } from './hooks/useNotes';
import apiClient from './services/api';
import './App.css';

const getInitials = (name) => {
  if (!name) return 'П';
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  return name[0].toUpperCase();
};

const TabContent = ({
  tab,
  t,
  onFillProfile,
  onEditProfile,
  navigate,
  onAddWork,
  onEditWork,
  onDeleteWork,
  portfolioItems = [],
  categoriesList = [],
  userRole,
  toggleUserRole,
  orderNotesHook,
  communityPostsHook,
  currentUser,
  myOrders = [],
  fetchMyOrders,
  setActiveTab,
  setViewMode,
  publicOrders = [],
  publicOrdersLoading = false,
  budgetFrom,
  setBudgetFrom,
  budgetTo,
  setBudgetTo,
  keywords,
  setKeywords,
  selectedOrdersSubcategories,
  setSelectedOrdersSubcategories,
  selectedOrdersSubSubcategories,
  setSelectedOrdersSubSubcategories,
  selectedBudgetRanges,
  setSelectedBudgetRanges,
  hiredPercent,
  setHiredPercent,
  selectedOfferRanges,
  setSelectedOfferRanges,
}) => {
  // TabContent для работы с API

  // Форматирование даты в DD.MM.YYYY
  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return '';
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    return `${day}.${month}.${year}`;
  };

  // Перевод статуса заказа
  const getOrderStatusText = (status) => {
    const map = {
      'draft': 'Черновик',
      'open': 'Открыт',
      'in_progress': 'В работе',
      'review': 'На проверке',
      'completed': 'Завершён',
      'cancelled': 'Отменён'
    };
    const val = status?.value || status;
    return map[val] || val || 'Открыт';
  };

  // Цвет бейджа статуса
  const getOrderStatusColor = (status) => {
    const val = status?.value || status;
    switch (val) {
      case 'open': return '#22c55e';
      case 'in_progress': return '#3b82f6';
      case 'review': return '#f59e0b';
      case 'completed': return '#8b5cf6';
      case 'cancelled': return '#ef4444';
      case 'draft': return '#6b7280';
      default: return '#22c55e';
    }
  };

  // Используем хуки для работы с API
  const { getNote, saveNote, fetchNote } = orderNotesHook || { getNote: () => '', saveNote: async () => { }, fetchNote: async () => { } };
  const communityPosts = communityPostsHook?.posts || [];
  const { addComment: addCommentHook } = communityPostsHook || {};
  const currentUserName = currentUser?.name || 'Пользователь';

  const [noteModalOpen, setNoteModalOpen] = useState(false);
  const [noteDraft, setNoteDraft] = useState('');
  const [noteTarget, setNoteTarget] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState('Все рубрики');
  const [filterOpen, setFilterOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [messagesLoading, setMessagesLoading] = useState(true);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [conversationMessages, setConversationMessages] = useState([]);
  const [conversationLoading, setConversationLoading] = useState(false);
  // Пагинация переписки: порции как в мессенджерах
  const MESSAGES_PAGE_SIZE = 100;
  const [hasMoreMessages, setHasMoreMessages] = useState(false);
  const [oldestMessageId, setOldestMessageId] = useState(null);
  const [loadingMoreMessages, setLoadingMoreMessages] = useState(false);
  const [newMessageText, setNewMessageText] = useState('');
  const messagesContainerRef = useRef(null);
  const isUserScrolledUpRef = useRef(false);
  const [myOrdersFilter, setMyOrdersFilter] = useState('all');
  const [orderSearch, setOrderSearch] = useState('');
  const [expandedCategoryId, setExpandedCategoryId] = useState(null);
  const [expandedSubcategoryId, setExpandedSubcategoryId] = useState(null);
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  // hiredPercent и selectedOfferRanges приходят из App-уровня через props
  // (были подняты для использования в publicOrdersFilters)
  const [showCreatePostModal, setShowCreatePostModal] = useState(false);
  const [postText, setPostText] = useState('');
  const [postPhotos, setPostPhotos] = useState([]);
  const postPhotoInputRef = useRef(null);
  const editPhotoInputRef = useRef(null);
  const [showCommentsModal, setShowCommentsModal] = useState(false);
  const [selectedPostId, setSelectedPostId] = useState(null);
  const [commentText, setCommentText] = useState('');
  const [commentsData, setCommentsData] = useState([]);
  const [commentsLoading, setCommentsLoading] = useState(false);
  const [communityFilter, setCommunityFilter] = useState('all'); // 'all' or 'my'
  const [editingPostId, setEditingPostId] = useState(null);
  const [editPostText, setEditPostText] = useState('');
  const [editPostPhotos, setEditPostPhotos] = useState([]);
  const [postImageIndex, setPostImageIndex] = useState({}); // { postId: currentIndex }
  const [touchStartPos, setTouchStartPos] = useState({}); // { postId: { x, y } }
  const [touchEndPos, setTouchEndPos] = useState({});
  const [showOfferModal, setShowOfferModal] = useState(false);
  const [viewingProject, setViewingProject] = useState(null);
  const [directOfferRecipient, setDirectOfferRecipient] = useState(null); // Для прямых предложений в чате
  const [offerForm, setOfferForm] = useState({
    description: '',
    totalPrice: '',
    paymentType: 'full', // 'full' or 'stages'
    orderName: '',
    deadline: '',
    stages: [{ name: '', price: '' }]
  });
  const [showCreateProjectModal, setShowCreateProjectModal] = useState(false);
  const [projectForm, setProjectForm] = useState({
    title: '',
    description: '',
    category: null, // {category, subcategory, subsubcategory}
    maxPrice: '',
    allowHigherPrice: false,
    files: [],
    deadline: '',
    skills: [],
    files: []
  });
  const [projectCategoryOpen, setProjectCategoryOpen] = useState(false);
  const [showProjectCategoryModal, setShowProjectCategoryModal] = useState(false);
  const [expandedProjectCategory, setExpandedProjectCategory] = useState(null);
  const [expandedProjectSubcategory, setExpandedProjectSubcategory] = useState(null);
  const [skillInput, setSkillInput] = useState('');
  // Загружаем проекты заказчика из API
  const [customerProjects, setCustomerProjects] = useState([]);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const [projectsFilter, setProjectsFilter] = useState('all');

  // Фильтрация проектов по статусу (должна быть на верхнем уровне)
  const customerProjectsFiltered = useMemo(() => {
    if (!Array.isArray(customerProjects)) return [];
    if (projectsFilter === 'all') return customerProjects;

    return customerProjects.filter((project) => {
      const statusValue = project.status?.value || project.status || 'open';
      const statusLower = statusValue.toLowerCase().replace('_', '-');

      const statusMap = {
        'pending': ['open', 'pending'],
        'in-progress': ['in-progress', 'in_progress'],
        'completed': ['completed', 'done'],
        'cancelled': ['cancelled', 'canceled']
      };

      const targetStatuses = statusMap[projectsFilter] || [projectsFilter];
      return targetStatuses.some(s => statusLower.includes(s.toLowerCase()));
    });
  }, [customerProjects, projectsFilter]);

  // Загружаем данные профиля из API
  const [userProfile, setUserProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [hasProfile, setHasProfile] = useState(false);

  useEffect(() => {
    if (tab === 'projects') {
      const fetchProjects = async () => {
        try {
          setProjectsLoading(true);
          const params = {};
          // Маппинг фильтров на статусы API
          if (projectsFilter !== 'all') {
            const statusMap = {
              'pending': 'open',
              'in-progress': 'in_progress',
              'completed': 'completed',
              'cancelled': 'cancelled'
            };
            if (statusMap[projectsFilter]) {
              params.status = statusMap[projectsFilter];
            }
          }
          const response = await apiClient.get('/orders/my', { params });
          setCustomerProjects(response.data.items || []);
        } catch (error) {
          console.error('Error fetching projects:', error);
        } finally {
          setProjectsLoading(false);
        }
      };
      fetchProjects();
    }
  }, [tab, projectsFilter]);

  useEffect(() => {
    if (tab === 'profile') {
      const fetchProfile = async () => {
        if (!currentUser) {
          setProfileLoading(false);
          return;
        }
        try {
          setProfileLoading(true);
          const response = await apiClient.get('/users/me/profile');
          setUserProfile(response.data);
          setHasProfile(true);
        } catch (error) {
          if (error.response?.status === 404) {
            setHasProfile(false);
          } else {
            console.error('Error fetching profile:', error);
          }
        } finally {
          setProfileLoading(false);
        }
      };
      fetchProfile();
    }
  }, [tab, currentUser]);

  // Загрузка истории транзакций кошелька
  const [walletTransactions, setWalletTransactions] = useState([]);
  const [walletLoading, setWalletLoading] = useState(false);

  useEffect(() => {
    if (tab === 'wallet' && currentUser) {
      const fetchTransactions = async () => {
        try {
          setWalletLoading(true);
          const response = await apiClient.get('/users/me/transactions');
          setWalletTransactions(response.data || []);
        } catch (error) {
          console.error('Error fetching transactions:', error);
          setWalletTransactions([]);
        } finally {
          setWalletLoading(false);
        }
      };
      fetchTransactions();
    }
  }, [tab, currentUser]);

  // Загрузка сообщений
  // WebSocket подключение для real-time сообщений
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const pollingIntervalRef = useRef(null);
  const pollingTimeoutRef = useRef(null);

  // Функция для проверки, находится ли пользователь внизу чата
  const isScrolledToBottom = () => {
    if (!messagesContainerRef.current) return true;
    const container = messagesContainerRef.current;
    const threshold = 100; // Порог в пикселях от низа
    return container.scrollHeight - container.scrollTop - container.clientHeight < threshold;
  };

  // Функция для прокрутки вниз
  const scrollToBottom = (smooth = true) => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTo({
        top: messagesContainerRef.current.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto'
      });
    }
  };

  useEffect(() => {
    if (tab === 'messages' && currentUser) {
      const fetchMessages = async () => {
        try {
          setMessagesLoading(true);
          const response = await apiClient.get('/messages');
          setMessages(response.data || []);
        } catch (error) {
          console.error('Error fetching messages:', error);
        } finally {
          setMessagesLoading(false);
        }
      };

      fetchMessages();

      // Polling для получения новых сообщений (fallback если WebSocket не работает)
      const startPolling = () => {
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
        }
        pollingIntervalRef.current = setInterval(async () => {
          try {
            const response = await apiClient.get('/messages');
            setMessages(prev => {
              const newMessages = response.data || [];
              // Обновляем только если есть новые сообщения
              const prevIds = new Set(prev.map(m => m.id));
              const hasNew = newMessages.some(m => !prevIds.has(m.id));
              if (hasNew) {
                return newMessages.sort((a, b) =>
                  new Date(b.created_at) - new Date(a.created_at)
                );
              }
              return prev;
            });

            // Обновляем переписку если открыта
            if (selectedConversation) {
              const convResponse = await apiClient.get(`/messages/conversation/${selectedConversation.userId}`);
              setConversationMessages(prev => {
                const newConvMessages = convResponse.data || [];
                const prevIds = new Set(prev.map(m => m.id));
                const hasNew = newConvMessages.some(m => !prevIds.has(m.id));
                if (hasNew) {
                  const updated = newConvMessages.sort((a, b) =>
                    new Date(a.created_at) - new Date(b.created_at)
                  );
                  // Возвращаем обновленные сообщения - прокрутка произойдет через useEffect
                  return updated;
                }
                return prev;
              });
            }
          } catch (error) {
            console.error('Error polling messages:', error);
          }
        }, 500); // Обновляем каждые 500ms для более быстрого отклика
      };

      // Подключаемся к WebSocket для real-time обновлений
      const connectWebSocket = () => {
        const token = localStorage.getItem('access_token');
        if (!token) {
          console.log('No token available for WebSocket, using polling');
          startPolling();
          return;
        }

        // Закрываем существующее подключение если есть
        if (wsRef.current) {
          wsRef.current.close();
          wsRef.current = null;
        }

        const API_URL = process.env.REACT_APP_API_URL;
        const wsBaseUrl = API_URL ? API_URL.replace('http://', 'ws://').replace('https://', 'wss://') : '';
        const wsUrl = `${wsBaseUrl}/api/v1/ws?token=${encodeURIComponent(token)}`;

        console.log('Connecting to WebSocket:', wsUrl);
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          console.log('✅ WebSocket connected successfully');
          // Останавливаем polling если WebSocket подключен
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }
          // Очищаем таймер переподключения если был
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
          }
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log('📨 WebSocket message received:', data);

            if (data.type === 'new_message' || data.type === 'message_sent') {
              const newMessage = data.message;
              console.log('New message via WebSocket:', newMessage);

              // Обновляем список сообщений
              setMessages(prev => {
                // Проверяем, нет ли уже такого сообщения
                const exists = prev.some(m => m.id === newMessage.id);
                if (exists) {
                  return prev;
                }
                // Сортируем по дате создания (новые сверху)
                const updated = [newMessage, ...prev].sort((a, b) =>
                  new Date(b.created_at) - new Date(a.created_at)
                );
                return updated;
              });

              // Если открыта переписка с отправителем/получателем, обновляем её
              setConversationMessages(prev => {
                const otherUserId = newMessage.from_user_id === currentUser?.id
                  ? newMessage.to_user_id
                  : newMessage.from_user_id;

                // Проверяем, относится ли сообщение к текущей переписке
                if (selectedConversation && selectedConversation.userId === otherUserId) {
                  const exists = prev.some(m => m.id === newMessage.id);
                  if (exists) {
                    return prev;
                  }
                  const updated = [...prev, newMessage].sort((a, b) =>
                    new Date(a.created_at) - new Date(b.created_at)
                  );
                  // Автоматически прокручиваем вниз при получении нового сообщения
                  // Прокручиваем только если пользователь был внизу или не прокручивал вверх
                  const shouldScroll = isScrolledToBottom() || !isUserScrolledUpRef.current;
                  if (shouldScroll) {
                    // Используем requestAnimationFrame для гарантии что DOM обновлен
                    requestAnimationFrame(() => {
                      requestAnimationFrame(() => {
                        if (messagesContainerRef.current) {
                          messagesContainerRef.current.scrollTo({
                            top: messagesContainerRef.current.scrollHeight,
                            behavior: 'smooth'
                          });
                        }
                      });
                    });
                  }
                  return updated;
                }
                return prev;
              });
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        ws.onerror = (error) => {
          console.error('❌ WebSocket error:', error);
          // Запускаем polling если WebSocket не работает
          if (!pollingIntervalRef.current) {
            startPolling();
          }
        };

        ws.onclose = (event) => {
          console.log('🔌 WebSocket disconnected', event.code, event.reason);
          wsRef.current = null;

          // Запускаем polling если WebSocket отключился
          if (!pollingIntervalRef.current) {
            startPolling();
          }

          // Переподключаемся только если это не было намеренное закрытие
          // И не было ошибки авторизации (1008 = POLICY_VIOLATION)
          if (event.code !== 1000 && event.code !== 1008 && tab === 'messages' && currentUser) {
            console.log('Reconnecting WebSocket in 3 seconds...');
            reconnectTimeoutRef.current = setTimeout(() => {
              connectWebSocket();
            }, 3000);
          } else if (event.code === 1008) {
            console.error('❌ WebSocket connection rejected (403 Forbidden). Token may be invalid or expired.');
            // Пробуем обновить токен или перезагрузить страницу
            const token = localStorage.getItem('access_token');
            if (!token) {
              console.log('No token found, redirecting to login');
              window.location.href = '/home';
            }
          }
        };

        wsRef.current = ws;
      };

      // Пробуем подключиться к WebSocket, если не получится - используем polling
      connectWebSocket();

      // Запускаем polling как fallback (будет остановлен если WebSocket подключится)
      // Уменьшаем задержку для более быстрого старта
      const pollingTimeout = setTimeout(() => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          startPolling();
        }
      }, 500);

      return () => {
        // Очищаем таймер переподключения
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
        // Останавливаем polling
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        // Очищаем таймер запуска polling
        if (pollingTimeoutRef.current) {
          clearTimeout(pollingTimeoutRef.current);
          pollingTimeoutRef.current = null;
        }
        // Закрываем WebSocket
        if (wsRef.current) {
          wsRef.current.close(1000, 'Component unmounting');
          wsRef.current = null;
        }
      };
    } else {
      // Закрываем WebSocket если ушли со вкладки сообщений
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
      if (pollingTimeoutRef.current) {
        clearTimeout(pollingTimeoutRef.current);
        pollingTimeoutRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Leaving messages tab');
        wsRef.current = null;
      }
    }
  }, [tab, currentUser?.id, selectedConversation?.userId]); // Добавил selectedConversation.userId для обновления переписки

  // Загрузка переписки с выбранным пользователем (последние MESSAGES_PAGE_SIZE сообщений)
  useEffect(() => {
    if (tab === 'messages' && selectedConversation && currentUser) {
      const fetchConversation = async () => {
        try {
          setConversationLoading(true);
          const response = await apiClient.get(`/messages/conversation/${selectedConversation.userId}`, {
            params: { limit: MESSAGES_PAGE_SIZE },
          });
          const data = Array.isArray(response.data) ? response.data : [];
          setConversationMessages(data);
          setHasMoreMessages(data.length === MESSAGES_PAGE_SIZE);
          setOldestMessageId(data.length ? data[0].id : null);
          // Сбрасываем флаг прокрутки вверх при загрузке новой переписки
          isUserScrolledUpRef.current = false;
          // Прокручиваем вниз после загрузки мгновенно (без анимации)
          requestAnimationFrame(() => {
            requestAnimationFrame(() => {
              if (messagesContainerRef.current) {
                messagesContainerRef.current.scrollTo({
                  top: messagesContainerRef.current.scrollHeight,
                  behavior: 'auto',
                });
              }
            });
          });
        } catch (error) {
          console.error('Error fetching conversation:', error);
        } finally {
          setConversationLoading(false);
        }
      };

      fetchConversation();
    }
  }, [tab, selectedConversation?.userId, currentUser?.id]);

  // Автоматическая прокрутка вниз при появлении новых сообщений
  const lastMessageId = conversationMessages.length > 0
    ? conversationMessages[conversationMessages.length - 1]?.id
    : null;

  useEffect(() => {
    if (tab === 'messages' && selectedConversation && conversationMessages.length > 0 && lastMessageId) {
      // Прокручиваем вниз только если пользователь был внизу или не прокручивал вверх
      const shouldScroll = isScrolledToBottom() || !isUserScrolledUpRef.current;
      if (shouldScroll) {
        // Используем небольшую задержку для гарантии что DOM обновлен
        const timeoutId = setTimeout(() => {
          if (messagesContainerRef.current) {
            const container = messagesContainerRef.current;
            container.scrollTo({
              top: container.scrollHeight,
              behavior: 'smooth'
            });
            // Сбрасываем флаг прокрутки вверх после прокрутки
            isUserScrolledUpRef.current = false;
          }
        }, 150);
        return () => clearTimeout(timeoutId);
      }
    }
  }, [lastMessageId, tab, selectedConversation?.userId]); // Отслеживаем изменения последнего сообщения

  const projectFilesInputRef = useRef(null);

  const handleProjectFilesChange = (e) => {
    const files = Array.from(e.target.files || []);
    const currentFiles = projectForm.files || [];

    if (currentFiles.length + files.length > 10) {
      alert('Максимум 10 файлов');
      return;
    }

    // Проверка общего размера (100 МБ = 100 * 1024 * 1024 байт)
    const maxTotalSize = 100 * 1024 * 1024;
    const currentSize = currentFiles.reduce((sum, f) => sum + (f.file?.size || 0), 0);
    const newSize = files.reduce((sum, f) => sum + (f.size || 0), 0);

    if (currentSize + newSize > maxTotalSize) {
      alert('Общий размер файлов не должен превышать 100 МБ');
      return;
    }

    const newFiles = files.map((file) => ({
      file,
      name: file.name,
      url: URL.createObjectURL(file),
      type: file.type
    }));

    setProjectForm({ ...projectForm, files: [...currentFiles, ...newFiles] });
  };

  const removeProjectFile = (index) => {
    const newFiles = projectForm.files.filter((_, i) => i !== index);
    setProjectForm({ ...projectForm, files: newFiles });
  };

  const handleSelectProjectCategory = (category, subcategory, subsubcategory) => {
    setProjectForm({
      ...projectForm,
      category: {
        category: category.name,
        subcategory: subcategory.name,
        subsubcategory: subsubcategory ? subsubcategory.name : null
      }
    });
    setShowProjectCategoryModal(false);
    setExpandedProjectCategory(null);
    setExpandedProjectSubcategory(null);
  };

  const addSkill = () => {
    if (skillInput.trim() && projectForm.skills.length < 5 && !projectForm.skills.includes(skillInput.trim())) {
      setProjectForm({ ...projectForm, skills: [...projectForm.skills, skillInput.trim()] });
      setSkillInput('');
    }
  };

  const removeSkill = (index) => {
    const newSkills = projectForm.skills.filter((_, i) => i !== index);
    setProjectForm({ ...projectForm, skills: newSkills });
  };

  const handleDeleteProject = async (projectId) => {
    try {
      await apiClient.delete(`/orders/${projectId}`);
      const updated = customerProjects.filter(p => p.id !== projectId);
      setCustomerProjects(updated);
    } catch (error) {
      console.error('Error deleting project:', error);
      alert(error.response?.data?.detail || 'Ошибка при удалении проекта');
    }
  };

  const calculateCommission = (price) => {
    const numPrice = parseFloat(price) || 0;
    const dealCommission = numPrice * 0.07; // 7% комиссия сделки
    const responseCommission = numPrice > 5000 ? numPrice * 0.01 : 0; // 1% если > 5000
    const totalCommission = dealCommission + responseCommission;
    const toReceive = numPrice - totalCommission;

    return {
      price: numPrice,
      dealCommission,
      responseCommission,
      totalCommission,
      toReceive
    };
  };

  const getTotalStagesPrice = () => {
    return offerForm.stages.reduce((sum, stage) => sum + (parseFloat(stage.price) || 0), 0);
  };

  const isStagesPriceValid = () => {
    const totalPrice = parseFloat(offerForm.totalPrice) || 0;
    const stagesTotal = getTotalStagesPrice();
    return stagesTotal <= totalPrice;
  };

  // Константы для комиссий исполнителя
  const COMMISSION_RATE = 0.07; // 7%
  const WITHDRAWAL_RATE = 0.03; // 3%
  const PAID_RESPONSE_THRESHOLD = 5000;
  const PAID_RESPONSE_RATE = 0.01; // 1%

  // Функции для работы с этапами
  const addStage = () => {
    setOfferForm({
      ...offerForm,
      stages: [...offerForm.stages, { name: '', price: '' }]
    });
  };

  const removeStage = (index) => {
    const newStages = offerForm.stages.filter((_, i) => i !== index);
    setOfferForm({ ...offerForm, stages: newStages });
  };

  const updateStage = (index, field, value) => {
    const newStages = [...offerForm.stages];
    newStages[index] = { ...newStages[index], [field]: value };
    setOfferForm({ ...offerForm, stages: newStages });
  };

  const handleOfferSubmit = async () => {
    // Проверяем, это прямое предложение в чате или отклик на проект
    const isDirectOffer = directOfferRecipient && !viewingProject;
    const isCustomer = currentUser?.role === 'customer' || currentUser?.role === 'CUSTOMER';
    const isExecutor = currentUser?.role === 'executor' || currentUser?.role === 'EXECUTOR';

    console.log('🔍 handleOfferSubmit:', {
      isDirectOffer,
      viewingProject: viewingProject?.id,
      directOfferRecipient: directOfferRecipient?.userId,
      isCustomer,
      isExecutor
    });

    // Валидация формы
    if (!offerForm.description || !offerForm.description.trim()) {
      alert('Пожалуйста, укажите описание предложения');
      return;
    }

    if (!offerForm.totalPrice || parseFloat(offerForm.totalPrice) <= 0) {
      alert('Пожалуйста, укажите корректную стоимость');
      return;
    }

    if (!viewingProject && !isDirectOffer) {
      console.error('❌ Ошибка: проект не выбран', { viewingProject, isDirectOffer });
      alert('Ошибка: проект не выбран. Пожалуйста, выберите проект на бирже.');
      return;
    }

    // Для прямых предложений проверяем название проекта
    if (isDirectOffer && (!offerForm.orderName || !offerForm.orderName.trim())) {
      alert('Пожалуйста, укажите название проекта');
      return;
    }

    try {
      // Вычисляем дату окончания: добавляем количество дней к текущей дате
      let deadlineDate = null;
      if (offerForm.deadline && offerForm.deadline.trim() !== '') {
        const days = parseInt(offerForm.deadline, 10);
        if (days > 0) {
          const deadline = new Date();
          deadline.setDate(deadline.getDate() + days);
          deadlineDate = deadline.toISOString();
        }
      }

      if (isDirectOffer) {
        // Прямое предложение в чате
        // Если заказчик предлагает заказ исполнителю - создаем заказ
        // Если исполнитель предлагает услуги заказчику - нужно создать заказ от заказчика или предложение без заказа

        if (isCustomer) {
          // Заказчик предлагает заказ исполнителю - создаем заказ
          const orderData = {
            title: offerForm.orderName || 'Предложение от ' + currentUser?.name,
            description: offerForm.description,
            category_id: null,
            budget_to: parseFloat(offerForm.totalPrice),
            deadline: deadlineDate
          };

          // Создаем заказ
          const orderResponse = await apiClient.post('/orders', orderData);
          const createdOrder = orderResponse.data;

          // Создаем предложение на этот заказ (от имени исполнителя, но это будет системное предложение)
          // На самом деле, заказчик не может создать оффер - это делает исполнитель
          // Поэтому нужно создать сообщение с предложением, а не оффер напрямую
          // Или создать заказ и отправить сообщение исполнителю с предложением создать оффер

          // Отправляем сообщение исполнителю с предложением
          await apiClient.post('/messages', {
            to_user_id: directOfferRecipient.userId,
            message_type: 'text',
            title: 'Предложение заказа',
            content: `Заказчик ${currentUser?.name} предлагает вам заказ:\n\n${offerForm.orderName || 'Новый заказ'}\n\n${offerForm.description}\n\n💰 Сумма: ${parseFloat(offerForm.totalPrice).toLocaleString('ru-RU')} ₽\n${deadlineDate ? '⏱️ Срок: ' + Math.ceil((new Date(deadlineDate) - new Date()) / (1000 * 60 * 60 * 24)) + ' дней' : ''}\n\nВы можете откликнуться на этот заказ на бирже.`
          });
        } else if (isExecutor) {
          // Исполнитель предлагает услуги заказчику - создаем заказ от имени заказчика
          // Но это невозможно через API, поэтому отправляем сообщение с предложением
          const stagesText = offerForm.paymentType === 'stages' && offerForm.stages.length > 0
            ? '\n\nЭтапы:\n' + offerForm.stages.filter(s => s.name && s.price).map(s => `  • ${s.name}: ${parseFloat(s.price).toLocaleString('ru-RU')} ₽`).join('\n')
            : '';

          await apiClient.post('/messages', {
            to_user_id: directOfferRecipient.userId,
            message_type: 'text',
            title: 'Предложение услуг',
            content: `Исполнитель ${currentUser?.name} предлагает свои услуги:\n\n${offerForm.description}\n\n💰 Сумма: ${parseFloat(offerForm.totalPrice).toLocaleString('ru-RU')} ₽\n📊 Оплата: ${offerForm.paymentType === 'stages' ? 'По этапам' : 'Сразу после завершения'}${stagesText}${deadlineDate ? '\n⏱️ Срок: ' + Math.ceil((new Date(deadlineDate) - new Date()) / (1000 * 60 * 60 * 24)) + ' дней' : ''}`
          });
        }

        alert('✅ Предложение отправлено!');
        setShowOfferModal(false);
        setViewingProject(null);
        setDirectOfferRecipient(null);
        setOfferForm({
          description: '',
          totalPrice: '',
          paymentType: 'full',
          orderName: '',
          deadline: '',
          stages: [{ name: '', price: '' }]
        });

        // Обновляем сообщения
        const response = await apiClient.get('/messages');
        setMessages(response.data || []);
        if (selectedConversation) {
          const convResponse = await apiClient.get(`/messages/conversation/${selectedConversation.userId}`);
          setConversationMessages(convResponse.data || []);
        }
      } else {
        // Обычный отклик на проект
        const offerData = {
          order_id: viewingProject.id,
          description: offerForm.description,
          total_price: parseFloat(offerForm.totalPrice),
          payment_type: offerForm.paymentType.toLowerCase(),
          deadline: deadlineDate,
          stages: []
        };

        // Добавляем этапы только если payment_type = 'stages'
        if (offerForm.paymentType === 'stages') {
          offerData.stages = offerForm.stages.filter(s => s.name && s.price).map((s, idx) => ({
            name: s.name,
            price: parseFloat(s.price),
            order_num: idx
          }));
        }

        // Создаем предложение через API
        await apiClient.post('/offers', offerData);

        alert('✅ Предложение отправлено!');
        setShowOfferModal(false);
        setViewingProject(null);
        setDirectOfferRecipient(null);
        setOfferForm({
          description: '',
          totalPrice: '',
          paymentType: 'full',
          orderName: '',
          deadline: '',
          stages: [{ name: '', price: '' }]
        });
      }
    } catch (error) {
      console.error('Error creating offer:', error);
      alert(error.response?.data?.detail || 'Ошибка при отправке предложения');
    }
  };

  const calculateCustomerCommission = (price) => {
    const numPrice = parseFloat(price) || 0;

    // Комиссия на ввод
    const depositCommission = numPrice <= 20000 ? numPrice * 0.01 : 0;

    // Наценка сервиса
    let serviceMarkup = 0;
    if (numPrice < 5000) {
      serviceMarkup = numPrice * 0.10; // 10%
    } else if (numPrice >= 5000 && numPrice < 15000) {
      serviceMarkup = numPrice * 0.05; // 5%
    } else {
      serviceMarkup = numPrice * 0.03; // 3%
    }

    // Стоимость публикации
    let publicationCost = 0;
    if (numPrice < 1000) {
      publicationCost = numPrice * 0.15; // 15%
    } else if (numPrice >= 1000 && numPrice < 5000) {
      publicationCost = 200;
    } else if (numPrice >= 5000 && numPrice < 15000) {
      publicationCost = 300;
    } else {
      publicationCost = 500;
    }

    const totalCommission = depositCommission + serviceMarkup + publicationCost;
    const totalToPay = numPrice + totalCommission;

    return {
      price: numPrice,
      depositCommission,
      serviceMarkup,
      publicationCost,
      totalCommission,
      totalToPay
    };
  };

  // orderNotes теперь управляется через API, не нужно сохранять в localStorage

  // Загружаем заказы пользователя из API
  useEffect(() => {
    if (tab === 'myOrders' && fetchMyOrders) {
      console.log('🔄 Загрузка заказов для вкладки myOrders, роль:', currentUser?.role || userRole);
      fetchMyOrders();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, currentUser, userRole]);

  // Преобразуем заказы из API в формат для отображения
  const myOrdersData = useMemo(() => {
    if (!Array.isArray(myOrders)) return [];
    const isExecutor = currentUser?.role === 'executor' || currentUser?.role === 'EXECUTOR' || userRole === 'executor' || userRole === 'EXECUTOR';

    return myOrders.map(order => {
      const statusValue = order.status?.value || order.status || 'OPEN';
      const deadline = order.deadline ? new Date(order.deadline) : null;
      const daysRemaining = deadline ? Math.ceil((deadline - new Date()) / (1000 * 60 * 60 * 24)) : null;

      return {
        id: order.id,
        title: order.title,
        buyer: isExecutor
          ? (order.customer?.name || order.customer_name || 'Заказчик')  // Для исполнителя показываем заказчика
          : (order.customer?.name || order.customer_name || currentUser?.name || 'Заказчик'),  // Для заказчика показываем себя
        price: order.budget_to ? `${order.budget_to} ₽` : (order.budget_from ? `от ${order.budget_from} ₽` : 'Не указано'),
        ordered: order.created_at ? new Date(order.created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }) : '',
        remaining: daysRemaining !== null ? `${daysRemaining} дней` : '',
        status: statusValue.toLowerCase().replace('_', '-'),
        note: getNote(order.id) || ''
      };
    });
  }, [myOrders, getNote, currentUser, userRole]);

  const displayNote = (txt) => {
    if (!txt || txt === '—') return '—';
    const trimmed = txt.trim();
    if (trimmed.length > 60) return `${trimmed.slice(0, 60)}…`;
    return trimmed;
  };

  const openNoteModal = async (id) => {
    setNoteTarget(id);
    try {
      // Загружаем заметку из API
      await fetchNote(id);
      setNoteDraft(getNote(id) || '');
      setNoteModalOpen(true);
    } catch (error) {
      console.error('Error loading note:', error);
      setNoteDraft('');
      setNoteModalOpen(true);
    }
  };

  const handleSaveNote = async () => {
    if (!noteTarget) return;
    const trimmed = noteDraft.trim();
    try {
      await saveNote(noteTarget, trimmed);
      setNoteModalOpen(false);
      setNoteDraft('');
      setNoteTarget(null);
    } catch (error) {
      console.error('Error saving note:', error);
      alert('Ошибка при сохранении заметки');
    }
  };

  const handleDeleteNote = async () => {
    if (!noteTarget) return;
    try {
      await saveNote(noteTarget, ''); // Пустая строка удаляет заметку
      setNoteModalOpen(false);
      setNoteDraft('');
      setNoteTarget(null);
    } catch (error) {
      console.error('Error deleting note:', error);
      alert('Ошибка при удалении заметки');
    }
  };

  const myOrdersFiltered = useMemo(() => {
    let byStatus = myOrdersData;
    if (myOrdersFilter !== 'all') {
      // Маппинг фильтров на статусы
      const statusMap = {
        'in-progress': ['in-progress', 'in_progress'],
        'review': ['review', 'на-проверке'],
        'done': ['completed', 'done'],
        'cancelled': ['cancelled', 'canceled']
      };
      const targetStatuses = statusMap[myOrdersFilter] || [myOrdersFilter];
      byStatus = myOrdersData.filter((o) => {
        const orderStatus = o.status?.toLowerCase() || '';
        return targetStatuses.some(s => orderStatus.includes(s.toLowerCase()));
      });
    }
    const q = orderSearch.trim().toLowerCase();
    if (!q) return byStatus;
    return byStatus.filter((o) =>
      (o.title?.toLowerCase().includes(q) || o.buyer?.toLowerCase().includes(q))
    );
  }, [myOrdersFilter, myOrdersData, orderSearch]);
  const filteredItems = useMemo(() => {
    if (tab !== 'portfolio') return [];
    if (!Array.isArray(portfolioItems)) return [];
    if (selectedCategory === 'Все рубрики') return portfolioItems;
    return portfolioItems.filter((p) => p.category === selectedCategory);
  }, [tab, portfolioItems, selectedCategory]);

  // Посты загружаются через API через хук useCommunity


  if (tab === 'home') {
    return (
      <div className="grid two">
        <div className="card">
          <div className="card-header">
            <div className="card-title">Добро пожаловать!</div>
          </div>
          <div className="card-body">
            <div className="profile">
              <div className="avatar">
                {currentUser?.avatar_url ? (
                  <img src={currentUser.avatar_url} alt="" style={{ width: '100%', height: '100%', borderRadius: 'inherit', objectFit: 'cover' }} />
                ) : (
                  getInitials(currentUser?.name)
                )}
              </div>
              <div className="profile-meta">
                <div className="profile-name">{currentUser?.name || 'Пользователь'}</div>
                <div className="profile-rating">
                  <span className="pill pill-green">{t('profile.rating')} {(currentUser?.rating || 5.0).toFixed(1)}</span>
                  {currentUser?.verification_status === 'verified' && (
                    <span className="pill pill-outline">Проверенный СЗ</span>
                  )}
                </div>
              </div>
            </div>
            <div style={{ marginTop: '16px', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              <button className="btn primary" onClick={() => navigate('/orders')}>
                {t('nav.orders')}
              </button>
              <button className="btn ghost" onClick={() => navigate('/portfolio')}>
                {t('nav.portfolio')}
              </button>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="card-header">
            <div className="card-title">Статистика</div>
          </div>
          <div className="card-body">
            <div className="wallet">
              <div className="wallet-balance">
                <div className="wallet-amount">{currentUser?.balance || 0} ₽</div>
                <div className="wallet-sub">{t('wallet.available')}</div>
              </div>
              <div className="wallet-balance ghost">
                <div className="wallet-amount">{myOrders?.length || 0}</div>
                <div className="wallet-sub">Активных заказов</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (tab === 'orders') {
    const toggleSubcategory = (categoryId, subcategoryId) => {
      setSelectedOrdersSubcategories(prev => {
        const categorySubs = prev[categoryId] || [];
        const isAdding = !categorySubs.includes(subcategoryId);
        const newSubs = isAdding
          ? [...categorySubs, subcategoryId]
          : categorySubs.filter(id => id !== subcategoryId);

        // Если добавляем подкатегорию, выбираем все её под-подкатегории
        if (isAdding) {
          // Находим подкатегорию и выбираем все её под-подкатегории
          const category = ORDERS_CATEGORIES.find(cat => cat.id === categoryId);
          const subcategory = category?.subcategories?.find(sub => sub.id === subcategoryId);
          if (subcategory?.subcategories && subcategory.subcategories.length > 0) {
            const allSubSubcategoryIds = subcategory.subcategories.map(subsub => subsub.id);
            setSelectedOrdersSubSubcategories(subSubs => ({
              ...subSubs,
              [subcategoryId]: allSubSubcategoryIds
            }));
          }
        } else {
          // Если удаляем подкатегорию, удаляем все её под-подкатегории
          setSelectedOrdersSubSubcategories(subSubs => {
            const newSubSubs = { ...subSubs };
            if (newSubSubs[subcategoryId]) {
              delete newSubSubs[subcategoryId];
            }
            return newSubSubs;
          });
        }

        return { ...prev, [categoryId]: newSubs };
      });
    };

    const toggleSubSubcategory = (categoryId, subcategoryId, subsubcategoryId) => {
      setSelectedOrdersSubSubcategories(prev => {
        const subSubs = prev[subcategoryId] || [];
        const isAdding = !subSubs.includes(subsubcategoryId);
        const newSubs = isAdding
          ? [...subSubs, subsubcategoryId]
          : subSubs.filter(id => id !== subsubcategoryId);

        // Если добавляем под-подкатегорию, автоматически выбираем подкатегорию
        if (isAdding) {
          setSelectedOrdersSubcategories(subs => {
            const categorySubs = subs[categoryId] || [];
            if (!categorySubs.includes(subcategoryId)) {
              return { ...subs, [categoryId]: [...categorySubs, subcategoryId] };
            }
            return subs;
          });
        }

        return { ...prev, [subcategoryId]: newSubs };
      });
    };

    const budgetRanges = [
      { id: 'up-to-1000', label: 'До 1 000 ₽' },
      { id: '1to3', label: '1 000 – 3 000 ₽' },
      { id: '3to10', label: '3 000 – 10 000 ₽' },
      { id: '10to30', label: '10 000 – 30 000 ₽' },
      { id: '30plus', label: 'Более 30 000 ₽' }
    ];

    const offerRanges = [
      { id: 'up-to-5', label: 'До 5' },
      { id: '5to10', label: '5 – 10' },
      { id: '10to15', label: '10 – 15' },
      { id: '15to20', label: '15 – 20' },
      { id: '20plus', label: 'Более 20' }
    ];

    const budgetRangeMap = {
      'up-to-1000': { from: null, to: 1000 },
      '1to3': { from: 1000, to: 3000 },
      '3to10': { from: 3000, to: 10000 },
      '10to30': { from: 10000, to: 30000 },
      '30plus': { from: 30000, to: null }
    };

    const toggleBudgetRange = (rangeId) => {
      setSelectedBudgetRanges(prev => {
        const isSelected = prev.includes(rangeId);
        const newSelected = isSelected
          ? prev.filter(id => id !== rangeId)
          : [...prev, rangeId];

        // Если выбран хотя бы один диапазон — устанавливаем budget_from/budget_to
        if (newSelected.length > 0) {
          const mins = newSelected.map(id => budgetRangeMap[id]?.from).filter(v => v !== null);
          const maxs = newSelected.map(id => budgetRangeMap[id]?.to).filter(v => v !== null);
          if (mins.length > 0 && !isSelected) setBudgetFrom(String(Math.min(...mins)));
          else if (mins.length === 0) setBudgetFrom('');
          if (maxs.length > 0 && !isSelected) setBudgetTo(String(Math.max(...maxs)));
          else if (maxs.length === 0) setBudgetTo('');
        } else {
          setBudgetFrom('');
          setBudgetTo('');
        }

        return newSelected;
      });
    };

    const toggleOfferRange = (rangeId) => {
      setSelectedOfferRanges(prev =>
        prev.includes(rangeId)
          ? prev.filter(id => id !== rangeId)
          : [...prev, rangeId]
      );
    };

    if (viewingProject) {
      return (
        <>
          <div className="project-detail-page">
            <div className="card">
              <div className="card-header">
                <button
                  className="btn ghost"
                  onClick={() => setViewingProject(null)}
                >
                  Назад к списку
                </button>
              </div>
              <div className="card-body">
                <div className="project-detail-content">
                  <div className="project-detail-header">
                    <h1 className="project-detail-title">{viewingProject.title}</h1>
                    <div className="project-detail-price">
                      <span className="price-label">Бюджет</span>
                      <span className="price-value">
                        {parseFloat(viewingProject.budget_to || viewingProject.budget_from || viewingProject.maxPrice || 0).toLocaleString('ru-RU')} ₽
                      </span>
                    </div>
                  </div>

                  <div className="project-detail-meta">
                    <div className="meta-card">
                      <div className="meta-label">Срок выполнения</div>
                      <div className="meta-value">
                        {viewingProject.deadline ? (
                          <>
                            <span style={{ marginRight: 8 }}>📅 {formatDate(viewingProject.deadline)}</span>
                            (осталось {Math.max(0, Math.ceil((new Date(viewingProject.deadline) - new Date()) / (1000 * 60 * 60 * 24)))} дней)
                          </>
                        ) : 'Не указан'}
                      </div>
                    </div>
                    <div className="meta-card">
                      <div className="meta-label">Заказчик</div>
                      <div className="meta-value">
                        {viewingProject.customer_name || viewingProject.customer?.name || viewingProject.buyer || 'Не указан'}
                      </div>
                    </div>
                    {(() => {
                      // Резолвим названия категорий из ID
                      const catId = viewingProject.category_id;
                      const subId = viewingProject.subcategory_id;
                      const subSubId = viewingProject.subsubcategory_id;
                      // Если категория задана как объект (старый формат из myOrders)
                      if (viewingProject.category && viewingProject.category.category) {
                        return (
                          <div className="meta-card">
                            <div className="meta-label">Рубрика</div>
                            <div className="meta-value">
                              {viewingProject.category.category}
                              {viewingProject.category.subcategory && <span style={{ opacity: 0.7 }}> → {viewingProject.category.subcategory}</span>}
                            </div>
                          </div>
                        );
                      }
                      // Резолвим из ID (формат API)
                      if (!catId && !subId && !subSubId) return null;
                      const catObj = ORDERS_CATEGORIES.find(c => c.id === catId);
                      const subObj = catObj?.subcategories?.find(s => s.id === subId);
                      const subSubObj = subObj?.subcategories?.find(ss => ss.id === subSubId);
                      // Fallback: если не нашли в словаре — показываем сырые ID
                      const parts = [
                        catObj?.name || catId,
                        subObj?.name || (subId && subId !== catId ? subId : null),
                        subSubObj?.name || (subSubId && subSubId !== subId ? subSubId : null)
                      ].filter(Boolean);
                      if (!parts.length) return null;
                      return (
                        <div className="meta-card">
                          <div className="meta-label">Рубрика</div>
                          <div className="meta-value">
                            {parts.map((p, i) => (
                              <span key={i}>
                                {i > 0 && <span style={{ opacity: 0.5 }}> → </span>}
                                {p}
                              </span>
                            ))}
                          </div>
                        </div>
                      );
                    })()}

                  </div>

                  <div className="project-detail-section">
                    <h3 className="section-title">Описание задачи</h3>
                    <div className="section-content">{viewingProject.description}</div>
                  </div>

                  {viewingProject.skills && viewingProject.skills.length > 0 && (
                    <div className="project-detail-section">
                      <h3 className="section-title">Требуемые навыки</h3>
                      <div className="skills-list">
                        {viewingProject.skills.map((skill, idx) => (
                          <span key={idx} className="tag skill-tag">{skill.skill_name || skill}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {viewingProject.files && viewingProject.files.length > 0 && (
                    <div className="project-detail-section">
                      <h3 className="section-title">Прикрепленные файлы ({viewingProject.files.length})</h3>
                      <div className="files-grid">
                        {viewingProject.files.map((file, idx) => (
                          <div key={idx} className="file-card">
                            {file.type.startsWith('image/') ? (
                              <div className="file-preview-image">
                                <img src={file.url} alt={file.name} />
                              </div>
                            ) : (
                              <div className="file-preview-doc">
                                <div className="file-icon">📄</div>
                                <div className="file-name">{file.name}</div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="project-detail-actions">
                    <button
                      className="btn primary large"
                      onClick={() => setShowOfferModal(true)}
                    >
                      Предложить услугу
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {showOfferModal && (
            <div className="modal-backdrop" onClick={() => {
              setShowOfferModal(false);
              setDirectOfferRecipient(null);
            }}>
              <div className="modal offer-modal" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                  <div className="modal-title">{directOfferRecipient ? 'Предложить заказ' : 'Предложить услугу'}</div>
                  <button className="modal-close" onClick={() => {
                    setShowOfferModal(false);
                    setDirectOfferRecipient(null);
                  }}>✕</button>
                </div>
                <div className="modal-body">
                  <div className="form">
                    <div className="form-group">
                      <label>Описание предложения</label>
                      <textarea
                        rows={5}
                        value={offerForm.description}
                        onChange={(e) => setOfferForm({ ...offerForm, description: e.target.value })}
                        placeholder="Опишите, как вы выполните этот заказ..."
                      />
                    </div>

                    <div className="form-group">
                      <label>Стоимость</label>
                      <div className="input-with-currency">
                        <input
                          type="number"
                          min="0"
                          step="1"
                          value={offerForm.totalPrice}
                          onChange={(e) => setOfferForm({ ...offerForm, totalPrice: e.target.value })}
                          placeholder="Введите стоимость"
                        />
                        <span className="currency-label">₽</span>
                      </div>
                    </div>

                    <div className="form-group">
                      <label>Срок выполнения (дней)</label>
                      <input
                        type="number"
                        min="1"
                        step="1"
                        value={offerForm.deadline}
                        onChange={(e) => setOfferForm({ ...offerForm, deadline: e.target.value })}
                        placeholder="Количество дней"
                      />
                    </div>

                    <div className="form-group">
                      <label>Желаемый порядок оплаты</label>
                      <div className="payment-type-tabs">
                        <button
                          type="button"
                          className={`payment-tab ${offerForm.paymentType === 'full' ? 'active' : ''}`}
                          onClick={() => setOfferForm({ ...offerForm, paymentType: 'full' })}
                        >
                          Вся сумма сразу
                        </button>
                        <button
                          type="button"
                          className={`payment-tab ${offerForm.paymentType === 'stages' ? 'active' : ''}`}
                          onClick={() => setOfferForm({ ...offerForm, paymentType: 'stages' })}
                        >
                          По этапам
                        </button>
                      </div>
                    </div>

                    {offerForm.paymentType === 'full' ? (
                      <div>
                        <p>Оплата сразу после завершения работы</p>
                        {/* Поле "Название проекта" показываем только для прямых предложений, не для отклика на существующий проект */}
                        {directOfferRecipient && (
                          <div className="form-group" style={{ marginTop: '12px' }}>
                            <label>Название проекта:</label>
                            <input
                              type="text"
                              value={offerForm.orderName}
                              onChange={(e) => setOfferForm({ ...offerForm, orderName: e.target.value })}
                              placeholder="Введите название проекта"
                            />
                          </div>
                        )}
                      </div>
                    ) : (
                      <div>
                        {/* Поле "Название проекта" показываем только для прямых предложений, не для отклика на существующий проект */}
                        {directOfferRecipient && (
                          <div className="form-group" style={{ marginBottom: '12px' }}>
                            <label>Название проекта:</label>
                            <input
                              type="text"
                              value={offerForm.orderName}
                              onChange={(e) => setOfferForm({ ...offerForm, orderName: e.target.value })}
                              placeholder="Введите название проекта"
                            />
                          </div>
                        )}
                        <div className="form-group">
                          <label>Этапы работы</label>
                          {offerForm.stages.map((stage, index) => (
                            <div key={index} className="stage-item">
                              <div className="stage-fields">
                                <input
                                  type="text"
                                  placeholder="Название этапа"
                                  value={stage.name}
                                  onChange={(e) => updateStage(index, 'name', e.target.value)}
                                />
                                <div className="input-with-currency">
                                  <input
                                    type="number"
                                    min="0"
                                    step="1"
                                    placeholder="Стоимость"
                                    value={stage.price}
                                    onChange={(e) => updateStage(index, 'price', e.target.value)}
                                  />
                                  <span className="currency-label">₽</span>
                                </div>
                                {offerForm.stages.length > 1 && (
                                  <button
                                    type="button"
                                    className="btn danger small"
                                    onClick={() => removeStage(index)}
                                  >
                                    ✕
                                  </button>
                                )}
                              </div>
                            </div>
                          ))}
                          {!isStagesPriceValid() && (
                            <div className="notice error">
                              Сумма этапов не может превышать общую стоимость
                            </div>
                          )}
                          <button
                            type="button"
                            className="btn ghost small"
                            onClick={addStage}
                          >
                            + Добавить этап
                          </button>
                        </div>
                      </div>
                    )}

                    {offerForm.totalPrice && (
                      <div className="commission-details">
                        <div className="commission-item">
                          <span>Комиссия при закрытии сделки (7%):</span>
                          <span className="commission-value">−{(parseFloat(offerForm.totalPrice) * COMMISSION_RATE).toLocaleString('ru-RU')} ₽</span>
                        </div>
                        <div className="commission-item">
                          <span>Комиссия при выводе (3%):</span>
                          <span className="commission-value">−{(parseFloat(offerForm.totalPrice) * WITHDRAWAL_RATE).toLocaleString('ru-RU')} ₽</span>
                        </div>
                        {parseFloat(offerForm.totalPrice) > PAID_RESPONSE_THRESHOLD && (
                          <div className="commission-item">
                            <span>Платный отклик (1%):</span>
                            <span className="commission-value">−{(parseFloat(offerForm.totalPrice) * PAID_RESPONSE_RATE).toLocaleString('ru-RU')} ₽</span>
                          </div>
                        )}
                        <div className="commission-total">
                          <span>К получению:</span>
                          <span className="commission-value positive">
                            {(() => {
                              const price = parseFloat(offerForm.totalPrice) || 0;
                              const commission = price * COMMISSION_RATE;
                              const withdrawal = price * WITHDRAWAL_RATE;
                              const paidResponse = price > PAID_RESPONSE_THRESHOLD ? price * PAID_RESPONSE_RATE : 0;
                              const total = price - commission - withdrawal - paidResponse;
                              return total.toLocaleString('ru-RU');
                            })()} ₽
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
                <div className="modal-footer">
                  <button className="btn ghost small" onClick={() => {
                    setShowOfferModal(false);
                    setDirectOfferRecipient(null);
                  }}>
                    Отмена
                  </button>
                  <button className="btn primary small" onClick={handleOfferSubmit}>
                    Отправить предложение
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      );
    }

    return (
      <>
        <div className="orders-layout">
          <div className="orders-sidebar">
            <div className="filter-section">
              <label>{t('orders.filters.selectCategory')}</label>
              <button
                className="btn ghost"
                onClick={() => setShowCategoryModal(true)}
                style={{ width: '100%', justifyContent: 'space-between', display: 'flex', alignItems: 'center' }}
              >
                <span>
                  {(() => {
                    const totalSelected = Object.values(selectedOrdersSubcategories).reduce((sum, arr) => sum + arr.length, 0);
                    return totalSelected > 0
                      ? `${totalSelected} ${t('orders.filters.selected') || 'выбрано'}`
                      : t('orders.filters.allCategories');
                  })()}
                </span>
                <span>▼</span>
              </button>
            </div>
            <div className="filter-section">
              <label>{t('orders.filters.budget')}</label>
              {budgetRanges.map((range) => (
                <label key={range.id} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={selectedBudgetRanges.includes(range.id)}
                    onChange={() => toggleBudgetRange(range.id)}
                  />
                  <span>{range.label}</span>
                </label>
              ))}
              <div className="filter-inputs-row">
                <input
                  type="number"
                  placeholder={t('orders.filters.budgetFrom')}
                  value={budgetFrom}
                  onChange={(e) => setBudgetFrom(e.target.value)}
                  className="filter-input"
                />
                <input
                  type="number"
                  placeholder={t('orders.filters.budgetTo')}
                  value={budgetTo}
                  onChange={(e) => setBudgetTo(e.target.value)}
                  className="filter-input"
                />
              </div>
            </div>
            <div className="filter-section">
              <label>
                {t('orders.filters.hiredPercent')}
                <span className="info-icon">ⓘ</span>
              </label>
              <input
                type="number"
                placeholder={t('orders.filters.hiredFrom')}
                value={hiredPercent}
                onChange={(e) => setHiredPercent(e.target.value)}
                className="filter-input"
              />
            </div>
            <div className="filter-section">
              <label>
                {t('orders.filters.keywords')}
                <span className="info-icon">ⓘ</span>
              </label>
              <input
                type="text"
                placeholder={t('orders.filters.keywords')}
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
                className="filter-input"
              />
            </div>
            <div className="filter-section">
              <label>{t('orders.filters.offersCount')}</label>
              {offerRanges.map((range) => (
                <label key={range.id} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={selectedOfferRanges.includes(range.id)}
                    onChange={() => toggleOfferRange(range.id)}
                  />
                  <span>{range.label}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="orders-content">
            <div className="card">
              <div className="card-header">
                <div className="card-title">{t('nav.orders')}</div>
                <div className="card-extra">
                  <input
                    type="text"
                    placeholder={t('orders.searchPlaceholder')}
                    value={orderSearch}
                    onChange={(e) => setOrderSearch(e.target.value)}
                    style={{ padding: '8px 12px', marginRight: '10px' }}
                  />
                </div>
              </div>
              <div className="card-body">
                {publicOrdersLoading ? (
                  <div style={{ textAlign: 'center', padding: '40px' }}>Загрузка...</div>
                ) : publicOrders.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '60px 20px' }}>
                    <div style={{ fontSize: '48px', marginBottom: '20px' }}>📋</div>
                    <h3 style={{ marginBottom: '12px', color: 'var(--text)' }}>Нет доступных заказов</h3>
                    <p style={{ color: 'var(--muted)' }}>На бирже пока нет открытых заказов</p>
                  </div>
                ) : (
                  <div className="exchange-list">
                    {publicOrders.map((project) => (
                      <div
                        key={`customer-${project.id}`}
                        className="exchange-item"
                        onClick={() => setViewingProject(project)}
                        style={{ cursor: 'pointer' }}
                      >
                        <div className="exchange-item-top">
                          <div className="exchange-item-main">
                            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '4px' }}>
                              <span
                                className="status-badge"
                                style={{
                                  display: 'inline-block',
                                  padding: '2px 8px',
                                  borderRadius: '12px',
                                  fontSize: '11px',
                                  fontWeight: '600',
                                  color: '#fff',
                                  backgroundColor: getOrderStatusColor(project.status),
                                  marginRight: '8px',
                                  flexShrink: 0
                                }}
                              >
                                {getOrderStatusText(project.status)}
                              </span>
                              <h3 className="exchange-item-title" style={{ margin: 0 }}>{project.title}</h3>
                            </div>
                            <div className="exchange-item-desc">{project.description}</div>
                            {project.skills && project.skills.length > 0 && (
                              <div className="exchange-item-tags">
                                {project.skills.map((skill, idx) => (
                                  <span key={idx} className="tag">{skill.skill_name || skill}</span>
                                ))}
                              </div>
                            )}
                            {(() => {
                              // Отобразить рубрику в карточке
                              const catObj = ORDERS_CATEGORIES.find(c => c.id === project.category_id);
                              const subObj = catObj?.subcategories?.find(s => s.id === project.subcategory_id);
                              const subSubObj = subObj?.subcategories?.find(ss => ss.id === project.subsubcategory_id);
                              // Приоритет: самый конкретный уровень → более общий → fallback на сырой ID
                              const label =
                                subSubObj?.name ||
                                subObj?.name ||
                                catObj?.name ||
                                project.subsubcategory_id ||
                                project.subcategory_id ||
                                project.category_id;
                              if (!label) return null;
                              return (
                                <div style={{ marginTop: '6px' }}>
                                  <span style={{
                                    fontSize: '11px',
                                    padding: '2px 8px',
                                    borderRadius: '10px',
                                    background: 'rgba(255,255,255,0.08)',
                                    color: 'var(--muted)',
                                    fontWeight: 500
                                  }}>
                                    📂 {label}
                                  </span>
                                </div>
                              );
                            })()}

                          </div>
                          <div className="exchange-item-price">
                            <div className="price-label">Бюджет:</div>
                            <div className="price-value">
                              {project.budget_to
                                ? `${parseFloat(project.budget_to).toLocaleString('ru-RU')} ₽`
                                : project.budget_from
                                  ? `от ${parseFloat(project.budget_from).toLocaleString('ru-RU')} ₽`
                                  : 'Не указан'}
                            </div>
                          </div>
                        </div>
                        <div className="exchange-item-bottom">
                          <div className="exchange-item-buyer">
                            <div className="buyer-avatar" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--brand-green)', color: '#111', fontWeight: 'bold' }}>
                              {project.customer_avatar_url ? (
                                <img src={project.customer_avatar_url} alt="" style={{ width: '100%', height: '100%', borderRadius: 'inherit', objectFit: 'cover' }} />
                              ) : (
                                getInitials(project.customer?.name || project.customer_name || 'З')
                              )}
                            </div>
                            <div className="buyer-info">
                              <span className="buyer-name">{project.customer?.name || project.customer_name || 'Заказчик'}</span>
                              <span className="buyer-stats">
                                Размещено проектов: {project.customer_projects_count || 0} · Нанято: {project.customer_hired_percent || 0}%
                              </span>
                            </div>
                          </div>
                          <div className="exchange-item-actions">
                            <div className="exchange-item-meta">
                              {project.deadline && (
                                <span className="meta-item">
                                  📅 Дедлайн: {formatDate(project.deadline)}
                                </span>
                              )}
                              <span className="meta-item">💬 Предложений: {project.offers_count || 0}</span>
                            </div>
                            <button
                              className="btn primary small offer-btn"
                              onClick={(e) => {
                                e.stopPropagation();
                                setViewingProject(project);
                                setShowOfferModal(true);
                              }}
                            >
                              Предложить услугу
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
        {showOfferModal && (
          <div className="modal-backdrop" onClick={() => {
            setShowOfferModal(false);
            setDirectOfferRecipient(null);
          }}>
            <div className="modal offer-modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <div className="modal-title">{directOfferRecipient ? 'Предложить заказ' : 'Предложить услугу'}</div>
                <button className="modal-close" onClick={() => {
                  setShowOfferModal(false);
                  setDirectOfferRecipient(null);
                }}>✕</button>
              </div>
              <div className="modal-body">
                <div className="form">
                  <div className="form-group">
                    <label>Описание предложения</label>
                    <textarea
                      rows={5}
                      value={offerForm.description}
                      onChange={(e) => setOfferForm({ ...offerForm, description: e.target.value })}
                      placeholder="Опишите, как вы выполните этот заказ..."
                    />
                  </div>

                  <div className="form-group">
                    <label>Стоимость</label>
                    <div className="input-with-currency">
                      <input
                        type="number"
                        min="0"
                        step="1"
                        value={offerForm.totalPrice}
                        onChange={(e) => setOfferForm({ ...offerForm, totalPrice: e.target.value })}
                        placeholder="Введите стоимость"
                      />
                      <span className="currency-label">₽</span>
                    </div>
                  </div>

                  {offerForm.totalPrice && (
                    <div className="commission-info">
                      <div className="commission-row">
                        <span>Стоимость заказа:</span>
                        <span className="commission-value">{calculateCommission(offerForm.totalPrice).price.toLocaleString('ru-RU')} ₽</span>
                      </div>
                      <div className="commission-row">
                        <span>Комиссия сделки (7%):</span>
                        <span className="commission-value negative">-{calculateCommission(offerForm.totalPrice).dealCommission.toLocaleString('ru-RU')} ₽</span>
                      </div>
                      {calculateCommission(offerForm.totalPrice).responseCommission > 0 && (
                        <div className="commission-row">
                          <span>Платный отклик (1%):</span>
                          <span className="commission-value negative">-{calculateCommission(offerForm.totalPrice).responseCommission.toLocaleString('ru-RU')} ₽</span>
                        </div>
                      )}
                      <div className="commission-row total">
                        <span>К получению:</span>
                        <span className="commission-value positive">{calculateCommission(offerForm.totalPrice).toReceive.toLocaleString('ru-RU')} ₽</span>
                      </div>
                      <div className="commission-note">
                        * Дополнительно 3% при выводе на карту
                      </div>
                    </div>
                  )}

                  <div className="form-group">
                    <label>Срок выполнения (дней)</label>
                    <input
                      type="number"
                      min="1"
                      step="1"
                      value={offerForm.deadline}
                      onChange={(e) => setOfferForm({ ...offerForm, deadline: e.target.value })}
                      placeholder="Количество дней"
                    />
                  </div>

                  <div className="form-group">
                    <label>Желаемый порядок оплаты</label>
                    <div className="payment-type-tabs">
                      <button
                        className={`payment-tab ${offerForm.paymentType === 'full' ? 'active' : ''}`}
                        onClick={() => setOfferForm({ ...offerForm, paymentType: 'full' })}
                      >
                        Вся сумма сразу
                      </button>
                      <button
                        className={`payment-tab ${offerForm.paymentType === 'stages' ? 'active' : ''}`}
                        onClick={() => setOfferForm({ ...offerForm, paymentType: 'stages' })}
                      >
                        По этапам
                      </button>
                    </div>
                  </div>

                  {offerForm.paymentType === 'full' ? (
                    <div>
                      <p>Оплата сразу после завершения работы</p>
                      {/* Поле "Название проекта" показываем только для прямых предложений, не для отклика на существующий проект */}
                      {directOfferRecipient && (
                        <div className="form-group" style={{ marginTop: '12px' }}>
                          <label>Название проекта:</label>
                          <input
                            type="text"
                            value={offerForm.orderName}
                            onChange={(e) => setOfferForm({ ...offerForm, orderName: e.target.value })}
                            placeholder="Введите название проекта"
                          />
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="stages-section">
                      {/* Поле "Название проекта" показываем только для прямых предложений, не для отклика на существующий проект */}
                      {directOfferRecipient && (
                        <div className="form-group" style={{ marginBottom: '12px' }}>
                          <label>Название проекта:</label>
                          <input
                            type="text"
                            value={offerForm.orderName}
                            onChange={(e) => setOfferForm({ ...offerForm, orderName: e.target.value })}
                            placeholder="Введите название проекта"
                          />
                        </div>
                      )}
                      <label>Этапы работы</label>
                      {offerForm.stages.map((stage, index) => (
                        <div key={index} className="stage-item">
                          <div className="stage-number">Этап {index + 1}</div>
                          <div className="stage-fields">
                            <input
                              type="text"
                              value={stage.name}
                              onChange={(e) => {
                                const newStages = [...offerForm.stages];
                                newStages[index].name = e.target.value;
                                setOfferForm({ ...offerForm, stages: newStages });
                              }}
                              placeholder="Название этапа"
                            />
                            <div className="input-with-currency stage-price-input">
                              <input
                                type="number"
                                min="0"
                                step="1"
                                value={stage.price}
                                onChange={(e) => {
                                  const newStages = [...offerForm.stages];
                                  newStages[index].price = e.target.value;
                                  setOfferForm({ ...offerForm, stages: newStages });
                                }}
                                placeholder="0"
                                className="stage-price"
                              />
                              <span className="currency-label">₽</span>
                            </div>
                            {offerForm.stages.length > 1 && (
                              <button
                                className="btn ghost xsmall"
                                onClick={() => {
                                  const newStages = offerForm.stages.filter((_, i) => i !== index);
                                  setOfferForm({ ...offerForm, stages: newStages });
                                }}
                              >
                                Удалить
                              </button>
                            )}
                          </div>
                        </div>
                      ))}

                      {!isStagesPriceValid() && (
                        <div className="validation-error">
                          Сумма этапов ({getTotalStagesPrice().toLocaleString('ru-RU')} ₽) превышает общую стоимость ({offerForm.totalPrice} ₽)
                        </div>
                      )}

                      {offerForm.totalPrice && isStagesPriceValid() && getTotalStagesPrice() < parseFloat(offerForm.totalPrice) && (
                        <div className="validation-info">
                          Распределено: {getTotalStagesPrice().toLocaleString('ru-RU')} ₽ из {parseFloat(offerForm.totalPrice).toLocaleString('ru-RU')} ₽
                        </div>
                      )}

                      <button
                        className="btn ghost small"
                        onClick={() => setOfferForm({
                          ...offerForm,
                          stages: [...offerForm.stages, { name: '', price: '' }]
                        })}
                      >
                        + Добавить этап
                      </button>
                    </div>
                  )}
                </div>
              </div>
              <div className="modal-footer">
                <button className="btn ghost small" onClick={() => {
                  setShowOfferModal(false);
                  setDirectOfferRecipient(null);
                }}>
                  Отмена
                </button>
                <button className="btn primary small">
                  Отправить предложение
                </button>
              </div>
            </div>
          </div>
        )}
        {showCategoryModal && (
          <div className="modal-backdrop" onClick={() => setShowCategoryModal(false)}>
            <div className="modal category-modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <div className="modal-title">{t('orders.filters.selectCategory')}</div>
                <button className="modal-close" onClick={() => setShowCategoryModal(false)}>✕</button>
              </div>
              <div className="modal-body category-modal-body">
                <div className="category-list">
                  {ORDERS_CATEGORIES.map((category) => (
                    <div key={category.id} className="category-item">
                      <div className="category-header">
                        <span className="category-title">{category.name}</span>
                        {category.subcategories && category.subcategories.length > 0 && (
                          <button
                            className="category-expand-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              setExpandedCategoryId(expandedCategoryId === category.id ? null : category.id);
                            }}
                          >
                            {expandedCategoryId === category.id ? '▲' : '▼'}
                          </button>
                        )}
                      </div>
                      {expandedCategoryId === category.id && category.subcategories && category.subcategories.length > 0 && (
                        <div className="subcategory-list">
                          {category.subcategories.map((subcategory) => (
                            <div key={subcategory.id} className="subcategory-item">
                              <div className="subcategory-main-wrapper">
                                <label className="checkbox-label" style={{ flex: 1, margin: 0, padding: 0 }}>
                                  <input
                                    type="checkbox"
                                    checked={(selectedOrdersSubcategories[category.id] || []).includes(subcategory.id)}
                                    onChange={(e) => {
                                      e.stopPropagation();
                                      toggleSubcategory(category.id, subcategory.id);
                                    }}
                                  />
                                  <span>{subcategory.name}</span>
                                </label>
                                {subcategory.subcategories && subcategory.subcategories.length > 0 && (
                                  <button
                                    className="category-expand-btn"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setExpandedSubcategoryId(expandedSubcategoryId === subcategory.id ? null : subcategory.id);
                                    }}
                                  >
                                    {expandedSubcategoryId === subcategory.id ? '▲' : '▼'}
                                  </button>
                                )}
                              </div>
                              {expandedSubcategoryId === subcategory.id && subcategory.subcategories && subcategory.subcategories.length > 0 && (
                                <div className="subsubcategory-list">
                                  {subcategory.subcategories.map((subsubcategory) => (
                                    <label key={subsubcategory.id} className="checkbox-label" style={{ margin: 0, padding: '8px 12px' }}>
                                      <input
                                        type="checkbox"
                                        checked={(selectedOrdersSubSubcategories[subcategory.id] || []).includes(subsubcategory.id)}
                                        onChange={(e) => {
                                          e.stopPropagation();
                                          toggleSubSubcategory(category.id, subcategory.id, subsubcategory.id);
                                        }}
                                      />
                                      <span>{subsubcategory.name}</span>
                                    </label>
                                  ))}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
              <div className="modal-footer">
                <button
                  className="btn ghost"
                  onClick={() => {
                    setExpandedCategoryId(null);
                    setExpandedSubcategoryId(null);
                    setSelectedOrdersSubcategories({});
                    setSelectedOrdersSubSubcategories({});
                    setShowCategoryModal(false);
                  }}
                >
                  {t('orders.filters.allCategories')}
                </button>
                <button
                  className="btn primary"
                  onClick={() => setShowCategoryModal(false)}
                >
                  {t('common.apply')}
                </button>
              </div>
            </div>
          </div>
        )}
      </>
    );
  }

  if (tab === 'myOrders') {
    const columns = (() => {
      switch (myOrdersFilter) {
        case 'in-progress':
          return [
            t('orders.columns.title'),
            t('orders.columns.buyer'),
            t('orders.columns.ordered'),
            t('orders.columns.remaining'),
            t('orders.columns.price'),
            t('orders.columns.note'),
            t('orders.columns.status'),
            'Действия'
          ];
        case 'review':
          return [
            t('orders.columns.title'),
            t('orders.columns.buyer'),
            t('orders.columns.ordered'),
            t('orders.columns.price'),
            t('orders.columns.note'),
            t('orders.columns.status'),
            'Действия'
          ];
        case 'done':
          return [
            t('orders.columns.title'),
            t('orders.columns.buyer'),
            t('orders.columns.paid'),
            t('orders.columns.price'),
            t('orders.columns.note'),
            t('orders.columns.status'),
            'Действия'
          ];
        case 'cancelled':
          return [
            t('orders.columns.title'),
            t('orders.columns.buyer'),
            t('orders.columns.cancelled'),
            t('orders.columns.price'),
            t('orders.columns.note'),
            t('orders.columns.status'),
            'Действия'
          ];
        default:
          return [
            t('orders.columns.title'),
            t('orders.columns.buyer'),
            t('orders.columns.ordered'),
            t('orders.columns.price'),
            t('orders.columns.note'),
            t('orders.columns.status'),
            'Действия'
          ];
      }
    })();
    const gridTemplate = (() => {
      switch (myOrdersFilter) {
        case 'in-progress':
          return [
            'minmax(200px, 2fr)',      // Название
            'minmax(150px, 1fr)',      // Покупатель
            'minmax(110px, 1fr)',      // Заказан
            'minmax(110px, 1fr)',      // Осталось
            'minmax(120px, 1fr)',      // Стоимость
            'minmax(220px, 1.6fr)',    // Заметка
            'minmax(120px, 1fr)',      // Статус
            'minmax(150px, 1fr)',      // Действия
          ].join(' ');
        case 'review':
          return [
            'minmax(200px, 2fr)',      // Название
            'minmax(150px, 1fr)',      // Покупатель
            'minmax(110px, 1fr)',      // Заказан
            'minmax(120px, 1fr)',      // Стоимость
            'minmax(220px, 1.6fr)',    // Заметка
            'minmax(120px, 1fr)',      // Статус
            'minmax(200px, 1.5fr)',    // Действия
          ].join(' ');
        case 'done':
        case 'cancelled':
        case 'all':
        default:
          return [
            'minmax(200px, 2fr)',      // Название
            'minmax(150px, 1fr)',      // Покупатель
            'minmax(110px, 1fr)',      // Дата (оплачено/заказан/отменен)
            'minmax(120px, 1fr)',      // Стоимость
            'minmax(220px, 1.6fr)',    // Заметка
            'minmax(120px, 1fr)',      // Статус
            'minmax(150px, 1fr)',      // Действия
          ].join(' ');
      }
    })();

    return (
      <>
        <div className="card">
          <div className="card-header">
            <div className="card-title">{t('orders.title')}</div>
            <div className="card-extra"><span className="pill pill-outline">{myOrdersFiltered.length}</span></div>
          </div>
          <div className="card-body">
            <div className="orders-top">
              <div className="status-tabs">
                <button
                  className={`status-tab ${myOrdersFilter === 'all' ? 'active' : ''}`}
                  onClick={() => setMyOrdersFilter('all')}
                >
                  {t('orders.filters.all')}
                </button>
                <button
                  className={`status-tab ${myOrdersFilter === 'in-progress' ? 'active' : ''}`}
                  onClick={() => setMyOrdersFilter('in-progress')}
                >
                  {t('orders.filters.inProgress')}
                </button>
                <button
                  className={`status-tab ${myOrdersFilter === 'review' ? 'active' : ''}`}
                  onClick={() => setMyOrdersFilter('review')}
                >
                  На проверке
                </button>
                <button
                  className={`status-tab ${myOrdersFilter === 'done' ? 'active' : ''}`}
                  onClick={() => setMyOrdersFilter('done')}
                >
                  {t('orders.filters.done')}
                </button>
                <button
                  className={`status-tab ${myOrdersFilter === 'cancelled' ? 'active' : ''}`}
                  onClick={() => setMyOrdersFilter('cancelled')}
                >
                  {t('orders.filters.cancelled')}
                </button>
              </div>
              <div className="orders-search">
                <input
                  placeholder={t('orders.searchPlaceholder')}
                  value={orderSearch}
                  onChange={(e) => setOrderSearch(e.target.value)}
                />
              </div>
            </div>

            <div className="table-scroll">
              <div className="orders-table">
                <div className="table-header" style={{ '--orders-grid': gridTemplate }}>
                  {columns.map((c) => (<div key={c}>{c}</div>))}
                </div>
                {myOrdersFiltered.map((order, idx) => {
                  const rowId = order.id || `order-${idx}`;
                  const noteText = getNote(rowId) || order.note || '—';
                  const hasNote = noteText && noteText !== '—' && noteText.trim() !== '';
                  return (
                    <div className="table-row" key={idx} style={{ '--orders-grid': gridTemplate }}>
                      <div data-label={t('orders.columns.title')}>
                        <div className="list-title">{order.title}</div>
                      </div>
                      <div data-label={t('orders.columns.buyer')} className="list-sub">{order.buyer || '—'}</div>
                      {myOrdersFilter === 'in-progress' && (
                        <>
                          <div data-label={t('orders.columns.ordered')}>{order.ordered || '—'}</div>
                          <div data-label={t('orders.columns.remaining')}>{order.remaining || '—'}</div>
                          <div data-label={t('orders.columns.price')} className="wallet-amount" style={{ fontSize: '16px' }}>{order.price}</div>
                          <div data-label={t('orders.columns.note')} className="list-sub">
                            {hasNote ? (
                              <div className="note-text" onClick={() => openNoteModal(rowId)}>{displayNote(noteText)}</div>
                            ) : (
                              <button className="btn ghost xsmall" onClick={() => openNoteModal(rowId)}>{t('orders.noteButton')}</button>
                            )}
                          </div>
                          <div data-label={t('orders.columns.status')}>
                            <span className="pill pill-blue">{t('orders.status.inProgress')}</span>
                          </div>
                          {/* Кнопки действий для заказов в работе */}
                          <div data-label="Действия" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                            {(() => {
                              const isExecutor = currentUser?.role === 'executor' || currentUser?.role === 'EXECUTOR' || userRole === 'executor' || userRole === 'EXECUTOR';

                              // Для исполнителя: кнопка "Сдать работу"
                              if (isExecutor) {
                                return (
                                  <button
                                    className="btn primary small"
                                    onClick={async () => {
                                      try {
                                        await apiClient.post(`/orders/${order.id}/submit-for-review`);
                                        alert('✅ Работа сдана на проверку заказчику!');
                                        if (fetchMyOrders) fetchMyOrders();
                                      } catch (error) {
                                        console.error('Error submitting work:', error);
                                        const errorMessage = error.response?.data?.detail || error.response?.data?.message || 'Ошибка при сдаче работы';
                                        alert(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
                                      }
                                    }}
                                  >
                                    Сдать работу
                                  </button>
                                );
                              }

                              return null;
                            })()}
                          </div>
                        </>
                      )}
                      {myOrdersFilter === 'review' && (
                        <>
                          <div data-label={t('orders.columns.ordered')}>{order.ordered || '—'}</div>
                          <div data-label={t('orders.columns.price')} className="wallet-amount" style={{ fontSize: '16px' }}>{order.price}</div>
                          <div data-label={t('orders.columns.note')} className="list-sub">
                            {hasNote ? (
                              <div className="note-text" onClick={() => openNoteModal(rowId)}>{displayNote(noteText)}</div>
                            ) : (
                              <button className="btn ghost xsmall" onClick={() => openNoteModal(rowId)}>{t('orders.noteButton')}</button>
                            )}
                          </div>
                          <div data-label={t('orders.columns.status')}>
                            <span className="pill pill-orange">На проверке</span>
                          </div>
                          {/* Кнопки действий для заказов на проверке */}
                          <div data-label="Действия" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                            {(() => {
                              const isCustomer = currentUser?.role === 'customer' || currentUser?.role === 'CUSTOMER' || userRole === 'customer' || userRole === 'CUSTOMER';

                              // Для заказчика: кнопки "Принять" и "На доработку"
                              if (isCustomer) {
                                return (
                                  <>
                                    <button
                                      className="btn primary small"
                                      onClick={async () => {
                                        try {
                                          await apiClient.post(`/orders/${order.id}/accept-work`);
                                          alert('✅ Работа принята! Заказ завершен.');
                                          if (fetchMyOrders) fetchMyOrders();
                                        } catch (error) {
                                          console.error('Error accepting work:', error);
                                          const errorMessage = error.response?.data?.detail || error.response?.data?.message || 'Ошибка при принятии работы';
                                          alert(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
                                        }
                                      }}
                                    >
                                      Принять работу
                                    </button>
                                    <button
                                      className="btn ghost small"
                                      onClick={async () => {
                                        const comment = prompt('Укажите, что нужно доработать (необязательно):');
                                        try {
                                          await apiClient.post(`/orders/${order.id}/request-revision`, { revision_comment: comment || null });
                                          alert('⚠️ Запрос на доработку отправлен исполнителю');
                                          if (fetchMyOrders) fetchMyOrders();
                                        } catch (error) {
                                          console.error('Error requesting revision:', error);
                                          const errorMessage = error.response?.data?.detail || error.response?.data?.message || 'Ошибка при запросе доработки';
                                          alert(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
                                        }
                                      }}
                                    >
                                      На доработку
                                    </button>
                                  </>
                                );
                              }

                              return null;
                            })()}
                          </div>
                        </>
                      )}
                      {myOrdersFilter === 'done' && (
                        <>
                          <div data-label={t('orders.columns.paid')}>{order.paid || '—'}</div>
                          <div data-label={t('orders.columns.price')} className="wallet-amount" style={{ fontSize: '16px' }}>{order.price}</div>
                          <div data-label={t('orders.columns.note')} className="list-sub">
                            {hasNote ? (
                              <div className="note-text" onClick={() => openNoteModal(rowId)}>{displayNote(noteText)}</div>
                            ) : (
                              <button className="btn ghost xsmall" onClick={() => openNoteModal(rowId)}>{t('orders.noteButton')}</button>
                            )}
                          </div>
                          <div data-label={t('orders.columns.status')}>
                            <span className="pill pill-green">{t('orders.status.done')}</span>
                          </div>
                          <div data-label="Действия"></div>
                        </>
                      )}
                      {myOrdersFilter === 'cancelled' && (
                        <>
                          <div data-label={t('orders.columns.cancelled')}>{order.cancelled || '—'}</div>
                          <div data-label={t('orders.columns.price')} className="wallet-amount" style={{ fontSize: '16px' }}>{order.price}</div>
                          <div data-label={t('orders.columns.note')} className="list-sub">
                            {hasNote ? (
                              <div className="note-text" onClick={() => openNoteModal(rowId)}>{displayNote(noteText)}</div>
                            ) : (
                              <button className="btn ghost xsmall" onClick={() => openNoteModal(rowId)}>{t('orders.noteButton')}</button>
                            )}
                          </div>
                          <div data-label={t('orders.columns.status')}>
                            <span className="pill pill-red">{t('orders.status.cancelled')}</span>
                          </div>
                          <div data-label="Действия"></div>
                        </>
                      )}
                      {myOrdersFilter === 'all' && (
                        <>
                          <div data-label={t('orders.columns.ordered')}>{order.ordered || '—'}</div>
                          <div data-label={t('orders.columns.price')} className="wallet-amount" style={{ fontSize: '16px' }}>{order.price}</div>
                          <div data-label={t('orders.columns.note')} className="list-sub">
                            {hasNote ? (
                              <div className="note-text" onClick={() => openNoteModal(rowId)}>{displayNote(noteText)}</div>
                            ) : (
                              <button className="btn ghost xsmall" onClick={() => openNoteModal(rowId)}>{t('orders.noteButton')}</button>
                            )}
                          </div>
                          <div data-label={t('orders.columns.status')}>
                            {order.status === 'in-progress' && <span className="pill pill-blue">{t('orders.status.inProgress')}</span>}
                            {order.status === 'review' && <span className="pill pill-orange">На проверке</span>}
                            {order.status === 'done' && <span className="pill pill-green">{t('orders.status.done')}</span>}
                            {order.status === 'cancelled' && <span className="pill pill-red">{t('orders.status.cancelled')}</span>}
                          </div>
                          {/* Кнопки действий для заказов */}
                          <div data-label="Действия" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                            {(() => {
                              const isExecutor = currentUser?.role === 'executor' || currentUser?.role === 'EXECUTOR' || userRole === 'executor' || userRole === 'EXECUTOR';
                              const isCustomer = currentUser?.role === 'customer' || currentUser?.role === 'CUSTOMER' || userRole === 'customer' || userRole === 'CUSTOMER';

                              // Для исполнителя: кнопка "Сдать работу" если заказ в работе
                              if (isExecutor && order.status === 'in-progress') {
                                return (
                                  <button
                                    className="btn primary small"
                                    onClick={async () => {
                                      try {
                                        await apiClient.post(`/orders/${order.id}/submit-for-review`);
                                        alert('✅ Работа сдана на проверку заказчику!');
                                        if (fetchMyOrders) fetchMyOrders();
                                      } catch (error) {
                                        console.error('Error submitting work:', error);
                                        const errorMessage = error.response?.data?.detail || error.response?.data?.message || 'Ошибка при сдаче работы';
                                        alert(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
                                      }
                                    }}
                                  >
                                    Сдать работу
                                  </button>
                                );
                              }

                              // Для заказчика: кнопки "Принять" и "На доработку" если заказ на проверке
                              if (isCustomer && order.status === 'review') {
                                return (
                                  <>
                                    <button
                                      className="btn primary small"
                                      onClick={async () => {
                                        try {
                                          await apiClient.post(`/orders/${order.id}/accept-work`);
                                          alert('✅ Работа принята! Заказ завершен.');
                                          if (fetchMyOrders) fetchMyOrders();
                                        } catch (error) {
                                          console.error('Error accepting work:', error);
                                          const errorMessage = error.response?.data?.detail || error.response?.data?.message || 'Ошибка при принятии работы';
                                          alert(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
                                        }
                                      }}
                                    >
                                      Принять работу
                                    </button>
                                    <button
                                      className="btn ghost small"
                                      onClick={async () => {
                                        const comment = prompt('Укажите, что нужно доработать (необязательно):');
                                        try {
                                          await apiClient.post(`/orders/${order.id}/request-revision`, { revision_comment: comment || null });
                                          alert('⚠️ Запрос на доработку отправлен исполнителю');
                                          if (fetchMyOrders) fetchMyOrders();
                                        } catch (error) {
                                          console.error('Error requesting revision:', error);
                                          const errorMessage = error.response?.data?.detail || error.response?.data?.message || 'Ошибка при запросе доработки';
                                          alert(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
                                        }
                                      }}
                                    >
                                      На доработку
                                    </button>
                                  </>
                                );
                              }

                              return <span style={{ color: 'var(--muted)' }}>—</span>;
                            })()}
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
        {noteModalOpen && (
          <div className="modal-backdrop" onClick={() => setNoteModalOpen(false)}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <div className="modal-title">{t('orders.noteModal.title')}</div>
                <button className="modal-close" onClick={() => setNoteModalOpen(false)}>✕</button>
              </div>
              <div className="modal-body">
                <div className="form">
                  <label>{t('orders.noteModal.label')}</label>
                  <textarea
                    maxLength={600}
                    rows={5}
                    value={noteDraft}
                    onChange={(e) => setNoteDraft(e.target.value)}
                    placeholder={t('orders.noteModal.placeholder')}
                  />
                  <div className="note-meta">
                    <span>{(t('orders.noteModal.counter') || '{count}').replace('{count}', noteDraft.length)}</span>
                  </div>
                </div>
              </div>
              <div className="modal-footer" style={{ justifyContent: 'space-between' }}>
                <div>
                  {noteTarget && getNote(noteTarget) && (
                    <button className="btn ghost small danger" onClick={handleDeleteNote}>{t('orders.noteModal.delete')}</button>
                  )}
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button className="btn ghost small" onClick={() => setNoteModalOpen(false)}>{t('common.cancel') || 'Отмена'}</button>
                  <button className="btn primary small" onClick={handleSaveNote}>{t('common.save') || 'Сохранить'}</button>
                </div>
              </div>
            </div>
          </div>
        )}
      </>
    );
  }

  if (tab === 'portfolio') {
    const hasPortfolio = Array.isArray(portfolioItems) && portfolioItems.length > 0;

    return (
      <div className="grid profile-grid">
        <div className="card">
          <div className="card-body">
            <p className="portfolio-desc">
              {t('portfolio.desc')}
            </p>
            {!hasPortfolio ? (
              <div className="portfolio-empty">
                <div className="portfolio-empty-cta">
                  <button className="btn primary" onClick={onAddWork}>{t('skills.addWork')}</button>
                </div>
              </div>
            ) : (
              <>
                <div className="portfolio-filter">
                  <div
                    className={`dropdown filter ${filterOpen ? 'open' : ''}`}
                    onClick={() => setFilterOpen(!filterOpen)}
                  >
                    <div className="dropdown-value">{selectedCategory}</div>
                    {filterOpen && (
                      <div className="dropdown-list">
                        {['Все рубрики', ...categoriesList].map((cat) => (
                          <div
                            key={cat}
                            className="dropdown-item"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedCategory(cat);
                              setFilterOpen(false);
                            }}
                          >
                            {cat}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                <div className={`portfolio-gallery ${filteredItems.length === 1 ? 'single' : ''}`}>
                  {filteredItems.map((item, idx) => {
                    const thumb = item.cover || (item.media || []).find((m) => m.isImage)?.url;
                    return (
                      <div
                        className="portfolio-card"
                        key={idx}
                        onClick={() => onEditWork(item.id)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => { if (e.key === 'Enter') onEditWork(item.id); }}
                      >
                        <div className="portfolio-card-thumb">
                          {thumb ? (
                            <img src={thumb} alt={item.title || 'Работа'} />
                          ) : (
                            <div className="thumb-placeholder">{t('portfolio.noCover')}</div>
                          )}
                        </div>
                        <div className="portfolio-card-body">
                          <div className="portfolio-card-title">{item.title || t('skills.work')}</div>
                          <div className="portfolio-card-meta">
                            <span>{item.category}</span>
                            {item.subcategory && <span>• {item.subcategory}</span>}
                          </div>
                          <div className="portfolio-card-actions">
                            <button
                              className="btn ghost small"
                              onClick={(e) => { e.stopPropagation(); onEditWork(item.id); }}
                            >
                              {t('portfolio.edit')}
                            </button>
                            <button
                              className="btn ghost small danger"
                              onClick={(e) => { e.stopPropagation(); onDeleteWork?.(item.id); }}
                            >
                              {t('portfolio.delete')}
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="portfolio-actions">
                  <button className="btn primary" onClick={onAddWork}>{t('skills.addWork')}</button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (tab === 'projects') {
    return (
      <>
        <div className="card">
          <div className="card-header">
            <div className="card-title">Мои проекты</div>
            <button className="btn primary small" onClick={() => setShowCreateProjectModal(true)}>
              Создать проект
            </button>
          </div>
          <div className="card-body">
            {projectsLoading ? (
              <div style={{ textAlign: 'center', padding: '40px' }}>Загрузка...</div>
            ) : (
              <>
                {/* Вкладки фильтров всегда видны, даже когда нет проектов */}
                <div className="orders-top" style={{ marginBottom: '20px' }}>
                  <div className="status-tabs">
                    <button
                      type="button"
                      className={`status-tab ${projectsFilter === 'all' ? 'active' : ''}`}
                      onClick={() => setProjectsFilter('all')}
                    >
                      Все
                    </button>
                    <button
                      type="button"
                      className={`status-tab ${projectsFilter === 'pending' ? 'active' : ''}`}
                      onClick={() => setProjectsFilter('pending')}
                    >
                      Ожидают откликов
                    </button>
                    <button
                      type="button"
                      className={`status-tab ${projectsFilter === 'in-progress' ? 'active' : ''}`}
                      onClick={() => setProjectsFilter('in-progress')}
                    >
                      В работе
                    </button>
                    <button
                      type="button"
                      className={`status-tab ${projectsFilter === 'completed' ? 'active' : ''}`}
                      onClick={() => setProjectsFilter('completed')}
                    >
                      Выполнено
                    </button>
                    <button
                      type="button"
                      className={`status-tab ${projectsFilter === 'cancelled' ? 'active' : ''}`}
                      onClick={() => setProjectsFilter('cancelled')}
                    >
                      Отменено
                    </button>
                  </div>
                </div>

                {customerProjectsFiltered.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '60px 20px' }}>
                    <div style={{ fontSize: '48px', marginBottom: '20px' }}>📋</div>
                    <h3 style={{ marginBottom: '12px', color: 'var(--text)' }}>
                      {projectsFilter === 'all'
                        ? 'У вас пока нет проектов'
                        : `Нет проектов со статусом "${projectsFilter === 'pending' ? 'Ожидают откликов' : projectsFilter === 'in-progress' ? 'В работе' : projectsFilter === 'completed' ? 'Выполнено' : 'Отменено'}"`}
                    </h3>
                    <p style={{ color: 'var(--muted)', marginBottom: '24px', maxWidth: '400px', margin: '0 auto 24px' }}>
                      {projectsFilter === 'all'
                        ? 'Создайте свой первый проект и найдите исполнителя для вашей задачи'
                        : 'Попробуйте выбрать другой фильтр'}
                    </p>
                    {projectsFilter === 'all' && (
                      <button className="btn primary" onClick={() => setShowCreateProjectModal(true)}>
                        Создать первый проект
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="exchange-list">
                    {customerProjectsFiltered.map((project) => {
                      const statusValue = project.status?.value || project.status || 'open';
                      const statusLower = statusValue.toLowerCase().replace('_', '-');
                      const getStatusBadge = (status) => {
                        const statusMap = {
                          'open': { text: 'Ожидает откликов', color: '#FFA500', icon: '🟡' },
                          'pending': { text: 'Ожидает откликов', color: '#FFA500', icon: '🟡' },
                          'in-progress': { text: 'В работе', color: '#4CAF50', icon: '🔵' },
                          'in_progress': { text: 'В работе', color: '#4CAF50', icon: '🔵' },
                          'completed': { text: 'Выполнено', color: '#2196F3', icon: '✅' },
                          'cancelled': { text: 'Отменено', color: '#F44336', icon: '❌' },
                          'canceled': { text: 'Отменено', color: '#F44336', icon: '❌' }
                        };
                        const statusKey = status.toLowerCase().replace('_', '-');
                        return statusMap[statusKey] || { text: status, color: '#999', icon: '📋' };
                      };
                      const statusInfo = getStatusBadge(statusLower);
                      return (
                        <div key={project.id} className="exchange-item">
                          <div className="exchange-item-top">
                            <div className="exchange-item-main">
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                                <div className="exchange-item-title">{project.title}</div>
                                <span
                                  style={{
                                    fontSize: '12px',
                                    padding: '4px 8px',
                                    borderRadius: '4px',
                                    background: statusInfo.color + '20',
                                    color: statusInfo.color,
                                    fontWeight: '500'
                                  }}
                                >
                                  {statusInfo.icon} {statusInfo.text}
                                </span>
                              </div>
                              <div className="exchange-item-desc">{project.description}</div>
                              {project.skills && project.skills.length > 0 && (
                                <div className="exchange-item-tags">
                                  {project.skills.map((skill, idx) => (
                                    <span key={idx} className="tag">{skill.skill_name || skill}</span>
                                  ))}
                                </div>
                              )}
                            </div>
                            <div className="exchange-item-price">
                              <div className="price-label">Бюджет</div>
                              <div className="price-value">
                                {project.budget_to
                                  ? `${parseFloat(project.budget_to).toLocaleString('ru-RU')} ₽`
                                  : project.budget_from
                                    ? `от ${parseFloat(project.budget_from).toLocaleString('ru-RU')} ₽`
                                    : 'Не указано'}
                              </div>
                            </div>
                          </div>
                          <div className="exchange-item-bottom">
                            <div className="exchange-item-meta">
                              {project.deadline && (
                                <div className="meta-item">
                                  ⏱ {Math.ceil((new Date(project.deadline) - new Date()) / (1000 * 60 * 60 * 24))} дней
                                </div>
                              )}
                              {(project.category_id || project.subcategory_id) && (
                                <div className="meta-item">
                                  📋 {project.category_id || ''} {project.subcategory_id ? `→ ${project.subcategory_id}` : ''}
                                </div>
                              )}
                            </div>
                            <div className="exchange-item-actions">
                              {/* Показываем кнопку удаления только для проектов со статусом "Ожидают откликов" */}
                              {(statusLower === 'open' || statusLower === 'pending') && (
                                <button
                                  className="btn danger small"
                                  onClick={() => {
                                    if (window.confirm('Удалить проект?')) {
                                      handleDeleteProject(project.id);
                                    }
                                  }}
                                >
                                  Удалить
                                </button>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {showCreateProjectModal && (
          <div className="modal-backdrop" onClick={() => setShowCreateProjectModal(false)}>
            <div className="modal create-project-modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <div className="modal-title">Опишите, что нужно сделать</div>
                <button className="modal-close" onClick={() => setShowCreateProjectModal(false)}>✕</button>
              </div>
              <div className="modal-body">
                <div className="form">
                  <div className="form-group">
                    <label>Название задачи</label>
                    <textarea
                      rows={2}
                      maxLength={55}
                      value={projectForm.title}
                      onChange={(e) => setProjectForm({ ...projectForm, title: e.target.value })}
                      placeholder="Введите название"
                    />
                    <div className="char-counter">{projectForm.title.length} из 55 символов</div>
                  </div>

                  <div className="form-group">
                    <label>Детальное описание задачи</label>
                    <textarea
                      rows={8}
                      maxLength={1500}
                      value={projectForm.description}
                      onChange={(e) => setProjectForm({ ...projectForm, description: e.target.value })}
                      placeholder="Опишите, что именно вам нужно, в каком объеме и за какой срок"
                    />
                    <div className="char-counter">
                      {projectForm.description.length} из 1500 символов
                      {projectForm.description.length < 100 && ` (минимум 100)`}
                    </div>
                  </div>

                  <div className="form-group">
                    <label>Рубрика</label>
                    <button
                      type="button"
                      className="btn ghost"
                      style={{ width: '100%', justifyContent: 'flex-start' }}
                      onClick={() => setShowProjectCategoryModal(true)}
                    >
                      {projectForm.category
                        ? `${projectForm.category.category} → ${projectForm.category.subcategory}${projectForm.category.subsubcategory ? ` → ${projectForm.category.subsubcategory}` : ''}`
                        : 'Выберите рубрику'}
                    </button>
                  </div>

                  <div className="form-group">
                    <label>Цена не более</label>
                    <div className="input-with-currency">
                      <input
                        type="number"
                        min="0"
                        step="1"
                        value={projectForm.maxPrice}
                        onChange={(e) => setProjectForm({ ...projectForm, maxPrice: e.target.value })}
                        placeholder="Введите цену"
                      />
                      <span className="currency-label">₽</span>
                    </div>
                  </div>

                  {projectForm.maxPrice && (
                    <div className="commission-info customer-commission">
                      <div className="commission-row">
                        <span>Цена заказа:</span>
                        <span className="commission-value">{calculateCustomerCommission(projectForm.maxPrice).price.toLocaleString('ru-RU')} ₽</span>
                      </div>
                      {calculateCustomerCommission(projectForm.maxPrice).depositCommission > 0 && (
                        <div className="commission-row">
                          <span>Комиссия на ввод (1%):</span>
                          <span className="commission-value negative">+{calculateCustomerCommission(projectForm.maxPrice).depositCommission.toLocaleString('ru-RU')} ₽</span>
                        </div>
                      )}
                      <div className="commission-row">
                        <span>Наценка сервиса ({projectForm.maxPrice < 5000 ? '10%' : projectForm.maxPrice < 15000 ? '5%' : '3%'}):</span>
                        <span className="commission-value negative">+{calculateCustomerCommission(projectForm.maxPrice).serviceMarkup.toLocaleString('ru-RU')} ₽</span>
                      </div>
                      <div className="commission-row">
                        <span>Стоимость публикации:</span>
                        <span className="commission-value negative">+{calculateCustomerCommission(projectForm.maxPrice).publicationCost.toLocaleString('ru-RU')} ₽</span>
                      </div>
                      <div className="commission-row total">
                        <span>Итого к оплате:</span>
                        <span className="commission-value total-price">{calculateCustomerCommission(projectForm.maxPrice).totalToPay.toLocaleString('ru-RU')} ₽</span>
                      </div>
                    </div>
                  )}

                  <div className="form-group">
                    <label>Примерный срок выполнения (в днях)</label>
                    <input
                      type="number"
                      min="1"
                      step="1"
                      value={projectForm.deadline}
                      onChange={(e) => setProjectForm({ ...projectForm, deadline: e.target.value })}
                      placeholder="Например: 7"
                    />
                  </div>

                  <div className="form-group">
                    <label>Необходимые навыки (до 5)</label>
                    <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                      <input
                        type="text"
                        value={skillInput}
                        onChange={(e) => setSkillInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            addSkill();
                          }
                        }}
                        placeholder="Введите навык"
                        disabled={projectForm.skills.length >= 5}
                        style={{ flex: 1 }}
                      />
                      <button
                        type="button"
                        className="btn primary small"
                        onClick={addSkill}
                        disabled={!skillInput.trim() || projectForm.skills.length >= 5}
                      >
                        Добавить
                      </button>
                    </div>
                    {projectForm.skills.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                        {projectForm.skills.map((skill, index) => (
                          <span key={index} className="tag" style={{ cursor: 'pointer' }} onClick={() => removeSkill(index)}>
                            {skill} ✕
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="form-group">
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={projectForm.allowHigherPrice}
                        onChange={(e) => setProjectForm({ ...projectForm, allowHigherPrice: e.target.checked })}
                      />
                      <span>Готов рассмотреть предложения с ценой выше, если уровень исполнителя будет выше</span>
                    </label>
                  </div>

                  <div className="form-group">
                    <label>Прикрепить файлы</label>
                    <div className="upload-hint" style={{ marginBottom: '8px' }}>
                      До 10 файлов, не более 100 Мб {projectForm.files && projectForm.files.length > 0 && `(${projectForm.files.length}/10, ${(projectForm.files.reduce((sum, f) => sum + (f.file?.size || 0), 0) / (1024 * 1024)).toFixed(1)} МБ)`}
                    </div>
                    <div className="upload-box" onClick={() => projectFilesInputRef.current?.click()}>
                      <div className="upload-label">📎 Выбрать файлы</div>
                      <div className="upload-sub">Любые форматы</div>
                      <input
                        ref={projectFilesInputRef}
                        className="file-input-hidden"
                        type="file"
                        multiple
                        onChange={handleProjectFilesChange}
                      />
                    </div>
                    {projectForm.files && projectForm.files.length > 0 && (
                      <div className="file-preview-grid" style={{ marginTop: '12px' }}>
                        {projectForm.files.map((file, idx) => (
                          <div key={idx} className="file-preview">
                            {file.type.startsWith('image/') ? (
                              <div className="file-thumb">
                                <img src={file.url} alt={file.name} />
                                <button
                                  className="file-remove"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    removeProjectFile(idx);
                                  }}
                                  type="button"
                                >
                                  ✕
                                </button>
                              </div>
                            ) : (
                              <div className="file-chip">
                                <span className="file-name">{file.name}</span>
                                <button
                                  className="file-remove"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    removeProjectFile(idx);
                                  }}
                                  type="button"
                                >
                                  ✕
                                </button>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button className="btn ghost small" onClick={() => setShowCreateProjectModal(false)}>
                  Отмена
                </button>
                <button
                  className="btn primary small"
                  onClick={async () => {
                    try {
                      let deadlineDate = null;
                      if (projectForm.deadline) {
                        const days = parseInt(projectForm.deadline, 10);
                        const deadlineObj = new Date();
                        deadlineObj.setDate(deadlineObj.getDate() + days);
                        deadlineDate = deadlineObj.toISOString();
                      }

                      const orderData = {
                        title: projectForm.title,
                        description: projectForm.description,
                        category_id: projectForm.category?.category || null,
                        subcategory_id: projectForm.category?.subcategory || null,
                        subsubcategory_id: projectForm.category?.subsubcategory || null,
                        budget_to: projectForm.maxPrice ? parseFloat(projectForm.maxPrice) : null,
                        allow_higher_price: projectForm.allowHigherPrice,
                        deadline: deadlineDate,
                        skills: projectForm.skills || []
                      };

                      const response = await apiClient.post('/orders', orderData);
                      setCustomerProjects([...customerProjects, response.data]);
                      setShowCreateProjectModal(false);
                      setProjectForm({
                        title: '',
                        description: '',
                        category: null,
                        maxPrice: '',
                        allowHigherPrice: false,
                        files: [],
                        deadline: '',
                        skills: [],
                        files: []
                      });
                    } catch (error) {
                      console.error('Error creating project:', error);
                      alert(error.response?.data?.detail || 'Ошибка при создании проекта');
                    }
                  }}
                  disabled={!projectForm.title || projectForm.description.length < 100 || !projectForm.category || !projectForm.maxPrice || !projectForm.deadline}
                >
                  Разместить
                </button>
              </div>
            </div>
          </div>
        )}
        {showProjectCategoryModal && (
          <div className="modal-backdrop" onClick={() => setShowProjectCategoryModal(false)}>
            <div className="modal category-modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <div className="modal-title">Выберите рубрику</div>
                <button className="modal-close" onClick={() => setShowProjectCategoryModal(false)}>✕</button>
              </div>
              <div className="modal-body category-modal-body">
                <div className="category-list">
                  {ORDERS_CATEGORIES.map((category) => (
                    <div key={category.id} className="category-item">
                      <div className="category-header">
                        <div className="category-title">{category.name}</div>
                      </div>
                      <div className="subcategory-list">
                        {category.subcategories.map((subcategory) => (
                          <div key={subcategory.id} className="subcategory-item">
                            <div
                              className="subcategory-main-wrapper"
                              onClick={() => {
                                if (subcategory.subcategories && subcategory.subcategories.length > 0) {
                                  setExpandedProjectSubcategory(
                                    expandedProjectSubcategory === subcategory.id ? null : subcategory.id
                                  );
                                } else {
                                  handleSelectProjectCategory(category, subcategory, null);
                                }
                              }}
                            >
                              <span>{subcategory.name}</span>
                              {subcategory.subcategories && subcategory.subcategories.length > 0 && (
                                <button
                                  className="category-expand-btn"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setExpandedProjectSubcategory(
                                      expandedProjectSubcategory === subcategory.id ? null : subcategory.id
                                    );
                                  }}
                                >
                                  {expandedProjectSubcategory === subcategory.id ? '−' : '+'}
                                </button>
                              )}
                            </div>
                            {expandedProjectSubcategory === subcategory.id && subcategory.subcategories && (
                              <div className="subsubcategory-list">
                                {subcategory.subcategories.map((subsubcategory) => (
                                  <div
                                    key={subsubcategory.id}
                                    className="subsubcategory-item"
                                    onClick={() => handleSelectProjectCategory(category, subcategory, subsubcategory)}
                                  >
                                    {subsubcategory.name}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </>
    );
  }

  if (tab === 'profile') {
    const userName = currentUser?.name || '';

    if (profileLoading) {
      return (
        <div className="card">
          <div className="card-body" style={{ textAlign: 'center', padding: '40px' }}>
            Загрузка...
          </div>
        </div>
      );
    }

    if (!hasProfile) {
      return (
        <div className="card">
          <div className="card-header">
            <div className="card-title">{t('profile.title')}</div>
          </div>
          <div className="card-body">
            <div style={{ textAlign: 'center', padding: '40px 20px' }}>
              <div style={{ fontSize: '48px', marginBottom: '20px' }}>👤</div>
              <h3 style={{ marginBottom: '12px', color: 'var(--text)' }}>{t('profile.emptyTitle')}</h3>
              <p style={{ color: 'var(--muted)', marginBottom: '24px', maxWidth: '400px', margin: '0 auto 24px' }}>
                {t('profile.emptyDescription')}
              </p>
              <button className="btn primary" onClick={onFillProfile}>
                {t('profile.fillProfile')}
              </button>
            </div>
          </div>
        </div>
      );
    }

    const getInitials = (name) => {
      if (!name) return 'П';
      const parts = name.trim().split(' ');
      if (parts.length >= 2) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
      }
      return name.substring(0, 2).toUpperCase();
    };

    return (
      <>
        <div className="role-switcher-card">
          <div className="role-switcher">
            <div className="role-switcher-label">Вы работаете как:</div>
            <div className="role-switcher-tabs">
              <button
                className={`role-tab ${userRole === 'executor' || userRole === 'EXECUTOR' ? 'active' : ''}`}
                onClick={() => {
                  setViewMode('executor');
                  localStorage.setItem('viewMode', 'executor');
                  setActiveTab('orders');
                }}
              >
                Исполнитель
              </button>
              <button
                className={`role-tab ${userRole === 'customer' || userRole === 'CUSTOMER' ? 'active' : ''}`}
                onClick={() => {
                  setViewMode('customer');
                  localStorage.setItem('viewMode', 'customer');
                  setActiveTab('projects');
                }}
              >
                Заказчик
              </button>
            </div>
          </div>
        </div>

        <div className="grid profile-grid">
          <div className="card">
            <div className="card-header">
              <div className="card-title">{t('profile.title')}</div>
              <button className="btn ghost small" onClick={onEditProfile}>
                {t('profile.edit')}
              </button>
            </div>
            <div className="card-body">
              <div className="profile">
                <div className="profile-avatar-wrapper">
                  {currentUser?.avatar_url ? (
                    <img
                      src={currentUser.avatar_url}
                      alt="Profile"
                      className="profile-avatar-img"
                    />
                  ) : (
                    <div className="avatar" style={{ width: '100%', height: '100%', borderRadius: 'inherit', fontSize: '72px' }}>
                      {getInitials(userProfile?.name || userName || currentUser?.name || 'П')}
                    </div>
                  )}
                </div>
                <div className="profile-meta">
                  <div className="profile-name">{userProfile?.name || userName || currentUser?.name || ''}</div>
                  <div className="profile-rating">
                    <span className="pill pill-green">{t('profile.rating')} {(currentUser?.rating || 5.0).toFixed(1)}</span>
                  </div>
                  <div className="profile-specialty">
                    {(currentUser?.role?.value || currentUser?.role || 'executor') === 'executor' || (currentUser?.role?.value || currentUser?.role) === 'EXECUTOR'
                      ? '🛠️ Исполнитель'
                      : '📋 Заказчик'}
                  </div>
                  {userProfile?.skills && userProfile.skills.length > 0 && (
                    <div className="profile-about">{userProfile.skills.map(s => s.skill_name || s).join(' · ')}</div>
                  )}
                </div>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="card-header">
              <div className="card-title">{t('profile.verification')}</div>
            </div>
            <div className="card-body">
              <div className="form">
                <label>{t('profile.inn')}</label>
                <div className="input-group">
                  <input defaultValue={userProfile?.inn || ''} placeholder="Не указан" />
                  <button className="btn ghost">{t('profile.check')}</button>
                </div>
                {userProfile?.inn && (
                  <div className="pill pill-green">{t('profile.status')}: {userProfile.verification_status === 'verified' ? t('profile.confirmed') : userProfile.verification_status}</div>
                )}
                <div className="otp-row">
                  <button className="btn ghost">{t('profile.otpEmail')}</button>
                  <button className="btn ghost">{t('profile.otpPhone')}</button>
                </div>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="card-header">
              <div className="card-title">{t('profile.about')}</div>
            </div>
            <div className="card-body">
              <div className="profile-about-text">
                {userProfile?.about || 'Информация о вас не указана'}
              </div>
            </div>
          </div>
          <div className="card">
            <div className="card-header">
              <div className="card-title">{t('profile.contactInfo')}</div>
            </div>
            <div className="card-body">
              <div className="profile-info-list">
                {userProfile?.country && (
                  <div className="profile-info-item">
                    <span className="profile-info-label">{t('profile.country')}:</span>
                    <span className="profile-info-value">{userProfile?.country}</span>
                  </div>
                )}
                {userProfile?.city && (
                  <div className="profile-info-item">
                    <span className="profile-info-label">{t('profile.city')}:</span>
                    <span className="profile-info-value">{userProfile?.city}</span>
                  </div>
                )}
                {userProfile?.work_schedule_from && userProfile?.work_schedule_to && (
                  <div className="profile-info-item">
                    <span className="profile-info-label">{t('profile.workSchedule')}:</span>
                    <span className="profile-info-value">
                      {userProfile.work_schedule_from} - {userProfile.work_schedule_to}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
          <div className="card">
            <div className="card-header">
              <div className="card-title">{t('profile.honorBoard')}</div>
              <div className="card-extra"><span className="pill pill-outline">#{currentUser?.rating_position || 0}</span></div>
            </div>
            <div className="card-body">
              <div className="honor">
                <div className="honor-item">
                  <div className="honor-rank">{currentUser?.rating_position || 0}</div>
                  <div className="honor-meta">{t('profile.currentPosition')}</div>
                </div>
                <div className="honor-divider" />
                <div className="honor-item">
                  <div className="honor-rank">{currentUser?.closed_orders_week || 0}</div>
                  <div className="honor-meta">{t('profile.closedOrdersWeek')}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </>
    );
  }


  if (tab === 'wallet') {
    return (
      <div className="grid two">
        <div className="card">
          <div className="card-header">
            <div className="card-title">{t('wallet.title')}</div>
          </div>
          <div className="card-body">
            <div className="wallet">
              <div className="wallet-balance">
                <div className="wallet-amount">{(currentUser?.balance || 0).toLocaleString('ru-RU')} ₽</div>
                <div className="wallet-sub">{t('wallet.available')}</div>
              </div>
              <div className="wallet-balance ghost">
                <div className="wallet-amount">{currentUser?.tf_coins || 0} TF-Coins</div>
                <div className="wallet-sub">{t('wallet.internalCurrency')}</div>
              </div>
            </div>
            <div className="wallet-actions">
              <button className="btn primary">{t('wallet.withdraw')}</button>
              <button className="btn ghost">{t('wallet.topUp')}</button>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="card-header">
            <div className="card-title">{t('wallet.history')}</div>
          </div>
          <div className="card-body">
            {walletLoading ? (
              <div style={{ textAlign: 'center', padding: '40px', color: 'var(--muted)' }}>Загрузка...</div>
            ) : walletTransactions.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px', color: 'var(--muted)' }}>
                <div style={{ fontSize: '40px', marginBottom: '12px' }}>💸</div>
                <p>Транзакций пока нет</p>
              </div>
            ) : (
              <div className="list">
                {walletTransactions.map((tx) => (
                  <div key={tx.id} className="list-row">
                    <div>
                      <div className="list-title">{tx.title}</div>
                      <div className="list-sub">
                        {tx.type === 'income' ? '+' : '−'}
                        {parseFloat(tx.amount).toLocaleString('ru-RU')} ₽
                        {' · '}
                        {new Date(tx.created_at).toLocaleDateString('ru-RU')}
                      </div>
                    </div>
                    <span className={`pill ${tx.type === 'income' ? 'pill-green' : 'pill-outline'}`}>
                      {tx.type === 'income' ? t('wallet.credited') : 'Оплачено'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <div className="card-title">{t('wallet.incomeChart')}</div>
          </div>
          <div className="card-body">
            <div className="chart-placeholder">График будет здесь</div>
          </div>
        </div>
      </div>
    );
  }

  // Первый блок messages удален - используется второй блок ниже

  if (tab === 'notifications') {
    // Используем непрочитанные сообщения как уведомления
    const notifications = messages
      .filter(msg => msg.to_user_id === currentUser?.id && !msg.is_read)
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    return (
      <div className="card">
        <div className="card-header">
          <div className="card-title">{t('notifications.title')} ({notifications.length})</div>
        </div>
        <div className="card-body">
          {messagesLoading ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--muted)' }}>
              <p>Загрузка уведомлений...</p>
            </div>
          ) : notifications.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--muted)' }}>
              <div style={{ fontSize: '48px', marginBottom: '20px' }}>🔔</div>
              <h3 style={{ marginBottom: '12px' }}>Нет уведомлений</h3>
              <p>Здесь будут отображаться уведомления о новых откликах, принятых предложениях и других событиях</p>
            </div>
          ) : (
            <div className="list">
              {notifications.map((notification) => {
                const isOfferCreated = notification.message_type === 'OFFER_CREATED' || notification.message_type === 'offer_created';
                const isOfferAccepted = notification.message_type === 'OFFER_ACCEPTED' || notification.message_type === 'offer_accepted';
                const isOfferRejected = notification.message_type === 'OFFER_REJECTED' || notification.message_type === 'offer_rejected';
                const offerData = notification.offer_data;
                const orderData = notification.order_data;
                const projectTitle = orderData?.title || 'Проект';
                const isCustomer = currentUser?.role === 'customer' || currentUser?.role === 'CUSTOMER';

                return (
                  <div key={notification.id} className="list-row" style={{
                    padding: '16px',
                    borderBottom: '1px solid var(--stroke)',
                    cursor: 'pointer',
                    background: !notification.is_read ? 'rgba(32, 238, 121, 0.05)' : 'transparent'
                  }}
                    onClick={() => {
                      setActiveTab('messages');
                      setSelectedConversation({
                        userId: notification.from_user_id,
                        userName: notification.from_user_name
                      });
                    }}>
                    <div style={{ flex: 1 }}>
                      <div className="list-title" style={{
                        fontWeight: !notification.is_read ? '600' : '400',
                        marginBottom: '4px'
                      }}>
                        {isOfferCreated && `📢 ${notification.from_user_name} отправил предложение`}
                        {isOfferAccepted && `✅ ${notification.from_user_name} одобрил ваше предложение`}
                        {isOfferRejected && `❌ ${notification.from_user_name} отклонил ваше предложение`}
                        {!isOfferCreated && !isOfferAccepted && !isOfferRejected && notification.title}
                      </div>
                      <div className="list-sub" style={{ fontSize: '13px', color: 'var(--muted)' }}>
                        {projectTitle && `Проект: ${projectTitle}`}
                        {projectTitle && ' • '}
                        {new Date(notification.created_at).toLocaleString('ru-RU')}
                      </div>
                      {notification.content && (
                        <div style={{
                          marginTop: '8px',
                          fontSize: '13px',
                          color: 'var(--muted)',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical'
                        }}>
                          {notification.content}
                        </div>
                      )}
                    </div>
                    <span className={`pill ${isOfferCreated ? 'pill-green' : isOfferAccepted ? 'pill-outline' : 'pill-outline'}`}>
                      {isOfferCreated ? 'Предложение' : isOfferAccepted ? 'Одобрено' : isOfferRejected ? 'Отклонено' : 'Уведомление'}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    );
  }

  if (tab === 'community') {

    const handleLike = async (postId) => {
      if (communityPostsHook?.toggleLike) {
        try {
          await communityPostsHook.toggleLike(postId);
        } catch (error) {
          console.error('Error toggling like:', error);
        }
      }
    };

    const handleCreatePost = async () => {
      if (!postText.trim() && postPhotos.length === 0) return;

      try {
        const postData = {
          text: postText,
          images: postPhotos.map(p => p.url || p.path || p)
        };

        if (communityPostsHook?.createPost) {
          await communityPostsHook.createPost(postData);
        }

        setPostText('');
        setPostPhotos([]);
        setShowCreatePostModal(false);
      } catch (error) {
        console.error('Error creating post:', error);
        alert('Ошибка при создании поста');
      }
    };

    const handleRemovePhoto = (index) => {
      setPostPhotos(prev => prev.filter((_, i) => i !== index));
    };

    // commentsData и commentsLoading объявлены на верхнем уровне компонента

    const handleOpenComments = async (postId) => {
      setSelectedPostId(postId);
      setShowCommentsModal(true);
      setCommentText('');
      setCommentsData([]);
      // Загружаем комментарии с сервера
      if (communityPostsHook?.fetchComments) {
        setCommentsLoading(true);
        try {
          const data = await communityPostsHook.fetchComments(postId);
          setCommentsData(data);
        } finally {
          setCommentsLoading(false);
        }
      }
    };

    const handleAddComment = async () => {
      if (!commentText.trim() || !selectedPostId) return;

      try {
        const newComment = await addCommentHook(selectedPostId, commentText.trim());
        // Добавляем новый комментарий локально без перезагрузки
        if (newComment) {
          setCommentsData(prev => [...prev, newComment]);
        }
        setCommentText('');
      } catch (err) {
        console.error('Error adding comment:', err);
        alert('Не удалось добавить комментарий');
      }
    };


    // Используем посты из API
    const allPosts = communityPosts || [];
    const selectedPost = allPosts.find(p => p.id === selectedPostId);

    // Фильтрация постов
    const filteredPosts = communityFilter === 'my'
      ? allPosts.filter(post => {
        // Фильтруем по user_id текущего пользователя
        return post.user_id === currentUser?.id;
      })
      : allPosts;

    const handleDeletePost = async (postId) => {
      if (!window.confirm(t('community.deleteConfirm'))) return;

      try {
        if (communityPostsHook?.deletePost) {
          await communityPostsHook.deletePost(postId);
        }
      } catch (error) {
        console.error('Error deleting post:', error);
        alert('Ошибка при удалении поста');
      }
    };

    const handleStartEditPost = (post) => {
      setEditingPostId(post.id);
      setEditPostText(post.text);
      setEditPostPhotos(post.images ? post.images.map(img => ({
        url: img.image_path || img.url || img,
        name: 'image'
      })) : []);
    };

    const handleSaveEditPost = async () => {
      if (!editPostText.trim() && editPostPhotos.length === 0) return;
      if (!editingPostId) return;

      try {
        const postData = {
          text: editPostText,
          images: editPostPhotos.map(p => p.url || p.path || p)
        };

        if (communityPostsHook?.updatePost) {
          await communityPostsHook.updatePost(editingPostId, postData);
        }

        setEditingPostId(null);
        setEditPostText('');
        setEditPostPhotos([]);
      } catch (error) {
        console.error('Error updating post:', error);
        alert('Ошибка при обновлении поста');
      }
    };

    const handleCancelEdit = () => {
      setEditingPostId(null);
      setEditPostText('');
      setEditPostPhotos([]);
    };

    const handleRemoveEditPhoto = (index) => {
      setEditPostPhotos(prev => prev.filter((_, i) => i !== index));
    };

    return (
      <div>
        <div className="community-header">
          <div className="community-title">{t('community.title')}</div>
          <button className="btn primary" onClick={() => setShowCreatePostModal(true)}>
            {t('community.createPost')}
          </button>
        </div>
        <div className="community-tabs">
          <button
            className={`community-tab ${communityFilter === 'all' ? 'active' : ''}`}
            onClick={() => setCommunityFilter('all')}
          >
            {t('community.tabs.all')}
          </button>
          <button
            className={`community-tab ${communityFilter === 'my' ? 'active' : ''}`}
            onClick={() => setCommunityFilter('my')}
          >
            {t('community.tabs.my')}
          </button>
        </div>
        <div className="community-feed">
          {filteredPosts.map((post) => {
            const isMyPost = post.user_id === currentUser?.id;
            return (
              <div key={post.id} className="community-post">
                <div className="post-header">
                  <div className="post-author">
                    {post.avatar ? (
                      <img src={post.avatar} alt={post.user_name || 'User'} className="avatar small" />
                    ) : (
                      <div className="avatar small">{(post.user_name || 'User')?.substring(0, 2) || 'АВ'}</div>
                    )}
                    <div className="author-info">
                      <div className="author-name">{post.user_name || 'Пользователь'}</div>
                      <div className="post-date">{formatDate(post.created_at)}</div>
                    </div>
                  </div>
                  {isMyPost && (
                    <div className="post-actions-menu">
                      <button
                        className="post-action-btn"
                        onClick={() => handleStartEditPost(post)}
                        title={t('community.edit')}
                      >
                        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                          <path d="M10.5 3L15 7.5L5.25 17.25H0.75V12.75L10.5 3Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </button>
                      <button
                        className="post-action-btn danger"
                        onClick={() => handleDeletePost(post.id)}
                        title={t('community.delete')}
                      >
                        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                          <path d="M2.25 4.5H15.75M6.75 4.5V3C6.75 2.58579 7.08579 2.25 7.5 2.25H10.5C10.9142 2.25 11.25 2.58579 11.25 3V4.5M14.25 4.5V15C14.25 15.4142 13.9142 15.75 13.5 15.75H4.5C4.08579 15.75 3.75 15.4142 3.75 15V4.5H14.25Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </button>
                    </div>
                  )}
                </div>
                {post.images && post.images.length > 0 && (
                  <div
                    className="post-image"
                    onTouchStart={(e) => {
                      const touch = e.touches[0];
                      setTouchStartPos(prev => ({
                        ...prev,
                        [post.id]: { x: touch.clientX, y: touch.clientY }
                      }));
                    }}
                    onTouchMove={(e) => {
                      const touch = e.touches[0];
                      setTouchEndPos(prev => ({
                        ...prev,
                        [post.id]: { x: touch.clientX, y: touch.clientY }
                      }));
                    }}
                    onTouchEnd={() => {
                      if (!touchStartPos[post.id] || !touchEndPos[post.id]) return;

                      const images = post.images && post.images.length > 0
                        ? post.images.map(img => img.image_path || img.url || img)
                        : (post.image ? [post.image] : []);
                      if (images.length <= 1) return;

                      const currentIndex = postImageIndex[post.id] || 0;
                      const deltaX = touchStartPos[post.id].x - touchEndPos[post.id].x;
                      const deltaY = touchStartPos[post.id].y - touchEndPos[post.id].y;
                      const minSwipeDistance = 50;

                      // Проверяем, что это горизонтальный свайп
                      if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > minSwipeDistance) {
                        if (deltaX > 0) {
                          // Свайп влево - следующая фотография
                          setPostImageIndex(prev => ({
                            ...prev,
                            [post.id]: currentIndex < images.length - 1 ? currentIndex + 1 : 0
                          }));
                        } else {
                          // Свайп вправо - предыдущая фотография
                          setPostImageIndex(prev => ({
                            ...prev,
                            [post.id]: currentIndex > 0 ? currentIndex - 1 : images.length - 1
                          }));
                        }
                      }

                      // Сбрасываем позиции
                      setTouchStartPos(prev => {
                        const updated = { ...prev };
                        delete updated[post.id];
                        return updated;
                      });
                      setTouchEndPos(prev => {
                        const updated = { ...prev };
                        delete updated[post.id];
                        return updated;
                      });
                    }}
                  >
                    {(() => {
                      const images = post.images && post.images.length > 0
                        ? post.images.map(img => img.image_path || img.url || img)
                        : [];
                      const currentIndex = postImageIndex[post.id] || 0;
                      const hasMultiple = images.length > 1;

                      return (
                        <>
                          <img src={images[currentIndex]} alt={post.title} />
                          {hasMultiple && (
                            <>
                              <div className="post-image-counter">
                                {currentIndex + 1} / {images.length}
                              </div>
                              <button
                                className="post-image-nav post-image-nav-prev"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setPostImageIndex(prev => ({
                                    ...prev,
                                    [post.id]: currentIndex > 0 ? currentIndex - 1 : images.length - 1
                                  }));
                                }}
                              >
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                                  <path d="M15 18L9 12L15 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                              </button>
                              <button
                                className="post-image-nav post-image-nav-next"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setPostImageIndex(prev => ({
                                    ...prev,
                                    [post.id]: currentIndex < images.length - 1 ? currentIndex + 1 : 0
                                  }));
                                }}
                              >
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                                  <path d="M9 18L15 12L9 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                              </button>
                            </>
                          )}
                        </>
                      );
                    })()}
                  </div>
                )}
                <div className="post-content">
                  <div className="post-title">{post.title}</div>
                  <div className="post-text">{post.text}</div>
                </div>
                <div className="post-actions">
                  <button
                    className={`post-action ${post.is_liked ? 'liked' : ''}`}
                    onClick={() => handleLike(post.id)}
                  >
                    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                      <path d="M10 17.5C10 17.5 3.125 12.5 3.125 7.1875C3.125 4.375 5.3125 2.5 7.8125 2.5C9.0625 2.5 10.1875 3.0625 10.9375 3.9375C11.6875 3.0625 12.8125 2.5 14.0625 2.5C16.5625 2.5 18.75 4.375 18.75 7.1875C18.75 12.5 11.875 17.5 10.9375 17.5C10.5625 17.5 10 17.5 10 17.5Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill={post.is_liked ? 'currentColor' : 'none'} />
                    </svg>
                    <span>{post.likes_count || 0}</span>
                  </button>
                  <button className="post-action" onClick={() => handleOpenComments(post.id)}>
                    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                      <path d="M17.5 9.58333C17.5 13.95 13.8667 17.5 9.58333 17.5C8.5 17.5 7.46667 17.2667 6.53333 16.85L2.5 18.3333L4.01667 14.3167C3.11667 13.2167 2.5 11.85 2.5 10.3333C2.5 6.01667 6.11667 2.5 10.5 2.5C14.8833 2.5 17.5 6.01667 17.5 9.58333Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <span>{post.comments_count || 0}</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
        {showCreatePostModal && (
          <div className="modal-backdrop" onClick={() => setShowCreatePostModal(false)}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <div className="modal-title">{t('community.modal.title')}</div>
                <button className="modal-close" onClick={() => setShowCreatePostModal(false)}>✕</button>
              </div>
              <div className="modal-body">
                <div className="form form-section">
                  <label>{t('community.modal.textLabel')}</label>
                  <textarea
                    className="textarea"
                    rows="6"
                    value={postText}
                    onChange={(e) => setPostText(e.target.value)}
                    placeholder={t('community.modal.textPlaceholder')}
                  />
                </div>
                <div className="form form-section">
                  <label>{t('community.modal.photosLabel')}</label>
                  <div className="upload-hint">
                    {t('community.modal.photosHint')}
                  </div>
                  <div className="upload-box" onClick={() => postPhotoInputRef.current?.click()}>
                    <div className="upload-label">{t('community.modal.uploadButton')}</div>
                    <div className="upload-sub">{t('community.modal.uploadSub')}</div>
                    <input
                      ref={postPhotoInputRef}
                      className="file-input-hidden"
                      type="file"
                      multiple
                      accept="image/jpeg,image/jpg,image/png,image/gif"
                      onChange={(e) => {
                        const files = Array.from(e.target.files || []);
                        if (!files.length) return;
                        const limit = 5;
                        const next = [...postPhotos];
                        files.slice(0, limit - next.length).forEach((file) => {
                          if (file.type.startsWith('image/')) {
                            const reader = new FileReader();
                            reader.onload = (ev) => {
                              const updated = [...next, { url: ev.target?.result, name: file.name }];
                              setPostPhotos(updated.slice(0, limit));
                            };
                            reader.readAsDataURL(file);
                          }
                        });
                        e.target.value = '';
                      }}
                    />
                  </div>
                  {postPhotos.length > 0 && (
                    <div className="file-preview-grid">
                      {postPhotos.map((photo, idx) => (
                        <div key={idx} className="file-preview">
                          <div className="file-thumb">
                            <img src={photo.url} alt={photo.name} />
                            <button
                              className="file-remove"
                              onClick={() => handleRemovePhoto(idx)}
                              type="button"
                            >
                              ✕
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              <div className="modal-footer">
                <button className="btn ghost" onClick={() => setShowCreatePostModal(false)}>
                  {t('community.modal.cancel')}
                </button>
                <button
                  className="btn primary"
                  onClick={handleCreatePost}
                  disabled={!postText.trim() && postPhotos.length === 0}
                >
                  {t('community.modal.publish')}
                </button>
              </div>
            </div>
          </div>
        )}
        {showCommentsModal && selectedPostId && (
          <div className="modal-backdrop" onClick={() => setShowCommentsModal(false)}>
            <div className="modal comments-modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <div className="modal-title">{t('community.comments.title')}</div>
                <button className="modal-close" onClick={() => setShowCommentsModal(false)}>✕</button>
              </div>
              <div className="modal-body comments-body">
                <div className="comments-list">
                  {commentsLoading ? (
                    <div style={{ textAlign: 'center', padding: '30px', color: 'var(--muted)' }}>
                      Загрузка комментариев...
                    </div>
                  ) : commentsData.length > 0 ? (
                    commentsData.map((comment) => (
                      <div key={comment.id} className="comment-item">
                        <div className="comment-author">
                          <div className="avatar small">
                            {(comment.user_name || 'П').substring(0, 2).toUpperCase()}
                          </div>
                          <div className="comment-info">
                            <div className="comment-author-name">{comment.user_name || 'Пользователь'}</div>
                            <div className="comment-date">{formatDate(comment.created_at)}</div>
                          </div>
                        </div>
                        <div className="comment-text">{comment.text}</div>
                      </div>
                    ))
                  ) : (
                    <div className="comments-empty">{t('community.comments.empty')}</div>
                  )}
                </div>
                <div className="comment-form">
                  <textarea
                    className="textarea"
                    rows="3"
                    value={commentText}
                    onChange={(e) => setCommentText(e.target.value)}
                    placeholder={t('community.comments.placeholder')}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                        handleAddComment();
                      }
                    }}
                  />
                  <button
                    className="btn primary"
                    onClick={handleAddComment}
                    disabled={!commentText.trim()}
                  >
                    {t('community.comments.send')}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {editingPostId && (
          <div className="modal-backdrop" onClick={handleCancelEdit}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <div className="modal-title">{t('community.editModal.title')}</div>
                <button className="modal-close" onClick={handleCancelEdit}>✕</button>
              </div>
              <div className="modal-body">
                <div className="form form-section">
                  <label>{t('community.modal.textLabel')}</label>
                  <textarea
                    className="textarea"
                    rows="6"
                    value={editPostText}
                    onChange={(e) => setEditPostText(e.target.value)}
                    placeholder={t('community.modal.textPlaceholder')}
                  />
                </div>
                <div className="form form-section">
                  <label>{t('community.modal.photosLabel')}</label>
                  <div className="upload-hint">
                    {t('community.modal.photosHint')}
                  </div>
                  <div className="upload-box" onClick={() => editPhotoInputRef.current?.click()}>
                    <div className="upload-label">{t('community.modal.uploadButton')}</div>
                    <div className="upload-sub">{t('community.modal.uploadSub')}</div>
                    <input
                      ref={editPhotoInputRef}
                      className="file-input-hidden"
                      type="file"
                      multiple
                      accept="image/jpeg,image/jpg,image/png,image/gif"
                      onChange={(e) => {
                        const files = Array.from(e.target.files || []);
                        if (!files.length) return;
                        const limit = 5;
                        const next = [...editPostPhotos];
                        files.slice(0, limit - next.length).forEach((file) => {
                          if (file.type.startsWith('image/')) {
                            const reader = new FileReader();
                            reader.onload = (ev) => {
                              const updated = [...next, { url: ev.target?.result, name: file.name }];
                              setEditPostPhotos(updated.slice(0, limit));
                            };
                            reader.readAsDataURL(file);
                          }
                        });
                        e.target.value = '';
                      }}
                    />
                  </div>
                  {editPostPhotos.length > 0 && (
                    <div className="file-preview-grid">
                      {editPostPhotos.map((photo, idx) => (
                        <div key={idx} className="file-preview">
                          <div className="file-thumb">
                            <img src={photo.url} alt={photo.name} />
                            <button
                              className="file-remove"
                              onClick={() => handleRemoveEditPhoto(idx)}
                              type="button"
                            >
                              ✕
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              <div className="modal-footer">
                <button className="btn ghost" onClick={handleCancelEdit}>
                  {t('community.modal.cancel')}
                </button>
                <button
                  className="btn primary"
                  onClick={handleSaveEditPost}
                  disabled={!editPostText.trim() && editPostPhotos.length === 0}
                >
                  {t('community.editModal.save')}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  if (tab === 'top') {
    const topOptions = [
      { title: t('top.forever'), badge: t('top.untilClose'), price: '∞', position: '1' },
      { title: t('top.hours24'), badge: t('top.secondPosition'), price: '150 ₽', position: '2' },
      { title: t('top.week'), badge: t('top.thirdPosition'), price: '490 ₽', position: '3' }
    ];

    return (
      <div className="grid three">
        {topOptions.map((item) => (
          <div key={item.title} className="top-card">
            <div className="top-badge">{item.badge}</div>
            <div className="top-title">{item.title}</div>
            <div className="top-price">{item.price}</div>
            <div className="top-position">{t('top.position')}: {item.position}</div>
            <button className="btn primary full">{t('top.select')}</button>
          </div>
        ))}
      </div>
    );
  }

  if (tab === 'messages') {

    const handleAcceptOffer = async (offerId) => {
      try {
        await apiClient.post(`/offers/${offerId}/accept`);
        alert('✅ Предложение принято!');
        // Обновляем список сообщений
        const response = await apiClient.get('/messages');
        setMessages(response.data || []);
        // Обновляем переписку если открыта
        if (selectedConversation) {
          const convResponse = await apiClient.get(`/messages/conversation/${selectedConversation.userId}`);
          setConversationMessages(convResponse.data || []);
        }
        // Обновляем список проектов если открыта вкладка "Проекты"
        if (tab === 'projects') {
          try {
            const projectsResponse = await apiClient.get('/orders/my');
            setCustomerProjects(projectsResponse.data.items || []);
          } catch (err) {
            console.error('Error refreshing projects:', err);
          }
        }
        // Обновляем список заказов если открыта вкладка "Мои заказы"
        if (tab === 'myOrders' && fetchMyOrders) {
          fetchMyOrders();
        }
      } catch (error) {
        console.error('Error accepting offer:', error);
        const errorMessage = error.response?.data?.detail || error.response?.data?.message || 'Ошибка при принятии предложения';
        alert(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
      }
    };

    const handleRejectOffer = async (offerId) => {
      try {
        await apiClient.post(`/offers/${offerId}/reject`);
        alert('Предложение отклонено');
        // Обновляем список сообщений
        const response = await apiClient.get('/messages');
        setMessages(response.data || []);
        // Обновляем переписку если открыта
        if (selectedConversation) {
          const convResponse = await apiClient.get(`/messages/conversation/${selectedConversation.userId}`);
          setConversationMessages(convResponse.data || []);
        }
      } catch (error) {
        console.error('Error rejecting offer:', error);
        const errorMessage = error.response?.data?.detail || error.response?.data?.message || 'Ошибка при отклонении предложения';
        alert(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
      }
    };

    const handleAcceptOrderByExecutor = async (offerId) => {
      try {
        await apiClient.post(`/offers/${offerId}/accept-by-executor`);
        alert('✅ Заказ принят и запущен в работу!');
        // Обновляем список сообщений
        const response = await apiClient.get('/messages');
        setMessages(response.data || []);
        // Обновляем переписку если открыта
        if (selectedConversation) {
          const convResponse = await apiClient.get(`/messages/conversation/${selectedConversation.userId}`);
          setConversationMessages(convResponse.data || []);
        }
        // Обновляем список заказов если открыта вкладка "Мои заказы"
        if (tab === 'myOrders' && fetchMyOrders) {
          fetchMyOrders();
        }
        // Обновляем список проектов если открыта вкладка "Проекты"
        if (tab === 'projects') {
          try {
            const projectsResponse = await apiClient.get('/orders/my');
            setCustomerProjects(projectsResponse.data.items || []);
          } catch (err) {
            console.error('Error refreshing projects:', err);
          }
        }
      } catch (error) {
        console.error('Error accepting order:', error);
        const errorMessage = error.response?.data?.detail || error.response?.data?.message || 'Ошибка при принятии заказа';
        alert(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
      }
    };

    const handleRejectOfferByExecutor = async (offerId) => {
      try {
        const reason = prompt('Укажите причину отказа (необязательно):');
        await apiClient.post(`/offers/${offerId}/reject-by-executor`, { reason: reason || null });
        alert('Вы отказались от заказа');
        // Обновляем список сообщений
        const response = await apiClient.get('/messages');
        setMessages(response.data || []);
        // Обновляем переписку если открыта
        if (selectedConversation) {
          const convResponse = await apiClient.get(`/messages/conversation/${selectedConversation.userId}`);
          setConversationMessages(convResponse.data || []);
        }
      } catch (error) {
        console.error('Error rejecting offer by executor:', error);
        alert(error.response?.data?.detail || 'Ошибка при отказе от заказа');
      }
    };

    // Функция для получения статуса оффера с иконкой
    const getOfferStatusIcon = (status) => {
      if (!status) return '';
      const statusLower = status.toLowerCase();
      if (statusLower === 'pending') return '🟡';
      if (statusLower === 'accepted') return '✅';
      if (statusLower === 'rejected') return '❌';
      if (statusLower === 'withdrawn') return '⚠️';
      return '';
    };

    const getOfferStatusText = (status) => {
      if (!status) return '';
      const statusLower = status.toLowerCase();
      if (statusLower === 'pending') return 'Ожидает рассмотрения';
      if (statusLower === 'accepted') return 'Одобрен, ожидает подтверждения исполнителя';
      if (statusLower === 'rejected') return 'Отклонен заказчиком';
      if (statusLower === 'withdrawn') return 'Исполнитель отказался после одобрения';
      return '';
    };


    const handleSendMessage = async () => {
      if (!newMessageText.trim() || !selectedConversation) return;

      const messageText = newMessageText.trim();
      const tempId = `temp-${Date.now()}`;

      // Создаем временное сообщение для оптимистичного обновления UI
      const tempMessage = {
        id: tempId,
        from_user_id: currentUser?.id,
        to_user_id: selectedConversation.userId,
        message_type: 'text',
        title: 'Сообщение',
        content: messageText,
        is_read: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        from_user_name: currentUser?.name || '',
        to_user_name: selectedConversation.userName || ''
      };

      // Сразу показываем сообщение в UI (оптимистичное обновление)
      setNewMessageText('');
      setMessages(prev => [tempMessage, ...prev]);
      setConversationMessages(prev => [...prev, tempMessage]);

      // Прокручиваем вниз мгновенно после добавления временного сообщения
      // Используем requestAnimationFrame для гарантии что DOM обновлен
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          if (messagesContainerRef.current) {
            messagesContainerRef.current.scrollTo({
              top: messagesContainerRef.current.scrollHeight,
              behavior: 'smooth'
            });
          }
        });
      });

      try {
        const response = await apiClient.post('/messages', {
          to_user_id: selectedConversation.userId,
          message_type: 'text',
          title: 'Сообщение',
          content: messageText
        });

        // Заменяем временное сообщение на реальное
        const newMessage = response.data;
        setMessages(prev => {
          // Удаляем временное сообщение и добавляем реальное
          const filtered = prev.filter(m => m.id !== tempId);
          const exists = filtered.some(m => m.id === newMessage.id);
          if (exists) {
            return filtered;
          }
          return [newMessage, ...filtered].sort((a, b) =>
            new Date(b.created_at) - new Date(a.created_at)
          );
        });

        // Обновляем переписку
        setConversationMessages(prev => {
          const filtered = prev.filter(m => m.id !== tempId);
          const exists = filtered.some(m => m.id === newMessage.id);
          if (exists) {
            return filtered;
          }
          const updated = [...filtered, newMessage].sort((a, b) =>
            new Date(a.created_at) - new Date(b.created_at)
          );
          // Возвращаем обновленные сообщения - прокрутка произойдет через useEffect
          return updated;
        });
      } catch (error) {
        console.error('Error sending message:', error);
        // Удаляем временное сообщение при ошибке
        setMessages(prev => prev.filter(m => m.id !== tempId));
        setConversationMessages(prev => prev.filter(m => m.id !== tempId));
        alert(error.response?.data?.detail || 'Ошибка при отправке сообщения');
      }
    };

    // Группируем сообщения по пользователям для списка чатов
    const conversationsMap = new Map();
    messages.forEach(msg => {
      const otherUserId = msg.from_user_id === currentUser?.id ? msg.to_user_id : msg.from_user_id;
      const otherUserName = msg.from_user_id === currentUser?.id ? msg.to_user_name : msg.from_user_name;

      if (!conversationsMap.has(otherUserId)) {
        conversationsMap.set(otherUserId, {
          userId: otherUserId,
          userName: otherUserName,
          lastMessage: msg,
          unreadCount: messages.filter(m =>
            m.to_user_id === currentUser?.id &&
            m.from_user_id === otherUserId &&
            !m.is_read
          ).length
        });
      } else {
        const conv = conversationsMap.get(otherUserId);
        if (new Date(msg.created_at) > new Date(conv.lastMessage.created_at)) {
          conv.lastMessage = msg;
        }
      }
    });

    const conversations = Array.from(conversationsMap.values()).sort((a, b) =>
      new Date(b.lastMessage.created_at) - new Date(a.lastMessage.created_at)
    );

    // Убираем общий список сообщений - показываем только в диалоге

    if (!currentUser) {
      return (
        <div className="card">
          <div className="card-body">
            <p>Необходимо войти в систему</p>
          </div>
        </div>
      );
    }

    return (
      <div style={{ display: 'flex', gap: '16px', height: '600px' }}>
        {/* Левая панель - список чатов */}
        <div style={{
          width: '300px',
          border: '1px solid var(--stroke)',
          borderRadius: '12px',
          background: 'var(--card-2)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}>
          <div style={{
            padding: '16px',
            borderBottom: '1px solid var(--stroke)',
            fontWeight: '600',
            fontSize: '16px'
          }}>
            Диалоги ({conversations.length})
          </div>
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {messagesLoading ? (
              <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--muted)' }}>
                <p>Загрузка...</p>
              </div>
            ) : conversations.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--muted)' }}>
                <div style={{ fontSize: '32px', marginBottom: '12px' }}>📬</div>
                <p>Нет диалогов</p>
              </div>
            ) : (
              conversations.map((conv) => (
                <div
                  key={conv.userId}
                  onClick={() => {
                    setSelectedConversation(conv);
                    setConversationMessages([]);
                  }}
                  style={{
                    padding: '12px 16px',
                    borderBottom: '1px solid var(--stroke)',
                    cursor: 'pointer',
                    background: selectedConversation?.userId === conv.userId ? 'var(--accent)' : 'transparent',
                    color: selectedConversation?.userId === conv.userId ? '#fff' : 'var(--text)',
                    transition: 'all 0.2s'
                  }}
                  onMouseEnter={(e) => {
                    if (selectedConversation?.userId !== conv.userId) {
                      e.currentTarget.style.background = 'var(--card)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (selectedConversation?.userId !== conv.userId) {
                      e.currentTarget.style.background = 'transparent';
                    }
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontWeight: '600', fontSize: '14px' }}>{conv.userName}</div>
                    {conv.unreadCount > 0 && (
                      <span style={{
                        background: selectedConversation?.userId === conv.userId ? '#fff' : 'var(--accent)',
                        color: selectedConversation?.userId === conv.userId ? 'var(--accent)' : '#fff',
                        borderRadius: '12px',
                        padding: '2px 8px',
                        fontSize: '12px',
                        fontWeight: '600'
                      }}>
                        {conv.unreadCount}
                      </span>
                    )}
                  </div>
                  <div style={{
                    fontSize: '12px',
                    color: selectedConversation?.userId === conv.userId ? 'rgba(255,255,255,0.8)' : 'var(--muted)',
                    marginTop: '4px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap'
                  }}>
                    {conv.lastMessage.title || conv.lastMessage.content?.substring(0, 30) || 'Сообщение'}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Правая панель - сообщения */}
        <div style={{
          flex: 1,
          border: '1px solid var(--stroke)',
          borderRadius: '12px',
          background: 'var(--card-2)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}>
          {selectedConversation ? (
            <>
              <div style={{
                padding: '16px',
                borderBottom: '1px solid var(--stroke)',
                fontWeight: '600',
                fontSize: '16px'
              }}>
                {selectedConversation.userName}
              </div>
              <div
                ref={messagesContainerRef}
                onScroll={() => {
                  // Отслеживаем, прокрутил ли пользователь вверх
                  if (messagesContainerRef.current) {
                    const container = messagesContainerRef.current;
                    const threshold = 150; // Порог в пикселях от низа
                    const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight < threshold;
                    isUserScrolledUpRef.current = !isAtBottom;
                  }
                }}
                style={{ flex: 1, overflowY: 'auto', padding: '16px' }}
              >
                {conversationLoading ? (
                  <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--muted)' }}>
                    <p>Загрузка переписки...</p>
                  </div>
                ) : conversationMessages.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--muted)' }}>
                    <p>Нет сообщений. Начните переписку!</p>
                  </div>
                ) : (
                  <div className="messages-list">
                    {/* Кнопка догрузки старых сообщений */}
                    {hasMoreMessages && (
                      <div style={{ textAlign: 'center', marginBottom: '12px' }}>
                        <button
                          className="btn ghost xsmall"
                          disabled={loadingMoreMessages}
                          onClick={async () => {
                            if (!selectedConversation || !oldestMessageId) return;
                            try {
                              setLoadingMoreMessages(true);
                              const res = await apiClient.get(
                                `/messages/conversation/${selectedConversation.userId}`,
                                {
                                  params: {
                                    limit: MESSAGES_PAGE_SIZE,
                                    before_id: oldestMessageId,
                                  },
                                }
                              );
                              const older = Array.isArray(res.data)
                                ? res.data
                                : [];
                              if (older.length > 0) {
                                setConversationMessages((prev) => [
                                  ...older,
                                  ...prev,
                                ]);
                                setOldestMessageId(older[0].id);
                                setHasMoreMessages(
                                  older.length === MESSAGES_PAGE_SIZE
                                );
                              } else {
                                setHasMoreMessages(false);
                              }
                            } catch (error) {
                              console.error(
                                'Error loading older messages:',
                                error
                              );
                            } finally {
                              setLoadingMoreMessages(false);
                            }
                          }}
                        >
                          {loadingMoreMessages
                            ? 'Загрузка...'
                            : 'Показать предыдущие сообщения'}
                        </button>
                      </div>
                    )}
                    {conversationMessages.map((msg) => {
                      const isOfferCreated = msg.message_type === 'OFFER_CREATED' || msg.message_type === 'offer_created';
                      const isOfferAccepted = msg.message_type === 'OFFER_ACCEPTED' || msg.message_type === 'offer_accepted';
                      const isOfferRejected = msg.message_type === 'OFFER_REJECTED' || msg.message_type === 'offer_rejected';
                      const isOfferWithdrawn = msg.message_type === 'OFFER_WITHDRAWN' || msg.message_type === 'offer_withdrawn';
                      const isTextMessage = msg.message_type === 'TEXT' || msg.message_type === 'text';
                      const offerData = msg.offer_data;
                      const orderData = msg.order_data;
                      const projectTitle = orderData?.title || 'Проект';
                      const offerStatusLower = (offerData?.status || '').toString().toLowerCase();
                      const orderStatusLower = (orderData?.status || '').toString().toLowerCase();
                      const isOrderInProgressOrDone =
                        orderStatusLower === 'in_progress' ||
                        orderStatusLower === 'completed' ||
                        orderStatusLower === 'cancelled';
                      const isCustomer = currentUser?.role === 'customer' || currentUser?.role === 'CUSTOMER';
                      const isExecutor = currentUser?.role === 'executor' || currentUser?.role === 'EXECUTOR';
                      const isFromMe = msg.from_user_id === currentUser?.id;

                      return (
                        <div key={msg.id} style={{
                          marginBottom: '16px',
                          display: 'flex',
                          justifyContent: isFromMe ? 'flex-end' : 'flex-start'
                        }}>
                          <div style={{
                            maxWidth: '70%',
                            padding: '12px 16px',
                            borderRadius: '12px',
                            background: isFromMe ? 'var(--accent)' : 'var(--card)',
                            color: isFromMe ? '#fff' : 'var(--text)',
                            border: isOfferCreated ? '1px solid var(--stroke)' : 'none'
                          }}>
                            {isOfferCreated && (
                              <>
                                <div style={{
                                  marginBottom: '8px',
                                  fontWeight: '600',
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '8px'
                                }}>
                                  <span>🟡</span>
                                  <span>{msg.title}</span>
                                  {offerData && (
                                    <span style={{
                                      fontSize: '11px',
                                      fontWeight: 'normal',
                                      opacity: 0.8,
                                      marginLeft: 'auto'
                                    }}>
                                      {offerData.status === 'pending' || offerData.status === 'PENDING' ? 'Ожидает рассмотрения' :
                                        offerData.status === 'accepted' || offerData.status === 'ACCEPTED' ? '✅ Одобрен' :
                                          offerData.status === 'rejected' || offerData.status === 'REJECTED' ? '❌ Отклонен' :
                                            offerData.status === 'withdrawn' || offerData.status === 'WITHDRAWN' ? '⚠️ Отозван' : ''}
                                    </span>
                                  )}
                                </div>
                                <div style={{
                                  fontSize: '14px',
                                  whiteSpace: 'pre-line',
                                  wordBreak: 'break-word',
                                  overflowWrap: 'anywhere',
                                  marginBottom: '12px',
                                  borderTop: '1px solid rgba(255,255,255,0.1)',
                                  paddingTop: '12px',
                                  marginTop: '8px'
                                }}>
                                  {msg.content}
                                </div>
                                {/* Кнопки действий для заказчика при получении предложения */}
                                {(() => {
                                  // Определяем заказчика: либо по роли, либо если сообщение адресовано ему и это предложение
                                  const isMessageForCustomer = msg.to_user_id === currentUser?.id;
                                  const isActuallyCustomer = isCustomer || (isOfferCreated && isMessageForCustomer && !isFromMe);
                                  const offerStatus = offerData?.status;
                                  const isPending = !offerStatus || offerStatus === 'pending' || offerStatus === 'PENDING';
                                  const hasOfferId = !!msg.offer_id;

                                  // Отладочная информация
                                  console.log('🔍 ДЕТАЛЬНАЯ ПРОВЕРКА КНОПОК:', {
                                    isCustomer,
                                    isActuallyCustomer,
                                    isOfferCreated,
                                    isFromMe,
                                    isMessageForCustomer,
                                    offerStatus,
                                    isPending,
                                    hasOfferId,
                                    msgToUserId: msg.to_user_id,
                                    currentUserId: currentUser?.id,
                                    currentUserRole: currentUser?.role,
                                    msgFromUserId: msg.from_user_id,
                                    offerData,
                                    msgOfferId: msg.offer_id,
                                    messageType: msg.message_type
                                  });

                                  // Показываем кнопки если: это предложение, сообщение адресовано заказчику (не от него), есть ID, статус pending
                                  const shouldShow = isOfferCreated && isMessageForCustomer && !isFromMe && hasOfferId && isPending;

                                  if (shouldShow) {
                                    return (
                                      <div style={{
                                        display: 'flex',
                                        gap: '10px',
                                        marginTop: '16px',
                                        flexWrap: 'wrap',
                                        padding: '12px',
                                        background: 'rgba(0,0,0,0.02)',
                                        borderRadius: '8px',
                                        border: '1px solid var(--stroke)'
                                      }}>
                                        <button
                                          className="btn primary"
                                          onClick={() => {
                                            console.log('✅ Одобрить предложение', { offerId: msg.offer_id });
                                            if (msg.offer_id) {
                                              handleAcceptOffer(msg.offer_id);
                                            } else {
                                              alert('Ошибка: ID предложения не найден');
                                            }
                                          }}
                                          style={{
                                            fontSize: '15px',
                                            padding: '12px 24px',
                                            background: 'var(--accent)',
                                            border: 'none',
                                            color: '#fff',
                                            borderRadius: '8px',
                                            cursor: 'pointer',
                                            fontWeight: '600',
                                            minWidth: '140px',
                                            boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                                          }}
                                        >
                                          ✅ Одобрить
                                        </button>
                                        <button
                                          className="btn ghost"
                                          onClick={() => {
                                            console.log('❌ Отклонить предложение', { offerId: msg.offer_id });
                                            if (msg.offer_id) {
                                              handleRejectOffer(msg.offer_id);
                                            } else {
                                              alert('Ошибка: ID предложения не найден');
                                            }
                                          }}
                                          style={{
                                            fontSize: '15px',
                                            padding: '12px 24px',
                                            borderRadius: '8px',
                                            cursor: 'pointer',
                                            fontWeight: '600',
                                            border: '2px solid var(--stroke)',
                                            minWidth: '140px',
                                            background: '#fff'
                                          }}
                                        >
                                          ❌ Отказать
                                        </button>
                                        {/* Кнопка "Написать сообщение" только для заказчика, не для исполнителя */}
                                        {isCustomer && (
                                          <button
                                            className="btn ghost"
                                            onClick={() => {
                                              const executorId = msg.from_user_id;
                                              const executorName = msg.from_user_name || 'Исполнитель';
                                              setSelectedConversation({ userId: executorId, userName: executorName });
                                            }}
                                            style={{
                                              fontSize: '14px',
                                              padding: '12px 20px',
                                              borderRadius: '8px',
                                              cursor: 'pointer',
                                              border: '1px solid var(--stroke)',
                                              background: '#fff'
                                            }}
                                          >
                                            💬 Написать сообщение
                                          </button>
                                        )}
                                      </div>
                                    );
                                  } else {
                                    // Если кнопки не показываются, выводим причину
                                    console.warn('⚠️ КНОПКИ НЕ ОТОБРАЖАЮТСЯ. Причины:', {
                                      isOfferCreated: isOfferCreated ? '✅' : '❌',
                                      isMessageForCustomer: isMessageForCustomer ? '✅' : '❌',
                                      isFromMe: isFromMe ? '❌ (сообщение от пользователя)' : '✅',
                                      hasOfferId: hasOfferId ? '✅' : '❌',
                                      isPending: isPending ? '✅' : '❌',
                                      offerStatus: offerStatus || 'не определен',
                                      shouldShow: shouldShow ? '✅' : '❌'
                                    });
                                  }
                                  return null;
                                })()}
                              </>
                            )}
                            {isOfferAccepted && (
                              <>
                                <div
                                  style={{
                                    marginBottom: '8px',
                                    fontWeight: '600',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                  }}
                                >
                                  <span>✅</span>
                                  <span>{msg.title}</span>
                                  {offerData && (
                                    <span
                                      style={{
                                        fontSize: '11px',
                                        fontWeight: 'normal',
                                        opacity: 0.8,
                                        marginLeft: 'auto',
                                      }}
                                    >
                                      {orderStatusLower === 'in_progress'
                                        ? 'Заказ в работе'
                                        : offerStatusLower === 'accepted'
                                          ? 'Одобрен, ожидает подтверждения исполнителя'
                                          : ''}
                                    </span>
                                  )}
                                </div>
                                <div style={{
                                  fontSize: '14px',
                                  whiteSpace: 'pre-line',
                                  marginBottom: '12px',
                                  borderTop: '1px solid rgba(255,255,255,0.1)',
                                  paddingTop: '12px',
                                  marginTop: '8px'
                                }}>
                                  {msg.content}
                                </div>
                                {/* Кнопки "Принять заказ" и "Отказаться" ТОЛЬКО для исполнителя, НЕ для заказчика.
                                    Не показываем их, если заказ уже в работе/завершен, чтобы не было повторного принятия. */}
                                {isExecutor &&
                                  !isCustomer &&
                                  offerData &&
                                  offerStatusLower === 'accepted' &&
                                  !isOrderInProgressOrDone &&
                                  msg.to_user_id === currentUser?.id && (
                                    <div style={{ display: 'flex', gap: '8px', marginTop: '12px', flexWrap: 'wrap' }}>
                                      <button
                                        className="btn primary small"
                                        onClick={() => {
                                          if (msg.offer_id) {
                                            handleAcceptOrderByExecutor(msg.offer_id);
                                          } else {
                                            alert('Ошибка: ID предложения не найден');
                                          }
                                        }}
                                        style={{ fontSize: '12px', padding: '6px 12px', background: 'var(--accent)', border: 'none', color: '#fff' }}
                                      >
                                        Принять заказ
                                      </button>
                                      <button
                                        className="btn ghost small"
                                        onClick={() => {
                                          if (msg.offer_id) {
                                            handleRejectOfferByExecutor(msg.offer_id);
                                          } else {
                                            alert('Ошибка: ID предложения не найден');
                                          }
                                        }}
                                        style={{ fontSize: '12px', padding: '6px 12px' }}
                                      >
                                        Отказаться
                                      </button>
                                    </div>
                                  )}
                              </>
                            )}
                            {isOfferRejected && (
                              <>
                                <div style={{
                                  marginBottom: '8px',
                                  fontWeight: '600',
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '8px'
                                }}>
                                  <span>❌</span>
                                  <span>{msg.title}</span>
                                  <span style={{
                                    fontSize: '11px',
                                    fontWeight: 'normal',
                                    opacity: 0.8,
                                    marginLeft: 'auto'
                                  }}>
                                    Отклонен заказчиком
                                  </span>
                                </div>
                                <div style={{
                                  fontSize: '14px',
                                  whiteSpace: 'pre-line',
                                  borderTop: '1px solid rgba(255,255,255,0.1)',
                                  paddingTop: '12px',
                                  marginTop: '8px'
                                }}>
                                  {msg.content}
                                </div>
                              </>
                            )}
                            {isOfferWithdrawn && (
                              <>
                                <div style={{
                                  marginBottom: '8px',
                                  fontWeight: '600',
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '8px'
                                }}>
                                  <span>⚠️</span>
                                  <span>{msg.title}</span>
                                  <span style={{
                                    fontSize: '11px',
                                    fontWeight: 'normal',
                                    opacity: 0.8,
                                    marginLeft: 'auto'
                                  }}>
                                    Исполнитель отказался после одобрения
                                  </span>
                                </div>
                                <div style={{
                                  fontSize: '14px',
                                  whiteSpace: 'pre-line',
                                  borderTop: '1px solid rgba(255,255,255,0.1)',
                                  paddingTop: '12px',
                                  marginTop: '8px'
                                }}>
                                  {msg.content}
                                </div>
                              </>
                            )}
                            {isTextMessage && (
                              <div
                                style={{
                                  fontSize: '14px',
                                  whiteSpace: 'pre-wrap',
                                  wordBreak: 'break-word',
                                  overflowWrap: 'anywhere',
                                }}
                              >
                                {msg.content || msg.title}
                              </div>
                            )}
                            {!isOfferCreated && !isOfferAccepted && !isOfferRejected && !isOfferWithdrawn && !isTextMessage && (
                              <div
                                style={{
                                  wordBreak: 'break-word',
                                  overflowWrap: 'anywhere',
                                }}
                              >
                                {msg.content || msg.title}
                              </div>
                            )}
                            <div style={{
                              fontSize: '11px',
                              marginTop: '8px',
                              opacity: 0.7
                            }}>
                              {new Date(msg.created_at).toLocaleString('ru-RU')}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
              {/* Поле для ввода сообщения */}
              <div style={{
                padding: '16px',
                borderTop: '1px solid var(--stroke)',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}>
                {/* Кнопки для прямых предложений */}
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {(currentUser?.role === 'customer' || currentUser?.role === 'CUSTOMER') && selectedConversation && (
                    <button
                      className="btn ghost small"
                      onClick={() => {
                        // Устанавливаем получателя для прямого предложения
                        setDirectOfferRecipient({ userId: selectedConversation.userId, userName: selectedConversation.userName });
                        setShowOfferModal(true);
                      }}
                      style={{ fontSize: '12px', padding: '6px 12px' }}
                    >
                      Предложить заказ
                    </button>
                  )}
                  {(currentUser?.role === 'executor' || currentUser?.role === 'EXECUTOR') && selectedConversation && (
                    <button
                      className="btn ghost small"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        console.log('Предложить свои услуги clicked', {
                          selectedConversation,
                          currentUser: currentUser?.role,
                          showOfferModal
                        });
                        // Устанавливаем получателя для прямого предложения
                        if (selectedConversation && selectedConversation.userId) {
                          setDirectOfferRecipient({
                            userId: selectedConversation.userId,
                            userName: selectedConversation.userName || 'Пользователь'
                          });
                          console.log('Setting directOfferRecipient and opening modal');
                          setShowOfferModal(true);
                          // Проверяем через небольшую задержку
                          setTimeout(() => {
                            console.log('Modal state after click:', showOfferModal);
                          }, 100);
                        } else {
                          console.error('selectedConversation is invalid:', selectedConversation);
                          alert('Ошибка: не выбран получатель');
                        }
                      }}
                      style={{ fontSize: '12px', padding: '6px 12px', cursor: 'pointer' }}
                    >
                      Предложить свои услуги
                    </button>
                  )}
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    type="text"
                    value={newMessageText}
                    onChange={(e) => setNewMessageText(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        if (newMessageText.trim()) {
                          handleSendMessage();
                        }
                      }
                    }}
                    placeholder="Написать сообщение..."
                    style={{
                      flex: 1,
                      padding: '10px 16px',
                      borderRadius: '8px',
                      border: '1px solid var(--stroke)',
                      background: 'var(--card)',
                      color: 'var(--text)',
                      fontSize: '14px'
                    }}
                  />
                  <button
                    className="btn primary"
                    onClick={handleSendMessage}
                    disabled={!newMessageText.trim()}
                    style={{ padding: '10px 20px' }}
                  >
                    Отправить
                  </button>
                </div>
              </div>
            </>
          ) : (
            <>
              <div style={{
                padding: '16px',
                borderBottom: '1px solid var(--stroke)',
                fontWeight: '600',
                fontSize: '16px'
              }}>
                Сообщения
              </div>
              <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div style={{ textAlign: 'center', color: 'var(--muted)' }}>
                  <div style={{ fontSize: '48px', marginBottom: '20px' }}>📬</div>
                  <h3 style={{ marginBottom: '12px' }}>Выберите диалог</h3>
                  <p>Выберите диалог слева, чтобы начать переписку</p>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    );
  }

  return null;
};

function App() {
  const { t, theme, toggleTheme, language, changeLanguage, isAuthenticated, login, logout, currentUser, loading: authLoading } = useApp();
  const navigate = useNavigate();
  const location = useLocation();
  const [langMenuOpen, setLangMenuOpen] = useState(false);
  const [showRegister, setShowRegister] = useState(false);
  const [showLogin, setShowLogin] = useState(false);
  const [showProfileSetup, setShowProfileSetup] = useState(false);
  const [showProfileEdit, setShowProfileEdit] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [showPortfolioModal, setShowPortfolioModal] = useState(false);
  const [portfolioForm, setPortfolioForm] = useState({
    title: '',
    category: 'Разработка и IT',
    subcategory: 'Создание сайта',
    type: '',
  });
  const [coverPreview, setCoverPreview] = useState(null);
  const [workFiles, setWorkFiles] = useState([]);
  const [categoryOpen, setCategoryOpen] = useState(false);
  const [subcategoryOpen, setSubcategoryOpen] = useState(false);
  const workInputRef = useRef(null);
  const coverInputRef = useRef(null);

  // Используем хуки для работы с API
  const { portfolioItems, addPortfolioItem, updatePortfolioItem, deletePortfolioItem, loading: portfolioLoading } = usePortfolio();
  const [communityFilter, setCommunityFilter] = useState('all');

  // Фильтры биржи — на уровне App, чтобы publicOrdersFilters мог их использовать
  const [budgetFrom, setBudgetFrom] = useState('');
  const [budgetTo, setBudgetTo] = useState('');
  const [keywords, setKeywords] = useState('');
  const [selectedOrdersSubcategories, setSelectedOrdersSubcategories] = useState({});
  const [selectedOrdersSubSubcategories, setSelectedOrdersSubSubcategories] = useState({});
  const [selectedBudgetRanges, setSelectedBudgetRanges] = useState([]);
  // hiredPercent и selectedOfferRanges — на уровне App, т.к. участвуют в API-запросе
  const [hiredPercent, setHiredPercent] = useState('');
  const [selectedOfferRanges, setSelectedOfferRanges] = useState([]);

  const { posts: communityPosts, createPost, updatePost, deletePost, toggleLike, addComment, fetchComments, loading: communityLoading } = useCommunity(communityFilter);

  const { notes: orderNotes, saveNote, getNote, fetchNote } = useNotes();

  // Получаем роль из currentUser (объявляем ДО использования в хуках)
  const dbUserRole = currentUser?.role?.value || currentUser?.role || 'executor';

  // Локальное состояние для режима просмотра (может отличаться от роли в БД)
  const [viewMode, setViewMode] = useState(() => {
    // Инициализируем из localStorage или используем роль из БД
    const saved = localStorage.getItem('viewMode');
    return saved || dbUserRole;
  });

  // userRole для отображения - используем viewMode (объявляем ДО использования в fetchMyOrders)
  const userRole = viewMode;

  // Используем useMemo для стабилизации объекта filters
  const myOrdersFilters = useMemo(() => ({ my: true }), []);
  const { orders: myOrders, fetchMyOrders: fetchMyOrdersBase, loading: myOrdersLoading } = useOrders(myOrdersFilters);

  // Обертка для fetchMyOrders с учетом роли пользователя
  const fetchMyOrders = useCallback(async (params = {}) => {
    const userRoleValue = userRole;
    console.log('📦 fetchMyOrders вызван с ролью:', userRoleValue);
    return fetchMyOrdersBase(params, userRoleValue);
  }, [userRole, fetchMyOrdersBase]);

  // Фильтры биржи — передаём реальные параметры в API
  const publicOrdersFilters = useMemo(() => {
    const params = { status: 'open' }; // По умолчанию только открытые заказы
    if (keywords && keywords.trim()) params.keywords = keywords.trim();
    if (budgetFrom && budgetFrom.trim()) params.budget_from = parseFloat(budgetFrom);
    if (budgetTo && budgetTo.trim()) params.budget_to = parseFloat(budgetTo);

    // === Категория: собираем ВСЕ ID из выбранной ветки иерархии ===
    const allSubIds = Object.values(selectedOrdersSubcategories).flat();
    const allSubSubIds = Object.values(selectedOrdersSubSubcategories).flat();
    const selectedCategoryIds = Object.keys(selectedOrdersSubcategories).filter(
      catId => (selectedOrdersSubcategories[catId] || []).length > 0
    );

    if (allSubIds.length > 0 || allSubSubIds.length > 0 || selectedCategoryIds.length > 0) {
      if (selectedCategoryIds.length > 0) {
        params.category_ids = selectedCategoryIds;
      }
      if (allSubIds.length > 0) {
        params.subcategory_ids = allSubIds;
      }
      if (allSubSubIds.length > 0) {
        params.subsubcategory_ids = allSubSubIds;
      }
    }

    // Фильтр по проценту найма заказчика
    const hiredVal = parseFloat(hiredPercent);
    if (!isNaN(hiredVal) && hiredVal > 0) params.min_hired_percent = hiredVal;

    // Фильтр по количеству откликов (берём диапазон из selectedOfferRanges)
    const offersRangeMap = {
      'up-to-5': { from: 0, to: 5 },
      '5to10': { from: 5, to: 10 },
      '10to15': { from: 10, to: 15 },
      '15to20': { from: 15, to: 20 },
      '20plus': { from: 20, to: null },
    };
    if (selectedOfferRanges.length > 0) {
      const froms = selectedOfferRanges.map(id => offersRangeMap[id]?.from).filter(v => v !== null && v !== undefined);
      const tos = selectedOfferRanges.map(id => offersRangeMap[id]?.to).filter(v => v !== null && v !== undefined);
      if (froms.length > 0) params.offers_count_from = Math.min(...froms);
      if (tos.length > 0) params.offers_count_to = Math.max(...tos);
    }

    return params;
  }, [keywords, budgetFrom, budgetTo, selectedOrdersSubcategories, selectedOrdersSubSubcategories, hiredPercent, selectedOfferRanges]);


  const { orders: publicOrders, loading: publicOrdersLoading, total } = useOrders(publicOrdersFilters);

  const [editingId, setEditingId] = useState(null);

  // Вычисляем activeTab на основе location.pathname (ДО использования в useEffect)
  const activeTab = useMemo(() => {
    const path = location.pathname.replace('/', '') || 'home';
    const validTabs = ['home', 'orders', 'community', 'myOrders', 'portfolio', 'messages', 'wallet', 'notifications', 'profile', 'projects'];
    return validTabs.includes(path) ? path : 'home';
  }, [location.pathname]);

  const setActiveTab = (tab) => {
    console.log('🔄 Переключение на вкладку:', tab);
    navigate(`/${tab}`);
    setMobileMenuOpen(false);
  };

  const toggleUserRole = () => {
    // Переключаем режим просмотра
    const newMode = viewMode === 'executor' || viewMode === 'EXECUTOR' ? 'customer' : 'executor';
    setViewMode(newMode);
    localStorage.setItem('viewMode', newMode);

    // Переключаемся на соответствующую вкладку
    if (newMode === 'customer' || newMode === 'CUSTOMER') {
      setActiveTab('projects');
    } else {
      setActiveTab('orders');
    }
  };

  // Синхронизируем viewMode с активной вкладкой при изменении пути
  useEffect(() => {
    if (activeTab === 'projects' && (viewMode === 'executor' || viewMode === 'EXECUTOR')) {
      setViewMode('customer');
      localStorage.setItem('viewMode', 'customer');
    } else if (activeTab === 'orders' && (viewMode === 'customer' || viewMode === 'CUSTOMER')) {
      setViewMode('executor');
      localStorage.setItem('viewMode', 'executor');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  const categories = useMemo(() => ({
    'Разработка и IT': ['Создание сайта', 'Верстка', 'Мобильные приложения', 'Игры'],
    'Дизайн': [
      'Логотип и брендинг',
      'Веб и мобильный дизайн',
      'Арт и иллюстрации',
      'Полиграфия',
      'Интерьер и экстерьер',
      'Промышленный дизайн',
      'ИИ-генерация изображений',
      'Презентации и инфографика',
      'Обработка и редактирование',
      'Наружная реклама',
      'Маркетплейсы и соцсети',
    ],
    'Тексты и переводы': ['Резюме и вакансии', 'Бизнес-тексты', 'Контент сайта', 'ИИ-тексты'],
    'Аудио, видео, съемка': ['Редактирование аудио', 'Видеосъемка', 'Видеоролики', 'Озвучка'],
    'Бизнес и жизнь': ['Персональный помощник', 'Менеджмент проектов'],
    'SEO и трафик': ['Статистика и аналитика', 'Анализ сайтов'],
  }), []);

  const handlePortfolioSave = async () => {
    if (!portfolioForm.title.trim()) return;

    try {
      const itemData = {
        title: portfolioForm.title.trim(),
        category: portfolioForm.category,
        subcategory: portfolioForm.subcategory,
        cover_image: coverPreview ? coverPreview.url : null,
        files: workFiles.map(f => f.url || f.path || f)
      };

      if (editingId) {
        await updatePortfolioItem(editingId, itemData);
      } else {
        await addPortfolioItem(itemData);
      }

      setShowPortfolioModal(false);
      setPortfolioForm({
        title: '',
        category: 'Разработка и IT',
        subcategory: 'Создание сайта',
        type: '',
      });
      setCoverPreview(null);
      setWorkFiles([]);
      setEditingId(null);
    } catch (error) {
      console.error('Error saving portfolio item:', error);
      alert('Ошибка при сохранении работы');
    }
  };

  const startAddWork = () => {
    setEditingId(null);
    setPortfolioForm({
      title: '',
      category: 'Разработка и IT',
      subcategory: 'Создание сайта',
      type: '',
    });
    setWorkFiles([]);
    setCoverPreview(null);
    setShowPortfolioModal(true);
  };

  const startEditWork = (id) => {
    const current = portfolioItems.find((p) => p.id === id);
    if (!current) return;
    setEditingId(id);
    setPortfolioForm({
      title: current.title || '',
      category: current.category || 'Разработка и IT',
      subcategory: current.subcategory || '',
      type: current.type || '',
    });
    setWorkFiles(current.media || []);
    setCoverPreview(current.cover ? { url: current.cover, name: 'Обложка' } : null);
    setShowPortfolioModal(true);
  };

  const startDeleteWork = async (id) => {
    if (!window.confirm('Удалить работу?')) return;
    try {
      await deletePortfolioItem(id);
    } catch (error) {
      console.error('Error deleting portfolio item:', error);
      alert('Ошибка при удалении работы');
    }
  };
  const langMenuRef = useRef(null);
  const mobileMenuRef = useRef(null);
  const burgerRef = useRef(null);

  // Редирект с корня на /home только один раз при монтировании
  useEffect(() => {
    if (location.pathname === '/') {
      navigate('/home', { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Запускаем только один раз при монтировании


  useEffect(() => {
    const handleClickOutside = (event) => {
      if (langMenuRef.current && !langMenuRef.current.contains(event.target)) {
        setLangMenuOpen(false);
      }
    };

    if (langMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [langMenuOpen]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      const navEl = mobileMenuRef.current;
      const burgerEl = burgerRef.current;
      if (!navEl) return;

      const clickInsideNav = navEl.contains(event.target);
      const clickOnBurger = burgerEl && burgerEl.contains(event.target);
      if (!clickInsideNav && !clickOnBurger) {
        setMobileMenuOpen(false);
      }
    };

    if (mobileMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [mobileMenuOpen]);

  const tabs = useMemo(() => {
    const baseTabs = [
      { id: 'home', label: t('nav.home') },
      { id: 'community', label: t('nav.community') },
      { id: 'messages', label: t('nav.messages') },
      { id: 'wallet', label: t('nav.wallet') },
      { id: 'notifications', label: t('nav.notifications') }
    ];

    if (userRole === 'executor') {
      return [
        baseTabs[0], // home
        { id: 'orders', label: t('nav.orders') },
        baseTabs[1], // community
        { id: 'myOrders', label: t('nav.myOrders') },
        { id: 'portfolio', label: t('nav.portfolio') },
        ...baseTabs.slice(2) // messages, wallet, notifications
      ];
    } else {
      return [
        baseTabs[0], // home
        { id: 'projects', label: 'Проекты' },
        baseTabs[1], // community
        ...baseTabs.slice(2) // messages, wallet, notifications
      ];
    }
  }, [t, userRole]);

  const mainNav = useMemo(() => {
    if (userRole === 'executor') {
      return [
        { id: 'home', label: t('nav.home') },
        { id: 'orders', label: t('nav.orders') },
        { id: 'community', label: t('nav.community') },
        { id: 'myOrders', label: t('nav.myOrders') },
        { id: 'portfolio', label: t('nav.portfolio') },
        { id: 'messages', label: t('nav.messages') }
      ];
    } else {
      return [
        { id: 'home', label: t('nav.home') },
        { id: 'projects', label: 'Проекты' },
        { id: 'community', label: t('nav.community') },
        { id: 'messages', label: t('nav.messages') }
      ];
    }
  }, [t, userRole]);

  const headline = useMemo(() => {
    const current = tabs.find((t) => t.id === activeTab);
    return current ? current.label : '';
  }, [activeTab, tabs]);

  if (showRegister) {
    return <Register onSuccess={(action) => {
      if (action === 'login') {
        setShowRegister(false);
        setShowLogin(true);
      } else if (action === 'registered') {
        // Регистрация завершена, пользователь уже вошел через Register компонент
        setShowRegister(false);
      } else {
        setShowRegister(false);
      }
    }} />;
  }

  if (showLogin) {
    return <Login onSuccess={(action) => {
      if (action === 'register') {
        setShowLogin(false);
        setShowRegister(true);
      } else if (action === 'logged_in') {
        // Вход выполнен, пользователь уже вошел через Login компонент
        setShowLogin(false);
      } else {
        setShowLogin(false);
      }
    }} />;
  }

  const handleProfileSetupComplete = async (profileData) => {
    // Профиль уже сохранен через API в компоненте
    setShowProfileSetup(false);
    // Обновляем данные пользователя
    try {
      const response = await apiClient.get('/users/me');
      // Данные пользователя обновятся автоматически через контекст
    } catch (error) {
      console.error('Error fetching user data:', error);
    }
  };

  const handleProfileEditComplete = async (profileData) => {
    // Профиль уже обновлен через API в компоненте
    setShowProfileEdit(false);
    // Обновляем данные пользователя
    try {
      const response = await apiClient.get('/users/me');
      // Данные пользователя обновятся автоматически через контекст
    } catch (error) {
      console.error('Error fetching user data:', error);
    }
  };

  return (
    <div className="page">
      <header className="topbar" style={{ zIndex: 10000, position: 'sticky', top: 0, pointerEvents: 'auto' }}>
        <div className="brand" style={{ pointerEvents: 'auto' }}>
          <img src="/logo.png" alt="Logo" className="brand-mark" />
        </div>
        <button
          ref={burgerRef}
          className={`burger-menu ${mobileMenuOpen ? 'open' : ''}`}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setMobileMenuOpen((prev) => !prev);
          }}
          onMouseDown={(e) => {
            e.preventDefault();
            e.stopPropagation();
          }}
          onTouchStart={(e) => {
            e.preventDefault();
            e.stopPropagation();
          }}
          aria-label="Menu"
          type="button"
          style={{ pointerEvents: 'auto', zIndex: 10001 }}
        >
          <span className={`burger-line ${mobileMenuOpen ? 'open' : ''}`}></span>
          <span className={`burger-line ${mobileMenuOpen ? 'open' : ''}`}></span>
          <span className={`burger-line ${mobileMenuOpen ? 'open' : ''}`}></span>
        </button>
        <nav
          className={`nav ${mobileMenuOpen ? 'mobile-open' : ''}`}
          ref={mobileMenuRef}
          style={{ zIndex: 10000, position: 'relative', pointerEvents: 'auto' }}
          onClick={(e) => {
            // Разрешаем клики внутри навигации
            e.stopPropagation();
          }}
        >
          {mainNav.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={`nav-item ${activeTab === tab.id ? 'active' : ''}`}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('🔄 Клик по навигации:', tab.id);
                try {
                  setActiveTab(tab.id);
                  setMobileMenuOpen(false);
                } catch (error) {
                  console.error('Ошибка при переключении вкладки:', error);
                  // Принудительная навигация через navigate
                  navigate(`/${tab.id}`);
                }
              }}
              onMouseDown={(e) => {
                e.preventDefault();
                e.stopPropagation();
              }}
              onTouchStart={(e) => {
                e.preventDefault();
                e.stopPropagation();
              }}
              style={{ pointerEvents: 'auto', cursor: 'pointer' }}
            >
              {tab.label}
            </button>
          ))}
        </nav>
        <div className="actions">
          <button
            className="theme-toggle"
            onClick={toggleTheme}
            title={t('common.theme')}
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
          <div className="lang-dropdown" ref={langMenuRef}>
            <button
              className="lang-toggle"
              onClick={() => setLangMenuOpen(!langMenuOpen)}
            >
              {language.toUpperCase()}
            </button>
            <div className={`lang-menu ${langMenuOpen ? 'open' : ''}`}>
              <div className="lang-option" onClick={() => { changeLanguage('ru'); setLangMenuOpen(false); }}>
                RU
              </div>
              <div className="lang-option" onClick={() => { changeLanguage('en'); setLangMenuOpen(false); }}>
                EN
              </div>
            </div>
          </div>
          <button
            className="action-icon notifications"
            onClick={() => navigate('/notifications')}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M10 2C8.9 2 8 2.9 8 4V5.58C6.08 6.26 4.5 7.66 3.67 9.47L3.5 9.83C3.32 10.18 3.23 10.57 3.23 10.97V14C3.23 14.55 3.68 15 4.23 15H15.77C16.32 15 16.77 14.55 16.77 14V10.97C16.77 10.57 16.68 10.18 16.5 9.83L16.33 9.47C15.5 7.66 13.92 6.26 12 5.58V4C12 2.9 11.1 2 10 2Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M7 15V16C7 16.7956 7.31607 17.5587 7.87868 18.1213C8.44129 18.6839 9.20435 19 10 19C10.7956 19 11.5587 18.6839 12.1213 18.1213C12.6839 17.5587 13 16.7956 13 16V15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          {isAuthenticated ? (
            <>
              <button
                className="wallet-display"
                onClick={() => navigate('/wallet')}
              >
                <span className="wallet-amount">{currentUser?.balance || 0} ₽</span>
              </button>
              <button
                className="avatar-btn"
                onClick={() => navigate('/profile')}
              >
                <div className="avatar small">
                  {currentUser?.avatar_url ? (
                    <img src={currentUser.avatar_url} alt="" style={{ width: '100%', height: '100%', borderRadius: 'inherit', objectFit: 'cover' }} />
                  ) : (
                    getInitials(currentUser?.name)
                  )}
                </div>
              </button>
              <button
                className="btn primary small"
                onClick={logout}
              >
                {t('common.logout')}
              </button>
            </>
          ) : (
            <>
              <button
                className="btn primary small"
                onClick={() => setShowLogin(true)}
              >
                {t('common.login')}
              </button>
              <button
                className="btn primary small"
                onClick={() => setShowRegister(true)}
              >
                {t('common.register')}
              </button>
            </>
          )}
        </div>
      </header>

      {isAuthenticated ? (
        <div style={{ pointerEvents: 'auto' }}>
          {showProfileSetup ? (
            <main className="content">
              <div className="hero">
                <div>
                  <div className="headline">{t('profileSetup.title')}</div>
                  <div className="subline">{t('profileSetup.subtitle')}</div>
                </div>
              </div>
              <ProfileSetup onComplete={handleProfileSetupComplete} />
            </main>
          ) : showProfileEdit ? (
            <main className="content">
              <div className="hero">
                <div>
                  <div className="headline">{t('profileEdit.title')}</div>
                  <div className="subline">{t('profileEdit.subtitle')}</div>
                </div>
              </div>
              <ProfileEdit onComplete={handleProfileEditComplete} />
            </main>
          ) : (
            <div style={{ pointerEvents: 'auto' }}>
              <main className="content" style={{ pointerEvents: 'auto' }}>
                <div className="hero">
                  <div>
                    <div className="headline">{headline}</div>
                    <div className="subline">{t('common.subtitle')}</div>
                  </div>
                </div>
                <TabContent
                  tab={activeTab}
                  t={t}
                  onFillProfile={() => setShowProfileSetup(true)}
                  onEditProfile={() => setShowProfileEdit(true)}
                  navigate={navigate}
                  onAddWork={startAddWork}
                  onEditWork={startEditWork}
                  onDeleteWork={startDeleteWork}
                  portfolioItems={portfolioItems}
                  categoriesList={Object.keys(categories)}
                  userRole={userRole}
                  toggleUserRole={toggleUserRole}
                  orderNotesHook={{ getNote, saveNote, fetchNote }}
                  communityPostsHook={{ posts: communityPosts, createPost, updatePost, deletePost, toggleLike, addComment, fetchComments }}

                  currentUser={currentUser}
                  myOrders={myOrders}
                  fetchMyOrders={fetchMyOrders}
                  setActiveTab={setActiveTab}
                  setViewMode={setViewMode}
                  publicOrders={publicOrders}
                  publicOrdersLoading={publicOrdersLoading}
                  budgetFrom={budgetFrom}
                  setBudgetFrom={setBudgetFrom}
                  budgetTo={budgetTo}
                  setBudgetTo={setBudgetTo}
                  keywords={keywords}
                  setKeywords={setKeywords}
                  selectedOrdersSubcategories={selectedOrdersSubcategories}
                  setSelectedOrdersSubcategories={setSelectedOrdersSubcategories}
                  selectedOrdersSubSubcategories={selectedOrdersSubSubcategories}
                  setSelectedOrdersSubSubcategories={setSelectedOrdersSubSubcategories}
                  selectedBudgetRanges={selectedBudgetRanges}
                  setSelectedBudgetRanges={setSelectedBudgetRanges}
                  hiredPercent={hiredPercent}
                  setHiredPercent={setHiredPercent}
                  selectedOfferRanges={selectedOfferRanges}
                  setSelectedOfferRanges={setSelectedOfferRanges}
                />
              </main>
              {showPortfolioModal && (
                <div className="modal-backdrop" onClick={() => setShowPortfolioModal(false)}>
                  <div className="modal" onClick={(e) => e.stopPropagation()}>
                    <div className="modal-header">
                      <div className="modal-title">{t('skills.addWork')}</div>
                      <button className="modal-close" onClick={() => setShowPortfolioModal(false)}>✕</button>
                    </div>
                    <div className="modal-body">
                      <div className="notice">
                        {t('portfolio.modal.notice')}
                      </div>
                      <div className="form form-section">
                        <label>{t('portfolio.modal.titleLabel')}</label>
                        <input
                          maxLength={40}
                          value={portfolioForm.title}
                          onChange={(e) => setPortfolioForm({ ...portfolioForm, title: e.target.value })}
                          placeholder={t('portfolio.modal.titlePlaceholder')}
                        />
                        <div className="grid two">
                          <div className="form">
                            <label>{t('portfolio.modal.category')}</label>
                            <div className={`dropdown ${categoryOpen ? 'open' : ''}`} onClick={() => setCategoryOpen(!categoryOpen)}>
                              <div className="dropdown-value">{portfolioForm.category}</div>
                              {categoryOpen && (
                                <div className="dropdown-list">
                                  {Object.keys(categories).map((cat) => (
                                    <div
                                      key={cat}
                                      className="dropdown-item"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        const firstSub = categories[cat]?.[0] || '';
                                        setPortfolioForm({ ...portfolioForm, category: cat, subcategory: firstSub });
                                        setCategoryOpen(false);
                                        setSubcategoryOpen(false);
                                      }}
                                    >
                                      {cat}
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                          <div className="form">
                            <label>{t('portfolio.modal.subcategory')}</label>
                            <div className={`dropdown ${subcategoryOpen ? 'open' : ''}`} onClick={() => setSubcategoryOpen(!subcategoryOpen)}>
                              <div className="dropdown-value">{portfolioForm.subcategory}</div>
                              {subcategoryOpen && (
                                <div className="dropdown-list">
                                  {(categories[portfolioForm.category] || []).map((sub) => (
                                    <div
                                      key={sub}
                                      className="dropdown-item"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        setPortfolioForm({ ...portfolioForm, subcategory: sub });
                                        setSubcategoryOpen(false);
                                      }}
                                    >
                                      {sub}
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="form">
                          <label>{t('portfolio.modal.typeLabel')}</label>
                          <input
                            value={portfolioForm.type}
                            onChange={(e) => setPortfolioForm({ ...portfolioForm, type: e.target.value })}
                            placeholder={t('portfolio.modal.typePlaceholder')}
                          />
                        </div>
                      </div>

                      <div className="form form-section">
                        <label>{t('portfolio.modal.uploadMediaLabel')}</label>
                        <div className="upload-hint">
                          {t('portfolio.modal.uploadMediaHint')}
                        </div>
                        <div className="upload-box" onClick={() => workInputRef.current?.click()}>
                          <div className="upload-label">{t('portfolio.modal.uploadButton')}</div>
                          <div className="upload-sub">{t('portfolio.modal.uploadSub')}</div>
                          <input
                            ref={workInputRef}
                            className="file-input-hidden"
                            type="file"
                            multiple
                            accept="image/jpeg,image/jpg,image/png,image/gif,video/*"
                            onChange={(e) => {
                              const files = Array.from(e.target.files || []);
                              if (!files.length) return;
                              const limit = 8;
                              const next = [...workFiles];
                              files.slice(0, limit - next.length).forEach((file) => {
                                if (file.type.startsWith('image/')) {
                                  const reader = new FileReader();
                                  reader.onload = (ev) => {
                                    const updated = [...next, { url: ev.target?.result, name: file.name, isImage: true }];
                                    next.splice(0, next.length, ...updated);
                                    setWorkFiles(updated.slice(0, limit));
                                  };
                                  reader.readAsDataURL(file);
                                } else {
                                  next.push({ url: null, name: file.name, isImage: false });
                                }
                              });
                              setWorkFiles(next.slice(0, limit));
                              e.target.value = '';
                            }}
                          />
                        </div>
                        {workFiles.length > 0 && (
                          <div className="file-preview multi">
                            {workFiles.map((file, idx) => (
                              <div key={idx} className="file-thumb">
                                {file.isImage ? (
                                  <img src={file.url} alt={file.name} />
                                ) : (
                                  <div className="file-chip">{file.name || t('portfolio.modal.video')}</div>
                                )}
                                <button
                                  className="file-remove"
                                  onClick={() => setWorkFiles(workFiles.filter((_, i) => i !== idx))}
                                  type="button"
                                >
                                  ✕
                                </button>
                              </div>
                            ))}
                            {workFiles.length >= 8 && (
                              <div className="upload-hint">{t('portfolio.modal.maxFiles')}</div>
                            )}
                          </div>
                        )}
                      </div>

                      <div className="form form-section">
                        <label>{t('portfolio.modal.coverLabel')}</label>
                        <div className="upload-hint">
                          {t('portfolio.modal.coverHint')}
                        </div>
                        <div className="upload-box" onClick={() => coverInputRef.current?.click()}>
                          <div className="upload-label">{t('portfolio.modal.coverButton')}</div>
                          <div className="upload-sub">{t('portfolio.modal.coverSub')}</div>
                          <input
                            ref={coverInputRef}
                            className="file-input-hidden"
                            type="file"
                            accept="image/jpeg,image/jpg,image/png,image/gif"
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (!file) {
                                setCoverPreview(null);
                                return;
                              }
                              const reader = new FileReader();
                              reader.onload = (ev) => setCoverPreview({ url: ev.target?.result, name: file.name });
                              reader.readAsDataURL(file);
                              e.target.value = '';
                            }}
                          />
                        </div>
                        {coverPreview && (
                          <div className="file-preview">
                            <div className="file-thumb">
                              <img src={coverPreview.url} alt={t('portfolio.modal.coverAlt')} />
                              <button
                                className="file-remove"
                                onClick={() => setCoverPreview(null)}
                                type="button"
                              >
                                ✕
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="modal-footer">
                      <button className="btn ghost" onClick={() => setShowPortfolioModal(false)}>{t('common.cancel') || 'Отмена'}</button>
                      <button className="btn primary" onClick={handlePortfolioSave}>{t('common.save') || 'Сохранить'}</button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        <main className="content">
          <div className="hero">
            <div>
              <div className="headline">{t('common.appName')}</div>
              <div className="subline">{t('common.subtitle')}</div>
            </div>
          </div>
          <div className="grid two" style={{ marginTop: '20px' }}>
            <div className="card">
              <div className="card-header">
                <div className="card-title">{t('home.welcome')}</div>
              </div>
              <div className="card-body">
                <p style={{ marginBottom: '16px', color: 'var(--muted)' }}>
                  {t('auth.welcomeText')}
                </p>
                <button className="btn primary full" onClick={() => setShowRegister(true)}>
                  {t('common.register')}
                </button>
                <button className="btn ghost full" style={{ marginTop: '10px' }} onClick={() => setShowLogin(true)}>
                  {t('common.login')}
                </button>
              </div>
            </div>
            <div className="card">
              <div className="card-header">
                <div className="card-title">{t('auth.features')}</div>
              </div>
              <div className="card-body">
                <div className="list">
                  <div className="list-row">
                    <div className="list-title">✓ {t('auth.feature1')}</div>
                  </div>
                  <div className="list-row">
                    <div className="list-title">✓ {t('auth.feature2')}</div>
                  </div>
                  <div className="list-row">
                    <div className="list-title">✓ {t('auth.feature3')}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      )}
    </div>
  );
}

export default App;

