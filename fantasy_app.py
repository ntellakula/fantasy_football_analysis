#%% Modules
import datetime
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st
from espn_api.football import League


#%% Structure
st.title('All Your Fantasy Needs')

## User-Input Parameters
param1, param2 = st.columns(2)

# First Year to Extract all History
with param1:
    league_start = st.number_input("What was the inaugural year of your league?",
                                   step = 1,
                                   min_value = 2000)
# League ID
with param2:
    league_id = st.number_input("What is your league ID?", step = 1)

# Instructions for Cookies
st.header('Instructions to Locate the Necessary Cookies:')
st.markdown('''
1. Open the ESPN league page.
2. Right click anywhere and scroll to `Inspect`.
3. Navigate to `Network`.
4. Refresh the page.
5. Under `Name`, there will be a alphanumeric string that begins with your league ID. Click it.
6. Scroll to `Request Headers` and locate the field `Cookie:`.
7. Copy the entire string and paste it into a text editor.
8. Ctrl+F/Cmd+F and search `swid` and `espn_s2`. These are the cookies to paste below.
            ''')

## Cookies
cookie1, cookie2 = st.columns(2)

# SWID
with cookie1:
    swid = st.text_input("What is your SWID cookie?")
    swid = "'" + swid + "'"

# ESPN S2
with cookie2:
    espn_s2 = st.text_input("What is your ESPN S2 cookie?")
    espn_s2 = "'" + espn_s2 + "'"

current_year = datetime.date.today().year
all_years = np.arange(league_start, current_year + 1)
index_2018 = np.where(all_years == 2018)
if index_2018[0].shape[0] == 1:
    all_years = np.delete(all_years, index_2018)

leagues = []
for year in all_years:
    league = League(league_id, year, espn_s2, swid)
    leagues.append(league)

scores_df = []
# outer loop to loop through all the leagues/years
for league in leagues:
    season_weeks = league.settings.reg_season_count
    teams = league.teams
    team_ids = [team.team_id for team in teams]

    # inner loop to loop through the teams in each year
    for id in team_ids:

        team_data = league.get_team_data(id)

        # some managers' data has been purged
        if team_data is None:
            continue
        else:
            opponent_list = pd.DataFrame({'opponent': [opp.owner for opp in team_data.schedule],
                                          'outcome': team_data.outcomes,
                                          'points_for': team_data.scores,
                                          'mov': team_data.mov})
            opponent_list['manager'] = team_data.owner
            opponent_list['game_type'] = 'postseason'
            scores_df.append(opponent_list)
            opponent_list.iloc[:season_weeks, 5] = 'season'
            opponent_list['year'] = league.year


scores_df = pd.concat(scores_df)
scores_df['points_against'] = scores_df['points_for'] - scores_df['mov']

# Head to Head
st.header('Head to Head Matchups')

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

# Look at the Table
filtered_scores = (scores_df[(scores_df['manager'].isin(manager1)) & 
                             (scores_df['opponent'].isin(manager2)) & 
                             (scores_df['outcome'] != 'U') & 
                             (scores_df['game_type'].isin(game_filter))])
filtered_scores = filtered_scores.reset_index(drop = True).iloc[:, [6, 4, 0, 1, 2, 7, 5]]

# subset before column fixes to create a plotting dataframe
plot_df_wins = (filtered_scores.loc[:, ['year', 'outcome', 'opponent']]
                               .groupby(['year', 'outcome'], as_index = False)
                               .count()
                               .rename(columns = {'opponent': 'counts'}))
plot_df_wins['cum_count'] = plot_df_wins.groupby('outcome').cumsum()[['counts']]
plot_df_wins['year'] = plot_df_wins['year'].astype(str)
plot_df_wins['outcome'] = plot_df_wins['outcome'].replace(['W', 'L'], ['Wins', 'Losses'])

filtered_pf = filtered_scores['points_for'].sum()
filtered_pa = filtered_scores['points_against'].sum()

# plot dataframe for total points for/against
plot_df_points = (filtered_scores.loc[:, ['year', 'points_for', 'points_against']]
                                 .groupby('year', as_index = False)
                                 .sum())
plot_df_points['cum_pf'] = plot_df_points['points_for'].cumsum()
plot_df_points['cum_pa'] = plot_df_points['points_against'].cumsum()
plot_df_points['year'] = plot_df_points['year'].astype(str)
plot_df_points = pd.melt(plot_df_points,
                         id_vars = ['year'],
                         value_vars = ['cum_pf', 'cum_pa'])
plot_df_points['variable'] = plot_df_points['variable'].replace(['cum_pf', 'cum_pa'], ['For', 'Against'])


filtered_scores.columns = ['Year', 'Manager(s) #1', 'Manager(s) #2',
                           'Outcome', 'Points For', 'Points Against',
                           'Game Type']
filtered_scores['Year'] = filtered_scores['Year'].astype(str)

# Apply coloring
def highlight_wins(value):
    color = 'green' if value == 'W' else 'yellow' if value == 'T' else 'red'
    return f'background-color: {color}'

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

if filtered_scores.shape[0] == 0:
    st.write('No data matching selected parameters.')
else:
    p1, p2, p3 = st.columns(3)
    with p1:
        st.subheader('Record: ' + record, divider = 'red')
    with p2:
        st.subheader('Total Points: ' + filtered_pf.astype(str) + '-' + filtered_pa.astype(str), divider = 'red')
    st.write(filtered_scores.style.applymap(highlight_wins, subset = ['Outcome']))

## Line Chart of Wins/Losses
domain = ["Wins", "Losses"]
domain2 = ['For', 'Against']
range = ["green", "red"]

wins_chart = alt.Chart(plot_df_wins,
                       title = 'Win/Loss Time Series').mark_line().encode(
    x = alt.X('year').title('Year'),
    y = alt.Y('cum_count').title('Count'),
    color = alt.Color('outcome').scale(domain = domain, range = range).title('Outcome')
).interactive()

## Line Chart of Points For/Against
points_chart = alt.Chart(plot_df_points,
                         title = 'Points For/Against Time Series').mark_line().encode(
                             x = alt.X('year').title('Year'),
                             y = alt.Y('value').title('Points'),
                             color = alt.Color('variable').scale(domain = domain2, range = range).title('Points')
                         ).interactive()

## Tabs for Graphs
ts1, ts2 = st.tabs(['Win/Loss', 'Points For/Against'])
with ts1:
    st.altair_chart(wins_chart, use_container_width = True)
with ts2:
    st.altair_chart(points_chart, use_container_width = True)
