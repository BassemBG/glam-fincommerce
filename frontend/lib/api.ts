// API Configuration
// Uses environment variable NEXT_PUBLIC_API_URL or defaults to localhost
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// API Endpoints
export const API = {
  users: {
    me: `${API_URL}/api/v1/users/me`,
    bodyPhoto: `${API_URL}/api/v1/users/body-photo`,
    analyzeProfile: `${API_URL}/api/v1/users/analyze-profile`,
  },
  clothing: {
    ingest: `${API_URL}/api/v1/clothing/ingest`,
  },
  closet: {
    items: `${API_URL}/api/v1/closet/items`,
    delete: (id: string) => `${API_URL}/api/v1/closet/items/${id}`,
    upload: `${API_URL}/api/v1/closet/upload`,
  },
  outfits: {
    list: `${API_URL}/api/v1/outfits/`,
  },
  stylist: {
    chat: `${API_URL}/api/v1/stylist/chat`,
    advisor: `${API_URL}/api/v1/stylist/advisor/compare`
  },
};
