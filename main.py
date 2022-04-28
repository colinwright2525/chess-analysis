import requests
import berserk
import pandas as pd
import math
import numpy as np
import chess.pgn
import datetime as dt
import plotly.express as px
import itertools
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, PasswordField
from wtforms.validators import DataRequired
from PIL import Image

# image = Image.open('static/images/chess-sleek.jpg')
# new_image = image.resize((500, 300))
# new_image.save('static/images/chess-sleek.jpg')

#------web host-------#
app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap(app)

#-----tokens for lichess api------#
# API_TOKEN = 'lip_Ehpyx6vhwwDplHLeZPpd'
# user = 'cow22'

class Game:
    def __init__(self, color, result, moves, first_three):
        self.color = color
        self.result = result
        self.moves = moves
        self.first_three = first_three

class Opening:
    def __init__(self, name, moves, percent, won, lost):
        self.name = name
        self.moves = moves
        self.percent = percent
        self.won = won
        self.lost = lost

class ChessForm(FlaskForm):
    user_name = StringField("What is your username?", validators=[DataRequired()])
    days_back = IntegerField("How many days back would you like data for?", validators=[DataRequired()])
    token = PasswordField('What is your secret lichess API token?', validators=[DataRequired()])
    submit = SubmitField("Show Data")

def get_time_params(days_back):
    today = dt.date.today()
    days_back = int(days_back)
    back = days_back
    day_back = today - dt.timedelta(days=back)

    today_y = int(today.strftime("%Y"))
    today_m = int(today.strftime("%m"))
    today_d = int(today.strftime("%d"))

    day_back_y = int(day_back.strftime("%Y"))
    day_back_m = int(day_back.strftime("%m"))
    day_back_d = int(day_back.strftime("%d"))

    start = berserk.utils.to_millis(dt.datetime(day_back_y, day_back_m, day_back_d))
    end = berserk.utils.to_millis(dt.datetime(today_y, today_m, today_d))
    time_params = [start, end]
    return time_params

