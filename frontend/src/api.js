import axios from 'axios';

const API = axios.create({
  baseURL: 'http://localhost:8000', // Replace with your backend URL 
  })

export const uploadRequirement = (formData) => API.post("/requirements/upload", formData);
export const generateTestCases = (reqId) => API.post(`/requirements/${reqId}/generate`);
export const approveTestCase = (testId, data) => API.put(`/testcases/${testId}`, data);