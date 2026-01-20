"""
Seed the database with demo clothing items and outfits.
Run: python seed_demo_data.py
"""
from app.db.session import engine
from app.models.models import SQLModel, User, ClothingItem, Outfit
from sqlmodel import Session
import json

# Demo clothing items with full data
DEMO_ITEMS = [
    {
        "category": "clothing",
        "sub_category": "Silk Blouse",
        "body_region": "top",
        "image_url": "https://images.unsplash.com/photo-1564584217132-2271feaeb3c5?w=400",
        "mask_url": "https://images.unsplash.com/photo-1564584217132-2271feaeb3c5?w=400",
        "metadata_json": {
            "colors": ["Cream", "Ivory"],
            "material": "Silk",
            "vibe": "chic",
            "season": "All Seasons",
            "description": "A luxurious cream silk blouse with elegant draping and mother-of-pearl buttons.",
            "styling_tips": "Pair with high-waisted trousers and gold jewelry for a sophisticated look."
        }
    },
    {
        "category": "clothing",
        "sub_category": "Tailored Blazer",
        "body_region": "outerwear",
        "image_url": "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=400",
        "mask_url": "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=400",
        "metadata_json": {
            "colors": ["Navy", "Dark Blue"],
            "material": "Wool Blend",
            "vibe": "classic",
            "season": "Autumn",
            "description": "A perfectly tailored navy blazer with subtle peak lapels and a structured silhouette.",
            "styling_tips": "Layer over a white tee and jeans for smart-casual elegance."
        }
    },
    {
        "category": "clothing",
        "sub_category": "High-Waisted Jeans",
        "body_region": "bottom",
        "image_url": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=400",
        "mask_url": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=400",
        "metadata_json": {
            "colors": ["Indigo", "Blue"],
            "material": "Denim",
            "vibe": "casual",
            "season": "All Seasons",
            "description": "Classic high-waisted straight-leg jeans in a deep indigo wash with comfortable stretch.",
            "styling_tips": "Tuck in a simple blouse and add loafers for effortless French-girl style."
        }
    },
    {
        "category": "shoes",
        "sub_category": "Leather Loafers",
        "body_region": "feet",
        "image_url": "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=400",
        "mask_url": "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=400",
        "metadata_json": {
            "colors": ["Tan", "Camel"],
            "material": "Leather",
            "vibe": "minimalist",
            "season": "Spring",
            "description": "Handcrafted Italian leather loafers in a warm tan shade with cushioned insole.",
            "styling_tips": "Perfect with cropped trousers or midi skirts for a polished finish."
        }
    },
    {
        "category": "clothing",
        "sub_category": "Emerald Midi Dress",
        "body_region": "full_body",
        "image_url": "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400",
        "mask_url": "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400",
        "metadata_json": {
            "colors": ["Emerald", "Green"],
            "material": "Satin",
            "vibe": "chic",
            "season": "Summer",
            "description": "An elegant emerald satin midi dress with a flattering cowl neckline.",
            "styling_tips": "Add strappy heels and a clutch for date night or special occasions."
        }
    },
    {
        "category": "accessory",
        "sub_category": "Leather Tote Bag",
        "body_region": "accessory",
        "image_url": "https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=400",
        "mask_url": "https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=400",
        "metadata_json": {
            "colors": ["Black"],
            "material": "Leather",
            "vibe": "minimalist",
            "season": "All Seasons",
            "description": "A spacious structured leather tote with elegant gold hardware.",
            "styling_tips": "Your everyday essential—pairs with everything from workwear to weekend outfits."
        }
    },
    {
        "category": "clothing",
        "sub_category": "Cashmere Sweater",
        "body_region": "top",
        "image_url": "https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=400",
        "mask_url": "https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=400",
        "metadata_json": {
            "colors": ["Camel", "Beige"],
            "material": "Cashmere",
            "vibe": "minimalist",
            "season": "Winter",
            "description": "Ultra-soft cashmere crewneck in a warm camel tone. Timeless luxury for cold days.",
            "styling_tips": "Layer over a collared shirt or wear alone with gold accessories."
        }
    },
    {
        "category": "clothing",
        "sub_category": "Pleated Midi Skirt",
        "body_region": "bottom",
        "image_url": "https://images.unsplash.com/photo-1583496661160-fb5886a0uj9a?w=400",
        "mask_url": "https://images.unsplash.com/photo-1583496661160-fb5886a0uj9a?w=400",
        "metadata_json": {
            "colors": ["Sage", "Green"],
            "material": "Satin",
            "vibe": "boho",
            "season": "Spring",
            "description": "A flowing sage green pleated midi skirt with elegant movement.",
            "styling_tips": "Pair with a fitted knit top and ankle boots for a balanced silhouette."
        }
    }
]

