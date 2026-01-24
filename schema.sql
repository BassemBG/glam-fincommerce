-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    full_body_image TEXT,           -- URL of user's standing photo for try-ons
    style_profile JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Clothing Items Table
CREATE TABLE clothing_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL,  -- clothing, shoes, accessory
    sub_category VARCHAR(50),       -- t-shirt, jeans, etc.
    body_region VARCHAR(50) DEFAULT 'top', -- head, top, bottom, feet, full_body, outerwear
    image_url TEXT NOT NULL,
    mask_url TEXT,
    metadata JSONB DEFAULT '{}',
    embedding vector(768),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Outfits Table
CREATE TABLE outfits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255),
    occasion VARCHAR(100),
    vibe VARCHAR(100),
    items UUID[] NOT NULL,
    score FLOAT DEFAULT 0.0,
    reasoning TEXT,
    tryon_image_url TEXT,           -- URL of AI-generated try-on visualization
    created_by VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Body Profile (v3 - placeholder)
CREATE TABLE body_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    body_image_url TEXT,
    body_shape VARCHAR(50),
    pose_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Profile Brands Table (User-curated brand profiles)
CREATE TABLE profile_brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_name VARCHAR(255) NOT NULL UNIQUE,
    brand_website VARCHAR(500),
    instagram_link VARCHAR(500),
    brand_logo_url TEXT,
    description TEXT,
    description_embedding vector(384),  -- For semantic search
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indices for performance
CREATE INDEX idx_clothing_items_user_id ON clothing_items(user_id);
CREATE INDEX idx_outfits_user_id ON outfits(user_id);
CREATE INDEX idx_clothing_items_embedding ON clothing_items USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_profile_brands_name ON profile_brands(brand_name);
CREATE INDEX idx_profile_brands_embedding ON profile_brands USING ivfflat (description_embedding vector_cosine_ops) WITH (lists = 100);
