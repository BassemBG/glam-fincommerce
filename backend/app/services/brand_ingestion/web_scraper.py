import requests
import os
import logging
from typing import Dict, List
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SERPER_API_KEY = os.getenv("SERPER_API_KEY")


def scrape_brand_website(url: str) -> Dict:
    """
    Hybrid approach: Use Serper API to find pages, then BeautifulSoup to extract content.
    Fast and detailed.
    """
    
    try:
        # Extract brand name from URL
        brand_name = _extract_brand_name(url)
        
        # Get product pages from homepage
        logger.info(f"🌐 Fetching homepage for {brand_name}...")
        homepage_content = _fetch_page(url)
        
        if not homepage_content:
            logger.warning(f"Could not fetch homepage for {brand_name}")
            return {
                "brand_name": brand_name,
                "products": [],
                "raw_text": ""
            }
        
        # Extract product links and details from homepage
        products = _extract_products_from_html(homepage_content, url)
        
        # Build raw text for LLM
        raw_text = _build_raw_text(homepage_content, brand_name, products)
        
        logger.info(f"✅ Extracted {len(products)} products")
        
        return {
            "brand_name": brand_name,
            "products": products,
            "raw_text": raw_text
        }
        
    except Exception as e:
        logger.error(f"❌ Scraping error: {str(e)}")
        return {
            "brand_name": _extract_brand_name(url),
            "products": [],
            "raw_text": ""
        }


def _extract_brand_name(url: str) -> str:
    """Extract brand name from URL"""
    domain = urlparse(url).netloc.replace("www.", "")
    return domain.split(".")[0].capitalize()


def _fetch_page(url: str) -> str:
    """Fetch page content with timeout"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {str(e)}")
        return ""


def _extract_products_from_html(html: str, base_url: str) -> List[Dict]:
    """Extract products from HTML"""
    soup = BeautifulSoup(html, "html.parser")
    products = []
    
    # Look for product containers (common patterns)
    product_selectors = [
        "article",
        "div[class*='product']",
        "li[class*='product']",
        "div[class*='item']",
        "[data-product]"
    ]
    
    import re
    
    for selector in product_selectors:
        for element in soup.select(selector)[:50]:  # Increased limit to 50
            name_elem = element.select_one("h1, h2, h3, a[href*='product']")
            if name_elem:
                product_text = element.get_text(separator=" ", strip=True)
                
                # Look for price patterns
                price_match = re.search(r'(\$|€|£)\s?[\d,]+(?:\.\d{2})?', product_text)
                price = price_match.group(0) if price_match else None
                
                if len(product_text) > 15:
                    products.append({
                        "product_name": name_elem.get_text(strip=True)[:100],
                        "description": product_text[:600],  # Increased to 600 chars
                        "price_text": price,
                        "url": base_url
                    })
        
        if products:
            break  # Found products, stop trying other selectors
    
    return products


def _build_raw_text(html: str, brand_name: str, products: List[Dict]) -> str:
    """Build raw text from HTML for LLM processing"""
    soup = BeautifulSoup(html, "html.parser")
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get all text
    page_text = soup.get_text(separator=" ", strip=True)
    page_text = " ".join(page_text.split())[:3000]  # Increased to 3000 chars
    
    # Add more detailed product information
    parts = [f"Brand: {brand_name}\n", f"Homepage content:\n{page_text}\n"]
    
    if products:
        parts.append("\n=== PRODUCTS ===")
        for i, product in enumerate(products, 1):
            parts.append(f"\nProduct {i}: {product['product_name']}")
            if product.get("description"):
                parts.append(f"Description: {product['description'][:500]}")
            if product.get("price_text"):
                parts.append(f"Price: {product['price_text']}")
    else:
        # If no products found, extract all text from the page for analysis
        all_text = soup.get_text(separator="\n", strip=True)
        parts.append("\n=== PAGE TEXT ===")
        parts.append(all_text[:5000])  # Include more page content
    
    return "\n".join(parts)