# Demo outfits composed of the items above
DEMO_OUTFITS = [
    {
        "name": "Office Power Look",
        "occasion": "Work",
        "vibe": "Classic",
        "item_indices": [0, 2, 3],  # Silk Blouse, Jeans, Loafers
        "score": 9.2,
        "reasoning": "This combination balances professional elegance with modern ease. The silk blouse elevates casual denim, while tan loafers tie the warm tones together."
    },
    {
        "name": "Date Night Elegance",
        "occasion": "Evening",
        "vibe": "Chic",
        "item_indices": [4, 3, 5],  # Emerald Dress, Loafers, Tote (would swap for heels ideally)
        "score": 9.5,
        "reasoning": "The emerald satin creates a stunning statement. The structured accessories keep the look grounded and sophisticated."
    },
    {
        "name": "Weekend Brunch",
        "occasion": "Casual",
        "vibe": "Minimalist",
        "item_indices": [6, 7, 3],  # Cashmere Sweater, Pleated Skirt, Loafers
        "score": 8.8,
        "reasoning": "Soft cashmere meets flowing pleats for an effortlessly chic weekend outfit. The neutral palette is timelessly elegant."
    },
    {
        "name": "Smart Casual Friday",
        "occasion": "Business Casual",
        "vibe": "Classic",
        "item_indices": [1, 0, 2, 3],  # Blazer, Blouse, Jeans, Loafers
        "score": 9.4,
        "reasoning": "The navy blazer transforms jeans into boardroom-ready attire. Cream silk adds a luxe touch beneath structured tailoring."
    }
]


def seed_database():
    # Create tables
    SQLModel.metadata.create_all(engine)
    print("✓ Tables created")
    
    with Session(engine) as session:
        # Get or create demo user
        user = session.query(User).first()
        if not user:
            user = User(
                email="demo@closet.ai",
                hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.RBnSdwUDljC4e.",
                full_name="Demo User"
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            print("✓ Demo user created")
        else:
            print("✓ Using existing user")
        
        # Clear existing items and outfits
        session.query(Outfit).delete()
        session.query(ClothingItem).delete()
        session.commit()
        print("✓ Cleared existing items")
        
        # Add clothing items
        item_ids = []
        for item_data in DEMO_ITEMS:
            item = ClothingItem(
                user_id=user.id,
                category=item_data["category"],
                sub_category=item_data["sub_category"],
                body_region=item_data["body_region"],
                image_url=item_data["image_url"],
                mask_url=item_data["mask_url"],
                metadata_json=item_data["metadata_json"]
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            item_ids.append(item.id)
            print(f"  + {item.sub_category}")
        
        print(f"✓ Added {len(item_ids)} clothing items")
        
        # Add outfits
        for outfit_data in DEMO_OUTFITS:
            outfit_item_ids = [item_ids[i] for i in outfit_data["item_indices"]]
            outfit = Outfit(
                user_id=user.id,
                name=outfit_data["name"],
                occasion=outfit_data["occasion"],
                vibe=outfit_data["vibe"],
                items=json.dumps(outfit_item_ids),  # Store as JSON string
                score=outfit_data["score"],
                reasoning=outfit_data["reasoning"],
                created_by="ai"
            )
            session.add(outfit)
            print(f"  + {outfit.name}")
        
        session.commit()
        print(f"✓ Added {len(DEMO_OUTFITS)} outfits")
        
    print("\n🎉 Demo data seeded successfully!")
    print("   - 8 clothing items")
    print("   - 4 curated outfits")


if __name__ == "__main__":
    seed_database()
