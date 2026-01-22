"""
🧪 TAVILY API – Clothing Price Estimator
Human-like web search + smart price filtering
USD ➜ TND conversion included
"""

import asyncio
import json
import re
import httpx
from dotenv import load_dotenv

# ================== CONFIG ==================

load_dotenv()

TAVILY_API_KEY = "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"
TAVILY_ENDPOINT = "https://api.tavily.com/search"

TND_RATE = 3.4  # 1 USD ≈ 3.4 TND

# ============================================


def usd_to_tnd(value: float) -> float:
    return round(value * TND_RATE, 1)


async def tavily_search(query: str) -> dict | None:
    """
    Perform Tavily web search
    """
    if not TAVILY_API_KEY:
        raise RuntimeError("❌ TAVILY_API_KEY not set")

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "advanced",
        "include_answer": False,
        "include_raw_content": False,
        "max_results": 10,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(TAVILY_ENDPOINT, json=payload)

    if response.status_code != 200:
        print(f"❌ Tavily error {response.status_code}: {response.text}")
        return None

    return response.json()


def parse_price_range(results: dict) -> dict | None:
    """
    Extract realistic prices only
    Avoid:
    - $5 / $6 / $1 scams
    - shipping prices
    - discounts
    """

    prices = []

    price_regex = re.compile(
        r"(?:\$|€|£|usd|eur)\s*(\d{2,4}(?:\.\d{1,2})?)",
        re.IGNORECASE,
    )

    for item in results.get("results", []):
        text = f"{item.get('title','')} {item.get('content','')}".lower()

        # Skip pages that smell like ads or coupons
        if any(x in text for x in ["coupon", "discount", "shipping", "promo"]):
            continue

        for match in price_regex.findall(text):
            try:
                value = float(match)

                # 🚫 HARD FILTER
                if 20 <= value <= 500:
                    prices.append(value)

            except ValueError:
                continue

    if len(prices) < 3:
        return None

    prices.sort()

    # -------- IQR OUTLIER REMOVAL --------
    q1 = prices[len(prices) // 4]
    q3 = prices[(len(prices) * 3) // 4]
    iqr = q3 - q1

    filtered = [
        p for p in prices
        if q1 - 1.5 * iqr <= p <= q3 + 1.5 * iqr
    ]

    if not filtered:
        return None

    median = filtered[len(filtered) // 2]

    # -------- CATEGORY --------
    if median < 40:
        category = "budget"
    elif median < 90:
        category = "mid-range"
    elif median < 200:
        category = "premium"
    else:
        category = "luxury"

    return {
        "usd": {
            "min": round(min(filtered), 2),
            "max": round(max(filtered), 2),
            "median": round(median, 2),
        },
        "tnd": {
            "min": usd_to_tnd(min(filtered)),
            "max": usd_to_tnd(max(filtered)),
            "median": usd_to_tnd(median),
        },
        "category": category,
        "exchange_rate": TND_RATE,
        "sample_prices_usd": filtered[:5],
        "price_sources": len(filtered),
    }


async def run_demo():
    queries = [
        "Pull&Bear T-shirt price",
        "Nike Air Force 1 price",
        "Zara oversized hoodie price",
        "Levi's 501 jeans price",
    ]

    for query in queries:
        print(f"\n🔍 {query}")
        results = await tavily_search(query)
        parsed = parse_price_range(results) if results else None

        if parsed:
            print(json.dumps(parsed, indent=2))
        else:
            print("❌ No reliable price found")

        await asyncio.sleep(1)


if __name__ == "__main__":
    print("🚀 Tavily Clothing Price Estimator")
    print("USD ➜ TND | Smart filtering | Human-like search\n")
    asyncio.run(run_demo())
