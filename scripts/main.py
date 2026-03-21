import db_init
import db_dict
import sqlite3
from pathlib import Path 
from datetime import datetime
from prettytable import PrettyTable
import shlex
import analysis

def view(curs, limit = 50):
    if limit == "latest":
         curs.execute("""
        SELECT t.id, c.name, t.amount, t.description,t.date_recorded 
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        ORDER BY t.id DESC LIMIT 1
        """)
         
    else:
        curs.execute("""
            SELECT t.id, c.name, t.amount, t.description,t.date_recorded 
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            ORDER BY t.date_recorded DESC LIMIT ?
            """,(limit,))
     
    rows = curs.fetchall()

    table = PrettyTable()
    table.field_names = ["ID", "Category", "Amount", "Description", "Date"]
    table.align["Category"] = "l"
    table.align["Amount"] = "r"

    for row in rows:
         table.add_row(row)
    print(table)

def status(curs, purpose = 0):#0 is for general status, 1 is for warnings
     curs.execute("""SELECT total_budget, monthly_budget FROM budget WHERE id = 1""")
     budgets = curs.fetchone()

     total_budget = budgets[0]
     monthly_budget = budgets[1]



     curs.execute("""SELECT COALESCE(SUM(CASE WHEN category_id != 1 AND category_id != 12 THEN - amount ELSE 0 END),0)
                  +COALESCE(SUM(CASE WHEN category_id == 1 OR category_id == 12 THEN amount ELSE 0 END),0)
                  FROM transactions""")

     total_spent = curs.fetchone()[0]
     curs.execute("""SELECT COALESCE(SUM(CASE WHEN category_id != 1 AND category_id != 12 THEN - amount ELSE 0 END),0)
                  FROM transactions WHERE date_recorded >= date('now','start of month')""")
     
     monthly_spent = curs.fetchone()[0]

     total_remaining = total_budget  + total_spent
     
     monthly_remaining = monthly_budget + monthly_spent
     if purpose == 0: 
        print("\n--- Financial Status ---")
        print(f"Current Total Budget: {total_remaining:.2f}")
        if monthly_budget != 0:
            print(f"Monthly Spending Budget: {monthly_budget:.2f} | Remaining: {monthly_remaining:.2f}")
        print(f"Spent this month: {-1 * monthly_spent:.2f}")
     if monthly_budget > 0 and monthly_remaining < 0:
        print("-------------------------------------------------------")
        print("WARNING: Monthly budget was exceeded!e")

     if total_budget > 0 and total_remaining < 0:
        print("-------------------------------------------------------")
        print("CRITICAL WARNING: Total budget was exceeded!")

     
     



def transaction_control(conn,curs,id_map):
    
    while(True):
        data = [11, float(0.00), "",datetime.now().strftime("%Y-%m-%d")]

        user_input = input("Enter transaction>")
        
        if user_input.lower() == "quit" or user_input.lower() == "exit":
            return 1
        
        elif user_input.lower() == "status":
             status(curs)
             data = analysis.analysis(conn,curs)
             curs.execute("""SELECT total_budget, monthly_budget FROM budget WHERE id = 1""")
             budgets = curs.fetchone()
             if budgets[0] != 0 or budgets[1] != 0:
                print("-------------------------------------------------------")
                if budgets[0] != 0:
                 print(f"Predicted Total Budget: {data[0]:.2f}")
                if budgets[1] != 0:
                    print(f"Predicted Monthly Budget: {data[1]:.2f}")
                if (budgets[1] != 0 and data[1] < 0) or (budgets[0] != 0 and data[0] < 0):
                    print("You are spending way too quickly, be careful!")
             print("-------------------------------------------------------")
             print(f"Your daily net flow for the past week: {data[3]:.2f}")
             if budgets[0] != 0:
                print(f"Daily spending limit: {data[2]:.2f}")
   
             continue

        elif user_input.lower() == "back":
            return 0
        

        elif user_input.lower() == "view_last":
             view(curs,1)
             continue
        
             

        user_input = shlex.split(user_input)

        if len(user_input) == 0:
            continue

        elif user_input[0].lower() == "view":
            if len(user_input) == 2: 
                view(curs, user_input[1])
            else:
                view(curs)
            continue
        elif user_input[0].lower() == "delete":
             print("Exit entry mode to delete transactions")
             continue
        elif user_input[0].lower() == "set_monthly_budget":
             try:
                new_budget = float(user_input[1])
                curs.execute("UPDATE budget SET monthly_budget = ? WHERE id =1",(new_budget,))
                conn.commit()
             except ValueError:
                 print("Please enter a valid budget")
             continue
        elif user_input[0].lower() == "set_budget":
            try:
                new_budget = float(user_input[1])
                curs.execute("UPDATE budget SET total_budget = ? WHERE id =1",(new_budget,))
                conn.commit()
            except ValueError:
                 print("Please enter a valid budget")
            continue

        user_input[0] = id_map.get(user_input[0])
        if user_input[0] == None:
            print("Please provide a valid expense category")
            continue

        try:
             user_input[1] = float(user_input[1])

             if user_input[1] <= 0.0 or user_input[1] > 1000000000 or user_input[1] == float('inf') or user_input[1] == float('-inf'):
                  print("Please provide a valid amout")
                  continue
        except ValueError:
             print("Please provide a valid amount")
             continue


        if len(user_input) > 3:
            try:
                  user_input[3] = datetime.strptime(user_input[3], "%Y-%m-%d")
                  user_input[3] = datetime.strftime(user_input[3],"%Y-%m-%d")

                  if user_input[3] > data[3]:
                       print("Please provide a valid date")
                       continue
            except (ValueError,OverflowError):
                     print("Please provide a valid date")     
                     continue             



        data[0] = user_input[0]
        data[1] = float(user_input[1])       
        if len(user_input) > 2:
            data[2] = user_input[2]         
        if len(user_input) > 3:
            data[3] = user_input[3]


    
        curs.execute("INSERT INTO transactions (category_id, amount, description, date_recorded) VALUES (?, ?, ?, ?)",data)
        conn.commit()

        status(curs,1)






