#%% Modules
import datetime
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st
from streamlit import session_state as ss

#%% Season-Level
scores_df = ss['data']
st.header('All Time Records')

scores_df['year'] = scores_df['year'].astype(str)

# Separate postseason & remove unplayed games
season_records = scores_df[(scores_df['outcome'] != 'U') & (scores_df['game_type'] == 'season')]
postseason_records = scores_df[(scores_df['outcome'] != 'U') & (scores_df['game_type'] == 'postseason')]

# Data Manipulation | Season
player_ppg = season_records.loc[:, ['manager', 'year', 'points_for']].groupby(['manager', 'year'], as_index = False).mean()
yearly_ppg = season_records.loc[:, ['year', 'points_for']].groupby('year', as_index = False).mean()
alltime_ppg = season_records['points_for'].mean()

# Data Manipulation | Postseason
player_p_ppg = postseason_records.loc[:, ['manager', 'year', 'points_for']].groupby(['manager', 'year'], as_index = False).mean()
yearly_p_ppg = postseason_records.loc[:, ['year', 'points_for']].groupby('year', as_index = False).mean()
alltime_p_ppg = postseason_records['points_for'].mean()

## Most Points
mp1, mp2, mp3 = st.columns(3)
with mp1:
	st.subheader('Top Weekly Scores')
	tws = season_records.sort_values('points_for', ascending = False)
	tws.reset_index(inplace = True, drop = True)
	tws = tws.loc[:19, ['manager', 'year', 'points_for']]
	tws.columns = ['Manager', 'Year', 'Points']
	st.dataframe(tws, hide_index = True,  height = len(tws) * 35 + 38)

with mp2:
	st.subheader('Top Playoff Scores (2 Weeks)')
	tps = postseason_records.sort_values('points_for', ascending = False)
	tps.reset_index(inplace = True, drop = True)
	tps = tps.loc[:19, ['manager', 'year', 'points_for']]
	tps.columns = ['Manager', 'Year', 'Points']
	st.dataframe(tps, hide_index = True,  height = len(tps) * 35 + 38)

## Highest Adjusted PPG
with mp3:
	st.subheader('Top Regular Season (Points)')
	best_ppg = pd.merge(player_ppg, yearly_ppg, how = 'left', on = 'year', suffixes = ['_b', '_y'])
	best_ppg['adj_pf'] = (best_ppg['points_for_b'] - best_ppg['points_for_y']) + alltime_ppg
	best_ppg = best_ppg.sort_values('adj_pf', ascending = False).iloc[:20, [0, 1, 2, 4]]
	best_ppg.columns = ['Manager', 'Year', 'PPG', 'Adj. PPG']
	st.dataframe(best_ppg, hide_index = True, height = len(best_ppg) * 35 + 38)

## Second Row
r1, r2, r3 = st.columns(3)
with r1:
	st.subheader('Top Playoff Scorers')
	best_p_ppg = pd.merge(player_p_ppg, yearly_p_ppg, how = 'left', on = 'year', suffixes = ['_b', '_y'])
	best_p_ppg['adj_pf'] = (best_p_ppg['points_for_b'] - best_p_ppg['points_for_y']) + alltime_p_ppg
	best_p_ppg = best_p_ppg.sort_values('adj_pf', ascending = False).iloc[:15, [0, 1, 2, 4]]
	best_p_ppg.columns = ['Manager', 'Year', 'PPG', 'Adj. PPG']
	st.dataframe(best_p_ppg, hide_index = True, height = len(best_p_ppg) * 35 + 38)

with r2:
	st.subheader('Lowest Weekly Scores (Season)')
	lws = season_records.sort_values('points_for', ascending = True)
	lws.reset_index(inplace = True, drop = True)
	lws = lws.loc[:14, ['manager', 'year', 'points_for']]
	lws.columns = ['Manager', 'Year', 'Points']
	st.dataframe(lws, hide_index = True,  height = len(lws) * 35 + 38)

with r3:
	st.subheader('Worst Regular Seasons (PPG)')
	wrs = season_records.groupby(['manager', 'year'])[['points_for']].mean().reset_index().sort_values('points_for')
	wrs.columns = ['Manager', 'Year', 'PPG']
	wrs = wrs.reset_index(drop = True).loc[:14, :]
	st.dataframe(wrs, hide_index = True, height = len(wrs) * 35 + 38)

## Third Row
t1, t2, t3 = st.columns(3)
espn_record = (season_records.groupby(['manager', 'year', 'outcome'])['points_for']
                             .count()
                             .reset_index()
                             .pivot_table(index = ['manager', 'year'],
                                          columns = 'outcome',
                                          values = 'points_for',
                                          fill_value = 0)
                             .reset_index())
if 'T' not in espn_record.columns:
    espn_record['T'] = 0
espn_record['win_pct'] = ((espn_record['W'] + 0.5 * espn_record['T']) / (espn_record['W'] + espn_record['L'] + espn_record['T']))

with t1:
	st.subheader('Best Regular Season (Win %)')
	brs = espn_record.sort_values('win_pct', ascending = False).reset_index(drop = True)
	brs = brs.loc[:10, ['manager', 'year', 'win_pct']]
	brs['win_pct'] = round(brs['win_pct'] * 100, 2)
	brs.columns = ['Manager', 'Year', 'Win %']
	st.dataframe(brs, hide_index = True, height = len(brs) * 35 + 38)

