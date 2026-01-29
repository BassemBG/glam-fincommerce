"""Debug script to test web scraping"""
import requests
from bs4 import BeautifulSoup

url = "https://noonclo.com/collections/pantalon"

print(f"🔍 Fetching {url}...")
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
response = requests.get(url, headers=headers, timeout=10)
print(f"✓ Status: {response.status_code}")
print(f"✓ Content length: {len(response.text)} chars\n")

soup = BeautifulSoup(response.text, "html.parser")

# Find product containers
products = soup.select("div.grid-product")
print(f"🛍️ Found {len(products)} product divs with class 'grid-product'\n")

# Inspect first 3 products
for i, product in enumerate(products[:3], 1):
    print(f"=== Product {i} ===")
    
    # Find title
    title = product.select_one("h3, h2, .grid-product__title, a.grid-product__link")
    if title:
        print(f"  Title: {title.get_text(strip=True)[:60]}")
    
    # Find image
    img = product.find("img")
    if img:
        print(f"  Image attributes:")
        for attr in ['src', 'data-src', 'data-srcset', 'data-original', 'alt']:
            val = img.get(attr)
            if val:
                print(f"    {attr}: {str(val)[:100]}")
    
    # Find price
    price = product.select_one(".grid-product__price, [class*='price']")
    if price:
        print(f"  Price: {price.get_text(strip=True)[:50]}")
    
    # Find link
    link = product.select_one("a[href*='product']")
    if link:
        print(f"  Link: {link.get('href')[:80]}")
    
    print()

