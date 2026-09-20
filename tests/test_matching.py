from dav_scraper.matching import build_variants, normalize


def test_normalize_variants():
    assert normalize("CÔNG TY_CP Dược phẩm Vĩnh_Phúc") == "cong ty cp duoc pham vinh phuc"
    variants = build_variants(["Vinphaco"])
    assert "vinphaco" in variants
    assert "vin phaco" in variants


def test_matcher_is_case_and_separator_insensitive():
    from dav_scraper.matching import build_matcher
    matcher = build_matcher(["Công ty cổ phần dược phẩm Vĩnh Phúc"])
    assert matcher("CÔNG_TY CỔ PHẦN DƯỢC PHẨM VĨNH-PHÚC")
    assert matcher("VinPhaco")
