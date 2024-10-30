#%% Modules
import datetime
import numpy as np
import pandas as pd
import streamlit as st
from espn_api.football import League
from espn_api.football import constant
from streamlit import session_state as ss

#%% Multipage and Session State Configuration
st.set_page_config(
    page_title = 'Fantasy Football Everything',
    page_icon = '🏈'
)

ss['data'] = False
ss['start_year'] = False
ss['all_standings'] = False
ss['acqusition'] = False
ss['draft'] = False
ss['comparisons_df'] = False
ss['comparisons_score'] = False


#%% Structure
st.title('All Your Fantasy Needs')
st.subheader('Enter your League Parameters:')

## User-Input Parameters
param1, param2 = st.columns(2)

# First Year to Extract all History
with param1:
    league_start = st.number_input("What was the inaugural year of your league?",
                                   step = 1,
                                   min_value = 2000)
    ss['start_year'] = league_start
# League ID
with param2:
    league_id = st.number_input("What is your league ID?", step = 1)

# Instructions for Cookies
st.header('Instructions to Locate the Necessary Cookies:')
st.markdown(
    '''
    1. Open the ESPN league page.
    2. Right click anywhere and scroll to `Inspect`.
    3. Navigate to `Network`.
    4. Refresh the page.
    5. Under `Name`, there will be a alphanumeric string that begins with your league ID. Click it.
    6. Scroll to `Request Headers` and locate the field `Cookie:`.
    7. Copy the entire string and paste it into a text editor.
    8. Ctrl+F/Cmd+F and search `swid` and `espn_s2`. These are the cookies to paste below.
    '''
)

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


#%% Additional Helper Functions
def find_optimal_lineup(week, positions, lineup):
    # empty lists to append to
    optimal_positions = []
    optimal_players = []

    # 1. outer loop: go through all the positions
    for position in positions:

        # skip the non-starters
        if position in ['BE', 'IR']:
            continue
        if positions[position] != 0:
            n_players = positions[position]
            
            # save the positions and counts
            optimal_positions.append(np.repeat(position, n_players))

            # 2. inner loop: find highest player for each position
            eligible_players = []
            for player in lineup:
                if position in player.eligibleSlots:

                    # save the player name
                    eligible_players.append(player)

            # sort players by points scored; keep roster available number
            eligible_players = sorted(eligible_players, key = lambda x: x.points, reverse = True)[:n_players]
            optimal_players.extend(eligible_players)

            # remove players already used
            for player in eligible_players:
                lineup.remove(player)

    optimal_lineup_df = pd.DataFrame({
        'optimal_positions': sum([pos.tolist() for pos in optimal_positions], []),
        'optimal_players': [player.name for player in optimal_players]
    })
    optimal_lineup_df['week'] = week

    # output the score as well
    optimal_score = np.sum(player.points for player in optimal_players)

    return optimal_lineup_df, optimal_score

def find_original_lineup(lineup):
    og_lineup_pos = [player.lineupSlot for player in lineup]
    og_lineup_name = [player.name for player in lineup]

    og_lineup_df = pd.DataFrame({
        'og_lineup_pos': og_lineup_pos,
        'og_lineup_name': og_lineup_name
    })

    # remove non-starters
    og_lineup_df = og_lineup_df[~og_lineup_df['og_lineup_pos'].isin(['BE', 'IR'])].reset_index(drop = True)

    # and thier score
    og_score = np.sum([player.points for player in lineup if player.lineupSlot not in ['BE', 'IR']])
    projected_score = np.sum([player.projected_points for player in lineup if player.lineupSlot not in ['BE', 'IR']])

    return og_lineup_df, og_score, projected_score


def combine_og_optimal(og_lineup_df, optimal_lineup_df):
    og_lineup_df['og_lineup_pos'] = og_lineup_df['og_lineup_pos'].astype('category')
    og_lineup_df['og_lineup_pos'] = og_lineup_df['og_lineup_pos'].cat.set_categories(optimal_lineup_df['optimal_positions'].unique())
    og_lineup_df = og_lineup_df.sort_values('og_lineup_pos').reset_index(drop = True)

    comp_df = pd.concat([optimal_lineup_df, og_lineup_df], axis = 1)

    return comp_df

