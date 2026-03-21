# BudgetHelper
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

BudgetHelper is a machine-learning-powered personal finance engine and command-line interface (CLI). It moves beyond traditional expense tracking by utilizing a Dual-Track Linear Regression model to forecast end-of-month financial realities, strictly separating behavioral spending habits from structural net worth.

##  Project Overview

The architecture is built to provide a pessimistic, mathematically sound view of financial health, developed across three phases:
1. **Storage & Interface:** A relational SQLite database driven by a custom Python CLI.
2. **Predictive Engine:** A Pandas/Scikit-Learn machine learning pipeline forecasting monthly limits and total liquidity.
3. **AI Integration:** An LLM-driven assistant for natural language financial reality checks (In Progress).

##  Technical Architecture: The Predictive Model

BudgetHelper does not simply draw a line through your bank balance. It actively isolates different financial behaviors using two distinct linear regression tracks:

* **Monthly Budget Track (Behavioral):** Trains exclusively on pure outflows (`expenses_only`). It ignores all income, ensuring the monthly spending limit acts as a strict behavioral guardrail.
* **Total Budget Track (Structural):** Trains on the cumulative sum of expenses plus `Continuous Income`. It accounts for reliable daily cash flow (e.g., business revenue) while ignoring lumpy, unpredictable cash injections (e.g., one-off bonuses) to prevent false optimism in the regression slope.

### The Worst-Case Delta & Volatility
To protect against spending spikes, the model calculates trailing metrics using Exponential Weighted Moving Averages (EWMA) and penalizes the final prediction using a 14-day rolling standard deviation:

    Worst_Case = Final_Prediction - (2 * std_dev * sqrt(days_left))

The engine calculates the predicted "Delta" (the total drain from today until the end of the month) and applies it to the real-time SQLite bank balance, generating a highly conservative financial limit.

### ETL & Data Filtering
The pipeline extracts raw ledger data and transforms it into isolated financial vectors. To maintain absolute statistical accuracy, the engine employs a strict filter that drops the current, incomplete day from the training set. This prevents a single mid-day transaction from prematurely warping the ML trajectory.

##  Tech Stack

* **Language:** Python 3.x
* **Database:** SQLite3
* **Data Engineering:** Pandas, NumPy
* **Machine Learning:** Scikit-Learn (Linear Regression)

##  Installation

Clone the repository and navigate into the directory:
    git clone https://github.com/yourusername/BudgetHelper.git
    cd BudgetHelper

Create and activate a virtual environment:
    python -m venv .venv
    
    # Windows:
    .venv\Scripts\activate
    # macOS/Linux:
    source .venv/bin/activate

Install the required dependencies:
    pip install -r requirements.txt

Run the application:
    python scripts/main.py

##  CLI Commands

BudgetHelper operates via an interactive, continuous shell environment.

| Command | Description |
| :--- | :--- |
| `status` | Generates the core analytical report, displaying balances, Net Flow, and ML predictions. |
| `enter_transaction` | Enters input mode. Format: `Category Amount Description Date:YYYY-MM-DD`. |
| `view [n]` | Displays the last `n` transactions (defaults to 50). Use `view latest` for the most recent. |
| `delete [id]` | Deletes a transaction by its database ID. |
| `set_budget` | Establishes the total baseline budget (Net Worth). |
| `set_monthly_budget` | Establishes the monthly behavioral spending limit. |
| `clear` | Wipes the transaction database (requires confirmation prompt). |
| `back` | Exits transaction entry mode. |
| `quit` / `exit` | Closes the application securely. |

## List of Categories
To avoid parsing errors, please provide the category name in quotes.

|Income|
|Groceries|
|Rent & Utilities|  
|Subscriptions|
|Transportation| 
|Education|
|Hobbies|
|Health & Care|
|Entertainment|
|Food|
|Other|
|Continous Income|

##  License

This project is licensed under the GNU AGPL-3.0