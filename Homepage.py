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


## Manual CSVs for Team Names, 2018
st.header('Manual File Uploads:')
file1, file2 = st.columns(2)

# Team Names
with file1:
    st.write('Team ID Mapping')
    team_name_file = st.file_uploader('Headers should be ID and Name, nothing else.')
    if team_name_file is not None:
        team_name_df = pd.read_csv(team_name_file)



#%% Create Master Dataframe that will hold all data
@st.cache_data
def create_master_data():
    # get all the possible years' worth of data
    current_year = datetime.date.today().year
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
                opponent_list = pd.DataFrame({'opponent': [opp.owners[0] for opp in team_data.schedule],
                                              'outcome': team_data.outcomes,
                                              'points_for': team_data.scores,
                                              'mov': team_data.mov})
                opponent_list['manager'] = team_data.owners[0]
                opponent_list['game_type'] = 'postseason'
                opponent_list['week'] = np.arange(opponent_list.shape[0]) + 1
                scores_df.append(opponent_list)
                opponent_list.iloc[:season_weeks, 5] = 'season'
                opponent_list['year'] = league.year

                # acquisition data
                team_id = team_data.owners[0]
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
        standings = [team.owners[0] for team in league.standings()]
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
            manager = manager = draft_pick.team.owners[0]

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

    # all the concatenations
    scores_df = pd.concat(scores_df)
    scores_df['points_against'] = scores_df['points_for'] - scores_df['mov']
    standings_df = pd.concat(standings_df)
    acq_df = pd.concat(acq_df)
    draft_board_df = pd.concat(draft_board)

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

    return scores_df, standings_df, acq_df, draft_board_df

# only run the function if all the parameters are entered
if swid != '' and espn_s2 != '':
    scores_df, standings_df, acq_df, draft_board_df = create_master_data()

    # replace cached team names
    dict = team_name_df.set_index('ID').to_dict()
    standings_df['Manager'] = standings_df['Manager'].map(dict['Name'])

    scores_df['opponent'] = scores_df['opponent'].map(dict['Name'])
    scores_df['manager'] = scores_df['manager'].map(dict['Name'])

    acq_df['team_id'] = acq_df['team_id'].map(dict['Name'])

    draft_board_df['manager'] = draft_board_df['manager'].map(dict['Name'])

    # cache objects
    ss['data'] = scores_df
    ss['all_standings'] = standings_df
    ss['acqusition'] = acq_df
    ss['draft'] = draft_board_df