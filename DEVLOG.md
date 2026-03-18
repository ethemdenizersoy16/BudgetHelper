Devlog: BudgetHelper - Core Architecture & ML Predictions

Project Overview

This project is a personal budget calculator designed to act as a comprehensive financial engine. The architecture is split into three main development phases:

1. Storage & Interface: An SQLite database driven by a custom Python CLI.
2. Predictive Engine: A machine learning pipeline using linear regression to forecast monthly and total budgets.
3. AI Integration: Hooking up an LLM to interpret the data and provide user-friendly financial reality checks.

This log covers the implementation of Phases 1 and 2.

Part 1: SQLite Database & Data Structure

One of my primary goals for starting this project was to teach myself SQL.

The database is built on a relational schema with three core tables:

* categories: A lookup table containing a list of budget categories and their unique IDs.
* transactions: The core ledger. Each entry holds an id, description, amount, date, and a category_id (acting as a foreign key mapping back to the categories table).
* budgets: Stores the target total and monthly budgets.

To ensure data integrity, the total and monthly budgets are not hard-updated after every single entry. Instead, the current state is calculated dynamically by summing up the transactions via SQL queries. Because the scale of personal finance data is relatively small, calculating on the fly prevents desynchronization without causing performance bottlenecks.

The Command Line Interface (CLI)

The user interacts with the program through a custom shell environment powered by an infinite while loop that listens for specific commands.

Core Commands:

* view [n|'latest']: Displays a list of the last n transactions (defaults to 50). Passing 'latest' displays only the most recent entry.
* delete [id]: Deletes a specific transaction by its ID. If no ID is provided, it defaults to deleting the latest entry.
* enter_transaction: Enters a dedicated input mode. Transactions are parsed using the format: Category Amount Desc Date:YYYY-MM-DD. If the description or date is omitted, they default to an empty string "" and today's date, respectively.
* back: Exits transaction entry mode.
* clear: Wipes the database (guarded by a confirmation prompt).
* set_budget & set_monthly_budget: First-time setup commands to establish the financial baseline.
* quit / exit: Safely closes the application.

The status Command:

This is the core analytical output of the engine. It returns a comprehensive financial report detailing:

* Remaining total and monthly budgets.
* Total money spent in the current month.
* The category with the highest average daily spend over the last week (and the amount).
* Predicted end-of-month monthly and total budgets.
* Net daily money flow for the past week.
* A strict daily spending limit to prevent budget overruns.

Part 2: Data Engineering & Pandas Pipeline

To drive the linear regression models, the raw SQL data is extracted and transformed using pandas and scikit-learn.

The pipeline starts with dataframe_raw, which pulls data directly from the transactions table. From there, it is transformed into dataframe_t through the following ETL (Extract, Transform, Load) steps:

1. Datetime Conversion: Strings are cast to datetime objects for accurate chronological sorting.
2. Feature Engineering: I created distinct columns to isolate different financial behaviors. expenses_only is a sum of pure outflows. expenses_and_cont is a sum of expenses plus continuous/structural income (ignoring lumpy, one-off income spikes). signed_amount is the absolute net flow of all transactions.
3. Time-Series Resampling: Because predictions are evaluated daily, set_index and .resample('D') are used to group and sum transactions occurring on the same day.
4. X-Axis Generation: A date_of_month column is created to act as the independent variable for the ML models.
5. Partial-Day Filtering: Entries from the current day are explicitly excluded from dataframe_t. Incomplete daily data can violently skew the regression slope.

Finally, I calculate cumulative sums for the expense tracks to act as our dependent variables for the machine learning models.

Velocity & Volatility Metrics

To give the model context about recent behavior, I calculate four specific trailing metrics using Exponential Weighted Moving Averages (EWMA). By using .ewm(span=7, min_periods=1), the engine prevents harsh drop-offs in the data when a large transaction crosses the 7-day threshold.

* 7day_average: The net daily money flow (displayed directly to the user).
* expense_7day_average: The average daily outflow (used to weight the monthly prediction).
* struct_7day_average: The average daily outflow plus continuous income (used to weight the total prediction).
* std_dev: A 14-day rolling standard deviation of expenses, used to measure the user's spending volatility.

Part 3: Dual-Track Linear Regression

The predictive engine runs two distinct linear regression models to account for the difference between Net Worth and Behavioral Spending.

1. Total Budget Prediction: This represents overall liquidity. It is trained on the structured cumulative sum (expenses_and_cont) against the days of the month. It accounts for reliable continuous income while ignoring massive, unpredictable income spikes.
2. Monthly Budget Prediction: This is a strict behavioral spending limit. It ignores all income entirely and trains exclusively on the expenses_only cumulative sum.

The Weighting System (Cold Start Handling)

To make the predictions responsive, the raw ML output is blended with the recent velocity.

* Cold Start (< 7 days of data): The ML prediction is given a weight of 0.3, and the recent velocity is given 0.7.
* Established (> 7 days of data): The ML prediction is trusted more, holding a weight of 0.8, while velocity is reduced to 0.2.

The Worst-Case Penalty & Delta Integration

To enforce a pessimistic, conservative financial strategy, the final prediction is penalized by the spending volatility.

Worst_Case = Final_Prediction - (2 * std_dev * sqrt{days_left})

However, this worst-case calculation yields the predicted cumulative sum on the 31st of the month, which is not a helpful metric for the user. To translate this into an actionable budget:

1. Subtract the current cumulative sum from the worst-case predicted sum to find the Delta (the exact amount of money expected to drain between today and the end of the month).
2. Add this Delta to the current actual budget balances (fetched via SQL) to output the true predicted budget.

The daily spending limit acts as a final guardrail, simply calculated as the lowest remaining budget divided by the days left in the month.

Category Velocity Tracking

Finally, to provide actionable insights, the engine isolates the most expensive recent habit. It iterates over the unique categories in dataframe_raw and compares the sum of all values for each category over the trailing 7 days.

The core logic for extracting this metric is:

currentcand = (dataframe_i['signed_amount'].where(dataframe_i['date_recorded'] >= one_weekago).sum()) / 7 if not dataframe_i.empty else 0
