"""Circa prints team nicknames ("BUCS", "49ERS"); ESPN uses abbreviations."""

NICKNAME_TO_ABBR = {
    "CARDINALS": "ARI", "FALCONS": "ATL", "RAVENS": "BAL", "BILLS": "BUF", "PANTHERS": "CAR",
    "BEARS": "CHI", "BENGALS": "CIN", "BROWNS": "CLE", "COWBOYS": "DAL", "BRONCOS": "DEN",
    "LIONS": "DET", "PACKERS": "GB", "TEXANS": "HOU", "COLTS": "IND", "JAGUARS": "JAX",
    "CHIEFS": "KC", "RAIDERS": "LV", "CHARGERS": "LAC", "RAMS": "LAR", "DOLPHINS": "MIA",
    "VIKINGS": "MIN", "PATRIOTS": "NE", "SAINTS": "NO", "GIANTS": "NYG", "JETS": "NYJ",
    "EAGLES": "PHI", "STEELERS": "PIT", "49ERS": "SF", "SEAHAWKS": "SEA", "BUCS": "TB",
    "BUCCANEERS": "TB", "TITANS": "TEN", "COMMANDERS": "WSH",
}


def abbr(nickname: str) -> str:
    try:
        return NICKNAME_TO_ABBR[nickname.upper()]
    except KeyError:
        raise ValueError(f"unknown team nickname {nickname!r}; add it to circa/teams.py") from None
