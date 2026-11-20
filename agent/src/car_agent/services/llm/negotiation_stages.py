"""LLM tasks for the 5-stage dealer negotiation flow.

Each stage has:
- A draft instruction (appended to the shared system prompt) used to generate
  the outbound email subject + body.
- A classifier instruction used to parse the dealer's reply into a structured
  outcome that determines whether the stage advances.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from pydantic import BaseModel

from car_agent.domain.pricing import TARGET_DISCOUNT, target_price
from car_agent.services.llm._base import invoke_json, invoke_model

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Draft prompts
# ---------------------------------------------------------------------------

_DRAFT_SYSTEM = """You are a professional car buyer's agent. A private client has retained you to find and negotiate their next vehicle — you are shopping on their behalf, never for yourself, and you never let the dealer mistake you for the buyer.

Hold to these in every email:
- Write in the first person as the agent ("I"), and call the person you represent "my client".
- Refer to your client as "they/them". Never guess their gender.
- Do not give out your client's name or contact details until the dealer has agreed a price and you are arranging the signing appointment.
- Never reveal your client's maximum budget, and never name the other dealerships you are contacting.
- Sign every email as "Your Buyer's Agent".

Write concisely, professionally, and warmly. Plain text only — no HTML, no markdown."""

_STAGE_DRAFT_INSTRUCTIONS: dict[int, str] = {
    1: (
        "TASK: Confirm vehicle availability.\n"
        "Write a brief email asking the dealer to confirm which of the listed "
        "vehicles are still available for immediate purchase or near-term delivery. "
        "Reference each vehicle by its VIN and color. Ask them to reply with "
        "current availability for each VIN.\n"
        "Keep the request itself under 4 sentences."
    ),
    2: (
        "TASK: Request a full price breakdown.\n"
        "The dealer confirmed availability. Write an email requesting the "
        "complete out-the-door (OTD) price breakdown for each available vehicle, "
        "specifically: base MSRP, any dealer markup or adjustments, destination "
        "charge, dealer doc fee, taxes, and total OTD price.\n"
        "Keep it concise and direct."
    ),
    3: (
        "TASK: Negotiate a discount.\n"
        "You have received pricing. Write an email making a competitive offer. "
        "Mention that your client is comparing multiple dealerships and is ready "
        "to move quickly for the right price. Ask for their best offer.\n"
        "Do not name a specific maximum budget — simply ask for their best price."
    ),
    4: (
        "TASK: Schedule a meeting to finalize the deal.\n"
        "The dealer agreed to a price. Write a brief, warm email thanking them "
        "and asking for their availability this week to come in and sign the "
        "paperwork. Mention the client is ready to complete the transaction.\n"
        "Keep it friendly and concise."
    ),
    5: (
        "TASK: Confirm the appointment.\n"
        "Confirm the meeting time the dealer proposed. Express enthusiasm. Ask "
        "for the name of the sales contact to ask for when arriving.\n"
        "Keep it brief and positive."
    ),
}


class EmailDraft(BaseModel):
    subject: str
    body: str


_FIRST_CONTACT_PREAMBLE = (
    "NOTE: This is your first email to this dealership — nobody there has heard from "
    "you before. Open by introducing yourself before anything else: give your role "
    "(a buyer's agent) and say that you are shopping on behalf of a client who is a "
    "serious, ready buyer. Two sentences at most, then go straight into the request "
    "below.\n\n"
)

_REASK_PREAMBLE = (
    "NOTE: In their last reply the dealer did not answer our question and instead "
    "invited an in-person visit, test drive, or phone call. Politely thank them, "
    "explain that your client prefers to handle these initial details over email for "
    "now, and courteously decline the in-person invitation for the moment. Then repeat "
    "the SAME request below. Stay warm and professional; do not sound annoyed.\n\n"
)


async def draft_stage_email(
    stage: int,
    dealership: dict[str, Any],
    cars: list[dict[str, Any]],
    customer_name: Optional[str],
    thread: list[dict[str, Any]],
    stage_data: dict[str, Any],
    is_reask: bool = False,
) -> EmailDraft:
    """Draft the outbound email for the current negotiation stage."""
    instruction = _STAGE_DRAFT_INSTRUCTIONS.get(stage, _STAGE_DRAFT_INSTRUCTIONS[1])
    if is_reask:
        instruction = _REASK_PREAMBLE + instruction
    elif not thread:
        # An empty thread — not stage 1 — is what marks first contact: a stage-1
        # re-ask is still stage 1, but the dealer has already met us by then.
        instruction = _FIRST_CONTACT_PREAMBLE + instruction

    car_list = "\n".join(
        f"- VIN {c.get('vin', 'N/A')}: "
        f"{c.get('year')} {c.get('make')} {c.get('model')} {c.get('trim', '')} "
        f"{c.get('exterior_color', '')} — listed at ${c.get('price', 0):,.0f}"
        for c in cars
    )

    prior = "\n\n".join(
        f"[{'US' if m['direction'] == 'outbound' else 'DEALER'} — Stage {m['stage']}]\n"
        f"Subject: {m.get('subject', '')}\n{m['body']}"
        for m in thread[-6:]  # last 6 messages for context
    )

    user = (
        f"Dealership: {dealership.get('dealer_name')}\n"
        f"Client name (internal — withhold until arranging the signing appointment): "
        f"{customer_name or 'not provided'}\n"
        f"Vehicles:\n{car_list}\n"
        f"Stage data so far: {json.dumps(stage_data)}\n\n"
        f"{'Prior conversation (oldest first):\n' + prior if prior else ''}\n\n"
        f"{instruction}\n\n"
        f"Return a JSON object with exactly two fields: "
        f'\"subject\" (string) and \"body\" (plain-text string, no HTML).'
    )

    try:
        return await invoke_model(
            task="negotiation_draft",
            system=_DRAFT_SYSTEM,
            user=user,
            model=EmailDraft,
        )
    except Exception:
        logger.exception("Draft LLM call failed for stage %d; using fallback", stage)
        make = cars[0].get("make", "") if cars else ""
        model_ = cars[0].get("model", "") if cars else ""
        vehicle = f"{make} {model_}".strip() or "the vehicles you have listed"
        # A reviewer edits this before it goes out, but it still has to carry the
        # agent identity — an empty body gave them nothing to work from.
        return EmailDraft(
            subject=f"Inquiry — {make} {model_}",
            body=(
                "Hello,\n\n"
                "I'm a buyer's agent working on behalf of a client who is looking to "
                f"purchase {vehicle}, and I'm reaching out to a short list of "
                "dealerships on their behalf. Could you let me know what you currently "
                "have available?\n\n"
                "Thank you,\n"
                "Your Buyer's Agent"
            ),
        )


# ---------------------------------------------------------------------------
# Classify prompts
# ---------------------------------------------------------------------------

_CLASSIFY_SYSTEM = """You are analyzing a car dealership's email reply. Extract structured information from the reply. Respond ONLY with valid JSON matching the requested schema."""

