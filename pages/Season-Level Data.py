#%% Modules
import datetime
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st
from streamlit import session_state as ss

#%% Season-Level
st.header('Season-Level League Data')

# Bring in the data
scores_df = ss['data']
league_start = ss['start_year']
standings_df = ss['all_standings']
all_comps_df = ss['comparisons_df']
all_scores_df = ss['comparisons_score']
current_year = datetime.date.today().year

# remove 2018 as its a problem (TO FIX)
all_years = np.arange(league_start, current_year + 1)
index_2018 = np.where(all_years == 2018)
if index_2018[0].shape[0] == 1:
    all_years = np.delete(all_years, index_2018)

season_of_interest = st.selectbox(
    'Season',
    all_years
)

#%% Heatmap Plot: Dataframe
scores_df['year'] = scores_df['year'].astype(int)
df_source = scores_df[(scores_df['outcome'] != 'U') & (scores_df['game_type'] == 'season') & (scores_df['year'] == season_of_interest)]

num_weeks = df_source['week'].max()

# Create the dataframe
def weekly_aggregate(i):
    """
    subset all scores by a given week then add record, wins, scores
    """
    # all the scores for the week, sorted, and adding columns for the w/l/t
    total_teams = df_source.manager.nunique()
    scores = (df_source[df_source['week'] == (i + 1)]
                .sort_values(by = ['points_for'])
                .reset_index(drop = True)
                .assign(total_wins = np.arange(0, total_teams, 1),
                        total_loss = np.arange(total_teams - 1, -1, -1),
                        ind = np.arange(0, total_teams, 1)))
    
    #which values have matching scores?
    ties_loc = np.argwhere(np.array(scores.duplicated(subset = 'points_for',
                                                      keep = False)) == True)
    
    #split the duplicated and non-duplicated values into separate DFs
    scores_nod = (scores[~scores['total_wins'].isin(ties_loc.flatten())]
                    .assign(total_ties = 0))
    scores_dup = scores[scores['total_wins'].isin(ties_loc.flatten())]
    
    #what are the unique scores in the list of duplicates?
    unique_scores = scores_dup['points_for'].unique()
    
    #only run through the loop if there are duplicates
    if len(unique_scores) > 0:
        #loop through all the scores to add the ties
        #initiate list
        dup_list = []
        for j in range(len(unique_scores)):
            
            #iterating through all the repeated scores
            unique = scores[scores['points_for'] == unique_scores[j]]
            
            #add in loss/wins
            unique['total_wins'] = min(unique['total_wins'])
            unique['total_loss'] = min(unique['total_loss'])
            unique = unique.assign(total_ties = total_teams - 1
                                   - (unique['total_loss'] + unique['total_wins']))
            
            dup_list.append(unique)
            
        #compile them
        dup_list = pd.concat(dup_list)
        dup_list = pd.concat([dup_list, scores_nod]).sort_values(by = ["ind"])
        return dup_list
    
    else:
        scores["total_ties"] = 0
        return scores


# initialize an empty dataframe to append to
full_wl = []

# loop through all the teams and have the rows append
for j in range(df_source['week'].max()):
    row = weekly_aggregate(j)
    full_wl.append(row)

# remove the first row which was just empty
full_wl = pd.concat(full_wl)

# Make the Plot
base = alt.Chart(
    full_wl,
    title = 'Simulated vs. ESPN Records by Week'
).encode(
    alt.X('week:O', axis = alt.Axis(labelAngle = 0)).title('Week'),
    alt.Y('manager:O').title('Manager')
)
heatmap = base.mark_rect().encode(
    alt.Color(
        'total_wins:Q',
        legend = None
    ).scale(
        scheme = 'redyellowgreen'
    )
).interactive()
text = base.mark_text(
    baseline = 'middle',
    fontWeight = 'bold'
).encode(
    alt.Text(
        'total_wins:Q'
    )
)

heatmap_chart = alt.layer(heatmap, text).configure_scale(rectBandPaddingInner = 0.1)
st.altair_chart(heatmap_chart, use_container_width = True)


#%% Record Comparison Dataframe
simulated_record = (full_wl.groupby('manager')[['total_wins', 'total_loss', 'total_ties', 'points_for']]
                           .sum()
                           .sort_values(by = 'total_wins', ascending = False))
