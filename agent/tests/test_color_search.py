"""Tests for two-tier color search (base buckets + marketing-name post-filter)
and grade -> MarketCheck trim variant expansion."""

from __future__ import annotations

from car_agent.clients.marketcheck import build_search_params, expand_trim_variants
from car_agent.services.color_search import (
    base_color_buckets,
    color_matches,
    filter_by_color,
)


# ---------------------------------------------------------------------------
# base_color_buckets
# ---------------------------------------------------------------------------


def test_buckets_for_known_colors():
    assert base_color_buckets(["Supersonic Red"]) == ["Red"]
    got = base_color_buckets(["Supersonic Red", "Wind Chill Pearl"])
    assert got is not None and set(got) == {"Red", "White"}


def test_buckets_none_when_no_colors():
    assert base_color_buckets(None) is None
    assert base_color_buckets([]) is None


def test_buckets_none_for_unbucketed_color():
    # Everest has live inventory but MarketCheck leaves it unbucketed —
    # applying any base filter would drop all of it.
    assert base_color_buckets(["Everest"]) is None
    assert base_color_buckets(["Supersonic Red", "Everest"]) is None


def test_buckets_none_for_unknown_color():
    assert base_color_buckets(["Chartreuse Dream"]) is None


# ---------------------------------------------------------------------------
# color matching / post-filter
# ---------------------------------------------------------------------------


def test_matches_dealer_suffix_variants():
    req = ["Supersonic Red"]
    assert color_matches("Supersonic Red", req)
    assert color_matches("Supersonic Red 1", req)
    assert color_matches("Supersonic Red [extra_cost_color]", req)
    assert color_matches("Supersonic Red With Midnight Black Metallic Roof", req)
    assert not color_matches("Ruby Flare Pearl", req)
    assert not color_matches(None, req)


def test_matches_two_tone_and_w_slash_shorthand():
    req = ["Wind Chill Pearl with Midnight Black Metallic roof"]
    assert color_matches("Wind Chill Pearl With Midnight Black Metallic Roof", req)
    assert color_matches("Wind Chill Pearl w/Midnight Black Metallic Roof", req)
    assert not color_matches("Wind Chill Pearl", req)


def test_filter_keeps_exact_matches():
    listings = [
        {"exterior_color": "Supersonic Red 1"},
        {"exterior_color": "Ruby Flare Pearl"},
        {"exterior_color": None},
    ]
    kept, exact = filter_by_color(listings, ["Supersonic Red"])
    assert exact is True
    assert kept == [{"exterior_color": "Supersonic Red 1"}]


def test_filter_falls_back_to_near_matches():
    listings = [{"exterior_color": "Ruby Flare Pearl"}]
    kept, exact = filter_by_color(listings, ["Supersonic Red"])
    assert exact is False
    assert kept == listings  # same-family near matches beat an empty result


def test_filter_no_colors_requested():
    listings = [{"exterior_color": "Ice Cap"}]
    assert filter_by_color(listings, []) == (listings, False)


# ---------------------------------------------------------------------------
# trim variant expansion
# ---------------------------------------------------------------------------


def test_expand_trim_hyphen_and_iforce_variants():
    got = expand_trim_variants(["TRD Off-Road i-FORCE MAX"])
    assert "TRD Off-Road i-FORCE MAX" in got
    assert "TRD Off-Road" in got
    assert "TRD Off Road" in got


def test_expand_trim_plain_grade_unchanged():
    assert expand_trim_variants(["XSE"]) == ["XSE"]


def test_build_search_params_uses_buckets_and_variants():
    params = build_search_params(
        make="Toyota",
        model="Camry",
        trim=["XSE"],
        base_ext_color=["Red", "White"],
        zip_code="90210",
        radius=50,
    )
    assert params["base_ext_color"] == "Red,White"
    assert params["trim"] == "XSE"
    assert "exterior_color" not in params
