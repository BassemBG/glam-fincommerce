"""
Test product validation logic
Ensures non-products are filtered out before storage
"""

from app.services.brand_ingestion.web_scraper import _is_valid_product

def test_validation():
    print("=" * 80)
    print("PRODUCT VALIDATION TEST")
    print("=" * 80)
    
    test_cases = [
        # Valid products
        {
            "name": "✓ Valid: Product with all fields",
            "product": {
                "product_name": "Blue Denim Jacket",
                "image_url": "https://example.com/jacket.jpg",
                "description": "High quality denim jacket with metal buttons",
                "price_text": "$59.99"
            },
            "expected": True
        },
        {
            "name": "✓ Valid: Product with description only",
            "product": {
                "product_name": "Red Summer Dress",
                "image_url": "https://example.com/dress.jpg",
                "description": "Beautiful summer dress perfect for beach days",
            },
            "expected": True
        },
        {
            "name": "✓ Valid: Product with price only",
            "product": {
                "product_name": "Cotton T-Shirt",
                "image_url": "https://example.com/tshirt.jpg",
                "price_text": "€25.00"
            },
            "expected": True
        },
        
        # Invalid products (should be filtered)
        {
            "name": "✗ Invalid: Navigation element",
            "product": {
                "product_name": "Promotions",
                "image_url": "https://example.com/banner.jpg",
                "description": "promo exist vente en ligne vêtement hommes"
            },
            "expected": False
        },
        {
            "name": "✗ Invalid: Category page",
            "product": {
                "product_name": "Catégories",
                "image_url": "https://example.com/cat.jpg",
                "description": "Products. New Products. Montre. 59,99 TND."
            },
            "expected": False
        },
        {
            "name": "✗ Invalid: New products section",
            "product": {
                "product_name": "Nouveaux produits",
                "image_url": "https://example.com/new.jpg",
                "description": "Nos nouveaux produits vente en ligne"
            },
            "expected": False
        },
        {
            "name": "✗ Invalid: Social media link",
            "product": {
                "product_name": "social media",
                "image_url": "https://example.com/social.jpg",
                "description": "Follow us on Instagram"
            },
            "expected": False
        },
        {
            "name": "✗ Invalid: No image URL",
            "product": {
                "product_name": "Nice Product",
                "description": "Great product description"
            },
            "expected": False
        },
        {
            "name": "✗ Invalid: No description or price",
            "product": {
                "product_name": "Product Name",
                "image_url": "https://example.com/img.jpg"
            },
            "expected": False
        },
        {
            "name": "✗ Invalid: Too short description",
            "product": {
                "product_name": "JEANS",
                "image_url": "https://example.com/jeans.jpg",
                "description": "Jean"
            },
            "expected": False
        },
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        result = _is_valid_product(test["product"])
        status = "PASS" if result == test["expected"] else "FAIL"
        
        if result == test["expected"]:
            passed += 1
            print(f"✓ {status}: {test['name']}")
        else:
            failed += 1
            print(f"✗ {status}: {test['name']}")
            print(f"   Expected: {test['expected']}, Got: {result}")
    
    print("\n" + "=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    return failed == 0

if __name__ == "__main__":
    success = test_validation()
    exit(0 if success else 1)