_STAGE_CLASSIFY_PROMPTS: dict[int, str] = {
    1: (
        'Extract vehicle availability. Return JSON:\n'
        '{"available_vins": ["..."], "unavailable_vins": ["..."], "advance": true/false, "deflected": true/false}\n'
        'Set advance=true if at least one VIN is confirmed available or the dealer '
        'responded positively about availability without specifying VINs.\n'
        'Set deflected=true if the dealer did NOT provide availability and instead '
        'invited an in-person visit, test drive, or phone call. When deflected=true, '
        'advance must be false.'
    ),
    2: (
        'Extract pricing information. Return JSON:\n'
        '{"has_breakdown": true/false, "otd_total": <number or null>, '
        '"components": {"msrp": <number or null>, "markup": <number or null>, '
        '"destination": <number or null>, "doc_fee": <number or null>, "taxes": <number or null>}, '
        '"advance": true/false, "deflected": true/false}\n'
        'Record otd_total ONLY when the dealer states an actual out-the-door total as a '
        'concrete number. A range, an "around"/"starting at" figure, or a total that '
        'explicitly excludes taxes and fees is NOT an OTD total — leave it null.\n'
        'Fill each field in components with the number the dealer gave for it, or null if '
        'they did not give it. Set has_breakdown=true if at least one component is a '
        'concrete number.\n'
        'Set advance=true ONLY if otd_total is a concrete number AND has_breakdown is true. '
        'A bare OTD total with no itemization does NOT advance; itemized fees with no OTD '
        'total does NOT advance either.\n'
        'Set deflected=true if the dealer shared NO pricing and instead invited an '
        'in-person visit, test drive, or phone call. When deflected=true, advance must be false.'
    ),
    3: (
        'Extract the dealer\'s vehicle price and score it against our target. Return JSON:\n'
        '{"agreed": true/false, "agreed_price": <number or null>, '
        '"dealer_msrp": <number or null>, "destination": <number or null>, '
        '"dealer_adjustment": <number or null>, "effective_price": <number or null>, '
        '"discount_confirmed": true/false, "target_met": true/false, '
        '"advance": true/false, "deflected": true/false}\n'
        'The REFERENCE PRICES block above gives, per VIN, the MSRP + destination base and '
        'the TARGET price we want to reach.\n'
        'Extract the dealer\'s VEHICLE price, excluding taxes, doc fees, and add-ons:\n'
        '  dealer_msrp — the MSRP the dealer states; fall back to the reference MSRP.\n'
        '  destination — the destination/freight charge the dealer states; fall back to the '
        'reference destination.\n'
        '  dealer_adjustment — SIGNED. Positive when it LOWERS the price (discount, rebate, '
        'price reduction, incentive applied to the vehicle). Negative when it RAISES the '
        'price (dealer markup, market adjustment, addendum). null if the dealer named none.\n'
        '  effective_price = dealer_msrp + destination - dealer_adjustment. Leave it null '
        'unless every term is a concrete number.\n'
        'Set discount_confirmed=true only if dealer_adjustment is a concrete positive number, '
        'or the dealer committed to a vehicle price strictly below its MSRP + destination base.\n'
        'Set discount_confirmed=false for: holding at MSRP, "no room to move", a vague promise '
        'to work with us, "let me check with my manager", an unquantified discount, or one '
        'conditional on financing, a trade-in, or add-ons.\n'
        'Set target_met=true ONLY if effective_price is a concrete number at or below that '
        'VIN\'s TARGET price. With several VINs, target_met=true if ANY one of them meets its '
        'target. Never score an out-the-door total against the target — OTD includes taxes '
        'and fees and is expected to exceed it.\n'
        'Set agreed=true if the dealer committed to any specific final price, even one above '
        'target; agreed_price is that number.\n'
        'Set advance=true ONLY if target_met is true.\n'
        'Set deflected=true if the dealer avoided discussing price and instead invited '
        'an in-person visit, test drive, or phone call. When deflected=true, advance must be false.'
    ),
    4: (
        'Extract scheduling information. Return JSON:\n'
        '{"proposed_times": ["..."], "advance": true/false}\n'
        'Set advance=true if the dealer proposed any meeting time or asked for '
        'our availability.'
    ),
    5: (
        'Extract appointment confirmation. Return JSON:\n'
        '{"confirmed": true/false, "confirmed_time": "<string or null>", "advance": true/false}\n'
        'Set advance=true if the dealer confirmed a meeting time.'
    ),
}