def gather_all_optimal(league, all_comps, all_scores):
    num_weeks = league.current_week
    # no need to loop for positions
    positions = league.settings.position_slot_counts

    # loop through all the weeks we have so far
    for j in range(num_weeks - 1):

        # Access a week of box scores
        week_box_scores = league.box_scores(week = j + 1)
        
        # loop through all the home & away teams
        num_of_matchups = len(week_box_scores)

        for i in range(num_of_matchups):
            home_team = week_box_scores[i].home_team
            home_lineup = week_box_scores[i].home_lineup

            manager = home_team.owners[0]['firstName'] + ' ' + home_team.owners[0]['lastName']
            
            # make a copy to not reset values
            home_lineup2 = home_lineup.copy()

            # find optimal & original lineups & scores for the team
            optimal_lineup_df, optimal_score = find_optimal_lineup(week = j + 1,
                                                                   positions = positions,
                                                                   lineup = home_lineup2)
            og_lineup_df, og_score, projected_score = find_original_lineup(home_lineup)

            # another data frame to host scores
            oo_score_df = pd.DataFrame({
                'manager': np.repeat(manager, 3),
                'week': np.repeat(j + 1, 3),
                'score': [og_score, optimal_score - og_score, projected_score],
                'type': ['original', 'optimal', 'projected']
            })

            optimal_lineup_df['manager'] = manager

            # join the dataframes
            comp_df = combine_og_optimal(og_lineup_df, optimal_lineup_df)

            # append the dataframes
            all_comps.append(comp_df)
            all_scores.append(oo_score_df)

        for i in range(num_of_matchups):
            away_team = week_box_scores[i].away_team
            away_lineup = week_box_scores[i].away_lineup

            manager = away_team.owners[0]['firstName'] + ' ' + away_team.owners[0]['lastName']
            
            # make a copy to not reset values
            away_lineup2 = away_lineup.copy()

            # find optimal & original lineups & scores for the team
            optimal_lineup_df, optimal_score = find_optimal_lineup(week = j + 1,
                                                                   positions = positions,
                                                                   lineup = away_lineup2)
            og_lineup_df, og_score, projected_score = find_original_lineup(away_lineup)

            # another data frame to host scores
            oo_score_df = pd.DataFrame({
                'manager': np.repeat(manager, 3),
                'week': np.repeat(j + 1, 3),
                'score': [og_score, optimal_score - og_score, projected_score],
                'type': ['original', 'optimal', 'projected']
            })

            optimal_lineup_df['manager'] = manager

            # join the dataframes
            comp_df = combine_og_optimal(og_lineup_df, optimal_lineup_df)

            # append the dataframes
            all_comps.append(comp_df)
            all_scores.append(oo_score_df)

    all_comps_df = pd.concat(all_comps).reset_index(drop = True)
    all_scores_df = pd.concat(all_scores).reset_index(drop = True)

    return all_comps_df, all_scores_df


