import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
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

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (credentials: { email: string; password: string }) =>
    api.post('/auth/login', credentials),
  
  register: (userData: any) =>
    api.post('/auth/register', userData),
  
  logout: () =>
    api.post('/auth/logout'),
  
  getMe: (token?: string) =>
    api.get('/auth/me', token ? { headers: { Authorization: `Bearer ${token}` } } : {}),
  
  refreshToken: (refreshToken: string) =>
    api.post('/auth/refresh', { refresh_token: refreshToken }),
  
  requestPasswordReset: (email: string) =>
    api.post('/auth/password-reset', { email }),
  
  confirmPasswordReset: (token: string, newPassword: string) =>
    api.post('/auth/password-reset/confirm', { token, new_password: newPassword }),
  
  changePassword: (currentPassword: string, newPassword: string) =>
    api.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword }),
};

// User API
export const userAPI = {
  getProfile: () =>
    api.get('/users/me'),
  
  updateProfile: (userData: any) =>
    api.put('/users/me', userData),
  
  getStats: () =>
    api.get('/users/me/stats'),
  
  getSubscription: () =>
    api.get('/users/me/subscription'),
  
  updateSubscription: (tier: string) =>
    api.put('/users/me/subscription', { tier }),
  
  deleteAccount: () =>
    api.delete('/users/me'),
};

// Audio API
export const audioAPI = {
  uploadFile: (file: File, onProgress?: (progress: number) => void) => {
    const formData = new FormData();
    formData.append('file', file);
    
    return api.post('/audio/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });
  },
  
  getFiles: (params?: any) =>
    api.get('/audio/', { params }),
  
  getFile: (fileId: string) =>
    api.get(`/audio/${fileId}`),
  
  downloadFile: (fileId: string) =>
    api.get(`/audio/${fileId}/download`, { responseType: 'blob' }),
  
  streamFile: (fileId: string) =>
    api.get(`/audio/${fileId}/stream`, { responseType: 'blob' }),
  
  deleteFile: (fileId: string) =>
    api.delete(`/audio/${fileId}`),
  
  masterFile: (fileId: string, options: any) =>
    api.post(`/audio/${fileId}/master`, options),
  
  getMasteringStatus: (fileId: string, sessionId: string) =>
    api.get(`/audio/${fileId}/master/${sessionId}/status`),
  
  downloadMasteredFile: (fileId: string, sessionId: string) =>
    api.get(`/audio/${fileId}/master/${sessionId}/download`, { responseType: 'blob' }),
};

// Music Generation API
export const musicAPI = {
  generateMusic: (prompt: string, options?: any) =>
    api.post('/sessions/', {
      session_type: 'music_generation',
      user_prompt: prompt,
      ...options,
    }),
  
  getSessions: (params?: any) =>
    api.get('/sessions/', { params }),
  
  getSession: (sessionId: string) =>
    api.get(`/sessions/${sessionId}`),
  
  getSessionProgress: (sessionId: string) =>
    api.get(`/sessions/${sessionId}/progress`),
  
  cancelSession: (sessionId: string) =>
    api.post(`/sessions/${sessionId}/cancel`),
};

// Health API
export const healthAPI = {
  check: () =>
    api.get('/health'),
};

export default api;