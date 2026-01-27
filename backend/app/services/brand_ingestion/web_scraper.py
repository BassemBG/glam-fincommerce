import requests
import os
import logging
from typing import Dict, List, Optional
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
if not SERPER_API_KEY:
    logger.warning("SERPER_API_KEY not found in environment. Serper search will be skipped.")


def _clean_text(value: Optional[str], max_length: int = 300) -> str:
    """Normalize whitespace, strip control chars, decode entities, and trim."""
    if not value:
        return ""
    import re
    import html

    # Decode HTML entities
    cleaned = html.unescape(value)

    # Remove control/private-use chars (e.g., \ue417) and excess underscores
    cleaned = re.sub(r"[\u0000-\u001f\u007f-\u009f\ue000-\uf8ff]", " ", cleaned)
    cleaned = re.sub(r"_+", " ", cleaned)

    # Collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Drop leading/trailing punctuation noise
    cleaned = cleaned.strip("|:-•·").strip()

    # Limit length
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip() + "..."

    return cleaned

# Exclude patterns for non-product elements
EXCLUDE_PATTERNS = [
    r'^(about|contact|blog|news|faq|help|support|cart|checkout|login|register|account)',
    r'(navigation|menu|header|footer|sidebar|banner|newsletter)',
    r'(category|categories|collection|collections)$',
    r'^(home|shop|store|promotions?)$',
    r'(social|media|instagram|facebook|twitter)',
    r'^(nouveaux?\s+produits?|new\s+products?)$',
    r'^(catégories?|cat)$',
]


def _is_valid_product(product: Dict) -> bool:
    """
    Validate that a product has all required fields and is not a UI element.
    
    Required:
    - product_name (non-empty, not a navigation element)
    - image_url (MUST be valid http/https URL) - CRITICAL for embeddings
    - description OR price (some content)
    
    Returns:
        True if product is valid, False otherwise
    """
    import re
    
    # Check required fields exist (handle None values)
    product_name = (product.get("product_name") or "").strip()
    image_url = (product.get("image_url") or "").strip()
    description = (product.get("description") or "").strip()
    price = (product.get("price_text") or "").strip()
    
    # Must have name
    if not product_name or len(product_name) < 3:
        logger.debug(f"Rejected: No valid product name")
        return False
    
    # CRITICAL: Must have image URL (http/https) - needed for image embeddings
    if not image_url or not image_url.startswith(("http://", "https://")):
        logger.debug(f"Rejected '{product_name}': MISSING IMAGE - cannot generate embeddings")
        return False
    
    # Must have description OR price
    if not description and not price:
        logger.debug(f"Rejected '{product_name}': No description or price")
        return False
    
    # Exclude navigation/UI elements by name pattern
    name_lower = product_name.lower()
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, name_lower, re.IGNORECASE):
            logger.debug(f"Rejected '{product_name}': Matches exclude pattern '{pattern}'")
            return False
    
    # Exclude very short descriptions (likely UI text)
    if description and len(description) < 20 and not price:
        logger.debug(f"Rejected '{product_name}': Description too short and no price")
        return False
    
    logger.debug(f"✓ Valid product: {product_name}")
    return True


def scrape_brand_website(url: str, brand_name_override: Optional[str] = None) -> Dict:
    """
    Enhanced brand website scraping with:
    1. Brand name extraction from metadata
    2. Product crawling via Serper API
    3. Image + description extraction for embeddings
    
    Args:
        url: Brand website URL
        brand_name_override: Optional override for brand name
    
    Returns:
        Dict with brand_name, products (with images/descriptions), and raw_text
    """
    try:
        # Step 1: Extract brand name from metadata/URL
        brand_name = brand_name_override or _extract_brand_name_from_metadata(url) or _extract_brand_name(url)
        logger.info(f"🏢 Brand detected: {brand_name}")
        
        # Step 2: Fetch homepage for context
        logger.info(f"🌐 Fetching homepage for {brand_name}...")
        homepage_content = _fetch_page(url)
        
        # Step 3: Crawl products using Serper API
        logger.info(f"🔍 Crawling products for {brand_name} using Serper...")
        products = _crawl_products_with_serper(url, brand_name)
        
        if not products:
            # Fallback: Extract from homepage HTML
            logger.warning(f"⚠️ Serper returned no products, falling back to HTML parsing...")
            products = _extract_products_from_html(homepage_content, url)
        
        # Step 4: Build raw text for LLM
        raw_text = _build_raw_text(homepage_content, brand_name, products)
        
        logger.info(f"✅ Extracted {len(products)} products for {brand_name}")
        
        return {
            "brand_name": brand_name,
            "products": products,
            "raw_text": raw_text
        }
        
    except Exception as e:
        logger.error(f"❌ Scraping error: {str(e)}")
        return {
            "brand_name": brand_name_override or _extract_brand_name(url),
            "products": [],
            "raw_text": ""
        }


