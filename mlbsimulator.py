#! python3
# mlb_simulator.py

import csv
import logging
import os
import pprint
import random
import shutil
import sys
import time
import threading
import tkinter

import bs4
import requests

import fgexporter

logging.basicConfig(level=logging.DEBUG, format=' %(asctime)s - %(levelname)s - %(message)s')
BATTING = {
    'C': {'Position': 'C', 'Stats': 'Batting'},
    '1B': {'Position': '1B', 'Stats': 'Batting'},
    '2B': {'Position': '2B', 'Stats': 'Batting'},
    'SS': {'Position': 'SS', 'Stats': 'Batting'},
    '3B': {'Position': '3B', 'Stats': 'Batting'},
    'LF': {'Position': 'LF', 'Stats': 'Batting'},
    'CF': {'Position': 'CF', 'Stats': 'Batting'},
    'RF': {'Position': 'RF', 'Stats': 'Batting'},
    'DH': {'Position': 'DH', 'Stats': 'Batting'}}
PITCHING = {
    'SP': {'Position': 'Starters', 'Stats': 'Pitching'},
    'RP': {'Position': 'Relievers', 'Stats': 'Pitching'}}

TEAM_COLORS = (
    ("#ba0021", "#ffffff"), ("#eb6e1f", "#002d62"),
    ("#efb21e", "#003831"), ("#134a8e", "#1d2d5c"),
    ("#ce1141", "#13274f"), ("#12284b", "#ffc52f"),
    ("#0c2340", "#c41e3a"), ("#cc3433", "#0e3386"),
    ("#e3d4ad", "#a71930"), ("#005a9c", "#ffffff"),

    ("#27251f", "#fd5a1e"), ("#e31937", "#0c2340"),
    ("#005c5c", "#0c2c56"), ("#41748d", "#00a3e0"),
    ("#ff5910", "#002d72"), ("#14225a", "#ab0003"),
    ("#000000", "#df4601"), ("#ffc425", "#2f241d"),
    ("#002d72", "#e81828"), ("#fd8827", "#27251f"),

    ("#c0111f", "#003278"), ("#8fbce6", "#092c5c"),
    ("#0c2340", "#bd3039"), ("#000000", "#c6011f"),
    ("#c4c3d4", "#33006f"), ("#bd9b60", "#004687"),
    ("#fa4616", "#0c2340"), ("#d31145", "#002b5c"),
    ("#c4c3d4", "#27251f"), ("#ffffff", "#0c2340"))