#%% Create Master Dataframe that will hold all data
@st.cache_data
def create_master_data():
    # get all the possible years' worth of data
    # current_year = datetime.date.today().year
    current_year = 2024
    all_years = np.arange(league_start, current_year + 1)

    # remove 2018 as its a problem (TO FIX)
    index_2018 = np.where(all_years == 2018)
    if index_2018[0].shape[0] == 1:
        all_years = np.delete(all_years, index_2018)

    # get data for all the years in raw format
    leagues = []
    for year in all_years:
        league = League(league_id, year, espn_s2, swid)
        leagues.append(league)

    # loop through each league and grab game-level data
    scores_df = []

    # use the loop to grab the final standings too
    standings_df = []

    # use the loop to grab the acquisition counts too
    acq_df = []

    # use the loop to grab the draft results
    draft_board = []

    # use the loop to grab player data
    player_lookup = []

    # use the loop to grab optimal comparison data
    all_comps = []
    all_scores = []

    # outer loop to loop through all the leagues/years
    for league in leagues:
        season_weeks = league.settings.reg_season_count
        teams = league.teams
        team_ids = [team.team_id for team in teams]

        # metrics for the draft board
        num_picks = len(league.draft)

        # inner loop to loop through the teams in each year
        for id in team_ids:
            team_data = league.get_team_data(id)

            # some managers' data has been purged
            if team_data is None:
                continue
            else:
                opponent_list = pd.DataFrame({'opponent': [opp.owners[0]['firstName'] + ' ' + opp.owners[0]['lastName'] for opp in team_data.schedule],
                                              'outcome': team_data.outcomes,
                                              'points_for': team_data.scores,
                                              'mov': team_data.mov})
                opponent_list['manager'] = team_data.owners[0]['firstName'] + ' ' + team_data.owners[0]['lastName']
                opponent_list['game_type'] = 'postseason'
                opponent_list['week'] = np.arange(opponent_list.shape[0]) + 1
                scores_df.append(opponent_list)
                opponent_list.iloc[:season_weeks, 5] = 'season'
                opponent_list['year'] = league.year

                # acquisition data
                team_id = team_data.owners[0]['firstName'] + ' ' + team_data.owners[0]['lastName']
                pickups = team_data.acquisitions
                trades = team_data.trades
                faab_used = team_data.acquisition_budget_spent
                acq_list = pd.DataFrame({'team_id': [team_id],
                                         'pickups': [pickups],
                                         'trades': [trades],
                                         'faab_used': [faab_used],
                                         'year': [league.year]})
                acq_df.append(acq_list)

        # accumulate the standings from each year
        standings = [team.owners[0]['firstName'] + ' ' + team.owners[0]['lastName'] for team in league.standings()]
        standings_num = np.arange(len(standings)) + 1
        df_standings = pd.DataFrame({'Manager': standings, 'Result': standings_num})
        df_standings['Year'] = league.year
        standings_df.append(df_standings)

        # collect draft values here
        for i in range(num_picks):
            draft_pick = league.draft[i]
            round = draft_pick.round_num
            pick = draft_pick.round_pick
            player = draft_pick.playerName
            manager = manager = draft_pick.team.owners[0]['firstName'] + ' ' + draft_pick.team.owners[0]['lastName']

            # combine all into an appendable data frame
            pick_df = pd.DataFrame({'round': [round],
                                    'pick': [pick],
                                    'player': [player],
                                    'manager': [manager],
                                    'year': [league.year]})

            draft_board.append(pick_df)

        # collect player data here
        dat = league.espn_request.get_pro_players()
        for player_info in dat:
            if 'eligibleSlots' not in player_info.keys():
                continue
            # position_id = player_info['eligibleSlots'][0]

            # filter for only first eligible player spot that isnt a combo
            for pos in player_info['eligibleSlots']:
                if (pos != 25 and '/' not in constant.POSITION_MAP[pos]) or '/' in player_info['fullName']:
                    position = constant.POSITION_MAP[pos]
                    break

            # remainder of player data
            player = player_info['fullName']
            pi = pd.DataFrame({'position': [position],
                               'player': [player],
                               'year': [league.year]})
            player_lookup.append(pi)

        if league.year == current_year:
            all_comps_df, all_scores_df = gather_all_optimal(league, all_comps, all_scores)

    # all the concatenations
    scores_df = pd.concat(scores_df)
    scores_df['manager'] = scores_df['manager'].str.title()
    scores_df['opponent'] = scores_df['opponent'].str.title()
    scores_df['points_against'] = scores_df['points_for'] - scores_df['mov']

    standings_df = pd.concat(standings_df)
    standings_df['Manager'] = standings_df['Manager'].str.title()

    acq_df = pd.concat(acq_df)
    acq_df['team_id'] = acq_df['team_id'].str.title()

    draft_board_df = pd.concat(draft_board)
    draft_board_df['manager'] = draft_board_df['manager'].str.title()

    all_scores_df['manager'] = all_scores_df['manager'].str.title()
    all_comps_df['manager'] = all_comps_df['manager'].str.title()

    # concatenate and remove duplicates (defense, etc.)
    player_lookup_df = pd.concat(player_lookup)
    player_lookup_df['row_num'] = player_lookup_df.groupby(['player', 'year'], as_index = False).cumcount() + 1
    player_lookup_df = player_lookup_df[player_lookup_df['row_num'] == 1]

    # add draft position to the draft
    draft_board_df['player_pos'] = draft_board_df['player'] + ' (' + draft_board_df['round'].astype(str) + '.' + draft_board_df['pick'].astype(str) + ')'

    # add playing position to the draft
    draft_board_df = pd.merge(draft_board_df,
                              player_lookup_df,
                              how = 'left',
                              on = ['player', 'year'])

    st.success('Data Imported.')

    return scores_df, standings_df, acq_df, draft_board_df, all_comps_df, all_scores_df

# only run the function if all the parameters are entered
if swid != '' and espn_s2 != '':
    scores_df, standings_df, acq_df, draft_board_df, all_comps_df, all_scores_df = create_master_data()

    # cache objects
    ss['data'] = scores_df
    ss['all_standings'] = standings_df
    ss['acqusition'] = acq_df
    ss['draft'] = draft_board_df
    ss['comparisons_df'] = all_comps_df
    ss['comparisons_score'] = all_scores_df