def _extract_brand_name_from_metadata(url: str) -> Optional[str]:
    """
    Extract brand name from website metadata:
    1. og:site_name meta tag (preferred)
    2. title tag (fallback)
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Try og:site_name first
        og_site = soup.find("meta", property="og:site_name")
        if og_site and og_site.get("content"):
            logger.info(f"📌 Brand name from og:site_name: {og_site.get('content')}")
            return og_site.get("content").strip()
        
        # Fallback to title
        title = soup.find("title")
        if title and title.string:
            title_text = title.string.strip()
            # Clean title (remove common suffixes)
            title_text = title_text.replace(" | Home", "").replace(" - Home", "").split("|")[0].split("-")[0].strip()
            if len(title_text) < 50:  # Sanity check
                logger.info(f"📌 Brand name from title: {title_text}")
                return title_text
        
        return None
    except Exception as e:
        logger.warning(f"Could not extract brand name from metadata: {e}")
        return None


def _extract_brand_name(url: str) -> str:
    """Fallback: Extract brand name from domain"""
    domain = urlparse(url).netloc.replace("www.", "")
    brand_name = domain.split(".")[0].capitalize()
    logger.info(f"📌 Brand name from domain: {brand_name}")
    return brand_name


def _crawl_products_with_serper(base_url: str, brand_name: str) -> List[Dict]:
    """
    Crawl brand products using Serper API
    Extracts first 10 products with image URLs and descriptions
    """
    if not SERPER_API_KEY:
        logger.warning("⚠️ SERPER_API_KEY not configured, skipping Serper crawl")
        return []
    
    try:
        domain = urlparse(base_url).netloc.replace("www.", "")
        # More specific query to get actual product pages with images
        query = f"site:{domain} (buy OR shop OR product) -category -blog -about"
        
        logger.info(f"🔎 Querying Serper for products on {domain}...")
        
        response = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": SERPER_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "q": query,
                "num": 10,
                "gl": "us",
                "hl": "en"
            },
            timeout=15
        )
        
        logger.info(f"Serper HTTP {response.status_code} (body {len(response.text)} chars)")
        if response.status_code != 200:
            logger.warning(f"Serper API error: {response.status_code} - {response.text[:300]}")
            return []
        
        data = response.json()
        products = []
        
        # Extract products from search results
        if "knowledge_graph" in data and "attributes" in data["knowledge_graph"]:
            # Try knowledge graph first
            logger.info("📊 Extracting from knowledge graph...")
            attributes = data["knowledge_graph"]["attributes"]
            for attr, value in list(attributes.items())[:10]:
                if value and isinstance(value, str):
                    products.append({
                        "product_name": attr[:100],
                        "description": value[:500],
                        "image_url": None,
                        "source": "serper_knowledge_graph"
                    })
        
        if not products:
            organic_count = len(data.get("organic", [])) if isinstance(data, dict) else 0
            logger.info(f"🔗 Organic results: {organic_count}")
        
        # Extract from organic results with strict validation
        if not products and "organic" in data:
            for item in data["organic"][:20]:  # Try more, filter down to 10 valid
                product = {
                    "product_name": _clean_text(item.get("title", ""), 120),
                    "description": _clean_text(item.get("snippet", ""), 500),
                    "image_url": item.get("image"),
                    "product_url": item.get("link"),
                    "price_text": None,
                    "source": "serper_organic"
                }
                
                # Validate product before adding
                if _is_valid_product(product):
                    products.append(product)
                    if len(products) >= 10:
                        break
                else:
                    logger.debug(f"Serper drop: missing image or invalid product → {product.get('product_name')}")
        
        logger.info(f"✅ Serper found {len(products)} valid products")
        return products[:10]  # Limit to first 10 valid
        
    except Exception as e:
        logger.error(f"Serper crawling failed: {e}")
        return []


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
                
                # Look for image in the element
                image_elem = element.select_one("img")
                image_url = None
                if image_elem:
                    image_url = image_elem.get("src") or image_elem.get("data-src")
                    if image_url and not image_url.startswith("http"):
                        image_url = urljoin(base_url, image_url)
                
                if len(product_text) > 15:
                    product = {
                        "product_name": _clean_text(name_elem.get_text(strip=True), 120),
                        "description": _clean_text(product_text, 600),
                        "price_text": price,
                        "image_url": image_url,
                        "source": "html_parsing"
                    }
                    # Validate before adding
                    if _is_valid_product(product):
                        products.append(product)
        
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