class ConfigureSimulationGUI:
    def __init__(self, teams):
        self.teams = teams
        self.root = tkinter.Tk()
        self.root.title('MLB Simulation - CONFIGURE SETTINGS')
        self.update_threads = {}
        self.leaderboards = fgexporter.Leaderboards()

        #Option to update FanGraphs data
        self.update_batting = dict(zip(
            list(BATTING),
            [tkinter.Button(
                self.root, text=position, width=20,
                command=lambda pos=position:self.update_file(pos))\
             for position in list(BATTING)]))
        self.update_pitching = dict(zip(
            list(PITCHING),
            [tkinter.Button(
                self.root, text=position, width=20,
                command=lambda pos=position:self.update_file(pos))\
            for position in list(PITCHING)]))
        self.disabled = []

        #Select Away Team
        self.away_variable = tkinter.StringVar(self.root)
        self.away_variable.set('--Select--')
        self.away_team_dropdown = tkinter.OptionMenu(
            self.root, self.away_variable, *self.teams,
            command=lambda _:self.color())

        #Select Home Team
        self.home_variable = tkinter.StringVar(self.root)
        self.home_variable.set('--Select--')
        self.home_team_dropdown = tkinter.OptionMenu(
            self.root, self.home_variable, *self.teams,
            command=lambda _:self.color())

        #Randomize teams
        self.random_away = tkinter.Button(
            self.root, text='Random',
            command=lambda:self.random_teams(away=True))
        self.random_home = tkinter.Button(
            self.root, text='Random',
            command=lambda:self.random_teams(home=True))
        self.random_matchup = tkinter.Button(
            self.root, text='Random Matchup',
            command=lambda:self.random_teams(away=True, home=True))

        #Set mode
        self.mode_variables = {
            '3-Game Series': tkinter.BooleanVar(self.root),
            '5-Game Series': tkinter.BooleanVar(self.root),
            '7-Game Series': tkinter.BooleanVar(self.root)}
        for mode in self.mode_variables:
            self.mode_variables[mode].trace("w", self.checkbox_callback)

        #Confirm selections
        self.confirm_button = tkinter.Button(
            self.root, text='Confirm', command=self.return_teams, width=10)
        self.notice = tkinter.Label(self.root, text='Select Teams')

        #Exit window
        self.continue_button = tkinter.Button(
            self.root, text='Continue', command=self.root.destroy, width=10)

    def display(self):
        ''' Grid all widgets to Tkinter window
'''
        tkinter.Label(self.root, text='Update:').grid(row=0, column=0)
        tkinter.Label(self.root, text='Batting:').grid(row=1, column=0)
        for i, pos in enumerate(list(self.update_batting)):
            row, col = i//3+2, i%3+1
            self.update_batting[pos].grid(row=row, column=col)
        tkinter.Label(self.root, text='Pitching:').grid(row=4, column=0)
        for i, pos in enumerate(list(self.update_pitching)):
            row, col = i//3+6, i%3+1
            self.update_pitching[pos].grid(row=row, column=col)

        for i in range(6):
            tkinter.Label(self.root, text='='*20).grid(row=7, column=i)

        tkinter.Label(self.root, text='Select:').grid(row=8, column=0)
        tkinter.Label(self.root, text="Away Team:").grid(row=9, column=0)
        tkinter.Label(self.root, text="Home Team:").grid(row=11, column=0)
    
        self.away_team_dropdown.grid(row=9, column=1)
        tkinter.Label(self.root, text='@').grid(row=10, column=1)
        self.home_team_dropdown.grid(row=11, column=1)

        self.random_away.grid(row=9, column=2)
        self.random_matchup.grid(row=10, column=2)
        self.random_home.grid(row=11, column=2)

        tkinter.Label(self.root, text='Series:').grid(row=8, column=3)
        for i, mode in enumerate(self.mode_variables):
            tkinter.Checkbutton(
                self.root, text=mode, variable=self.mode_variables[mode]).grid(
                    row=9+i, column=3)

        for i in range(6):
            tkinter.Label(self.root, text='='*20).grid(row=12, column=i)
            
        self.confirm_button.grid(row=13, column=0)
        self.notice.grid(row=13, column=1)

        self.root.mainloop()

    def checkbox_callback(self, name, indx, mode):
        for var in self.mode_variables:
            if self.mode_variables[var] == name:
                setting = self.mode_variables[var].get()
        logging.debug(setting)
        for serie in self.mode_variables:
            if self.mode_variables[serie] != name:
                self.mode_variables[serie].set(not setting)

    def color(self):
        ''' Set dropdown background to team colors
'''
        if self.away_variable.get() != '--Select--':
            team_colors = TEAM_COLORS[
                self.teams.index(self.away_variable.get())]
            self.away_team_dropdown["menu"].config(
                fg=team_colors[0], bg=team_colors[1])
        if self.home_variable.get() != '--Select--':
            team_colors = TEAM_COLORS[
                self.teams.index(self.home_variable.get())]
            self.home_team_dropdown["menu"].config(
                fg=team_colors[0], bg=team_colors[1])
        self.notice.config(text='', fg="black")
        self.continue_button.grid_forget()

    def update_file(self, pos):
        if pos in BATTING:
            configs = BATTING.get(pos)
        elif pos in PITCHING:
            configs = PITCHING.get(pos)
        thread = threading.Thread(target=self.export, args=(pos, configs,))
        self.update_threads.setdefault(pos, thread)
        thread.start()

    def export(self, pos, configs):
        self.disabled.append(pos)
        for p in self.update_batting:
            self.update_batting[p].config(state='disabled')
        for p in self.update_pitching:
            self.update_pitching[p].config(state='disabled')
        self.leaderboards.config(
            Stats=configs['Stats'], Position=configs['Position'],
            Min=0, Type='Standard')
        self.leaderboards.name = f'{pos}.csv'
        self.leaderboards.webdriver.export()
        while True:
            if os.path.exists(os.path.join(os.getcwd(), f'{pos}.csv')):
                status = tkinter.Label(
                    self.root, text=f"'{pos}.csv' Done", fg='green')
                status.grid(row=0, column=1)
                break
        for p in self.update_batting:
            if p in self.disabled:
                continue
            self.update_batting[p].config(state='normal')
        for p in self.update_pitching:
            if p in self.disabled:
                continue
            self.update_pitching[p].config(state='normal')

    def random_teams(self, *, away=False, home=False):
        if away:
            team = random.choice(self.teams)
            self.away_variable.set(team)
            self.color()
        if home:
            team = random.choice(self.teams)
            self.home_variable.set(team)
            self.color()

    def return_teams(self):
        #Assert that all position CSV files are available
        for pos in list(BATTING)+list(PITCHING):
            if not os.path.exists(os.path.join(os.getcwd(), f'{pos}.csv')):
                self.notice.config(text=f'Missing File: {pos}.csv', fg="red")
                return
        #Assert that not file updates are in progress
        if any([t.is_alive() for t in self.update_threads.values()]):
            self.notice.config(text='Incomplete Updates', fg="red")
            return
        #Assert that selected teams are not defaults
        if self.away_variable.get() == '--Select--'\
           or self.home_variable.get() == '--Select--':
            self.notice.config(text='Invalid Entry', fg="red")
            return
        #Assert that selected teams are unique
        if self.away_variable.get() == self.home_variable.get():
            self.notice.config(text='Invalid Entry', fg="red")
            return
        #Set teams
        self.away_team = self.away_variable.get()
        self.home_team = self.home_variable.get()
        #Lock file update options
        threading.Thread(target=self.leaderboards.webdriver.quit).start()
        for button in self.update_batting.values():
            button.config(state='disabled')
        for button in self.update_pitching.values():
            button.config(state='disabled')
        #Notify user of success, allow user to proceed
        self.notice.config(text='Submitted', fg="green")
        self.continue_button.grid(row=13, column=0)

