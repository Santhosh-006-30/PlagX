import axios from 'axios';

const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api',
});

export default api;

export const authApi = {
  login: (data: any) => api.post('/auth/login', data),
  register: (data: any) => api.post('/auth/register', data),
};

export const docsApi = {
  upload: (formData: FormData) => api.post('/docs/upload', formData),
  list: () => api.get('/docs'),
};

export const scanApi = {
  analyze: (documentId: string) => api.post('/scan/analyze', { document_id: documentId }),
  getReport: (id: string) => api.get(`/scan/report/${id}`),
};

export const getFileUrl = (fileKey: string) => {
  if (!fileKey) return '';
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api';
  const baseUrl = apiUrl.replace('/api', '');
  return `${baseUrl}/uploads/${fileKey}`;
};
