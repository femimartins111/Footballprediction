import sqlite3
import pandas as pd

conn = sqlite3.connect("league_predictions.db")

df = pd.read_sql("SELECT * FROM predictions", conn)

df.to_excel("pl_predictions.xlsx", index=False)

conn.close()

print("Exported predictions to league_predictions.xlsx")

