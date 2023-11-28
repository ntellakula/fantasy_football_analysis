#%% Modules
import datetime
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st
from streamlit import session_state as ss

#%% Season-Level
st.header('Historical Transactions')

# Raw Data
acq_df = ss['acqusition']
league_start = ss['start_year']
current_year = datetime.date.today().year

# remove 2018 as its a problem (TO FIX)
all_years = np.arange(league_start, current_year + 1)
index_2018 = np.where(all_years == 2018)
if index_2018[0].shape[0] == 1:
    all_years = np.delete(all_years, index_2018)

# Make it Long for Display
acq_df.columns = ['Manager', 'Pickups', 'Trades', 'FAAB Spent', 'Year']
acq_df['Year'] = acq_df['Year'].astype(int)
acq_df_wide = (acq_df.pivot_table(index = 'Manager',
								  columns = 'Year',
								  values = ['Pickups', 'Trades', 'FAAB Spent'])
						.T
						.reset_index()
						.sort_values('Year')
						.rename(columns = {'level_0': 'Metric'}))

# filter the data by year or metric
metrics = st.multiselect('Display Which metrics?',
						 ['FAAB Spent', 'Trades', 'Pickups'],
						 ['FAAB Spent', 'Trades', 'Pickups'])
years = st.multiselect('Display which years?',
					   all_years,
					   all_years)

# acq_df_wide.fillna('', inplace = True)
acquistions_df = acq_df_wide[(acq_df_wide['Metric'].isin(metrics)) & (acq_df_wide['Year'].isin(years))]
acquistions_df['Year'] = acquistions_df['Year'].astype(str)
st.dataframe(acquistions_df, hide_index = True)


#%% Time Series of Acquisition Metrics
metrics_agg = (acq_df.groupby('Year')
                     .agg(total_trades = ('Trades', np.sum),
                          mean_acq = ('Pickups', np.mean),
                          mean_faab = ('FAAB Spent', np.mean))
                     .reset_index()
                     .melt(id_vars = 'Year',
                           value_vars = ['total_trades', 'mean_acq', 'mean_faab']))
metrics_agg['variable'] = metrics_agg['variable'].map({'total_trades': 'Total Trades',
													   'mean_acq': 'Avg. Acq.',
													   'mean_faab': 'Avg. FAAB Spent'})

## Plot
trans_chart = (
    alt.Chart(
        metrics_agg,
        title = 'Transaction Metrics'
    ).mark_line().encode(
        x = alt.X('Year:O'),
        y = alt.Y('value:Q').title('Value'),
        color = alt.Color('variable:N').title('Metric')
    )
).interactive()

st.altair_chart(trans_chart, use_container_width = True, theme = None)