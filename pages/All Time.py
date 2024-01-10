#%% Modules
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st
from streamlit import session_state as ss

# Bring in the data
scores_df = ss['data']
standings_df = ss['all_standings']

# All Time
st.header('All Time')


# ------------- #
# Combination, Interactive Plot
tab1, tab2 = st.tabs(['Win %', 'Final Placing'])


# ------------- #
# Panel 1: All Time Win Percentage
with tab1:

    playoff = st.checkbox('Include Playoffs?')
    if playoff:
        games = ['season', 'postseason']
    else:
        games = ['season']

    # ------------- #
    # Plot 1.1 Data Manipulation
    rolling_tally = (scores_df[(scores_df['game_type'].isin(games)) & 
                               (scores_df['outcome'] != 'U')]
                        .groupby(['manager', 'year', 'week', 'outcome'])['opponent']
                        .count()
                        .reset_index()
                        .pivot_table(index = ['manager', 'year', 'week'],
                                     columns = 'outcome',
                                     values = 'opponent',
                                     fill_value = 0)
                        .reset_index()
                        .rename_axis(None, axis = 1))
    if 'T' not in rolling_tally.columns:
        rolling_tally['T'] = 0

    # rolling counts of W, L T
    rolling_counts = pd.concat([rolling_tally.drop('year', axis = 1).groupby('manager').cumsum(),
                                rolling_tally[['year']]],
                               axis = 1)
    # rolling_counts = rolling_tally.groupby('manager').cumsum()
    # rolling_counts = rolling_tally.drop('year', axis = 1).groupby('manager').cumsum()
    rolling_df = pd.merge(rolling_tally.loc[:, ['manager', 'year', 'week']],
                          rolling_counts.loc[:, ['W', 'L', 'T']],
                          left_index = True,
                          right_index = True)

    # create metrics
    rolling_df['game_id'] = rolling_df['year'].astype(str) + '-' + rolling_df['week'].astype(str)
    rolling_df['win_pct'] = (rolling_df['W'] + 0.5 * rolling_df['T']) / (rolling_df['W'] + rolling_df['L'] + rolling_df['T'])
    rolling_df['year_end'] = rolling_df['year'].astype(int) + 1
    game_id_sort = rolling_df['game_id'].unique()

    # ------------- #
    # Plot 1.2 Data Manipulation
    membership_df = scores_df.groupby('manager')[['year']].agg(['min', 'max'])
    membership_df.columns = ['_'.join(col).strip() for col in membership_df.columns.values]
    membership_df.reset_index(inplace = True)
    membership_df['year_max'] = membership_df['year_max'].astype(int) + 1

    league_start = membership_df['year_min'].min()
    continuation = membership_df['year_max'].max() + 1

    (membership_df.sort_values(['year_min', 'year_max'],
                               ascending = [True, False],
                               inplace = True))
    domain = membership_df.year_min.unique()


    # ------------- #
    # Plot 1.1
    # Brush highlights, click allows click
    brush = alt.selection_interval(encodings = ['x'])
    click = alt.selection_multi(encodings = ['color'])

    # interactive module
    click = alt.selection_multi(encodings = ['color'])

    # Manual sort order
    membership_sort = rolling_df.groupby('manager')[['year']].agg(['min', 'max'])
    membership_sort.columns = ['_'.join(col).strip() for col in membership_sort.columns.values]
    membership_sort.reset_index(inplace = True)
    (membership_sort.sort_values(['year_min', 'year_max'],
                               ascending = [True, False],
                               inplace = True))

    # Time Series Plot
    win_pct_chart = (
        alt.Chart(
            rolling_df,
            title = 'Win % Time Series'
        ).mark_line().encode(
            x = alt.X(
                'game_id:O',
                sort = game_id_sort
            ).title('Year-Week'),
            y = alt.Y('win_pct:Q').title('Win %').axis(format = '%'),
            color = alt.condition(
                click,
                alt.Color(
                    'manager:N',
                    scale = alt.Scale(
                        scheme = 'category20'
                    )
                ).title('Manager'),
                alt.value('lightgray')
            )
        ).properties(width = 1000)
    )

    # ------------- #
    # Plot 1.2
    timeline_chart = (
        alt.Chart(
            rolling_df,
            title = 'League Membership Timeline'
        ).mark_bar().encode(
            y = alt.Y(
                'manager:N',
                title = 'Manager',
                sort = membership_sort['manager'].to_numpy()
            ),
            x = alt.X(
                'min(year):O',
                title = 'Year',
                scale = alt.Scale(
                    domain = np.arange(membership_sort['year_min'].astype(int).min(),
                                       membership_sort['year_max'].astype(int).max() + 2)
                )
            ),
            x2 = ('max(year_end):O'),
            color = alt.condition(
                click,
                'manager:N',
                alt.value('lightgray')
            )
        ).add_selection(click).properties(width = 1000)
    )

    combo_plot = alt.vconcat(win_pct_chart, timeline_chart)
    st.altair_chart(combo_plot)


# ------------- #
# Panel 2: Final Placement
# Plot 2.1 Parameters
max_range = standings_df['Result'].max()
domain2 = standings_df['Manager'].unique()
range2 = np.repeat('circle', len(domain2))
click = alt.selection_multi(encodings = ['color'])
standings_df['year_end'] = standings_df['Year'] + 1

