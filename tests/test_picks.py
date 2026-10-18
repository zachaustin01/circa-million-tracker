import pytest

from circa.picks import parse_line_value, parse_lines, parse_row

ROW = "ZWEI BRUDER-1 4. EAGLES +7½ 12. DOLPHINS +7 16. GIANTS +4 18. TITANS +7½ 21. SEAHAWKS -3"


def test_line_values():
    assert parse_line_value("-3½") == -3.5
    assert parse_line_value("+7") == 7
    assert parse_line_value("-½") == -0.5
    assert parse_line_value("PK") == 0


def test_parse_row():
    name, picks = parse_row(ROW)
    assert name == "ZWEI BRUDER-1"
    assert picks == [(4, "PHI", 7.5), (12, "MIA", 7.0), (16, "NYG", 4.0), (18, "TEN", 7.5), (21, "SEA", -3.0)]


def test_entry_name_that_looks_like_a_pick():
    name, picks = parse_row("5. ALPHA +3-2 1. COWBOYS -8 14. RAIDERS +3½ 25. BEARS -1½ 19. BRONCOS -3½ 30. BILLS +3")
    assert name == "5. ALPHA +3-2" and len(picks) == 5


def test_header_footer_and_wrapped_rows():
    lines = ["Circa Sports Million VIII", "Week 5 Selections", "ENTRY NAME SELECTIONS", ROW,
             "LONG NAME THAT WRAPS-1 3. JAGUARS -7½ 5. STEELERS -2½ 14. RAIDERS +3½",
             "17. TEXANS -7½ 19. BRONCOS -3½", "10/10/26"]
    rows = parse_lines(lines)
    assert [r[0] for r in rows] == ["ZWEI BRUDER-1", "LONG NAME THAT WRAPS-1"]


def test_garbage_raises():
    with pytest.raises(ValueError):
        parse_lines(["something unexpected"])


def test_unknown_team_is_loud():
    with pytest.raises(ValueError):
        parse_row("X-1 1. WHALERS -1 2. COWBOYS +1 3. JAGUARS -1 4. EAGLES +1 5. STEELERS -1")
