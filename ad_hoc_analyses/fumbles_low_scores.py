#%% Modules
import numpy as np
import pandas as pd
from espn_api.football import League


#%% League Parameters
league_id = 298982
# year = 2019
swid = '{D825016D-4C3D-4575-B33C-2C2277B026F0}'
espn_s2 = 'AEAmlIpZf7Zd7LTyvSFyl9k3zui2t4hQwlVtJM8WK3Lmx33eWNAUq32gR9NK98ZjqXWIEsK3NETxdtcctstCwGu45Mx9QOM9wIeB9KBTALOs8wg512Me2GSTnw3MCQL8bAeTp16w0xkggMxdmDGX9BX6nS2dKDx5OfjEIFLsgnntd3CW%2BmYsMnCywwMpQQZQkigiNNM54cM7OmivIq2kGkZY%2BJEhquYe%2FHnSRhBa9f052nnEmYn0fAzax8RHr3boSL9UASeMp2B8dLubfQd83Bj%2B%2BwBJPpeGyxi36lwJPtMXjg%3D%3D'


#%% Helper Functions to Find Fumbles
def return_fumbles(player):
    if player.points_breakdown == 0:
        return 0
    elif 'lostFumbles' in player.points_breakdown.keys():
        return player.points_breakdown.get('lostFumbles')
    else:
        return 0

def find_original_lineup(lineup):
    og_lineup_pos = [player.lineupSlot for player in lineup]
    og_lineup_name = [player.name for player in lineup]
    og_lineup_score = [player.points for player in lineup]

    # delete this later
    og_fumbles = [return_fumbles(player) for player in lineup]

    og_lineup_df = pd.DataFrame({
        'og_lineup_pos': og_lineup_pos,
        'og_lineup_name': og_lineup_name,
        'og_lineup_score': og_lineup_score,

        # delete this later
        'og_fumbles': og_fumbles
    })

    # and thier score
    og_score = np.sum([player.points for player in lineup if player.lineupSlot not in ['BE', 'IR']])

    return og_lineup_df, og_score


#%% Gather all box scores
all_comps = []
for year in range(2019, 2025):

    # pull league info
    league = League(league_id, year, espn_s2, swid)

    # how many weeks of data?
    num_weeks = league.current_week

    # loop through weeks for each weeks' box score
    for i in range(num_weeks):
        week_box_scores = league.box_scores(week = i + 1)

        # count the number of matchups in the week
        num_of_matchups = len(week_box_scores)

        # loop through matchups and retrieve box scores
        for j in range(num_of_matchups):
            home_team = week_box_scores[j].home_team
            home_lineup = week_box_scores[j].home_lineup

            manager = home_team.owners[0]['firstName'] + ' ' + home_team.owners[0]['lastName']
            
            og_lineup_df, og_score = find_original_lineup(home_lineup)

            manager = home_team.owners[0]['firstName'] + ' ' + home_team.owners[0]['lastName']

            # add other identifiable parameters
            og_lineup_df['year'] = year
            og_lineup_df['manager'] = manager
            og_lineup_df['week'] = i + 1

            # append the dataframes
            all_comps.append(og_lineup_df)

        for k in range(num_of_matchups):
            away_team = week_box_scores[k].away_team
            away_lineup = week_box_scores[k].away_lineup

            manager = away_team.owners[0]['firstName'] + ' ' + away_team.owners[0]['lastName']
            
            og_lineup_df, og_score = find_original_lineup(away_lineup)

            manager = away_team.owners[0]['firstName'] + ' ' + away_team.owners[0]['lastName']

            # add other identifiable parameters
            og_lineup_df['year'] = year
            og_lineup_df['manager'] = manager
            og_lineup_df['week'] = i + 1

            # append the dataframes
            all_comps.append(og_lineup_df)

all_lineup_df = pd.concat(all_comps).reset_index(drop = True)


#%% Filter for Positions then Sum
lowest_skill_pos_score = (
    all_lineup_df[all_lineup_df['og_lineup_pos'].isin(['RB', 'WR', 'RB/WR', 'TE', 'RB/WR/TE'])]
    .drop(['og_lineup_name', 'og_lineup_pos'], axis = 1)
    .groupby(['manager', 'year', 'week'])
    .sum()
    .reset_index()
    .sort_values('og_lineup_score')
)

# remove this line as weeks progress
indices_to_remove = lowest_skill_pos_score[(lowest_skill_pos_score['year'] == 2024) & (lowest_skill_pos_score['week'] == 7)]

lowest_skills = lowest_skill_pos_score[~lowest_skill_pos_score.index.isin(indices_to_remove.index)]


#%% Total Fumbles Lost
df = pd.concat(all_comps)
(
    df[df['og_lineup_pos'] != 'BE']
    .loc[:, ['manager', 'og_fumbles']]
    .groupby(['manager'], as_index = False)
    .sum()
    .sort_values('og_fumbles', ascending = False)
)
