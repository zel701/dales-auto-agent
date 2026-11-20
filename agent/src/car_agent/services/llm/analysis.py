"""Analysis email task: generate a customer-facing market analysis from inventory data."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from car_agent.clients.marketcheck import extract_photo_url
from car_agent.domain.pricing import TARGET_DISCOUNT
from car_agent.services.llm._base import invoke_text

_SYSTEM = """You are an expert car buying advisor. Generate an analysis email for a customer who is interested in buying a specific car.

You will receive context including: the car they want (with the trim(s) and color(s) they're open to — they may have selected multiple), MarketCheck inventory data from nearby dealerships, and a target discount percentage.

Generate an email with exactly 3 sections. Return your response as a JSON object with two fields:
- "subject": a compelling email subject line
- "html_body": the email body as HTML with inline styles

The HTML must use inline styles (not CSS classes) for email client compatibility. Use this design system:
- Section headers: font-family: 'Merriweather', Georgia, serif; font-size: 20px; color: #161616; font-weight: 700
- Body text: font-family: 'Lato', Arial, sans-serif; font-size: 15px; color: #4a4a4a; line-height: 1.6
- Accent color: #ff0083 (use sparingly for emphasis)
- Background cards: background-color: #f7f7f7; border-radius: 8px; padding: 16px
- Price text: font-size: 20px; font-weight: 700; color: #161616

The 3 sections:

1. **Great Choice** — Affirm their choice in AT MOST 2 sentences (50 words max, hard limit). Pick the two or three most compelling specifics — features, reliability, safety ratings, fuel economy, value, whatever fits this car best — and state them plainly rather than elaborating on each. Be knowledgeable and enthusiastic but not salesy; no closing flourish.

2. **What We Found** — Summarize the inventory search results:
   - Show the price range (min-max) if available
   - Display up to 5 notable listings. Render each listing as its OWN <table> (one card = one table) with width="100%", cellpadding="0", cellspacing="0", style="background-color: #f7f7f7; border-radius: 8px; margin-bottom: 12px;". Stack the cards vertically.
   - Each card table has exactly TWO rows:
     - **Header row** — a single <td> with colspan="2" style="padding: 16px 16px 8px 16px;". Contains, in this order:
       - Line 1: Trim level — font-size: 16px; font-weight: 700; color: #161616.
       - Line 2: MSRP formatted as currency ($XX,XXX); if msrp is null, show price instead — font-size: 20px; font-weight: 700; color: #161616.
       - Line 3: Dealer name, then city/state — font-size: 13px; color: #777.
       - Availability label only if needed (new line, font-size 13px, color #777): if in_transit is true show "In Transit"; if vehicle_status is "coming soon" show "Coming Soon"; if vehicle_status is "available" show nothing.
     - **Body row** — exactly TWO <td> cells:
       1. Photo cell: width="180" valign="middle" align="left" style="padding: 8px 16px 16px 16px;". Inside, an <img> with the listing's photo_url, width="180" height="135", style="border-radius: 6px; object-fit: cover; display: block;". If photo_url is null, render a flat grey block instead: <div style="width: 180px; height: 135px; background-color: #e5e5e5; border-radius: 6px;"></div>.
       2. CTA cell: valign="middle" align="right" style="padding: 8px 16px 16px 16px;". Inside, an <a href="{vdp_url}" style="display: inline-block; background-color: #ff0083; color: #ffffff; font-family: 'Lato', Arial, sans-serif; font-size: 14px; font-weight: 600; text-decoration: none; padding: 10px 18px; border-radius: 6px; white-space: nowrap;">View Listing</a>. If vdp_url is null, leave the cell empty (do not omit the cell — keep the column structure consistent).
   - Use fixed pixel widths on the photo cell (not percentages) — Outlook requires this for reliable rendering.
   - Format all prices as currency ($XX,XXX)

3. **Our Recommendation** — Actionable advice based on inventory:
   - If total_found <= 3: Inventory is limited. Suggest expanding search radius or being flexible on color/trim to find better deals. Be encouraging, not discouraging.
   - If total_found > 3: Good inventory available. Recommend targeting {target_discount_pct}% below MSRP as a starting negotiation point. Calculate and show the specific target price.
   - If no listings found: Suggest the car may be in high demand in their area. Recommend expanding radius significantly or checking back soon.

Keep the tone friendly, professional, and helpful. Write as if you're a knowledgeable friend who happens to be a car expert. Do NOT mention that you are an AI.

Respond ONLY with the JSON object, no other text."""


class AnalysisEmail(BaseModel):
    subject: str
    html_body: str


async def generate_analysis_email(
    car_info: dict[str, str],
    listings: list[dict[str, Any]],
    num_found: int,
) -> AnalysisEmail:
    """Generate the analysis email subject + HTML body.

    Falls back to the raw model output as `html_body` if the response is not
    valid JSON — the prompt enforces JSON but the LLM occasionally drifts and
    we'd rather send a degraded email than fail the request.
    """
    context = _build_context(car_info, listings, num_found)
    user_prompt = (
        "Generate an analysis email for this customer.\n\n"
        f"Context:\n{json.dumps(context, indent=2)}"
    )

    text = await invoke_text(task="analysis_email", system=_SYSTEM, user=user_prompt)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = {}

    make = car_info["make"]
    model = car_info["model"]
    trims_label = "/".join(car_info.get("trims") or [])
    return AnalysisEmail(
        subject=parsed.get("subject", f"Your {make} {model} {trims_label} Market Analysis"),
        html_body=parsed.get("html_body", text),
    )


def _build_context(
    car_info: dict[str, str],
    listings: list[dict[str, Any]],
    num_found: int,
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "car": {
            "make": car_info["make"],
            "model": car_info["model"],
            "trims": car_info.get("trims") or [],
            "colors": car_info.get("colors") or [],
        },
        "search": {
            "zipcode": car_info["zipcode"],
            "radius_miles": car_info["radius"],
        },
        "results": {
            "total_found": num_found,
            "listings": [
                {
                    "price": l.get("price", 0),
                    "msrp": l.get("msrp"),
                    "trim": l.get("trim", ""),
                    "exterior_color": l.get("exterior_color", ""),
                    "dealer_name": l.get("dealer_name", ""),
                    "dealer_city": l.get("dealer_city", ""),
                    "dealer_state": l.get("dealer_state", ""),
                    "distance_miles": round(l.get("distance_miles", 0), 1),
                    "in_transit": l.get("in_transit", False),
                    "vehicle_status": l.get("vehicle_status"),
                    "vdp_url": l.get("vdp_url"),
                    "photo_url": l.get("photo_url") or extract_photo_url(l.get("raw_json")),
                }
                for l in listings[:10]
            ],
        },
        "target_discount_pct": int(TARGET_DISCOUNT * 100),
    }

    prices = [l.get("price", 0) for l in listings if l.get("price")]
    msrps = [l.get("msrp", 0) for l in listings if l.get("msrp")]
    if prices:
        context["results"]["price_range"] = {
            "min": min(prices),
            "max": max(prices),
            "avg": round(sum(prices) / len(prices)),
        }
    if msrps:
        avg_msrp = sum(msrps) / len(msrps)
        context["results"]["avg_msrp"] = round(avg_msrp)
        context["results"]["target_price"] = round(avg_msrp * (1 - TARGET_DISCOUNT))

    return context
