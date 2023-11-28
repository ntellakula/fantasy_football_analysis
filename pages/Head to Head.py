#%% Modules
import pandas as pd
import altair as alt
import streamlit as st
from streamlit import session_state as ss

# Head to Head
st.header('Head to Head Matchups')

# Bring in the data
scores_df = ss['data']

# Parameters for the matchup
man1, man2, man3 = st.columns(3)
with man1:
    manager1 = st.multiselect(
        'Manager(s) #1',
        scores_df['manager'].unique()
    )
with man2:
    manager2 = st.multiselect(
        'Manager(s) #2',
        scores_df['opponent'].unique()
    )
with man3:
    game_filter = st.multiselect(
        'Game Type',
        scores_df['game_type'].unique(),
        scores_df['game_type'].unique()
    )

# Apply coloring
def highlight_wins(value):
    color = 'green' if value == 'W' else 'yellow' if value == 'T' else 'red'
    return f'background-color: {color}'

## Create the DataFrame to be output: H2H
# Look at the Table
filtered_scores = (scores_df[(scores_df['manager'].isin(manager1)) & 
                             (scores_df['opponent'].isin(manager2)) & 
                             (scores_df['outcome'] != 'U') & 
                             (scores_df['game_type'].isin(game_filter))]
                    .reset_index(drop = True)
                    .iloc[:, [6, 4, 0, 1, 2, 8, 7, 5]])
filtered_scores.columns = ['Week', 'Manager(s) #1', 'Manager(s) #2',
                           'Outcome', 'Points For', 'Points Against',
                           'Year', 'Game Type']
filtered_scores['Year'] = filtered_scores['Year'].astype(str)

## Create the H2H Record
# Create Record
winloss = filtered_scores['Outcome'].value_counts()
if 'W' in winloss.index:
    wins = winloss[winloss.index == 'W'].values[0]
else:
    wins = 0
if 'L' in winloss.index:
    loss = winloss[winloss.index == 'L'].values[0]
else:
    loss = 0
if 'T' in winloss.index:
    ties = winloss[winloss.index == 'T'].values[0]
else:
    ties = 0

record = str(wins) + '-' + str(loss) + '-' + str(ties)

## Create the Aggregate H2H Score
filtered_pf = filtered_scores['Points For'].sum()
filtered_pa = filtered_scores['Points Against'].sum()

# Output the values
if filtered_scores.shape[0] == 0:
    st.write('No data matching selected parameters.')
else:
    p1, p2, p3 = st.columns(3)
    with p1:
        st.subheader('Record: ' + record, divider = 'red')
    with p2:
        st.subheader('Total Points: ' + filtered_pf.astype(str) + '-' + filtered_pa.astype(str), divider = 'red')

    # Checkbox to show all data
    show_all = st.checkbox('Show all matchups')
    if show_all:
        st.dataframe(filtered_scores.style.applymap(highlight_wins, subset = ['Outcome']), hide_index = True, height = len(filtered_scores) * 35 + 38)
    else:
        st.dataframe(filtered_scores.style.applymap(highlight_wins, subset = ['Outcome']), hide_index = True)



## Create the Wins/Points Charts
# subset before column fixes to create a plotting dataframe
plot_df_wins = (filtered_scores.loc[:, ['Year', 'Outcome', 'Manager(s) #2']]
                               .groupby(['Year', 'Outcome'], as_index = False)
                               .count()
                               .rename(columns = {'Manager(s) #2': 'counts'}))
plot_df_wins['cum_count'] = plot_df_wins.groupby('Outcome')['counts'].cumsum()
plot_df_wins['Outcome'] = plot_df_wins['Outcome'].replace(['W', 'L'], ['Wins', 'Losses'])


# plot dataframe for total points for/against
plot_df_points = (filtered_scores.loc[:, ['Year', 'Points For', 'Points Against']]
                                 .groupby('Year', as_index = False)
                                 .sum())
plot_df_points['cum_pf'] = plot_df_points['Points For'].cumsum()
plot_df_points['cum_pa'] = plot_df_points['Points Against'].cumsum()
plot_df_points['Year'] = plot_df_points['Year'].astype(str)
plot_df_points = pd.melt(plot_df_points,
                         id_vars = ['Year'],
                         value_vars = ['cum_pf', 'cum_pa'])
plot_df_points['variable'] = plot_df_points['variable'].replace(['cum_pf', 'cum_pa'], ['For', 'Against'])


# Output the charts
## Line Chart of Wins/Losses
domain = ["Wins", "Losses"]
domain2 = ['For', 'Against']
range = ["green", "red"]

wins_chart = alt.Chart(plot_df_wins,
                       title = 'Win/Loss Time Series').mark_line().encode(
    x = alt.X('Year').title('Year'),
    y = alt.Y('cum_count').title('Count'),
    color = alt.Color('Outcome').scale(domain = domain, range = range).title('Outcome')
).interactive()

## Line Chart of Points For/Against
points_chart = alt.Chart(plot_df_points,
                         title = 'Points For/Against Time Series').mark_line().encode(
                             x = alt.X('Year').title('Year'),
                             y = alt.Y('value').title('Points'),
                             color = alt.Color('variable').scale(domain = domain2, range = range).title('Points')
                         ).interactive()

## Tabs for Graphs
ts1, ts2 = st.tabs(['Win/Loss', 'Points For/Against'])
with ts1:
    st.altair_chart(wins_chart, use_container_width = True)
with ts2:
    st.altair_chart(points_chart, use_container_width = True)