result_chart = (
    alt.Chart(
        standings_df,
        title = 'Yearly Results'
    ).mark_line().encode(
        x = 'Year:O',
        y = alt.Y(
            'Result:Q',
            scale = alt.Scale(
                domain = [max_range, 1]
            )
        ),
        color = alt.condition(
            click,
            alt.Color(
                'Manager:N',
                scale = alt.Scale(
                    scheme = 'category20'
                )
            ),
            alt.value('lightgray')
        ),
        shape = alt.Shape(
            'Manager:N',
            legend = None,
            scale = alt.Scale(
                domain = domain2,
                range = range2
            )
        )
    )
).properties(width = 1000)

timeline_chart2 = (
    alt.Chart(
        standings_df,
        title = 'League Membership Timeline'
    ).mark_bar().encode(
        y = alt.Y(
            'Manager:N',
            sort = membership_sort['manager'].to_numpy()
        ),
        x = alt.X(
            'min(Year):O',
            title = 'Year',
            scale = alt.Scale(
                domain = np.arange(membership_sort['year_min'].astype(int).min(),
                                   membership_sort['year_max'].astype(int).max() + 2)
            )
        ),
        x2 = 'max(year_end):O',
        color = alt.condition(
            click,
            'Manager:N',
            alt.value('lightgray')
        )
    ).add_selection(click).properties(width = 1000)
)

combo_plot2 = alt.vconcat(result_chart, timeline_chart2)

with tab2:
    st.altair_chart(combo_plot2)


# ------------- #
## Filters, etc. for Display
all_time_record = (scores_df[(scores_df['outcome'] != 'U') & 
                             (scores_df['game_type'].isin(['season', 'postseason']))]
                   .groupby(['manager', 'outcome'])[['points_for', 'points_against']]
                   .agg({'points_for': ['sum', 'count'], 'points_against': 'sum'})
                   .reset_index())
all_time_record_szn = (scores_df[(scores_df['outcome'] != 'U') & 
                                 (scores_df['game_type'].isin(['season']))]
                        .groupby(['manager', 'outcome'])[['points_for', 'points_against']]
                        .agg({'points_for': ['sum', 'count'], 'points_against': 'sum'})
                        .reset_index())
all_time_record_pzn = (scores_df[(scores_df['outcome'] != 'U') & 
                                 (scores_df['game_type'].isin(['postseason']))]
                        .groupby(['manager', 'outcome'])[['points_for', 'points_against']]
                        .agg({'points_for': ['sum', 'count'], 'points_against': 'sum'})
                        .reset_index())

def fix_all_time(df):
    df.columns = ['manager', 'outcome', 'points_for', 'count', 'points_against']
    df = df.pivot_table(index = 'manager',
                        columns = 'outcome',
                        values = ['points_for', 'count'],
                        fill_value = 0)
    df.columns = [''.join(col).strip() for col in df.columns.values]

    # check for ties
    if 'countT' not in df.columns:
        df['countT'] = 0
    if 'points_forT' not in df.columns:
        df['points_forT'] = 0

    # create metrics of interest
    df['total_points'] = df['points_forW'] + df['points_forT'] + df['points_forL']
    df['record'] = df['countW'].astype(str) + '-' + df['countL'].astype(str) + '-' + df['countT'].astype(str)
    df['win_pct'] = round(((df['countW'] + 0.5 * df['countT']) / (df['countW'] + df['countL'] + df['countT'])) * 100, 2)

    # clean up dataframe
    df = (df.loc[:, ['record', 'win_pct', 'total_points']]
            .sort_values('win_pct', ascending = False)
            .reset_index())

    df.columns = ['Manager', 'Record', 'Win %', 'Total Points']
    
    return df

atr = fix_all_time(all_time_record)
atr_s = fix_all_time(all_time_record_szn)
atr_p = fix_all_time(all_time_record_pzn)

# Display all the data
align = st.checkbox('Align data?')
d1, d2, d3 = st.columns(3)
with d1:
    st.subheader('All Games')
    if align:
    	st.dataframe(atr.sort_values(by = 'Manager'),
    				 hide_index = True,
    				 height = len(atr) * 35 + 38)
    else:
	    st.dataframe(atr,
	    			 hide_index = True,
	    			 height = len(atr) * 35 + 38)
with d2:
    st.subheader('Regular Season')
    if align:
    	st.dataframe(atr_s.sort_values(by = 'Manager'),
    				 hide_index = True,
    				 height = len(atr) * 35 + 38)
    else:
	    st.dataframe(atr_s,
	    			 hide_index = True,
	    			 height = len(atr) * 35 + 38)
with d3:
	st.subheader('Postseason')
	if align:
		st.dataframe(atr_p.sort_values(by = 'Manager'),
					 hide_index = True,
					 height = len(atr) * 35 + 38)
	else:
		st.dataframe(atr_p,
					 hide_index = True,
					 height = len(atr) * 35 + 38)


# ------------- #
# Number of Championships/Sackos
num_of_teams = standings_df.groupby(['Year'], as_index = False).max()[['Year', 'Result']]
last_place = pd.merge(num_of_teams,
                      standings_df,
                      how = 'left',
                      on = ['Result', 'Year'])
if 'U' in scores_df['outcome'].unique():
    championships = standings_df[standings_df['Result'] == 1].iloc[:-1, :]['Manager'].value_counts()
    sackos = last_place.iloc[:-1, :]['Manager'].value_counts()
else:
    championships = standings_df[standings_df['Result'] == 1]['Manager'].value_counts()
    sackos = last_place['Manager'].value_counts()

results_df = (pd.merge(championships,
                       sackos,
                       how = 'outer',
                       left_index = True,
                       right_index = True)
                .fillna(0)
                .reset_index()
                .rename(columns = {'count_x': 'Champs',
                                   'count_y': 'Sackos'}))

st.subheader('# of Championships/Sackos')
st.dataframe(results_df,
             hide_index = True,
             height = len(results_df) * 35 + 38)