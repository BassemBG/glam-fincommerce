// API Configuration
// Uses environment variable NEXT_PUBLIC_API_URL or defaults to localhost
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// API Endpoints
export const API = {
  auth: {
    login: `${API_URL}/api/v1/auth/login`,
    signup: `${API_URL}/api/v1/auth/signup`,
  },
  users: {
    me: `${API_URL}/api/v1/users/me`,
    bodyPhoto: `${API_URL}/api/v1/users/body-photo`,
    onboarding: `${API_URL}/api/v1/users/onboarding`,
  },
  closet: {
    items: `${API_URL}/api/v1/closet/items`,
    upload: `${API_URL}/api/v1/closet/upload`,
  },
  outfits: {
    list: `${API_URL}/api/v1/outfits/`,
  },
  stylist: {
    chat: `${API_URL}/api/v1/stylist/chat`,
  },
};
