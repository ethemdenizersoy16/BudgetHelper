import pandas
from datetime import datetime
import calendar
from sklearn.linear_model import LinearRegression
import numpy

def prediction(dataframe_t,stats, budgets, curs):
     now = datetime.now()
     monthly_enteries = dataframe_t[(dataframe_t.index.month == now.month) & (dataframe_t.index.year == now.year)].copy()

     curs.execute("""SELECT COALESCE(SUM(CASE WHEN category_id != 1 AND category_id != 12 THEN - amount ELSE 0 END),0)
                  FROM transactions WHERE date_recorded >= date('now','start of month')""")
     monthly_spent = curs.fetchone()[0]

     curs.execute("""SELECT COALESCE(SUM(CASE WHEN category_id != 1 AND category_id != 12 THEN - amount ELSE 0 END),0)
                  +COALESCE(SUM(CASE WHEN category_id == 1 OR category_id == 12 THEN amount ELSE 0 END),0)
                  FROM transactions""")

     total_spent = curs.fetchone()[0]

     num_days = len(monthly_enteries)

     if num_days < 7:
        weight_model = 0.3
        weight_velocity = 0.7
     else:
        weight_model = 0.8
        weight_velocity = 0.2

     if num_days < 2:
        struct_cumsum = dataframe_t['structured_cumilative_sum'].iloc[-1] if not dataframe_t.empty else 0
        expense_cumsum = dataframe_t['expense_cumilative_sum'].iloc[-1] if not dataframe_t.empty else 0
        return [budgets[0] + total_spent, budgets[1]+ monthly_spent, 0.0, stats[0]]

     X = monthly_enteries['date_of_month'].values.reshape(-1,1)

     last_day = calendar.monthrange(now.year, now.month)[1]
     y = monthly_enteries['expense_cumilative_sum'].values

     model = LinearRegression().fit(X,y)

     monthly_raw_prediction = model.predict([[last_day]])[0]


     y = monthly_enteries['structured_cumilative_sum'].values

     model = LinearRegression().fit(X,y)

     total_raw_prediction = model.predict([[last_day]])[0]

     
     struct_cumsum = 0
     expense_cumsum = 0
     if not dataframe_t.empty:
        struct_cumsum = dataframe_t['structured_cumilative_sum'].iloc[-1]
        expense_cumsum = dataframe_t['expense_cumilative_sum'].iloc[-1]

     days_left = last_day - now.day
     total_velocity_prediction = days_left * stats[3] + struct_cumsum
     monthly_velocity_prediction = days_left * stats[2] + expense_cumsum

     total_final_prediction = weight_model * total_raw_prediction + weight_velocity * total_velocity_prediction
     monthly_final_prediction = weight_model * monthly_raw_prediction + weight_velocity * monthly_velocity_prediction


     total_worst_case = total_final_prediction - 2*stats[1] * (days_left ** 0.5)
     monthly_worst_case = monthly_final_prediction - 2*stats[1] * (days_left ** 0.5)


     monthly_daily = max((budgets[1] + monthly_spent)/max(days_left, 1),0)
     total_daily = max((budgets[0] + total_spent)/max(days_left,1),0)

     daily = min(total_daily , monthly_daily) if budgets[1] != 0 else total_daily #the daily limit is made to make sure you 1)do not exceed total budget and 2) you do not exceed monthly budget in this order

     worst_total_budget = total_spent + budgets[0] + (total_worst_case - struct_cumsum)
     worst_monthly_budget = monthly_spent + budgets[1] + (monthly_worst_case - expense_cumsum)

     return [worst_total_budget,worst_monthly_budget,daily,stats[0]]
    

def get_statistics(dataframe_t):
     if dataframe_t.empty:
       return [0,0,0,0]

     recent_velocity = dataframe_t['7day_avarage'].iloc[-1]

     std_deviation = dataframe_t['standart_dev'].iloc[-1]
   
     exp_velocity = dataframe_t['expense_7day_avarage'].iloc[-1]

     struct_velocity = dataframe_t['struct_7day_avarage'].iloc[-1]

     return [recent_velocity, std_deviation, exp_velocity, struct_velocity]

