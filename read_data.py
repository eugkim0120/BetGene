import pandas as pd
import csv

ATTAC_FILE = 'ATTAC.xlsx'
BET_OUTCOMES_FILE = 'bet_outcomes.csv'

def read_attac():
    """
    Reads the ATTAC spreadsheet and returns the data as a dictionary grouped by rounds and matches.
    """
    attac_data = pd.read_excel(ATTAC_FILE, sheet_name=None)  # Load all sheets
    rounds_data = {}

    for sheet_name, sheet_data in attac_data.items():
        sheet_data = sheet_data.dropna(how='all')  # Remove empty rows
        sheet_data.columns = [col.strip() for col in sheet_data.columns]  # Clean column names
        rounds_data[sheet_name] = sheet_data

    return rounds_data

def save_bet_outcome(round_name, match_name, bet_id, outcome):
    """
    Saves or updates a bet outcome in the bet_outcomes.csv file.
    """
    bet_outcomes = []
    updated = False

    # Read existing outcomes
    with open(BET_OUTCOMES_FILE, 'r') as f:
        reader = csv.DictReader(f)
        bet_outcomes = list(reader)

    # Update or append the bet outcome
    for row in bet_outcomes:
        if row["Bet ID"] == bet_id:
            row["Round"] = round_name
            row["Match"] = match_name
            row["Outcome"] = outcome
            updated = True
            break

    if not updated:
        bet_outcomes.append({"Bet ID": bet_id, "Round": round_name, "Match": match_name, "Outcome": outcome})

    # Save back to the file
    with open(BET_OUTCOMES_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["Bet ID", "Round", "Match", "Outcome"])
        writer.writeheader()
        writer.writerows(bet_outcomes)

if __name__ == "__main__":
    rounds_data = read_attac()
    print("Available Rounds:")
    for i, round_name in enumerate(rounds_data.keys(), start=1):
        print(f"{i}. {round_name}")

    round_choice = int(input("Select a round by number: ")) - 1
    selected_round = list(rounds_data.keys())[round_choice]
    matches = rounds_data[selected_round]

    print(f"Available Matches in {selected_round}:")
    for i, match in enumerate(matches['Match'], start=1):
        print(f"{i}. {match}")

    match_choice = int(input("Select a match by number: ")) - 1
    selected_match = matches['Match'].iloc[match_choice]
    bet_id = input("Enter Bet ID: ")
    outcome = input("Enter Outcome (win/lose): ")

    save_bet_outcome(selected_round, selected_match, bet_id, outcome)
    print("Bet outcome saved successfully.")