class Teams:
    def __init__(self):
        self.teams = [
            'Angels', 'Astros', 'Athletics', 'Blue Jays', 'Braves', 'Brewers',
            'Cardinals', 'Cubs', 'Diamondbacks', 'Dodgers', 'Giants',
            'Indians', 'Mariners', 'Marlins', 'Mets', 'Nationals', 'Orioles',
            'Padres', 'Phillies', 'Pirates', 'Rangers', 'Rays', 'Red Sox',
            'Reds', 'Rockies', 'Royals', 'Tigers', 'Twins', 'White Sox',
            'Yankees'
            ]
        self.away_team = ''
        self.home_team = ''
        self.away_roster = {}
        self.home_roster = {}
        self.away_depth_chart = {}
        self.home_depth_chart = {}

    def compile_rosters(self):
        for position in list(BATTING)+list(PITCHING):
            self.away_depth_chart.setdefault(position, {})
            self.home_depth_chart.setdefault(position, {})
            with open(f'{position}.csv', encoding='utf-8-sig') as csvfile:
                data = list(csv.reader(csvfile))
            headers = data.pop(0)
            for row in data:
                if row[1] not in (self.away_team, self.home_team):
                    continue
                for i, item in enumerate(row):
                    try:
                        row[i] = float(item)
                    except ValueError:
                        if item.endswith('%'):
                            row[i] = round(float(item.strip('%'))/100, 3)
                player_data = dict(zip(headers, row))
                name, team = row[0], row[1]
                if team == self.away_team:
                    self.away_depth_chart[position].setdefault(
                        name, player_data)
                    self.away_roster.setdefault(name, player_data)
                elif team == self.home_team:
                    self.home_depth_chart[position].setdefault(
                        name, player_data)
                    self.home_roster.setdefault(name, player_data)