def get_dataframe(conn):

     #dataframe containing raw information with every single entry    
     dataframe_raw = pandas.read_sql_query("""SELECT t.date_recorded, c.name as category, CASE WHEN c.name = "Income" OR c.name = "Continous Income" 
                                           THEN t.amount
                                           ELSE -t.amount END as signed_amount FROM transactions t JOIN categories c ON t.category_id = c.id
                                            ORDER BY t.date_recorded ASC
                                            """,conn)
   



     dataframe_raw['date_recorded'] = pandas.to_datetime(dataframe_raw['date_recorded'])
     dataframe_raw['expenses_only'] = numpy.where((dataframe_raw['category'] == 'Income') | (dataframe_raw['category'] == 'Continous Income'), 0, dataframe_raw['signed_amount'])
     dataframe_raw['expenses_and_cont'] = numpy.where(dataframe_raw['category'] == 'Income', 0, dataframe_raw['signed_amount'])
     #the income on the same days are summed up, this database will be used for monthly prediction
     dataframe_time = dataframe_raw.set_index('date_recorded').resample('D').sum().fillna(0)
     dataframe_time['date_of_month'] = dataframe_time.index.day#the days are what will be used as the x axis
     dataframe_time = dataframe_time[dataframe_time.index.date != pandas.Timestamp('today').date()] #since today is incomplete we filter it
  

     dataframe_time['expense_cumilative_sum'] = dataframe_time['expenses_only'].cumsum()
     dataframe_time['structured_cumilative_sum'] = dataframe_time['expenses_and_cont'].cumsum()


     dataframe_time['7day_avarage'] = dataframe_time['signed_amount'].ewm(span=7, min_periods=1).mean() #the avarage spending + gain of the last week, will be used for predictions
     dataframe_time['expense_7day_avarage'] = dataframe_time['expenses_only'].ewm(span = 7, min_periods = 1).mean()#the avarage spending, used for the monthly prediction
     dataframe_time['struct_7day_avarage'] = dataframe_time['expenses_and_cont'].ewm(span = 7, min_periods = 1).mean()#the avarage spending + cont income
     dataframe_time['standart_dev'] = dataframe_time['expenses_only'].rolling(window = 14, min_periods= 1).std().fillna(0)#the spending volatility

    #cumilative_sum on the 31st by itself isnt very meaningful, so we will need to do some operations on it later

     return [dataframe_raw, dataframe_time]
def get_category_velocity(dataframe_raw):
      max_velocity = 0
      category = ""
      categories = dataframe_raw['category'].unique()
      one_weekago = (pandas.to_datetime('today') - pandas.Timedelta(days=7)).normalize()
      for i in categories:
            if i == 'Income' or i == 'Continous Income':
                continue
            dataframe_i = dataframe_raw[dataframe_raw['category'] == i].copy() 
            currentcand = (dataframe_i['signed_amount'].where(dataframe_i['date_recorded'] >= one_weekago).sum()) /7 if not dataframe_i.empty else 0

            max_velocity = min(max_velocity, currentcand)
            if max_velocity == currentcand:
                category = i 
      return [category,float(abs(max_velocity))]


def analysis(conn,curs):
     dataframes = get_dataframe(conn)
     stats = get_statistics(dataframes[1])
     curs.execute("""SELECT total_budget, monthly_budget FROM budget WHERE id = 1""")
     budgets = curs.fetchone()
     max_cat = get_category_velocity(dataframes[0])
     print("-------------------------------------------------------")
     print(f"In the past week you spent the most on: {max_cat[0]}")
     print(f"On avarage you spent {max_cat[1]:.2f} per day for this category")

     return prediction(dataframes[1],stats, budgets,curs)
  


     
     