#-----gets user games from lichess-----#
def get_player_games(client, user_name, start, end):
    # user_info = client.account.get()
    games = client.games.export_by_player(user_name, since=int(start), until=int(end))
    games_list = [elem for elem in list(games)]

    colors = []
    for game in games_list:
        if game['players']['white']['user']['name'] == user_name:
            color = 'white'
            colors.append(color)
        else:
            color = 'black'
            colors.append(color)

    results = []
    for i in range(len(games_list)):
        try:
            if games_list[i]['winner'] == 'white' and colors[i] == 'white':
                result = 'won'
                results.append(result)
            elif games_list[i]['winner'] == 'white' and colors[i] == 'black':
                result = 'lost'
                results.append(result)
            elif games_list[i]['winner'] == 'black' and colors[i] == 'black':
                result = 'won'
                results.append(result)
            else:
                result = 'lost'
                results.append(result)
        except:
            result = 'No winner'
            results.append(result)


    moves_list = [game['moves'] for game in games_list]
    first_three_moves_list = [move.split()[:6] for move in moves_list]
    first_three_moves = [' '.join(moves) for moves in first_three_moves_list]
    first_two_moves_list = [move.split()[:4] for move in moves_list]
    first_two_moves = [' '.join(moves) for moves in first_two_moves_list]


    my_games = []
    for i in range(len(games_list)):
        if results[i] != None:
            new_game = Game(colors[i], results[i], moves_list[i], first_three_moves[i])
            my_games.append(new_game)

    #-----creates dataframe for user games-----#
    data = pd.DataFrame({'User color': colors, 'User result': results, 'First three moves': first_three_moves, 'First two moves': first_two_moves, 'All moves': moves_list})
    data_clean = data[data['User result'] != 'No winner']

    move_names = []

    for move in data_clean['First two moves']:
        moves_index = (openings_data[openings_data['Opening moves'] == move].index.astype(int))
        try:
            index_value = (moves_index.item())
        except:
            index_value = 'Empty'
        if index_value != 'Empty':
            move_name = openings_data.loc[index_value].at['Opening name']
            move_name = move_name.strip()
            move_names.append(move_name)
        else:
            move_name = 'No opening found'
            move_names.append(move_name)


    reserve_move_names = []

    for move in data_clean['First three moves']:
        moves_index = (openings_data[openings_data['Opening moves'] == move].index.astype(int))
        try:
            index_value = (moves_index.item())
        except:
            index_value = 'Empty'
        if index_value != 'Empty':
            move_name = openings_data.loc[index_value].at['Opening name']
            move_name = move_name.strip()
            reserve_move_names.append(move_name)
        else:
            move_name = 'No opening found'
            reserve_move_names.append(move_name)

    for i in range(len(move_names)):
        if move_names[i] == 'No opening found' and reserve_move_names[i] !='No opening found':
            move_names[i] = reserve_move_names[i]

    print(move_names)
    data_clean['Opening Names'] = move_names

    games_played_openings = data_clean['First three moves'].value_counts()
    games_played_openings = pd.DataFrame({'First three moves': games_played_openings.index, 'Total Games Played': games_played_openings.values})


    data_clean = pd.merge(data_clean, games_played_openings, on='First three moves')


    data_white = data_clean[data_clean['User color'] == 'white']
    data_black = data_clean[data_clean['User color'] == 'black']

    opening_results_white = data_white.groupby(['First three moves', 'User result', 'Opening Names', 'Total Games Played'], as_index=False).agg({'All moves': pd.Series.count})
    opening_results_white_wins = opening_results_white[opening_results_white['User result'] == 'won']
    opening_results_white_wins['Losses'] = opening_results_white_wins['Total Games Played'] - opening_results_white_wins['All moves']
    opening_results_white_wins['Percent Won'] = round(((opening_results_white_wins['All moves'] / opening_results_white_wins['Total Games Played']) * 100), 2)
    opening_results_white_wins = opening_results_white_wins.sort_values(by='Percent Won', ascending=False)
    opening_results_white_losses = opening_results_white[opening_results_white['User result'] == 'lost']
    opening_results_white_losses['Wins'] = opening_results_white_losses['Total Games Played'] - opening_results_white_losses['All moves']
    opening_results_white_losses['Percent Won'] = round(((opening_results_white_losses['Wins'] / opening_results_white_losses['Total Games Played']) * 100), 2)
    opening_results_white_losses = opening_results_white_losses.sort_values(by='Percent Won', ascending=True)

    opening_results_black = data_black.groupby(['First three moves', 'User result', 'Opening Names', 'Total Games Played'], as_index=False).agg({'All moves': pd.Series.count})
    opening_results_black_wins = opening_results_black[opening_results_black['User result'] == 'won']
    opening_results_black_wins['Losses'] = opening_results_black_wins['Total Games Played'] - opening_results_black_wins['All moves']
    opening_results_black_wins['Percent Won'] = round(((opening_results_black_wins['All moves'] / opening_results_black_wins['Total Games Played']) * 100), 2)
    opening_results_black_wins = opening_results_black_wins.sort_values(by='Percent Won', ascending=False)
    opening_results_black_losses = opening_results_black[opening_results_black['User result'] == 'lost']
    opening_results_black_losses['Wins'] = opening_results_black_losses['Total Games Played'] - opening_results_black_losses['All moves']
    opening_results_black_losses['Percent Won'] = round(((opening_results_black_losses['Wins'] / opening_results_black_losses['Total Games Played']) * 100), 2)
    opening_results_black_losses = opening_results_black_losses.sort_values(by='Percent Won', ascending=True)

    #-------organizes data into readable charts for webpage-------#
    fig_white = px.bar(opening_results_white, x='First three moves', y='Total Games Played', color='User result', barmode='group', title='Results by Most Played Openings as White')
    fig_white.update_layout(xaxis_title='Opening', yaxis_title='Result count')
    fig_black = px.bar(opening_results_black, x='First three moves', y='Total Games Played', color='User result', barmode='group', title='Results by Most Played Openings as Black')
    fig_black.update_layout(xaxis_title='Opening', yaxis_title='Result count')

    all_data = [opening_results_white_wins, opening_results_white_losses, opening_results_black_wins, opening_results_black_losses, fig_white, fig_black]

    return all_data

# fig_white.show()
# fig_black.show()

