# API Key for football-data.org
import math
import requests
import sqlite3  
import pandas as pd



# Put your actual API key here as a string
API_KEY = "YOUR_API_KEY"

BASE_URL = "https://api.football-data.org/v4/"

HEADERS = {
    "X-Auth-Token": API_KEY
}

REQUEST_TIMEOUT = 10  # seconds

# Put teams in here for proper tier-based adjustments. This is a simplified categorization and can be adjusted based on current season performance.    
BIG_TEAMS = {
}


MID_TEAMS = {
}

LOW_TEAMS = {
}

# Rivalries are defined as sets of teams that have a strong historical rivalry. This is a simplified model and can be expanded with more teams and rivalries as needed.
RIVALRIES = {

}

# REPLACE ALL APPEARANCES OF "LEAGUE" WITH THE ACTUAL LEAGUE CODE YOU WANT TO ANALYZE (e.g., "PL" for Premier League)

# API HELPER
def get_json(endpoint, params=None):
    url = BASE_URL + endpoint
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=REQUEST_TIMEOUT)
        print(f"[DEBUG] GET {url} params={params} -> {resp.status_code}")
        resp.raise_for_status()
        data = resp.json()
        return data
    except Exception as e:
        print(f"ERROR: {e} | URL: {url}")
        return None

# Gets upcoming fixtures for the specified league sorted by date, limited to a certain number.  
def get_upcoming_LEAGUE_fixtures(limit=20):
    endpoint = "competitions/LEAGUE/matches"
    params = {"status": "SCHEDULED"}
    data = get_json(endpoint, params)

    if not data:
        return []

    matches = data.get("matches", [])
    matches.sort(key=lambda m: m.get("utcDate", ""))
    return matches[:limit]


# Utility function to print fixtures in a numbered list format for user selection. Shows matchday, teams, and date. 
def print_numbered_fixtures(matches):
    print("\nUpcoming LEAGUE Fixtures:")
    print("-" * 80)
    for i, m in enumerate(matches, start=1):
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        date = m.get("utcDate", "")
        md = m.get("matchday", "N/A")
        print(f"{i}. MD {md} | {home} vs {away} | {date}")
    print("-" * 80)

# Utility function to prompt user to select a fixture by number. Validates input and ensures it's within the correct range.
def pick_fixture(n):
    while True:
        try:
            num = int(input(f"Select a fixture 1–{n}: "))
            if 1 <= num <= n:
                return num
        except:
            pass
        print("Invalid choice.")


# Fetches the last 5 head-to-head matches between the two teams in the specified match. Returns a list of matches with scores and dates for further analysis.   
def get_head_to_head(match_id, limit=5):
    endpoint = f"matches/{match_id}/head2head"
    params = {"limit": limit}
    data = get_json(endpoint, params)

    if not data:
        return None

    return data

# Computes the head-to-head boost for home and away teams based on the last 5 matches. 
# Each win gives a boost of 0.04 to the winner's rating, while the loser gets a negative boost. 
# Draws do not affect ratings. Returns the calculated boosts for both teams.
def compute_h2h_boost(h2h_data, home_id, away_id):
    if not h2h_data or "matches" not in h2h_data:
        return 0, 0

    matches = h2h_data["matches"][:5]

    home_wins = 0
    away_wins = 0

    for m in matches:
        score = m["score"]["fullTime"]
        gh = score["home"]
        ga = score["away"]

        if gh is None or ga is None:
            continue

        match_home = m["homeTeam"]["id"]
        match_away = m["awayTeam"]["id"]

        # Determine winner of the match
        if gh > ga:
            winner = match_home
        elif ga > gh:
            winner = match_away
        else:
            winner = None  # draw → no one gets a boost

        # Assign win to correct team bucket
        if winner == home_id:
            home_wins += 1
        elif winner == away_id:
            away_wins += 1

    # Difference → boost
    diff = home_wins - away_wins

    home_boost = diff * 0.04
    away_boost = -home_boost

    return home_boost, away_boost

# Initializes the SQLite database and creates the necessary tables if they do not already exist. 
# This function ensures that the database is ready to store predictions and related data. 
# It returns a connection object that can be used for subsequent database operations.
def init_db():
    conn = sqlite3.connect('LEAGUE_predictions.db')
    c = conn.cursor()
    # Create tables (simplified for brevity, ensures they exist)
    c.execute('''CREATE TABLE IF NOT EXISTS predictions 
                 (match_id INTEGER, date TEXT, home_team TEXT, away_team TEXT, 
                  home_prob REAL, draw_prob REAL, away_prob REAL, 
                  home_rating REAL, away_rating REAL, prediction TEXT)''')
    conn.commit()
    return conn

