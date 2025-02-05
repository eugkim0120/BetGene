from flask import Flask, render_template, request, redirect, url_for, session
import csv
import os
from datetime import datetime
import webbrowser
import time
import pandas as pd

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key

# Users with passwords (no hash for simplicity; in production, use hashed passwords)
USERS = {
    'user1': 'password123',
    'user2': 'password123',
    'user3': 'password123',
    'user4': 'password123',
    'user5': 'password123'
}

USER_BETS_FILE = 'user_bets.csv'
BET_OUTCOMES_FILE = 'bet_outcomes.csv'

# Initialize CSV files if not present
if not os.path.exists(USER_BETS_FILE):
    with open(USER_BETS_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Username", "Bet ID", "Time Placed", "Amount", "Prediction"])

if not os.path.exists(BET_OUTCOMES_FILE):
    with open(BET_OUTCOMES_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Bet ID", "Outcome"])


ATTA_FILE = 'ATTA.xlsx'
ATTAC_DOWNLOAD_URL = "https://auroraer-my.sharepoint.com/:x:/r/personal/alexander_wignall_auroraer_com/_layouts/15/Doc.aspx?sourcedoc=%7BFE944A1D-7B7E-44A8-B64A-6DBCFEEFD6A4%7D&file=ATTA.xlsx&action=default&mobileredirect=true"

def check_atta_file():
    """Check if ATTA.xlsx has been downloaded today, otherwise open SharePoint."""
    if os.path.exists(ATTA_FILE):
        last_modified = datetime.fromtimestamp(os.path.getmtime(ATTA_FILE))
        if last_modified.date() == datetime.today().date():
            return  # Already downloaded today

    # Open SharePoint URL in the default web browser
    webbrowser.open(ATTAC_DOWNLOAD_URL)
    
    # Wait for ATTA.xlsx to appear
    print("Waiting for ATTA.xlsx to be downloaded...")
    while not os.path.exists(ATTA_FILE):
        time.sleep(5)  # Check every 5 seconds

    print("ATTA.xlsx has been detected.")

def load_bets():
    with open(USER_BETS_FILE, 'r') as f:
        reader = csv.DictReader(f)
        return list(reader)
    
def load_game_names():
    """Load mapping of Bet IDs."""
    with open(BET_OUTCOMES_FILE, 'r') as f:
        reader = csv.DictReader(f)
        return {row["Bet ID"]: row["Bet ID"] for row in reader}


def save_bet(username, bet_id, amount, prediction):
    with open(USER_BETS_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([username, bet_id, datetime.now().isoformat(), amount, prediction])


def load_outcomes():
    """Load outcomes including match times."""
    with open(BET_OUTCOMES_FILE, 'r') as f:
        reader = csv.DictReader(f)
        return {row["Bet ID"]: {"Outcome": row["Outcome"], "Match Time": row.get("Match Time", None)} for row in reader}



def calculate_score(username):
    refund_late_bets()
    user_bets = load_bets()
    outcomes = load_outcomes()
    score = 100  # Start with a base score of 100

    bets_by_id = {}  # Group bets by Bet ID
    for bet in user_bets:
        bet_id = bet["Bet ID"]
        amount = int(bet["Amount"])
        prediction = bet["Prediction"]

        # Deduct the bet amount immediately from the user's score
        if bet["Username"] == username:
            score -= amount

        if bet_id not in bets_by_id:
            bets_by_id[bet_id] = {"win": 0, "lose": 0, "bets": []}

        bets_by_id[bet_id]["bets"].append(bet)
        bets_by_id[bet_id][prediction] += amount

    # Distribute winnings for completed matches
    for bet_id, data in bets_by_id.items():
        if bet_id not in outcomes or not outcomes[bet_id]:
            continue  # Skip matches without outcomes

        outcome = outcomes[bet_id]
        total_pot = data["win"] + data["lose"]
        winning_pot = data[outcome]

        if winning_pot > 0:
            for bet in data["bets"]:
                if bet["Username"] == username and bet["Prediction"] == outcome:
                    amount = int(bet["Amount"])
                    share = amount / winning_pot
                    winnings = share * total_pot
                    score += winnings  # Add proportional winnings

    return round(score, 2)  # Round to 2 decimal places

def refund_late_bets():
    """Refund bets placed after 12 PM on the match outcome day."""
    user_bets = load_bets()
    outcomes = load_outcomes()  # Now includes Match Time

    updated_bets = []
    for bet in user_bets:
        bet_id = bet["Bet ID"]
        bet_time = datetime.fromisoformat(bet["Time Placed"])

        if bet_id in outcomes and outcomes[bet_id]["Match Time"]:
            try:
                match_time = datetime.fromisoformat(outcomes[bet_id]["Match Time"])
                match_day_12pm = match_time.replace(hour=12, minute=0, second=0, microsecond=0)

                if bet_time > match_day_12pm:
                    print(f"Refunding bet for {bet['Username']} on {bet_id}")
                    continue  # Skip adding this bet (i.e., refund)

            except ValueError:
                print(f"Invalid match time format for {bet_id}. Skipping refund check.")
        
        updated_bets.append(bet)

    # Rewrite `user_bets.csv` with only valid bets
    with open(USER_BETS_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Username", "Bet ID", "Time Placed", "Amount", "Prediction"])
        for bet in updated_bets:
            writer.writerow([bet["Username"], bet["Bet ID"], bet["Time Placed"], bet["Amount"], bet["Prediction"]])

JAN_BRACKET_CURRENT = "jan_bracket.csv"
JAN_BRACKET_PREVIOUS = "previous_jan_bracket.csv"
BET_OUTCOMES_FILE = "bet_outcomes.csv"

def check_and_update_jan_bracket():
    """
    Ensure ATTA.xlsx is downloaded and updated before 12 PM daily.
    Parse the 'Jan Bracket' sheet and maintain 'previous_jan_bracket.csv'.
    """
    if not os.path.exists(ATTA_FILE):
        print("ATTA.xlsx is missing. Cannot update Jan Bracket.")
        return

    # Check if ATTA.xlsx was updated before 12 PM today
    last_modified = datetime.fromtimestamp(os.path.getmtime(ATTA_FILE))
    if last_modified.date() != datetime.today().date() or last_modified.time() > datetime.now().replace(hour=12, minute=0, second=0).time():
        print("ATTA.xlsx was not updated before 12 PM today. Skipping update.")
        return

    # Backup the current jan_bracket.csv as previous_jan_bracket.csv
    if os.path.exists(JAN_BRACKET_CURRENT):
        os.rename(JAN_BRACKET_CURRENT, JAN_BRACKET_PREVIOUS)

    # Parse the 'Jan Bracket' sheet and save as jan_bracket.csv
    try:
        jan_bracket_df = pd.read_excel(ATTA_FILE, sheet_name="Jan Bracket", header=None)
        jan_bracket_df.to_csv(JAN_BRACKET_CURRENT, index=False)
        print(f"'Jan Bracket' sheet has been saved as {JAN_BRACKET_CURRENT}.")
    except Exception as e:
        print(f"Error parsing or saving 'Jan Bracket' sheet: {e}")


def load_csv(file_path):
    """
    Load a CSV file if it exists; otherwise, return an empty DataFrame.
    """
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        return pd.DataFrame()


def save_csv(df, file_path):
    """
    Save a DataFrame to a CSV file.
    """
    df.to_csv(file_path, index=False)


def compare_and_log_match_times():
    """
    Compare the current and previous ATTA.xlsx versions to detect match changes and log match times.
    """
    # Load current and previous Jan Bracket files
    current_bracket = load_csv(JAN_BRACKET_CURRENT)
    previous_bracket = load_csv(JAN_BRACKET_PREVIOUS)
    bet_outcomes = load_csv(BET_OUTCOMES_FILE)

    # Ensure bet_outcomes has necessary columns
    if bet_outcomes.empty:
        bet_outcomes = pd.DataFrame(columns=["Bet ID", "Outcome", "Match Time"])

    # Check for changes in scores
    changes_detected = False
    match_updates = []
    current_time = datetime.now()

    for index, row in current_bracket.iterrows():
        if pd.isna(row[0]) or pd.isna(row[1]):  # Skip if player names are missing
            continue

        player_1 = row[0].strip()
        player_2 = row[1].strip()
        match_id = f"{player_1} vs {player_2}"

        # Detect if scores changed
        if index < len(previous_bracket):
            prev_row = previous_bracket.iloc[index]
            prev_scores = prev_row[2:4]  # Assuming scores are in columns 2 and 3
            curr_scores = row[2:4]

            # Match "happened" if scores were previously missing and are now present
            if any(pd.isna(prev_scores)) and all(pd.notna(curr_scores)):
                changes_detected = True
                # Determine match time
                match_time = (
                    current_time.replace(hour=12, minute=0, second=0, microsecond=0)
                    if current_time.hour >= 12
                    else current_time.isoformat()
                )
                match_updates.append({"Bet ID": match_id, "Match Time": match_time})

    # Log changes
    for update in match_updates:
        match_id = update["Bet ID"]
        match_time = update["Match Time"]
        bet_outcomes.loc[bet_outcomes["Bet ID"] == match_id, "Match Time"] = match_time

    # Save the updated bet outcomes
    if changes_detected:
        print(f"Changes detected in ATTA.xlsx. Updating match times.")
    else:
        print("No changes detected in ATTA.xlsx. No matches happened today.")

    save_csv(bet_outcomes, BET_OUTCOMES_FILE)
    save_csv(current_bracket, JAN_BRACKET_PREVIOUS)  # Save current as previous



@app.route('/')
def home():
    bets = load_bets()
    leaderboard = [
        (user, calculate_score(user))
        for user in USERS
    ]
    leaderboard.sort(key=lambda x: x[1], reverse=True)

    return render_template('home.html', username=session.get('username'), leaderboard=leaderboard)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if USERS.get(username) == password:
            session['username'] = username
            return redirect(url_for('home'))
        return render_template('login.html', error="Invalid username or password.")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/bet', methods=['GET', 'POST'])
def bet():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    game_name_to_id = load_game_names()  # Load mapping of game names to Bet IDs

    if request.method == 'POST':
        try:
            game_name = request.form['game_name']
            amount = int(request.form['amount'])
            prediction = request.form['prediction']

            if game_name not in game_name_to_id:
                return render_template('bet.html', error="Invalid game name.")

            bet_id = game_name_to_id[game_name]  # Map game name to Bet ID

            if amount <= 0 or amount > calculate_score(username):
                return render_template('bet.html', error="Invalid bet amount.")

            save_bet(username, bet_id, amount, prediction)

            return render_template('bet.html', result=f"Bet placed successfully on {game_name}.")

        except ValueError:
            return render_template('bet.html', error="Invalid input.")

    return render_template('bet.html', game_names=list(game_name_to_id.keys()))


if __name__ == '__main__':
    check_atta_file()
    check_and_update_jan_bracket()
    compare_and_log_match_times()
    app.run(debug=True)