#-------organize data into a presentable format for the webpage--------#
def compile_data(all_data):
    opening_results_white_wins = all_data[0]
    opening_results_white_losses = all_data[1]
    opening_results_black_wins = all_data[2]
    opening_results_black_losses = all_data[3]

    opening_results_white_wins_counted = (opening_results_white_wins[opening_results_white_wins['Total Games Played'] >= 5])[:5]
    print(opening_results_white_wins_counted)
    opening_results_white_losses_counted = (opening_results_white_losses[opening_results_white_losses['Total Games Played'] >= 5])[:5]
    opening_results_black_wins_counted = (opening_results_black_wins[opening_results_black_wins['Total Games Played'] >= 5])[:5]
    opening_results_black_losses_counted = (opening_results_black_losses[opening_results_black_losses['Total Games Played'] >= 5])[:5]

    website_data = [opening_results_white_wins_counted, opening_results_white_losses_counted, opening_results_black_wins_counted, opening_results_black_losses_counted]
    return website_data


#------reads in actual opening names from text file-----#
opening_names = []
opening_moves = []
with open('openings.txt') as file:
    for line in file:
        line_list = line.split('1.')
        opening_name = line_list[0]
        opening_name = [char for char in opening_name]
        opening_name = opening_name[4:]
        opening_name = ''.join(opening_name)
        opening_names.append(opening_name)
        try:
            opening_move = line_list[1]
            if '3.' not in opening_move:
                opening_move_one = opening_move.split('2.')
                opening_move_two = opening_move_one[1]
                opening_sequence = [opening_move_one[0], opening_move_two]
                opening_move = ''.join(opening_sequence)
                opening_move.strip()
                opening_move = (' ' * 1).join(opening_move.split())
                opening_moves.append(opening_move)
            elif '4.' not in opening_move:
                opening_move_one = opening_move.split('2.')
                opening_move_two = opening_move_one[1].split('3.')
                opening_move_three = opening_move_two[1]
                opening_sequence = [opening_move_one[0], opening_move_two[0], opening_move_three]
                opening_move = ''.join(opening_sequence)
                opening_move.strip()
                opening_move = (' ' * 1).join(opening_move.split())
                opening_moves.append(opening_move)

            else:
                opening_move = "No moves"
                opening_moves.append(opening_move)
        except:
            opening_move = "No moves"
            opening_moves.append(opening_move)

print(opening_moves)

#------defines all openings into a dataframe for use-----#
openings_data = pd.DataFrame({'Opening name': opening_names, 'Opening moves': opening_moves})

@app.route('/', methods=['GET', 'POST'])
def home():
    form = ChessForm()
    if request.method == 'POST':
        days_back = request.form.get('days_back')
        user_name = request.form.get('user_name')
        API_TOKEN = request.form.get('token')

        session = berserk.TokenSession(API_TOKEN)
        client = berserk.Client(session=session)

        time_params = get_time_params(days_back)
        start = time_params[0]
        end = time_params[1]

        all_data = get_player_games(client, user_name, start, end)

        white_graph = all_data[4]
        black_graph = all_data[5]

        website_data = compile_data(all_data)

        white_wins = website_data[0]
        white_losses = website_data[1]
        black_wins = website_data[2]
        black_losses = website_data[3]

        white_w_openings = []
        white_l_openings = []
        black_w_openings = []
        black_l_openings = []

        for index, row in white_wins.iterrows():
            white_w = Opening(row['Opening Names'], row['First three moves'], row['Percent Won'], row['All moves'], row['Losses'])
            white_w_openings.append(white_w)

        for index, row in white_losses.iterrows():
            white_l = Opening(row['Opening Names'], row['First three moves'], row['Percent Won'], row['Wins'], row['All moves'])
            white_l_openings.append(white_l)

        for index, row in black_wins.iterrows():
            black_w = Opening(row['Opening Names'], row['First three moves'], row['Percent Won'], row['All moves'], row['Losses'])
            black_w_openings.append(black_w)

        for index, row in black_losses.iterrows():
            black_l = Opening(row['Opening Names'], row['First three moves'], row['Percent Won'], row['Wins'], row['All moves'])
            black_l_openings.append(black_l)



        return render_template('index.html', form=form, white_w=white_w_openings, white_l=white_l_openings, black_w=black_w_openings, black_l=black_l_openings)

    return render_template('index.html', form=form)


if __name__ == "__main__":
    app.run(debug=True)