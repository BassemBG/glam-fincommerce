"""
Service for managing user-curated brand profiles with embedding support.
Uses cosine similarity for semantic search on brand descriptions.
Uses local sentence-transformers model (all-MiniLM-L12-v2) - no API key needed.
"""

from typing import Optional, List
from datetime import datetime
from sqlmodel import Session, select
from app.models.models import ProfileBrand, Brand

try:
    from sentence_transformers import SentenceTransformer
    MODEL = SentenceTransformer("all-MiniLM-L12-v2")
except ImportError:
    print("Warning: sentence-transformers not installed. Install with: pip install sentence-transformers")
    MODEL = None

class ProfileBrandsService:
    """Handle CRUD operations and vector similarity search for brand profiles."""
    
    def __init__(self, db: Session):
        self.db = db
    
    @staticmethod
    def _embed_text(text: str) -> Optional[List[float]]:
        """Generate embedding using local sentence-transformers model."""
        if not MODEL or not text or not text.strip():
            return None
        try:
            embedding = MODEL.encode(text.strip())
            # Ensure we persist as plain Python list regardless of backend return type
            try:
                return embedding.tolist()  # numpy array -> list
            except AttributeError:
                # Already a list or other sequence
                return list(embedding)
        except Exception as e:
            print(f"Warning: Failed to generate embedding: {e}")
            return None
    
    def get_or_create_brand_profile(
        self,
        brand_id: str,
        brand_name: str,
        office_email: Optional[str] = None,
        brand_type: Optional[str] = None,
        brand_website: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ProfileBrand:
        """
        Get or create a brand profile linked to a brand.
        Idempotent: called multiple times with same brand_id returns same profile.
        Called from brand signup to auto-initialize profile.
        """
        # Check if profile already exists for this brand_id
        statement = select(ProfileBrand).where(ProfileBrand.brand_id == brand_id)
        existing = self.db.execute(statement).scalars().first()
        
        if existing:
            # Update existing profile with latest sign-up data
            existing.brand_name = brand_name
            existing.office_email = office_email
            existing.brand_type = brand_type
            existing.brand_website = brand_website
            existing.updated_at = datetime.utcnow()
            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        
        # Create new profile
        new_profile = ProfileBrand(
            brand_id=brand_id,
            brand_name=brand_name,
            office_email=office_email,
            brand_type=brand_type,
            brand_website=brand_website,
            description=description,
            brand_metadata={}
        )
        self.db.add(new_profile)
        self.db.commit()
        self.db.refresh(new_profile)
        return new_profile
    
    def update_brand_profile(
        self,
        brand_id: str,
        brand_name: Optional[str] = None,
        brand_website: Optional[str] = None,
        instagram_link: Optional[str] = None,
        brand_logo_url: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[ProfileBrand]:
        """
        Update only the editable fields of a brand profile.
        Returns the updated profile or None if not found.
        """
        statement = select(ProfileBrand).where(ProfileBrand.brand_id == brand_id)
        profile = self.db.execute(statement).scalars().first()
        
        if not profile:
            return None
        
        # Update editable fields
        if brand_name is not None:
            profile.brand_name = brand_name
        if brand_website is not None:
            profile.brand_website = brand_website
        if instagram_link is not None:
            profile.instagram_link = instagram_link
        if brand_logo_url is not None:
            profile.brand_logo_url = brand_logo_url
        if description is not None:
            profile.description = description
            # Update embedding when description changes
            embedding = self._embed_text(description)
            if embedding:
                profile.brand_metadata = profile.brand_metadata or {}
                profile.brand_metadata['description_embedding'] = embedding
        
        profile.updated_at = datetime.utcnow()
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile
    
    def get_profile_by_brand_id(self, brand_id: str) -> Optional[ProfileBrand]:
        """Fetch a brand profile by brand_id (one-to-one relationship)."""
        statement = select(ProfileBrand).where(ProfileBrand.brand_id == brand_id)
        return self.db.execute(statement).scalars().first()
    
    def upsert_profile_brand(
        self,
        brand_name: str,
        brand_website: Optional[str] = None,
        instagram_link: Optional[str] = None,
        brand_logo_url: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ProfileBrand:
        """
        Upsert a brand profile. If brand_name exists, update it; otherwise create new.
        Generates and stores embedding for the description for semantic search.
        [DEPRECATED] Use get_or_create_brand_profile or update_brand_profile instead.
        """
        # Check if brand already exists
        statement = select(ProfileBrand).where(ProfileBrand.brand_name == brand_name)
        existing = self.db.execute(statement).scalars().first()
        
        # Generate embedding for description if provided
        embedding = None
        if description:
            embedding = self._embed_text(description)
        
        if existing:
            # Update existing brand
            existing.brand_website = brand_website
            existing.instagram_link = instagram_link
            existing.brand_logo_url = brand_logo_url
            existing.description = description
            existing.updated_at = datetime.utcnow()
            # Only update embedding if description changed
            if embedding:
                existing.brand_metadata = existing.brand_metadata or {}
                existing.brand_metadata['description_embedding'] = embedding
            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new brand
            new_brand = ProfileBrand(
                brand_id="",  # This will cause issues - use get_or_create_brand_profile instead
                brand_name=brand_name,
                brand_website=brand_website,
                instagram_link=instagram_link,
                brand_logo_url=brand_logo_url,
                description=description,
                brand_metadata={'description_embedding': embedding} if embedding else {}
            )
            self.db.add(new_brand)
            self.db.commit()
            self.db.refresh(new_brand)
            return new_brand
    
    def get_profile_brand_by_name(self, brand_name: str) -> Optional[ProfileBrand]:
        """Fetch a brand profile by exact brand name match."""
        statement = select(ProfileBrand).where(ProfileBrand.brand_name == brand_name)
        return self.db.execute(statement).scalars().first()
    
    def get_profile_brand_by_id(self, brand_id: str) -> Optional[ProfileBrand]:
        """Fetch a brand profile by ID."""
        return self.db.get(ProfileBrand, brand_id)
    
    def list_profile_brands(self, limit: int = 100, offset: int = 0) -> List[ProfileBrand]:
        """List all profile brands with pagination."""
        statement = select(ProfileBrand).offset(offset).limit(limit).order_by(ProfileBrand.updated_at.desc())
        return self.db.execute(statement).scalars().all()
    
    def delete_profile_brand(self, brand_name: str) -> bool:
        """Delete a brand profile by name."""
        brand = self.get_profile_brand_by_name(brand_name)
        if brand:
            self.db.delete(brand)
            self.db.commit()
            return True
        return False
    
    def search_by_description(self, query: str, limit: int = 10) -> List[ProfileBrand]:
        """
        Search brands by semantic similarity to a query description.
        Uses cosine similarity over embeddings (all-MiniLM-L12-v2 model).
        """
        try:
            # Generate embedding for the query using local model
            query_embedding = self._embed_text(query)
            if not query_embedding:
                return []
            
            # Get all brands (in production, use vector DB for efficiency)
            all_brands = self.list_profile_brands(limit=1000)
            
            # Calculate cosine similarity for each brand
            similarities = []
            for brand in all_brands:
                brand_embedding = brand.brand_metadata.get('description_embedding') if brand.brand_metadata else None
                if brand_embedding:
                    similarity = self._cosine_similarity(query_embedding, brand_embedding)
                    similarities.append((similarity, brand))
            
            # Sort by similarity and return top results
            similarities.sort(key=lambda x: x[0], reverse=True)
            return [brand for _, brand in similarities[:limit]]
        except Exception as e:
            print(f"Warning: Search by description failed: {e}")
            return []
    
    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        magnitude_a = math.sqrt(sum(a ** 2 for a in vec_a))
        magnitude_b = math.sqrt(sum(b ** 2 for b in vec_b))
        
        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0
        
        return dot_product / (magnitude_a * magnitude_b)