class ConfigureLineupsGUI:
    def __init__(self, teams, away_team, home_team, away_roster, home_roster,
                 away_depth_chart, home_depth_chart):
        self.teams = teams
        self.away_team, self.home_team = away_team, home_team
        self.away_roster, self.home_roster = away_roster, home_roster
        self.away_depth_chart = away_depth_chart
        self.home_depth_chart = home_depth_chart
        self.away_colors = TEAM_COLORS[self.teams.index(self.away_team)]
        self.home_colors = TEAM_COLORS[self.teams.index(self.home_team)]

        self.root = tkinter.Tk()
        self.root.title('MLB Simulation - Configure Simulation')

        self.less_reps = tkinter.Button(
            self.root, text='-', command=lambda:self.adjust_reps('-'))
        self.reps = {}
        self.reps.setdefault(
            'Variable', tkinter.StringVar(self.root, value='1'))
        self.reps.setdefault(
            'Entry', tkinter.Entry(self.root))
        self.reps['Entry']['textvariable'] = self.reps['Variable']
        self.more_reps = tkinter.Button(
            self.root, text='+', command=lambda:self.adjust_reps('+'))

        self.rand_away_lineup = tkinter.Button(
            self.root, text='Random',
            command=lambda:self.random_lineup(away=True))
        self.rand_home_lineup = tkinter.Button(
            self.root, text='Random',
            command=lambda:self.random_lineup(home=True))
        self.rand_away_sp = tkinter.Button(
            self.root, text='Random',
            command=lambda:self.random_sp(away=True))
        self.rand_home_sp = tkinter.Button(
            self.root, text='Random',
            command=lambda:self.random_sp(home=True))

        self.lineup_card_menu(away=True)
        self.lineup_card_menu(home=True)

        self.away_pitchers = {}
        self.away_pitchers.setdefault(
            'Variable', tkinter.StringVar(self.root, value='--Select--'))
        self.away_pitchers.setdefault(
            'OptionMenu', tkinter.OptionMenu(
                self.root, self.away_pitchers['Variable'],
                *list(self.away_depth_chart['SP'])))
        self.away_pitchers['OptionMenu'].config(width=20)
        self.home_pitchers = {}
        self.home_pitchers.setdefault(
            'Variable', tkinter.StringVar(self.root, value='--Select--'))
        self.home_pitchers.setdefault(
            'OptionMenu', tkinter.OptionMenu(
                self.root, self.home_pitchers['Variable'],
                *list(self.home_depth_chart['SP'])))
        self.home_pitchers['OptionMenu'].config(width=20)

        self.confirm_button = tkinter.Button(
            self.root, text='Confirm', command=self.confirm)
        self.notice = tkinter.Label(self.root, text='Invalid', fg="red")
        self.continue_button = tkinter.Button(
            self.root, text='Continue', command=self.root.destroy)

    def display(self):
        tkinter.Label(self.root, text=self.away_team,
                      fg=self.away_colors[0], bg=self.away_colors[1]).grid(
                          row=0, column=0)
        tkinter.Label(self.root, text='@'.center(5)).grid(row=0, column=4)
        tkinter.Label(self.root, text=self.home_team,
                      fg=self.home_colors[0], bg=self.home_colors[1]).grid(
                          row=0, column=5)
        tkinter.Label(self.root, text='Repititions:').grid(row=0, column=10)
        self.less_reps.grid(row=0, column=11)
        self.reps['Entry'].grid(row=0, column=12)
        self.more_reps.grid(row=0, column=13)

        tkinter.Label(self.root, text='Lineup').grid(row=1, column=0)
        tkinter.Label(self.root, text='Set Order', anchor='w').grid(
            row=1, column=1)
        tkinter.Label(self.root, text='Set Starters', anchor='w').grid(
            row=1, column=2)
        self.rand_away_lineup.grid(row=1, column=3)
        tkinter.Label(self.root, text='Lineup').grid(row=1, column=5)
        tkinter.Label(self.root, text='Set Order', anchor='w').grid(
            row=1, column=6)
        tkinter.Label(self.root, text='Set Starters', anchor='w').grid(
            row=1, column=7)
        self.rand_home_lineup.grid(row=1, column=8)


        tkinter.Label(self.root, text='Pitching').grid(row=13, column=0)
        tkinter.Label(self.root, text='Set Pitcher', anchor='w').grid(
            row=13, column=2)
        self.rand_away_sp.grid(row=13, column=3)
        tkinter.Label(self.root, text='Pitching').grid(row=13, column=5)
        tkinter.Label(self.root, text='Set Pitcher', anchor='w').grid(
            row=13, column=7)
        self.rand_home_sp.grid(row=13, column=8)

        self.update_options()

        tkinter.Label(self.root, text='--').grid(row=14, column=0)
        tkinter.Label(self.root, text='SP').grid(row=14, column=1)
        self.away_pitchers['OptionMenu'].grid(row=14, column=2)
        tkinter.Label(self.root, text='--').grid(row=14, column=5)
        tkinter.Label(self.root, text='SP').grid(row=14, column=6)
        self.home_pitchers['OptionMenu'].grid(row=14, column=7)

        self.confirm_button.grid(row=15, column=0)

        self.root.mainloop()

    def confirm(self):
        passed = True
        away_players = [self.away_starters[pos]['Variable'].get()\
                        for pos in self.away_starters]
        home_players = [self.home_starters[pos]['Variable'].get()\
                        for pos in self.home_starters]
        if any([away_players.count(item) > 1 for item in away_players])\
           or '--Select--' in away_players:
            passed = False
        if any([home_players.count(item) > 1 for item in home_players])\
           or '--Select--' in home_players:
            passed = False
        if not passed:
            self.notice.grid(row=15, column=1)
            return
        reps = int(self.reps['Variable'].get())
        if reps < 1:
            self.reps['Variable'].set('1')
        elif reps > 100:
            self.reps['Variable'].set('100')
        self.continue_button.grid(row=16, column=0)
            
    def adjust_reps(self, mode):
        assert mode == '-' or mode == '+'
        num = int(self.reps['Variable'].get())
        if mode == '-' and num > 1:
            self.reps['Entry'].delete(0, 'end')
            self.reps['Entry'].insert(0, num-1)    
        elif mode == '+' and num < 100:
            self.reps['Entry'].delete(0, 'end')
            self.reps['Entry'].insert(0, num+1)
        elif num < 1:
            self.reps['Entry'].delete(0, 'end')
            self.reps['Entry'].insert(0, 1)
        elif num > 100:
            self.reps['Entry'].delete(0, 'end')
            self.reps['Entry'].insert(0, 100)
        self.continue_button.grid_forget()
            
    def lineup_card_menu(self, *, away=False, home=False):
        assert away is not home
        depth_chart = self.away_depth_chart if away else self.home_depth_chart
        batting_order = {}
        starters = {}
        for i, pos in enumerate(list(BATTING), 1):
            batting_order.setdefault(i, {})
            starters.setdefault(pos, {})
            batting_order[i].setdefault(
                'Variable', tkinter.StringVar(self.root, value=pos))
            batting_order[i].setdefault(
                'OptionMenu', tkinter.OptionMenu(
                    self.root, batting_order[i]['Variable'],
                    *list(BATTING),
                    command=lambda _:self.reorder(away=away, home=home)))
            batting_order[i]['OptionMenu'].config(width=5)
            batting_order[i].setdefault(
                'History', [batting_order[i]['Variable'].get(),])
            starters[pos].setdefault(
                'Variable', tkinter.StringVar(self.root, value='--Select--'))
            starters[pos].setdefault(
                'OptionMenu', tkinter.OptionMenu(
                    self.root, starters[pos]['Variable'],
                    *list(depth_chart[pos])))
            starters[pos]['OptionMenu'].config(width=20)

        if away and not home:
            self.away_batting_order = batting_order
            self.away_starters = starters
        elif home and not away:
            self.home_batting_order = batting_order
            self.home_starters = starters

    def update_options(self):
        for i in self.away_batting_order:
            tkinter.Label(self.root, text=str(i)).grid(row=i+2, column=0)
            self.away_batting_order[i]['OptionMenu'].grid(row=i+2, column=1)
            pos = self.away_batting_order[i]['Variable'].get()
            row = self.away_batting_order[i]['OptionMenu'].grid_info()['row']
            self.away_starters[pos]['OptionMenu'].grid(row=row, column=2)
        for i in self.home_batting_order:
            tkinter.Label(self.root, text=str(i)).grid(row=i+2, column=5)
            self.home_batting_order[i]['OptionMenu'].grid(row=i+2, column=6)
            pos = self.home_batting_order[i]['Variable'].get()
            row = self.home_batting_order[i]['OptionMenu'].grid_info()['row']
            self.home_starters[pos]['OptionMenu'].grid(row=row, column=7)
        self.notice.grid_forget()

    def reorder(self, *, away=False, home=False):
        assert away is not home
        depth_chart = self.away_depth_chart if away else self.home_depth_chart
        batting_order = self.away_batting_order if away\
                        else self.home_batting_order
        original, new = '', ''
        for spot in batting_order:
            pos = batting_order[spot]['Variable'].get()
            batting_order[spot]['History'].append(pos)
        for spot in batting_order:
            history = batting_order[spot]['History']
            if history[-1] != history[-2]:
                new, original = history[-1], history[-2]
        for spot in batting_order:
            if batting_order[spot]['History'][-2] == new:
                batting_order[spot]['Variable'].set(original)
                batting_order[spot]['History'][-1] = original
                break
        if away and not home:
            self.away_batting_order = batting_order
        elif home and not away:
            self.home_batting_order = batting_order
        self.update_options()
        
    def random_lineup(self, away=False, home=False):
        assert away is not home
        depth_chart = self.away_depth_chart if away else self.home_depth_chart
        lineup = {}
        for pos in BATTING:
            pos_data = depth_chart.get(pos)
            players = [item for item in pos_data\
                       if item not in lineup]
            player_pa = [pos_data[p].get('PA') for p in pos_data]
            total_pa = sum(player_pa)

            start_probs = [p_pa/total_pa for p_pa in player_pa]
            starter = random.choices(
                list(players),
                weights=start_probs)[0]
            existing_starters = list(lineup.values())
            while starter in existing_starters:
                del start_probs[players.index(starter)]
                players.remove(starter)
                if not players:
                    raise Exception(
                        "Impossible lineup permutation")
                starter = random.choices(
                    list(players),
                    weights=start_probs)[0]
            lineup.setdefault(pos, starter)
        ordered = list(lineup.items())
        random.shuffle(ordered)
        lineup = dict(ordered)
        for i, (pos, starter) in enumerate(lineup.items(), 1):
            if away and not home:
                self.away_batting_order[i]['Variable'].set(pos)
                self.away_starters[pos]['Variable'].set(starter)
                self.away_batting_order[i]['History'][-1] = pos
            elif home and not away:
                self.home_batting_order[i]['Variable'].set(pos)
                self.home_starters[pos]['Variable'].set(starter)
                self.home_batting_order[i]['History'][-1] = pos
        self.update_options()
        self.continue_button.grid_forget()

    def random_sp(self, away=False, home=False):
        assert away is not home
        depth_chart = self.away_depth_chart if away\
                      else self.home_depth_chart
        starting_pitchers = depth_chart.get('SP')
        pitchers, pitcher_tbf = [], []
        for i, player in enumerate(list(starting_pitchers)):
            tbf = starting_pitchers[player].get('TBF')
            if tbf is not None:
                pitchers.append(player)
                pitcher_tbf.append(tbf)
        total_tbf = sum(pitcher_tbf)
        start_probs = [p_tbf/total_tbf for p_tbf in pitcher_tbf]
        pitcher = random.choices(
            list(pitchers),
            weights=start_probs)[0]
        if away and not home:
            self.away_pitchers['Variable'].set(pitcher)
        elif home and not away:
            self.home_pitchers['Variable'].set(pitcher)
        self.continue_button.grid_forget()

