from car_agent.clients.marketcheck import build_search_params, parse_listing


def test_build_search_params_joins_multi_trim_and_color():
    params = build_search_params(
        make="Toyota",
        model="Camry",
        trim=["XSE", "SE"],
        base_ext_color=["Red", "White"],
    )
    assert params["trim"] == "XSE,SE"
    assert params["base_ext_color"] == "Red,White"


def test_build_search_params_omits_empty_lists():
    params = build_search_params(
        make="Toyota",
        model="Camry",
        trim=[],
        base_ext_color=[],
    )
    assert "trim" not in params
    assert "base_ext_color" not in params


def test_build_search_params_omits_none():
    params = build_search_params(make="Toyota", model="Camry")
    assert "trim" not in params
    assert "base_ext_color" not in params


def test_build_search_params_single_value_list():
    params = build_search_params(
        make="Toyota",
        model="Camry",
        trim=["XSE"],
        base_ext_color=["Red"],
    )
    assert params["trim"] == "XSE"
    assert params["base_ext_color"] == "Red"


def test_parse_listing_extracts_photo_url():
    raw = {
        "id": "abc",
        "vin": "1",
        "media": {"photo_links": ["https://example.com/a.jpg", "https://example.com/b.jpg"]},
    }
    assert parse_listing(raw)["photo_url"] == "https://example.com/a.jpg"


def test_parse_listing_falls_back_to_cached_photos():
    raw = {
        "id": "abc",
        "vin": "1",
        "media": {"photo_links_cached": ["https://cdn.example.com/a.jpg"]},
    }
    assert parse_listing(raw)["photo_url"] == "https://cdn.example.com/a.jpg"


def test_parse_listing_photo_url_none_when_missing():
    assert parse_listing({"id": "abc", "vin": "1"})["photo_url"] is None
    assert parse_listing({"id": "abc", "vin": "1", "media": {}})["photo_url"] is None
    assert parse_listing({"id": "abc", "vin": "1", "media": {"photo_links": []}})["photo_url"] is None
