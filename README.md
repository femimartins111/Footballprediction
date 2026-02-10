# ⚽ Football Match Prediction Engine

A Python-based football match prediction system that uses real-time data from the **football-data.org API** to analyze upcoming fixtures and generate probabilistic match predictions.  
Predictions are stored in a **SQLite database** and can be exported to **Excel** for further analysis.

The project is league-agnostic, with **Ligue 1 (France)** included as a reference guide for setup and customization.

---

## 📌 Features

- Live data fetching from **football-data.org**
- Predicts:
  - Home Win
  - Draw
  - Away Win
- Venue-specific analysis (home vs away form)
- Uses:
  - Recent form & momentum
  - Head-to-head history
  - League table position
  - Team tier adjustments (Big / Mid / Low)
  - Rivalry-based draw bias
- Stores predictions in a **SQLite database**
- Includes a **converter file** to export predictions from DB to **Excel**
- Interactive CLI for selecting fixtures

---

## 🏆 Supported Leagues

This system works for **any league supported by football-data.org**.

- **Ligue 1 (France)** is included as a guide
- Easily adaptable to:
  - Premier League
  - Bundesliga
  - La Liga
  - Serie A

---

## 📂 Project Structure
- footballpredictions.py # Main prediction engine
- converter.py # Converts SQLite DB to Excel
- LEAGUE_predictions.db # SQLite database (auto-generated)
- README.md

🔑 API Key Setup (Required)
---------------------------

This project uses the **football-data.org API**.

1.  Create a free account at:\
    👉 <https://www.football-data.org/>

2.  Get your API key

3.  In `footballpredictions.py`, replace:

`API_KEY = "YOUR_API_KEY"`

* * * * *

⚙️ Requirements
---------------

Make sure you have **Python 3.9+** installed.

### Python Libraries

Install dependencies using:

`pip install requests pandas`

* * * * *

▶️ How to Run
-------------

1.  Clone the repository:

`git clone https://github.com/yourusername/football-predictions.git
cd football-predictions`

1.  Run the prediction engine:

`python footballpredictions.py`

1.  Select a fixture from the list to generate predictions

2.  Predictions are automatically saved to:

`LEAGUE_predictions.db`

* * * * *

📤 Export Predictions to Excel
------------------------------

A **converter file** is included to transform the SQLite database into an Excel spreadsheet.

Run:

`convverter.py`

This will generate:

`LEAGUE_predictions.xlsx`

Perfect for:

-   Data analysis

-   Visualization

-   Sharing results

* * * * *

🧠 Customization Guide
----------------------

### Change League

Replace all occurrences of:

`LEAGUE`

with the league code you want (e.g. `PL`, `BL1`, `SA`, `PD`).

* * * * *

### Team Tier Classification

Edit these sets to improve prediction accuracy:

`BIG_TEAMS = {...}
MID_TEAMS = {...}
LOW_TEAMS = {...}`

* * * * *

### Rivalries

Add historical rivalries to influence draw probabilities:

`RIVALRIES = {
    "Team A": {"Team B"}
}`

* * * * *