def _reference_prices(
    cars: list[dict[str, Any]],
    stage_data: dict[str, Any],
) -> str:
    """Render the per-VIN price base and target that stage 3 scores an offer against.

    The base is MSRP + destination — vehicle price only, so it stays comparable to
    a dealer's pre-tax quote and never to an out-the-door total. MSRP comes from
    the listing when we have it, otherwise from whatever the dealer quoted at
    stage 2; destination is dealer-quoted only, and treated as 0 when unknown
    (which makes the target slightly conservative rather than unreachable).
    """
    stage2 = stage_data.get("2") or {}
    components = stage2.get("components") or {}
    quoted_msrp = components.get("msrp")
    destination = components.get("destination") or 0.0

    lines = []
    for c in cars:
        msrp = c.get("msrp") or quoted_msrp or c.get("price")
        if not msrp:
            lines.append(f"- VIN {c.get('vin', 'N/A')}: MSRP unknown — no target available")
            continue
        base = msrp + destination
        target = target_price(msrp, destination)
        lines.append(
            f"- VIN {c.get('vin', 'N/A')} "
            f"({c.get('year')} {c.get('make')} {c.get('model')} {c.get('trim', '')}): "
            f"MSRP ${msrp:,.0f} + destination ${destination:,.0f} = base ${base:,.0f}; "
            f"TARGET at {int(TARGET_DISCOUNT * 100)}% off base = ${target:,.0f}"
        )
    if not lines:
        return ""

    block = "REFERENCE PRICES (vehicle price only — excludes taxes, doc fees, add-ons)\n"
    block += "\n".join(lines)
    if not components.get("destination"):
        block += "\nNote: destination not quoted by the dealer; treated as $0 in the base."
    if stage2.get("otd_total"):
        block += (
            f"\nStage-2 out-the-door total quoted by this dealer: "
            f"${stage2['otd_total']:,.0f} (includes taxes and fees — not comparable to the target)."
        )
    return block


async def classify_stage_reply(
    stage: int,
    dealer_reply: str,
    stage_data: dict[str, Any],
    cars: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Classify a dealer reply for the current stage. Returns the parsed outcome dict."""
    prompt = _STAGE_CLASSIFY_PROMPTS.get(stage, _STAGE_CLASSIFY_PROMPTS[1])
    references = _reference_prices(cars or [], stage_data)
    user = (
        f"Stage: {stage}\n"
        f"Prior stage data: {json.dumps(stage_data)}\n\n"
        f"{references + '\n\n' if references else ''}"
        f"Dealer reply:\n{dealer_reply}\n\n"
        f"{prompt}"
    )

    try:
        result = await invoke_json(task="negotiation_classify", system=_CLASSIFY_SYSTEM, user=user)
        if not isinstance(result, dict):
            raise ValueError("Expected dict")
        return result
    except Exception:
        logger.exception("Classify LLM call failed for stage %d; defaulting to no-advance", stage)
        return {"advance": False}