simulated_record['simulated_record'] = simulated_record['total_wins'].astype(str) + '-' + simulated_record['total_loss'].astype(str) + '-' + simulated_record['total_ties'].astype(str)
simulated_record['s_standing'] = np.arange(simulated_record.shape[0]) + 1

# EDIT: to create totalpoints then sort by wins then points, add ties
espn_record = (df_source.groupby(['manager', 'outcome'])['points_for']
                        .agg(['sum', 'count'])
                        .reset_index()
                        .pivot_table(index = 'manager',
                                     columns = 'outcome',
                                     values = ['sum', 'count'],
                                     fill_value = 0))
espn_record.columns = [''.join(col).strip() for col in espn_record.columns.values]
espn_record = (espn_record.sort_values(by = ['countW', 'sumW'], ascending = False)
                          .drop(['sumL', 'sumW'], axis = 1))

if 'countT' not in espn_record.columns:
    espn_record['countT'] = 0
espn_record['espn_record'] = espn_record['countW'].astype(str) + '-' + espn_record['countL'].astype(str) + '-' + espn_record['countT'].astype(str)
espn_record['e_standing'] = np.arange(espn_record.shape[0]) + 1

records = pd.merge(simulated_record,
                   espn_record,
                   left_index = True,
                   right_index = True)
records['difference'] = records['s_standing'] - records['e_standing']
records = records.loc[:, ['simulated_record', 'espn_record', 'difference']].reset_index()


## Pythagorean Expectation of Wins
grouped_scores = df_source.loc[:, ['manager', 'points_for', 'points_against']].groupby('manager').sum()
grouped_scores['expectation'] = (grouped_scores['points_for'] ** 6.2 / (grouped_scores['points_for'] ** 6.2 + grouped_scores['points_against'] ** 6.2)) * num_weeks
grouped_scores.reset_index(inplace = True)

# add in PE into records df
records = pd.merge(records, grouped_scores, on = 'manager').drop(['points_for', 'points_against'], axis = 1)

records.columns = ['Manager', 'Simulated', 'ESPN', 'Difference', 'PE*']

# Apply coloring
def highlight_wins(value):
    color = 'green' if value > 0 else 'red' if value < 0 else 'yellow'
    return f'background-color: {color}'



#%% Results of the Season
standings_year = standings_df[standings_df['Year'] == season_of_interest]
standings_year['Year'] = standings_year['Year'].astype(str)
# standings_year.drop('year_end', axis = 1, inplace = True)
# standings_year['year_end'] = standings_year['year_end'].astype(str)

#%% Output the Season's DataFrames
## User-Input Parameters
frame1, frame2 = st.columns(2)
with frame1:
    st.subheader('Simulated vs. ESPN')
    st.dataframe(records.style.applymap(highlight_wins, subset = ['Difference']), hide_index = True, height = len(records) * 35 + 38)
    st.write('*PE: Pythagorean Expectation, or expected wins, is calculated as:')
    st.markdown(r'$$Wins=\frac{PF^{6.2}}{PF^{6.2}+PA^{6.2}} \times \# games$$')
with frame2:
    st.subheader('Season Results')
    st.dataframe(standings_year, hide_index = True, height = len(standings_year) * 35 + 38)

st.divider()


#%% Optimal Lineups
st.subheader('Optimal Lineups')

manager_of_interest = st.selectbox(
    'Manager',
    all_scores_df['manager'].unique()
)

scoring_chart_df = all_scores_df[(all_scores_df['manager'] == manager_of_interest) & (all_scores_df['type'] != 'projected')]
scoring_chart = (
    alt.Chart(
        scoring_chart_df,
        title = 'Optimal vs. Observed Scoring'
    ).mark_bar().encode(
        x = alt.X('week:O').title('Week'),
        y = alt.Y('score').title('Score'),
        color = alt.Color(
            'type',
            scale = alt.Scale(
                domain = ['original', 'optimal'],
                range = ['red', '#ffbfbf']
            )
        ).title('Score Type')
    )
)

st.altair_chart(scoring_chart, use_container_width = True)

