from circa.weeks import Game, Side, cover, partner


def test_partner():
    assert partner(3) == 4 and partner(4) == 3 and partner(29) == 30


def test_cover():
    assert cover(24, 16, -8) == "P"      # won by exactly the spread
    assert cover(24, 16, -7.5) == "W"
    assert cover(17, 19, 3.5) == "W"
    assert cover(16, 24, -8) == "L"


def _game(state, a, h):
    return Game("1", "2026-10-09T00:15Z", state, "", Side("TB", a, 2, 8.0), Side("DAL", h, 1, -8.0))


def test_status_pending_live_final():
    assert _game("pre", 0, 0).status_of(2) is None
    assert _game("in", 20, 10).status_of(2) == "W"      # TB +8 leading 20-10
    assert _game("post", 24, 16).status_of(1) == "L"    # DAL -8 loses 16-24
    assert _game("post", 16, 24).status_of(1) == "P"    # DAL -8 wins by 8: push
    assert _game("post", 24, 16).status_of(9) is None   # unknown selection