with t2:
	st.subheader('Worst Regular Season (Win %)')
	lrs = espn_record.sort_values('win_pct', ascending = True).reset_index(drop = True)
	lrs = lrs.loc[:10, ['manager', 'year', 'win_pct']]
	lrs['win_pct'] = round(lrs['win_pct'] * 100, 2)
	lrs.columns = ['Manager', 'Year', 'Win %']
	st.dataframe(lrs, hide_index = True, height = len(lrs) * 35 + 38)

with t3:
	st.subheader('Largest MoV (Season)')
	largest_mov = season_records.sort_values('mov', ascending = False).reset_index(drop = True)
	largest_mov['score'] = largest_mov['points_for'].astype(str) + '-' + largest_mov['points_against'].astype(str)
	largest_mov = largest_mov.loc[:10, ['manager', 'opponent', 'year', 'score', 'mov']]
	largest_mov.columns = ['Winner', 'Loser', 'Year', 'Score', 'MoV']
	st.dataframe(largest_mov, hide_index = True, height = len(largest_mov) * 35 + 38)


## 4th Row
f1, f2, f3 = st.columns(3)

# Manipulation to find win/loss streaks
streak_df = scores_df.sort_values(['manager', 'year', 'week']).loc[:, ['manager', 'year', 'week', 'outcome']]
streak_df['start_of_streak'] = streak_df['outcome'].ne(streak_df['outcome'].shift())
streak_df['streak_id'] = streak_df['start_of_streak'].cumsum()
streak_df['streak_counter'] = streak_df.groupby('streak_id').cumcount() + 1
streak_df['end_of_streak'] = streak_df['start_of_streak'].shift(-1, fill_value = True)


with f1:
	st.subheader('Longest Winning Streaks')
	win_streaks = streak_df[(streak_df['outcome'] == 'W') & (streak_df['end_of_streak'] == True)].sort_values('streak_counter', ascending = False)
	
	# range of streak? length of streak? unique streaks
	best_w_streak = win_streaks.iloc[:10, :]['streak_id'].to_numpy()
	best_w_streak_range = streak_df[streak_df['streak_id'].isin(best_w_streak)].groupby('streak_id')[['year']].agg(['min', 'max'])
	best_w_streak_range.columns = ['_'.join(col).strip() for col in best_w_streak_range.columns.values]
	
	# check for multi-year streaks
	best_w_streak_range['range'] = np.where(
	    best_w_streak_range['year_min'] == best_w_streak_range['year_max'],
	    best_w_streak_range['year_max'],
	    best_w_streak_range['year_min'].astype(str) + '-' + best_w_streak_range['year_max'].astype(str)
	)
	win_streaks = pd.merge(win_streaks, best_w_streak_range, how = 'left', on = 'streak_id')
	win_streaks = win_streaks.iloc[:10, [0, 10, 6]]
	win_streaks.columns = ['Manager', 'Year(s)', 'Streak']
	st.dataframe(win_streaks, hide_index = True, height = len(win_streaks) * 35 + 38)

with f2:
	st.subheader('Longest Losing Streaks')
	loss_streaks = streak_df[(streak_df['outcome'] == 'L') & (streak_df['end_of_streak'] == True)].sort_values('streak_counter', ascending = False)
	
	# range of streak? length of streak? unique streaks
	best_l_streak = loss_streaks.iloc[:10, :]['streak_id'].to_numpy()
	best_l_streak_range = streak_df[streak_df['streak_id'].isin(best_l_streak)].groupby('streak_id')[['year']].agg(['min', 'max'])
	best_l_streak_range.columns = ['_'.join(col).strip() for col in best_l_streak_range.columns.values]
	
	# check for multi-year streaks
	best_l_streak_range['range'] = np.where(
	    best_l_streak_range['year_min'] == best_l_streak_range['year_max'],
	    best_l_streak_range['year_max'],
	    best_l_streak_range['year_min'].astype(str) + '-' + best_l_streak_range['year_max'].astype(str)
	)
	loss_streaks = pd.merge(loss_streaks, best_l_streak_range, how = 'left', on = 'streak_id')
	loss_streaks = loss_streaks.iloc[:10, [0, 10, 6]]
	loss_streaks.columns = ['Manager', 'Year(s)', 'Streak']
	st.dataframe(loss_streaks, hide_index = True, height = len(loss_streaks) * 35 + 38)

with f3:
	st.subheader('Highest Scoring Game (Season)')
	season_records['matchup_points'] = season_records['points_for'] + season_records['points_against']
	hsg = season_records[season_records['outcome'] == 'W'].sort_values('matchup_points', ascending = False).reset_index(drop = True)
	hsg['score'] = hsg['points_for'].astype(str) + '-' + hsg['points_against'].astype(str)
	hsg = hsg.loc[:9, ['manager', 'opponent', 'year', 'score', 'matchup_points']]
	hsg.columns = ['Winner', 'Loser', 'Year', 'Score', 'Total']
	st.dataframe(hsg, hide_index = True, height = len(hsg) * 35 + 38)