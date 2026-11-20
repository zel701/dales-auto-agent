"""Pricing targets shared by the customer strategy email and dealer negotiation.

The discount we promise the customer in the strategy email is the same number we
hold the dealer to at negotiation stage 3, so both sides read it from here.
"""

from __future__ import annotations

TARGET_DISCOUNT = 0.12


def target_price(
    msrp: float,
    destination: float = 0.0,
    discount: float = TARGET_DISCOUNT,
) -> float:
    """Our goal vehicle price: (MSRP + destination) discounted by `discount`.

    Vehicle price only — excludes taxes, doc fees, and dealer add-ons, so it is
    comparable to a dealer's pre-tax quote, never to an out-the-door total.
    """
    return (msrp + destination) * (1 - discount)
