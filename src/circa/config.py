"""Everything that changes season to season."""
SEASON = 2026
CONTEST = "VIII"  # Roman numeral in Circa's file names
WEEKS = 18

# Circa uploads each PDF to the WordPress media folder of the month it was posted, so the month varies.
PDF_URL = ("https://www.circasports.com/wp-content/uploads/{year}/{month:02d}/"
           "Circa-Sports-Million-{contest}-Week-{week}-Selections.pdf")
PDF_URL_PREFIX = "https://www.circasports.com/wp-content/uploads/"  # every PDF URL must start with this
MAX_PDF_BYTES = 50 * 1024 * 1024   # real files are ~3 MB
MAX_PDF_PAGES = 500                # real files are ~90 pages
PDF_FIRST_MONTH = (SEASON, 8)   # earliest folder to probe
PDF_LAST_MONTH = (SEASON + 1, 2)
REVALIDATE_LAST = 2             # re-check the newest N weeks' PDFs for corrections; older ones are frozen

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

# Sub-contests (quarters), inclusive week ranges. Matches the comparable winnerscircleproxy leaderboard.
QUARTERS = [(1, 4), (5, 9), (10, 13), (14, 18)]

# Circa scoring: win = 1, push = 0.5, loss = 0.
WIN_POINTS, PUSH_POINTS = 1.0, 0.5

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; circa-million-tracker; +https://github.com/zachaustin01/circa-million-tracker)"}