proj_chart_df = all_scores_df[(all_scores_df['manager'] == manager_of_interest) & (all_scores_df['type'] != 'optimal')]
proj_chart = (
    alt.Chart(
        proj_chart_df,
        title = 'Projected vs. Observed Scoring'
    ).mark_bar().encode(
        x = alt.X('type:N').title('Type'),
        y = alt.Y('score:Q').title('Score'),
        column = alt.Column('week:O').title('Week'),
        color = alt.Color(
            'type:N',
            scale = alt.Scale(
                domain = ['original', 'projected'],
                range = ['red', '#ffbfbf']
            )
        ).title('Score Type')
    )
)

st.altair_chart(proj_chart)


#%% Dataframes
cols = st.columns(3)
for i in range(num_weeks):
    col = cols[i % 3]
    optimal_df = all_comps_df[(all_comps_df['manager'] == manager_of_interest) & (all_comps_df['week'] == i + 1)].loc[:, ['optimal_positions', 'optimal_players', 'og_lineup_name']]
    optimal_df.columns = ['Position', 'Optimal', 'Original']
    col.write(f'Week {i + 1}')
    col.dataframe(optimal_df, hide_index = True, height = len(optimal_df) * 35 + 38)
    og_score = all_scores_df[(all_scores_df['manager'] == manager_of_interest) & (all_scores_df['week'] == i + 1) & (all_scores_df['type'] == 'original')]['score'].values[0]
    op_score = all_scores_df[(all_scores_df['manager'] == manager_of_interest) & (all_scores_df['week'] == i + 1) & (all_scores_df['type'] != 'projected')]['score'].sum()
    pr_score = all_scores_df[(all_scores_df['manager'] == manager_of_interest) & (all_scores_df['week'] == i + 1) & (all_scores_df['type'] == 'projected')]['score'].values[0]
    col.write(f'Optimal: {op_score} || Original: {og_score} || Projected: {pr_score}')


#%% Lineup Accuracy
st.divider()
st.subheader('Lineup Accuracy')

opt_acc1 = (
    all_scores_df[all_scores_df['type'] != 'projected']
    .groupby(['manager'], as_index = False)
    .sum()
    .drop(['type', 'week'], axis = 1)
    .rename(columns = {'score': 'Optimal'})
)
opt_acc2 = (
    all_scores_df[all_scores_df['type'] == 'original']
    .groupby(['manager'], as_index = False)
    .sum()
    .rename(columns = {'score': 'Original'})
    .drop(['type', 'week'], axis = 1)
)
opt_acc3 = pd.merge(opt_acc1, opt_acc2, on = ['manager'])
opt_acc3['pct'] = round(opt_acc3['Original'] / opt_acc3['Optimal'] * 100, 2)

prj_acc1 = (
    all_scores_df[all_scores_df['type'] == 'projected']
    .groupby(['manager'], as_index = False)
    .sum()
    .drop(['type', 'week'], axis = 1)
    .rename(columns = {'score': 'Projected'})
)
prj_acc2 = (
    all_scores_df[all_scores_df['type'] == 'original']
    .groupby(['manager'], as_index = False)
    .sum()
    .rename(columns = {'score': 'Original'})
    .drop(['type', 'week'], axis = 1)
)
prj_acc3 = pd.merge(prj_acc1, prj_acc2, on = ['manager'])
prj_acc3['pct'] = round(prj_acc3['Original'] / prj_acc3['Projected'] * 100, 2)


# The Plots
optimization_base = (
    alt.Chart(
        opt_acc3,
        title = 'Optimal Accuracy'
    ).encode(
        x = alt.X('pct').title('Percent Optimal'),
        y = alt.Y('manager', sort = ('-x')).title('Manager'),
        text = 'pct'
    )
)
optimization_chart = optimization_base.mark_bar() + optimization_base.mark_text(align = 'right', dx = -4)

projection_base = (
    alt.Chart(
        prj_acc3,
        title = 'Projection Accuracy'
    ).encode(
        x = alt.X('pct').title('Percent of Projection'),
        y = alt.Y('manager', sort = ('-x')).title('Manager'),
        text = 'pct'
    )
)
projection_chart = projection_base.mark_bar() + projection_base.mark_text(align = 'right', dx = -4)

# Display the Plots
plot1, plot2 = st.columns(2)
with plot1:
    st.altair_chart(optimization_chart)
with plot2:
    st.altair_chart(projection_chart)