class Game:
    def __init__(self, away_team, home_team, away_roster, home_roster,
                 away_depth_chart, home_depth_chart,
                 away_lineup, home_lineup, away_sp, home_sp):
        self.away, self.home = away_team, home_team
        self.away_roster, self.home_roster = away_roster, home_roster
        self.away_depth_chart = away_depth_chart
        self.home_depth_chart = home_depth_chart

        self.away_lineup, self.home_lineup = away_lineup, home_lineup
        self.away_pitcher, self.home_pitcher = away_sp, home_sp
        self.away_index, self.home_index = 1, 1
        self.away_score, self.home_score = 0, 0
        self.top, self.bottom = False, False
        self.inning = 1
        self.gameover = True

        self.away_box_score = {'Lineup': {}, 'Pitchers': {}}
        self.home_box_score = {'Lineup': {}, 'Pitchers': {}}

        self.bases = {1: '', 2: '', 3: '', 4: []}

        innings = list(range(1, 10)) if self.inning <= 9\
                  else list(range(1, self.inning+1))
        categories = ['R', 'H', 'E']

        self.root = tkinter.Tk()
        self.ls_labels = {
            'Head': [tkinter.StringVar(self.root, value='')],
            'Body': [tkinter.StringVar(self.root, value=i)\
                     for i in innings],
            'Tail': [tkinter.StringVar(self.root, value=c)\
                     for c in categories]}
        self.ls_away = {
            'Head': [tkinter.StringVar(self.root, value=self.away)],
            'Body': [tkinter.StringVar(self.root, value='')\
                     for i in innings],
            'Tail': [tkinter.StringVar(self.root, value='0')\
                     for c in categories]}
        self.ls_home = {
            'Head': [tkinter.StringVar(self.root, value=self.home)],
            'Body': [tkinter.StringVar(self.root, value='')\
                     for i in innings],
            'Tail': [tkinter.StringVar(self.root, value='0')\
                     for c in categories]}
        self.line_score = [self.ls_labels, self.ls_away, self.ls_home]
        self.display()

    def display(self):
        for r, row in enumerate(self.line_score):
            values = []
            values.extend(list(row.values())[0])
            values.extend(list(row.values())[1])
            values.extend(list(row.values())[2])
            for c, item in enumerate(values):
                w = 30 if item in row['Head'] else 10
                tkinter.Label(
                    self.root, textvariable=item, relief="sunken",
                    width=w
                    ).grid(row=r, column=c)
        threading.Thread(target=self.simulate_game).start()
        self.root.mainloop()

    def simulate_game(self, *, xrunner=True):
        while self.inning <= 9 or self.away_score == self.home_score:
            self.simulate_inning(xrunner)
            self.inning += 1
        tkinter.Button(
            self.root, text="Continue", command=self.root.destroy
            ).grid(row=3, column=0)

    def simulate_inning(self, xrunner):
        self.ls_away['Body'][self.inning-1].set(0)
        self.ls_home['Body'][self.inning-1].set(0)

        if xrunner and self.inning > 9:
            self.bases[2] = self.away_lineup.get(self.away_index)
            print(f'{self.bases[2]} starting at second.')
        self.outs = 0
        self.top, self.bottom = True, False
        while self.outs < 3:
            self.away_index = 1 if self.away_index == 9\
                              else self.away_index+1
            self.batter = self.away_lineup.get(self.away_index)
            self.pitcher = self.away_pitcher
            self.batter_data = self.away_roster.get(self.batter)
            self.pitcher_data = self.away_roster.get(self.pitcher)
            self.plate_appearance()
            if self.outs == 3:
                self.bases = dict(zip(list(self.bases), (
                    '', '', '', [])))
            runs_scored, self.bases[4] = self.bases[4], []
            for runner in runs_scored:
                if runner:
                    self.ls_away['Body'][self.inning-1].set(
                        int(self.ls_away['Body'][self.inning-1].get())+1)
                    self.ls_away['Tail'][0].set(
                        int(self.ls_away['Tail'][0].get())+1)
                    self.away_score += 1
                    print(f'{runner} scored.', end='\t')
            print()
            print(f'1B: {self.bases[1]}'.ljust(25), end='')
            print(f'2B: {self.bases[2]}'.ljust(25), end='')
            print(f'3B: {self.bases[3]}'.ljust(25), end='')
            print(f'{self.outs} outs')
            print()

        if self.inning >= 9 and self.home_score > self.away_score:
            self.ls_home['Body'][self.inning-1].set('X')
            return

        if xrunner and self.inning > 9:
            self.bases[2] = self.home_lineup.get(self.home_index)
            print(f'{self.bases[2]} starting at second.')
        self.outs = 0
        self.top, self.bottom = False, True
        while self.outs < 3:
            self.home_index = 1 if self.home_index == 9\
                              else self.home_index+1
            self.batter = self.home_lineup.get(self.home_index)
            self.pitcher = self.home_pitcher
            self.batter_data = self.home_roster.get(self.batter)
            self.pitcher_data = self.home_roster.get(self.pitcher)
            self.plate_appearance()
            if self.outs == 3:
                self.bases = dict(zip(list(self.bases), (
                    '', '', '', [])))
            runs_scored, self.bases[4] = self.bases[4], []
            for runner in runs_scored:
                if runner:
                    self.ls_home['Body'][self.inning-1].set(
                        int(self.ls_home['Body'][self.inning-1].get())+1)
                    self.ls_home['Tail'][0].set(
                        int(self.ls_home['Tail'][0].get())+1)
                    self.home_score += 1
                    print(f'{runner} scored.', end='\t')
            print()
            print(f'1B: {self.bases[1]}'.ljust(25), end='')
            print(f'2B: {self.bases[2]}'.ljust(25), end='')
            print(f'3B: {self.bases[3]}'.ljust(25), end='')
            print(f'{self.outs} outs')
            print()

    def plate_appearance(self):
        self.outcomes = {
            'Strikeout': self.outcome_probability(
                ['SO'], ['SO']),
            'Walk': self.outcome_probability(
                ['BB', 'IBB', 'HBP'], ['BB', 'IBB', 'HBP']),
            'Hit': self.outcome_probability(
                ['H'], ['H']),
            'Out': 1-self.outcome_probability(
                ['SO', 'BB', 'IBB', 'HBP', 'H'],
                ['SO', 'BB', 'IBB', 'HBP', 'H'])}
        self.ab_outcome = random.choices(
            list(self.outcomes), list(self.outcomes.values()))[0]
        if self.ab_outcome == 'Strikeout':
            self.strikeout()
        elif self.ab_outcome == 'Walk':
            self.walk()
        elif self.ab_outcome == 'Hit':
            self.hit()
        elif self.ab_outcome == 'Out':
            self.out()

    def outcome_probability(self, s_bat, s_pitch, weights=['PA', 'TBF']):
        assert len(weights) == 2
        n_bat = sum([self.batter_data[stat] for stat in s_bat])
        n_pitch = sum([self.pitcher_data[stat] for stat in s_pitch])
        weight_bat = self.batter_data[weights[0]]
        weight_pitch = self.pitcher_data[weights[1]]
        p_outcome = (n_bat+n_pitch)/(weight_bat+weight_pitch)
        return p_outcome
    
    def strikeout(self):
        specific = random.choices(
            ['Swinging', 'Looking', 'Foul Tip'],
            [0.70, 0.25, 0.05])[0]
        if specific == 'Swinging':
            print(f'{self.batter} strikes out swinging.', end='\t')
        elif specific == 'Looking':
            print(f'{self.batter} strikes out looking.', end='\t')
        elif specific == 'Foul Tip':
            print(f'{self.batter} strikes out on a foul tip.', end='\t')
        self.outs += 1

    def walk(self):
        outcomes = {
            'BB': self.outcome_probability(['BB'], ['BB']),
            'IBB': self.outcome_probability(['IBB'], ['IBB']),
            'HBP': self.outcome_probability(['HBP'], ['HBP'])}
        specific = random.choices(
            list(outcomes), list(outcomes.values()))[0]
        if specific == 'BB':
            print(f'{self.batter} walks.', end='\t')
        elif specific == 'IBB':
            print(f'{self.batter} intentionally walks.', end='\t')
        elif specific == 'HBP':
            print(f'{self.batter} hit by pitch.', end='\t')
        if all([self.bases[1], self.bases[2], self.bases[3]]):
            self.bases = dict(zip(self.bases, (
                self.batter, self.bases[1],
                self.bases[2], [self.bases[3]])))
        elif self.bases[1] and self.bases[2]:
            self.bases = dict(zip(self.bases, (
                self.batter, self.bases[1], self.bases[2], [])))
        elif self.bases[1] and self.bases[3]:
            self.bases = dict(zip(self.bases, (
                self.batter, self.bases[1], self.bases[3], [])))
        elif self.bases[1]:
            self.bases = dict(zip(self.bases, (
                self.batter, self.bases[1], '', [])))
        elif not self.bases[1]:
            self.bases = dict(zip(self.bases, (
                self.batter, self.bases[2], self.bases[3], [])))

    def hit(self):
        outcomes = {
            '1B': self.batter_data['1B'],
            '2B': self.batter_data['2B'],
            '3B': self.batter_data['3B'],
            'HR': self.batter_data['HR']}
        specific = random.choices(
            list(outcomes), list(outcomes.values()))[0]
        x_bases = random.random()
        if specific == '1B':
            print(f'{self.batter} singles.', end='\t')
            if x_bases < 0.5:
                self.bases = dict(zip(self.bases, (
                    self.batter, self.bases[1],
                    self.bases[2], [self.bases[3]])))
            else:
                self.bases = dict(zip(self.bases, (
                    self.batter, '', self.bases[1],
                    [self.bases[2], self.bases[3]])))
        elif specific == '2B':
            print(f'{self.batter} doubles.', end='\t')
            if x_bases < 0.8:
                self.bases = dict(zip(self.bases, (
                    '', self.batter, self.bases[1],
                    [self.bases[3], self.bases[2]])))
            else:
                self.bases = dict(zip(self.bases, (
                    '', self.batter, '',
                    [self.bases[3], self.bases[2],
                     self.bases[1]])))
        elif specific == '3B':
            print(f'{self.batter} triples.', end='\t')
            self.bases = dict(zip(self.bases, (
                '', '', self.batter,
                [self.bases[3], self.bases[2],
                 self.bases[1]])))
        elif specific == 'HR':
            print(f'{self.batter} homers.', end='\t')
            self.bases = dict(zip(self.bases, (
                '', '', '',
                [self.bases[3], self.bases[2],
                 self.bases[1], self.batter])))
        if self.top:
            self.ls_away['Tail'][1].set(
                int(self.ls_away['Tail'][1].get())+1)
        elif self.bottom:
            self.ls_home['Tail'][1].set(
                int(self.ls_home['Tail'][1].get())+1)

    def out(self):
        outcomes = {
            'Groundout': 0.55,
            'Flyout': 0.25,
            'Lineout': 0.10,
            'Popout': 0.10}
        specific = random.choices(
            list(outcomes), list(outcomes.values()))[0]
        if specific == 'Groundout':
            p_gdp = self.batter_data['GDP']/self.outcomes['Out']
            gdp = random.choices([True, False], [p_gdp, 1-p_gdp])[0]
            if self.bases[1] and self.outs < 2 and gdp:
                print(f'{self.batter} grounds into a double play.',
                      end='\t')
                if self.outs == 0:
                    self.bases = dict(zip(self.bases, (
                        '', '', self.bases[2], [self.bases[3]])))
                self.outs += 1
            else:
                print(f'{self.batter} grounds out.', end='\t')
                if self.bases[1]:
                    self.bases = dict(zip(self.bases, (
                        '', self.bases[1], self.bases[2],
                        [self.bases[3]])))
                else:
                    self.bases = dict(zip(self.bases, (
                        '', self.bases[2], '', [self.bases[3]])))
        elif specific == 'Flyout':
            print(f'{self.batter} flies out.', end='\t')
            if self.outs < 2:
                self.bases = dict(zip(self.bases, (
                    self.bases[1], '', self.bases[2],
                    [self.bases[3]])))
        elif specific == 'Lineout':
            print(f'{self.batter} lines out.', end='\t')
        elif specific == 'Popout':
            print(f'{self.batter} pops out.', end='\t')
        self.outs += 1

