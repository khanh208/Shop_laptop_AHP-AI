import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:5000/api',
  headers: { 'Content-Type': 'application/json' }
});

export const getFormOptions = () => api.get('/form-options');
export const runRecommendation = (data) => api.post('/recommendations/run', data);
export const getDashboard = (key) => api.get(`/recommendations/${key}/dashboard`);
export const getInferenceTrace = (key) => api.get(`/recommendations/${key}/inference-trace`);
export const getAlternativeAHP = (key) => api.get(`/recommendations/${key}/alternative-ahp`);
export const getCandidates = (key) => api.get(`/recommendations/${key}/candidates`);

export default api;