print("""---Welcome to Budget Helper, an AI powered household budget planning tool---
---To enter an expense, write it in the format of [TYPE] [AMOUNT] [DESCRIPTION] [YYYY-MM-DD]--- 
---To clear the database, use the command 'clear'---
---Make sure that the description is in quotes!---""")


db_path  = db_path = Path(__file__).parent.parent / "data" / "budget.db"

if __name__ == '__main__':
    db_init.db_setup()

conn = sqlite3.connect(db_path)
curs = conn.cursor()

id_map = db_dict.id_to_name(conn)

while True:

    
    user_input = input("BudgetHelper>")

    if len(user_input) == 0:
        continue

    elif user_input.lower() == "quit" or user_input.lower() == "exit":
        break


    elif user_input.lower() == "view_last":
             view(curs,1)
             continue
    elif user_input.lower() == "status":
             status(curs)
             data = analysis.analysis(conn,curs)
             curs.execute("""SELECT total_budget, monthly_budget FROM budget WHERE id = 1""")
             budgets = curs.fetchone()
             print("-------------------------------------------------------")
             print(f"Predicted Total Budget: {data[0]:.2f}")
             if budgets[1] != 0:
                print(f"Predicted Monthly Budget: {data[1]:.2f}")
             if (budgets[1] != 0 and data[1] < 0) or data[0] < 0:
                  print("You are spending way too quickly, be careful!")
             print("-------------------------------------------------------")
             print(f"Your daily net flow for the past week: {data[3]:.2f}")
             print(f"Daily spending limit: {data[2]:.2f}")
   
             continue


    elif user_input.lower() == "clear":
        print("Are you sure you want to delete all transactions? y/n")
        ans = input()
        if ans.lower() == "y":
            curs.execute("DELETE from transactions")
            conn.commit()
            print("Database cleared")
            continue
        else:
            continue
    #The above section handles keywords such as clear and quit
    #Now commands will be handled
    user_input = shlex.split(user_input)
    
    if user_input[0].lower() == "enter_transaction":
        print("-----You can now enter transactions, type 'back' to go back to command mode-----")
        exit_status = transaction_control(conn,curs,id_map)
        if exit_status == 0:
            continue
        else:
             break
    elif user_input[0].lower() == "set_monthly_budget":
             try:
                new_budget = float(user_input[1])
                curs.execute("UPDATE budget SET monthly_budget = ? WHERE id =1",(new_budget,))
                conn.commit()
             except ValueError:
                 print("Please enter a valid budget")
             continue
    elif user_input[0].lower() == "view":
            if len(user_input) == 2: 
                view(curs, user_input[1])
            else:
                view(curs)
            continue

    elif user_input[0].lower() == "set_budget":
            try:
                new_budget = float(user_input[1])
                curs.execute("UPDATE budget SET total_budget = ? WHERE id =1",(new_budget,))
                conn.commit()
            except ValueError:
                 print("Please enter a valid budget")
            continue
    
    elif user_input[0].lower() == "delete":
            curs.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT 1")
            result = curs.fetchone() #if no id is given, delete the latest one
            id_to_delete = 0

            if result:
                 id_to_delete = result[0]
            else:
                 print("Database is empty")
                 continue

            if len(user_input) > 1:
                 id_to_delete = user_input[1]
            
            curs.execute("DELETE FROM transactions WHERE id = ?",(id_to_delete,))
            conn.commit()

            id_to_delete =str(id_to_delete)
            if curs.rowcount > 0:     #if the last SQL command affected at least 1 row
                if len(user_input) < 2:
                    print("Success: Deleted latest transaction with id: " +id_to_delete)
                else: 
                    print("Success: Transaction "+id_to_delete+" deleted.")
            else:
                print("Error: Transaction "+id_to_delete +" not found.")
            
            continue
    else:
        print("Invalid or incomplete command")


    
