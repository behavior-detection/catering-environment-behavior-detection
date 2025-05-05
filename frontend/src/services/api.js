import axios from 'axios'

// Create axios instance with default config
const api = axios.create({
  baseURL: process.env.VUE_APP_API_URL || 'http://localhost:8000/api',
  timeout: 30000, // 30 seconds timeout
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  withCredentials: true // Include cookies in requests
})

// Request interceptor
api.interceptors.request.use(
  config => {
    // You can add auth token here if needed
    // const token = localStorage.getItem('token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  response => {
    return response
  },
  error => {
    // Handle common errors
    if (error.response) {
      // Server responded with an error status
      console.error('API Error:', error.response.status, error.response.data)

      // Handle authentication errors
      if (error.response.status === 401 || error.response.status === 403) {
        // You can redirect to login or handle auth errors here
        console.error('Authentication error')
      }
    } else if (error.request) {
      // Request was made but no response was received
      console.error('Network Error:', error.request)
    } else {
      // Something happened in setting up the request
      console.error('Request Error:', error.message)
    }

    return Promise.reject(error)
  }
)

export default api
