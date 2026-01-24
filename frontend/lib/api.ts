// API Configuration
// Uses environment variable NEXT_PUBLIC_API_URL or defaults to localhost
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// API Endpoints
export const API = {
  users: {
    me: `${API_URL}/api/v1/users/me`,
    bodyPhoto: `${API_URL}/api/v1/users/body-photo`,
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
  brandIngestion: {
    ingest: `${API_URL}/api/v1/brands/ingest`,
    list: `${API_URL}/api/v1/brands`,
  },
};