def main():
    teams = Teams()

    configure_simulation = ConfigureSimulationGUI(teams.teams)
    configure_simulation.display()
    teams.away_team = configure_simulation.away_team
    teams.home_team = configure_simulation.home_team
    teams.compile_rosters()

    configure_lineups = ConfigureLineupsGUI(
        teams.teams,
        teams.away_team, teams.home_team,
        teams.away_roster, teams.home_roster,
        teams.away_depth_chart, teams.home_depth_chart)
    configure_lineups.display()

    away_starters = [configure_lineups.away_starters[pos]['Variable'].get()\
                     for pos in configure_lineups.away_starters]
    home_starters = [configure_lineups.home_starters[pos]['Variable'].get()\
                     for pos in configure_lineups.home_starters]
    away_lineup = dict(zip(
        list(configure_lineups.away_batting_order),
        [configure_lineups.away_starters[
            configure_lineups.away_batting_order[i]['Variable'].get()
            ]['Variable'].get()\
         for i in list(configure_lineups.away_batting_order)]
        ))
    home_lineup = dict(zip(
        list(configure_lineups.home_batting_order),
        [configure_lineups.home_starters[
            configure_lineups.home_batting_order[i]['Variable'].get()
            ]['Variable'].get()\
         for i in list(configure_lineups.home_batting_order)]
        ))

    away_starting_pitcher = configure_lineups.away_pitchers['Variable'].get()
    home_starting_pitcher = configure_lineups.home_pitchers['Variable'].get()

    i = 0
    reps = int(configure_lineups.reps['Variable'].get())
    while i < reps:
        simulation = Game(
            configure_lineups.away_team, configure_lineups.home_team,
            configure_lineups.away_roster, configure_lineups.home_roster,
            configure_lineups.away_depth_chart,
            configure_lineups.home_depth_chart,
            away_lineup, home_lineup,
            away_starting_pitcher, home_starting_pitcher)
        i += 1

if __name__ == '__main__':
    main()
