"""Run sample dealer replies through the stage classifiers — no email, no DB.

`classify_stage_reply` only needs an ANTHROPIC_API_KEY, so the negotiation
prompts can be exercised in isolation: no graph run, no Resend call, nothing
written anywhere. Use it to see how a prompt edit changes the advance decision.

Run from the agent directory:

  # every fixture
  uv run python -m scripts.try_classifier

  # one stage, or one named case
  uv run python -m scripts.try_classifier --stage 3
  uv run python -m scripts.try_classifier --case markup_dealer

  # show the full prompt sent to the model, and the full JSON it returned
  uv run python -m scripts.try_classifier --stage 3 --verbose

  # paste your own reply text instead of a fixture
  uv run python -m scripts.try_classifier --stage 3 --reply "We can do $29,000 out the door."

Cases assert only on `advance`, which is the field that drives the graph. The
other extracted fields are printed for eyeballing, not checked — the point is
to catch a prompt that advances when it shouldn't, or stalls when it should
move on.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from dotenv import load_dotenv

load_dotenv()

from car_agent.services.llm.negotiation_stages import (
    _reference_prices,
    classify_stage_reply,
)

# One dealership group, one car — the common shape. MSRP 31,900 + destination
# 1,145 = 33,045 base, so the 12% target lands at $29,080.
CARS = [
    {
        "vin": "4T1K61AK8RU123456",
        "year": 2026,
        "make": "Toyota",
        "model": "Camry",
        "trim": "SE",
        "exterior_color": "Celestial Silver",
        "price": 32_450,
        "msrp": 31_900,
    }
]

# What stage 2 captured, as stage 3 sees it.
STAGE2_DATA = {
    "2": {
        "has_breakdown": True,
        "otd_total": 35_900,
        "components": {
            "msrp": 31_900,
            "markup": None,
            "destination": 1_145,
            "doc_fee": 699,
            "taxes": 2_156,
        },
    }
}

CASES: list[dict] = [
    # -- Stage 2: needs an OTD total AND at least one itemized component -----
    {
        "name": "otd_with_full_breakdown",
        "stage": 2,
        "advance": True,
        "why": "total plus itemization — the whole ask",
        "reply": (
            "Happy to help. On the Celestial Silver SE:\n"
            "MSRP $31,900, destination $1,145, no dealer markup on this one.\n"
            "Doc fee is $699 and tax comes to $2,156.\n"
            "Out the door: $35,900."
        ),
    },
    {
        "name": "otd_total_only",
        "stage": 2,
        "advance": False,
        "why": "bare total, nothing itemized — used to advance, shouldn't",
        "reply": "We can do $35,900 out the door on the silver SE. Let me know.",
    },
    {
        "name": "fees_no_total",
        "stage": 2,
        "advance": False,
        "why": "itemization with no OTD total",
        "reply": (
            "Our doc fee is $699 and destination is $1,145. Tax depends on your "
            "county. MSRP is $31,900."
        ),
    },
    {
        "name": "vague_starting_at",
        "stage": 2,
        "advance": False,
        "why": '"starting around" is not a concrete total',
        "reply": "These are starting around $35k out the door depending on options.",
    },
    {
        "name": "price_excludes_tax_and_fees",
        "stage": 2,
        "advance": False,
        "why": "a total that excludes tax/fees is not an OTD total",
        "reply": "Selling price is $32,450 plus tax, title, and dealer fees.",
    },
    {
        "name": "deflect_to_visit",
        "stage": 2,
        "advance": False,
        "deflected": True,
        "why": "should re-ask, not stall",
        "reply": (
            "Best thing is to come on in and take one for a spin — pricing is "
            "easier to go through in person. When are you free this week?"
        ),
    },
    # -- Stage 3: needs the vehicle price at or below target ($29,080) -------
    {
        "name": "meets_target",
        "stage": 3,
        "advance": True,
        "why": "$28,500 including destination is under the $29,080 target",
        "reply": (
            "Spoke with my manager. Best we can do is $28,500 for the car with "
            "destination included — that's before tax, title, and doc fee."
        ),
    },
    {
        "name": "discount_short_of_target",
        "stage": 3,
        "advance": False,
        "why": "a real $1,000 discount, but $32,045 is still way above target",
        "reply": "I can knock $1,000 off MSRP for you. That puts us at $32,045 on the car.",
    },
    {
        "name": "check_with_manager",
        "stage": 3,
        "advance": False,
        "why": "the old loophole — engagement is not a discount",
        "reply": "Let me check with my manager and see what we can do on price.",
    },
    {
        "name": "otd_below_target_number",
        "stage": 3,
        "advance": False,
        "why": "an OTD figure must not be scored against the vehicle-price target",
        "reply": "We could get you out the door at $29,000 even.",
    },
    {
        "name": "markup_dealer",
        "stage": 3,
        "advance": False,
        "why": "a market adjustment raises the effective price; must not read as a discount",
        "reply": (
            "There's a $2,000 market adjustment on this one, but I could take "
            "$500 off that adjustment for you."
        ),
    },
    {
        "name": "conditional_on_financing",
        "stage": 3,
        "advance": False,
        "why": "discount contingent on financing is not a committed price",
        "reply": "If you finance with us I can get you to $29,000 on the car.",
    },
    {
        "name": "holding_firm",
        "stage": 3,
        "advance": False,
        "why": "no movement at all",
        "reply": "These are in high demand — we're selling at MSRP, no discounts right now.",
    },
]


async def run_case(case: dict, verbose: bool) -> bool:
    stage = case["stage"]
    stage_data = STAGE2_DATA if stage == 3 else {}

    if verbose:
        print(f"  reference block:\n{_reference_prices(CARS, stage_data)}\n")

    outcome = await classify_stage_reply(
        stage=stage,
        dealer_reply=case["reply"],
        stage_data=stage_data,
        cars=CARS,
    )

    got = bool(outcome.get("advance", False))
    want = case["advance"]
    ok = got == want

    # classify_stage_reply swallows LLM/parse errors and returns a bare
    # {"advance": False}. That looks identical to a correct "don't advance"
    # verdict, so a broken call would quietly pass every negative case.
    if set(outcome) == {"advance"}:
        print(f"ERROR [stage {stage}] {case['name']}: classifier fell back "
              f"(LLM or parse failure) — verdict is not from the prompt")
        print()
        return False

    print(f"{'PASS' if ok else 'FAIL'}  [stage {stage}] {case['name']}")
    print(f"      {case['why']}")
    print(f"      advance: got {got}, want {want}")

    if "deflected" in case:
        d_got = bool(outcome.get("deflected", False))
        print(f"      deflected: got {d_got}, want {case['deflected']}")
        ok = ok and d_got == case["deflected"]

    extras = {k: v for k, v in outcome.items() if k not in ("advance", "deflected")}
    if verbose:
        print(f"      full: {json.dumps(outcome, indent=8)}")
    elif extras:
        print(f"      extracted: {json.dumps(extras)}")
    print()
    return ok


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=int, choices=[1, 2, 3, 4, 5], help="only this stage")
    parser.add_argument("--case", help="only the case with this name")
    parser.add_argument("--reply", help="classify this text instead of the fixtures")
    parser.add_argument("--verbose", action="store_true", help="show prompt context and full JSON")
    args = parser.parse_args()

    if args.reply:
        if not args.stage:
            parser.error("--reply requires --stage")
        stage_data = STAGE2_DATA if args.stage == 3 else {}
        if args.verbose:
            print(_reference_prices(CARS, stage_data), "\n")
        outcome = await classify_stage_reply(
            stage=args.stage,
            dealer_reply=args.reply,
            stage_data=stage_data,
            cars=CARS,
        )
        print(json.dumps(outcome, indent=2))
        return 0

    cases = CASES
    if args.stage:
        cases = [c for c in cases if c["stage"] == args.stage]
    if args.case:
        cases = [c for c in cases if c["name"] == args.case]
    if not cases:
        print("No matching cases.", file=sys.stderr)
        return 2

    results = [await run_case(c, args.verbose) for c in cases]
    passed = sum(results)
    print(f"{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
