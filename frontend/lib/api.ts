// API Configuration
// Uses environment variable NEXT_PUBLIC_API_URL or defaults to localhost
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// API Endpoints
export const API = {
  base: `${API_URL}/api/v1`,
  auth: {
    login: `${API_URL}/api/v1/auth/login`,
    signup: `${API_URL}/api/v1/auth/signup`,
  },
  users: {
    me: `${API_URL}/api/v1/users/me`,
    bodyPhoto: `${API_URL}/api/v1/users/body-photo`,
    analyzeProfile: `${API_URL}/api/v1/users/analyze-profile`,
    onboarding: `${API_URL}/api/v1/users/onboarding`,
    settings: `${API_URL}/api/v1/users/settings`,
    wallet: {
      spend: `${API_URL}/api/v1/users/wallet/spend`,
      topup: `${API_URL}/api/v1/users/wallet/topup`,
    }
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
    list: `${API_URL}/api/v1/outfits`,
    save: `${API_URL}/api/v1/stylist/outfits/save`,
  },
  stylist: {
    chat: `${API_URL}/api/v1/stylist/chat`,
    tryon: `${API_URL}/api/v1/stylist/tryon`,
    advisor: `${API_URL}/api/v1/stylist/advisor/compare`,
    search: (q: string) => `${API_URL}/api/v1/stylist/search?query=${encodeURIComponent(q)}`
  },
  pinterest: {
    login: `${API_URL}/api/v1/auth/pinterest/login`,
    status: `${API_URL}/api/v1/auth/pinterest/status`,
  },
  brandIngestion: {
    ingest: `${API_URL}/api/v1/brands/ingest`,
    list: `${API_URL}/api/v1/brands`,
  },
  profileBrands: {
    upsert: `${API_URL}/api/v1/brands/profile/ingest`,
    list: `${API_URL}/api/v1/brands/profile/list`,
    getByName: (name: string) => `${API_URL}/api/v1/brands/profile/${name}`,
  },
};