# Saves the prediction data for a specific match into the SQLite database. It checks if a prediction for the given match already exists to avoid duplicates.
# If not, it inserts a new record with the match details, probabilities, ratings, and the final prediction text. 
# The function commits the transaction to ensure data is saved and provides feedback on the operation's success or if a duplicate was detected.   
def save_prediction_to_db(conn, match, h_rating, a_rating, p_home, p_draw, p_away, pred_text):
    c = conn.cursor()
    
    # Check if prediction already exists for this match to avoid duplicates
    c.execute("SELECT * FROM predictions WHERE match_id = ?", (match['id'],))
    data = c.fetchone()
    
    if data is None:
        c.execute('''INSERT INTO predictions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (match['id'], match['utcDate'], match['homeTeam']['name'], match['awayTeam']['name'],
                   round(p_home, 4), round(p_draw, 4), round(p_away, 4),
                   round(h_rating, 4), round(a_rating, 4), pred_text))
        conn.commit()
        print(f"✅ Data saved to SQL for {match['homeTeam']['name']} vs {match['awayTeam']['name']}")
    else:
        print("⚠️ Prediction already exists in DB, skipping save.")


# Applies tier-based rating adjustments based on the team's classification as Big, Mid, or Low.
def team_tier_bonus(team_name):
    """
    Apply tier-based rating adjustments.
    Big = +0.10
    Mid = 0
    Low = -0.10
    """
    if team_name in BIG_TEAMS:
        return 0.05
    elif team_name in MID_TEAMS:
        return 0.00
    elif team_name in LOW_TEAMS:
        return -0.05
    else:
        # Any unknown team is considered LOW
        return -0.10

# Applies a rivalry bonus if the home and away teams are known rivals. This increases the draw probability and gives a boost to the underdog team.
def rivalry_bonus(home_name, away_name):
    if home_name in RIVALRIES and away_name in RIVALRIES[home_name]:
        return {
            "draw_boost": 0.08,
            "underdog": 0.10
        }
    return None

# Computes the home and away ratings based on the provided stats. The formula combines form, attack, defense, and momentum with specific weights.
def compute_home_away_rating(stats, is_home):
    """
    Home rating uses home-only stats.
    Away rating uses away-only stats.
    """
    rating = (
        0.45 * stats["form_index"] +
        0.30 * stats["attack"] -
        0.25 * stats["defense"] +
        0.20 * (stats["momentum"] - 0.5)
    )

    # Home advantage still applies but reduced
    if is_home:
        rating += 0.12  # slightly smaller now because home stats included

    return rating

# Converts the computed home and away ratings into probabilities for home win, draw, and away win.
#  The function uses a logistic transformation to convert rating differences into probabilities and includes a boost for draws if a rivalry is detected. 
# The probabilities are normalized to ensure they sum to 1.
def ratings_to_probs(home_rating, away_rating, draw_boost=0):
    diff = home_rating - away_rating
    k = 2.5

    p_home_raw = 1 / (1 + math.exp(-k * diff))
    p_away_raw = 1 - p_home_raw

    base_draw = 0.22
    draw_adj = max(0, 0.15 - abs(diff) * 0.1)
    p_draw = base_draw + draw_adj + draw_boost

    scale = 1 - p_draw
    p_home = p_home_raw * scale
    p_away = p_away_raw * scale

    total = p_home + p_away + p_draw
    return p_home/total, p_draw/total, p_away/total

# Computes the home and away stats (form index, attack, defense, momentum) based on the provided matches for a specific team.
def compute_home_away_stats(matches, team_id):
    wins = draws = losses = 0
    gf = ga = 0
    played = 0
    
    for m in matches:
        score = m.get("score", {}).get("fullTime", {})
        gh = score.get("home")
        ga_ = score.get("away")
        if gh is None or ga_ is None:
            continue

        home_id = m["homeTeam"]["id"]
        away_id = m["awayTeam"]["id"]

        if home_id == team_id:
            gf_i, ga_i = gh, ga_
        elif away_id == team_id:
            gf_i, ga_i = ga_, gh
        else:
            continue

        played += 1
        gf += gf_i
        ga += ga_i

        if gf_i > ga_i:
            wins += 1
        elif gf_i < ga_i:
            losses += 1
        else:
            draws += 1

    if played == 0:
        return {
            "form_index": 0.5,
            "attack": 1,
            "defense": 1,
            "momentum": 0.5
        }

    form_index = (3*wins + draws) / (3*played)

    # last 5 momentum
    last5 = matches[-5:]
    pts = 0
    for m in last5:
        score = m.get("score", {}).get("fullTime", {})
        gh = score.get("home")
        ga_ = score.get("away")

        home_id = m["homeTeam"]["id"]
        away_id = m["awayTeam"]["id"]

        if home_id == team_id:
            gf_i, ga_i = gh, ga_
        else:
            gf_i, ga_i = ga_, gh

        if gf_i > ga_i:
            pts += 1
        elif gf_i == ga_i:
            pts += 0.5

    momentum = pts / 5

    return {
        "form_index": round(form_index, 2),
        "attack": gf/played,
        "defense": ga/played,
        "momentum": round(momentum, 2)
    }


# Fetches matches for a specific team filtered by venue (home or away). This is used to compute venue-specific stats for the team, which are crucial for accurate predictions.
#  The function returns a list of matches that can be analyzed to determine the team's performance in different venues. 
def get_team_matches_by_venue(team_id, venue, limit=20):
    endpoint = f"teams/{team_id}/matches"
    params = {
        "status": "FINISHED",
        "competitions": "LEAGUE",
        "venue": venue,
        "limit": limit
    }
    data = get_json(endpoint, params)
    return data.get("matches", []) if data else []

# Fetches the current league standings and extracts the position, points, and goal difference for each team. This information is used to apply table-based biases in the prediction model.  
def get_current_standings():
    endpoint = "competitions/LEAGUE/standings"
    data = get_json(endpoint)
    if not data or 'standings' not in data:
        print("WARNING: Could not fetch standings")
        return {}
    
    table = data['standings'][0]['table']  # Total standings
    positions = {}
    for entry in table:
        team = entry['team']['name']
        positions[team] = {
            'position': entry['position'],
            'points': entry['points'],
            'goal_diff': entry['goalDifference']
        }
    return positions

# Main function to predict the outcome of a match. It integrates all the steps: fetching stats, applying tier and rivalry adjustments, computing ratings, and converting them to probabilities.
def predict_match(match):
    home = match["homeTeam"]["name"]
    away = match["awayTeam"]["name"]
    hid = match["homeTeam"]["id"]
    aid = match["awayTeam"]["id"]

    print(f"\n\n====================== MATCH ANALYSIS ======================")
    print(f"Selected: {home} vs {away}")
    print("============================================================\n")

    print("Venue-Specific Form, Attack, Defense")
    home_home_matches = get_team_matches_by_venue(hid, "HOME", limit=20)
    home_stats = compute_home_away_stats(home_home_matches, hid)

    away_away_matches = get_team_matches_by_venue(aid, "AWAY", limit=20)
    away_stats = compute_home_away_stats(away_away_matches, aid)

    print(f"- {home} (HOME) → Form={home_stats['form_index']}, "
          f"Attack={home_stats['attack']:.2f}, Defense={home_stats['defense']:.2f}, "
          f"Momentum={home_stats['momentum']}")
    print(f"- {away} (AWAY) → Form={away_stats['form_index']}, "
          f"Attack={away_stats['attack']:.2f}, Defense={away_stats['defense']:.2f}, "
          f"Momentum={away_stats['momentum']}\n")

    home_rating = compute_home_away_rating(home_stats, is_home=True)
    away_rating = compute_home_away_rating(away_stats, is_home=False)

    print(f"➡ Base ratings from form/stats:")
    print(f"   {home}: {home_rating:.3f}")
    print(f"   {away}: {away_rating:.3f}\n")

    print("Tier Bonus")
    home_tier = team_tier_bonus(home)
    away_tier = team_tier_bonus(away)

    home_rating += home_tier
    away_rating += away_tier

    print(f"- {home}: {home_tier:+.2f}")
    print(f"- {away}: {away_tier:+.2f}")

    print(f"➡ Ratings after Tier:")
    print(f"   {home}: {home_rating:.3f}")
    print(f"   {away}: {away_rating:.3f}\n")

    print("Rivalry Check")
    rb = rivalry_bonus(home, away)
    draw_boost = 0
    if rb:
        print("Rivalry detected — increasing draw % and boosting underdog.")
        draw_boost = rb["draw_boost"]

        if home_rating > away_rating:
            away_rating += rb["underdog"]
            print(f"   Underdog boost → {away} +{rb['underdog']}")
        else:
            home_rating += rb["underdog"]
            print(f"   Underdog boost → {home} +{rb['underdog']}")
    else:
        print("No rivalry.\n")

    print(f"➡ Ratings after rivalry:")
    print(f"   {home}: {home_rating:.3f}")
    print(f"   {away}: {away_rating:.3f}\n")

    print("Head-to-Head Influence (last 5)")
    h2h_data = get_head_to_head(match["id"])

    home_h2h, away_h2h = compute_h2h_boost(h2h_data, home_id=hid, away_id=aid)

    home_rating += home_h2h
    away_rating += away_h2h

    print(f"- {home} H2H boost: {home_h2h:+.3f}")
    print(f"- {away} H2H boost: {away_h2h:+.3f}")

    print(f"➡ Ratings after H2H:")
    print(f"   {home}: {home_rating:.3f}")
    print(f"   {away}: {away_rating:.3f}\n")

    print("Last 5 H2H Matches:")
    if h2h_data and "matches" in h2h_data:
        for m in h2h_data["matches"][:5]:
            date = m.get("utcDate", "")[:10]
            hteam = m["homeTeam"]["name"]
            ateam = m["awayTeam"]["name"]
            score = m["score"]["fullTime"]
            gh = score.get("home")
            ga = score.get("away")

            # Determine winner label
            if gh is not None and ga is not None:
                if gh > ga:
                    result = f"{hteam} WON"
                elif ga > gh:
                    result = f"{ateam} WON"
                else:
                    result = "DRAW"
            else:
                result = "Unknown result"

            print(f"  {date}: {hteam} {gh}-{ga} {ateam} → {result}")
    else:
        print("  No H2H data available.")

    print("League Table Influence")
    standings = get_current_standings()
    table_bias_reason = "No table-based boost applied."

    if home in standings and away in standings:
        home_pos = standings[home]["position"]
        away_pos = standings[away]["position"]

        print(f"- {home}: position {home_pos}")
        print(f"- {away}: position {away_pos}")

        pos_diff = abs(home_pos - away_pos)

        # Eligible table zones
        european_zone = range(1, 9)     # 1–8
        relegation_zone = range(16, 21) # 16–20

        # Check if both teams are in the SAME competitive zone
        same_zone = (
            (home_pos in european_zone and away_pos in european_zone) or
            (home_pos in relegation_zone and away_pos in relegation_zone)
        )

        if same_zone and 2 <= pos_diff <= 3:
            # Apply underdog boost only in these zones
            if home_pos > away_pos:
                home_rating += 0.05  # much smaller boost
                table_bias_reason = f"{home} boosted (+0.05): lower-ranked inside competitive zone."
            else:
                away_rating += 0.05
                table_bias_reason = f"{away} boosted (+0.05): lower-ranked inside competitive zone."

            print("Table competitive-zone underdog bias applied.")

        elif 2 <= pos_diff <= 3:
            # Apply smaller boost if not in same zone
            if home_pos > away_pos:
                home_rating += 0.03
                table_bias_reason = f"{home} boosted (+0.03): lower-ranked but outside competitive zone."
            else:
                away_rating += 0.03
                table_bias_reason = f"{away} boosted (+0.03): lower-ranked but outside competitive zone."

            print("table underdog bias applied (outside competitive zone).")
        else:
            print("No table bias applied: teams not in same competitive zone or too far apart.")

    else:
        print("Standings unavailable.")

    print("➡", table_bias_reason)
    print(f"➡ Ratings after table:")
    print(f"   {home}: {home_rating:.3f}")
    print(f"   {away}: {away_rating:.3f}\n")

    print("Convert Ratings → Probabilities")
    p_home, p_draw, p_away = ratings_to_probs(home_rating, away_rating, draw_boost)
    print(f"- Home win: {p_home*100:.1f}%")
    print(f"- Draw:     {p_draw*100:.1f}%")
    print(f"- Away win: {p_away*100:.1f}%\n")

    homeP, drawP, awayP = p_home*100, p_draw*100, p_away*100
    winner_prob = max(homeP, drawP, awayP)
    
    prediction_text = "Unknown"

    if abs(winner_prob - drawP) <= 5:
        if winner_prob == homeP:
            prediction_text = f"{home} OR Draw"
        elif winner_prob == awayP:
            prediction_text = f"{away} OR Draw"
        else:
            if abs(drawP - homeP) < abs(drawP - awayP):
                prediction_text = f"Draw OR {home}"
            else:
                prediction_text = f"Draw OR {away}"
    else:
        if winner_prob == homeP:
            prediction_text = f"{home} Win"
        elif winner_prob == awayP:
            prediction_text = f"{away} Win"
        else:
            prediction_text = "Draw"

    print(f"Prediction: {prediction_text}")
    print("============================================================\n")
    return home_rating, away_rating, p_home, p_draw, p_away, prediction_text


if __name__ == "__main__":
    conn = init_db()
    print("League Predictions")

    while True:
        upcoming = get_upcoming_LEAGUE_fixtures(20)

        if not upcoming:
            print("No upcoming fixtures found.")
            break

        print_numbered_fixtures(upcoming)

        pick = pick_fixture(len(upcoming))
        match = upcoming[pick - 1]

        h_rat, a_rat, p_h, p_d, p_a, p_text = predict_match(match)
        save_prediction_to_db(conn, match, h_rat, a_rat, p_h, p_d, p_a, p_text)

        cont = input("\nPredict another? (y/n): ").strip().lower()
        if cont != 'y':
            break

    conn.close()

