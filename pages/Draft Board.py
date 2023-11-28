#%% Modules
import datetime
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st
from streamlit import session_state as ss

# All Time
st.header('Draft Board')

# Bring in the data
draft_board_df = ss['draft']
league_start = ss['start_year']
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


#%% Data Processing
draft_board_year = draft_board_df[draft_board_df['year'] == season_of_interest]
draft_order = draft_board_year[draft_board_year['round'] == 1]['manager'].to_list()
num_teams = len(draft_order)
num_rounds = draft_board_year['round'].max()

# What is the longest string?
# This allows for appropriate scaling of draft board
max_characters = pd.concat([draft_board_year['manager'].str.len(),
                            draft_board_year['player_pos'].str.len()]).max()

# color selection
color_range = ['#488f31', '#f1878e', '#955196', '#5886a5', '#ff6e54', '#ffa600']
# color_range = ['green', 'blue', 'yellow', 'red', 'purple', 'brown']
color_domain = ['RB', 'WR', 'TE', 'QB', 'K', 'D/ST']

base = alt.Chart(
    draft_board_year,
    title = 'Draft Board'
).encode(
    x = alt.X(
        'manager:N',
        sort = draft_order,
        title = 'Manager',
        axis = alt.Axis(labelAngle = 0,
                        orient = 'top')
    ),
    y = alt.Y(
        'round:O',
        scale = alt.Scale(reverse = False),
        title = 'Round'
    )
).properties(
    height = num_rounds * 50,
    width = max_characters * num_teams * 6
)
heatmap = base.mark_rect().encode(
    alt.Color(
        'position:N',
        legend = None
    ).scale(domain = color_domain, range = color_range)
).interactive()
text = base.mark_text(
).encode(
    alt.Text(
        'player_pos:N'
    )
)

draft_chart = alt.layer(heatmap, text)
st.altair_chart(draft_chart, theme = None)
# st.altair_chart(draft_chart, use_container_width = True)

