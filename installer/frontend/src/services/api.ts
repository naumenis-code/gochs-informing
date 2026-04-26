import axios from 'axios';
import { message } from 'antd';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    } else if (error.response?.status === 403) {
      message.error('Недостаточно прав для выполнения операции');
    } else if (error.response?.status >= 500) {
      message.error('Ошибка сервера. Попробуйте позже.');
    } else if (error.code === 'ECONNABORTED') {
      message.error('Превышено время ожидания ответа');
    }
    return Promise.reject(error);
  }
);

export default api;
