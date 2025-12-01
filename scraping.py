from datetime import datetime
import requests
from bs4 import BeautifulSoup
from time import sleep
from tqdm import tqdm
import pandas as pd
import re
from io import StringIO

team_tags = []

print('Scraping Team Pages')
for year in tqdm(range(2000, 2026)):

    url = f"https://www.baseball-reference.com/leagues/majors/{year}.shtml"

    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

    else:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")

    team_tags += [link['href'] for link in soup.find_all('a', href=re.compile(r'/teams/.*' + str(year)))]
    
    sleep(3)

batter_tags = []

print('Scraping Player Pages')
for team_tag in tqdm(team_tags):

    team_url = f"https://www.baseball-reference.com{team_tag}"

    response = requests.get(team_url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

    else:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")
        
    tables = pd.read_html(StringIO(str(soup)))
    
    standard_batting = tables[0]
    standard_batters = standard_batting.loc[~standard_batting['Pos'].isin(['P', 'Pos'])].dropna(subset='Pos')
    qualified_batters = standard_batters.loc[standard_batters['AB'].astype(int) >= 130]

    qualified_names = [batter.strip('*#') for batter in qualified_batters['Player'].tolist()]
    
    player_links = soup.find_all('a', href=re.compile(r'/players/.*'))

    batter_tags += [link['href'] for link in player_links if link.text in qualified_names]
    
    sleep(3)

unique_tags = list(set(batter_tags))

rookie_seasons = {}
rookie_robas = {}
rookie_PAs = {}
minors_tags = {}

print('Scraping Minors Pages')
for player_tag in tqdm(unique_tags):

    player_url = f"https://www.baseball-reference.com{player_tag}"

    response = requests.get(player_url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

    else:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")

    try:
        rookie_season = soup.find(string=re.compile(r'Exceeded rookie limits during', re.I)).strip().split()[4]
        
        tables = pd.read_html(StringIO(str(soup)))
        
        advanced_batting = tables[[table['id'] for table in soup.find_all('table')].index('players_advanced_batting')].copy()
        
        advanced_batting.columns = [col[1] for col in advanced_batting.columns]
        
        if int(advanced_batting.loc[advanced_batting['Season']==rookie_season, 'PA'].iloc[0]) >= 130:
            rookie_seasons[player_tag[11:-6]] = int(rookie_season)
            rookie_robas[player_tag[11:-6]] = float(advanced_batting.loc[advanced_batting['Season']==rookie_season, 'rOBA'].iloc[0])
            rookie_PAs[player_tag[11:-6]] = int(advanced_batting.loc[advanced_batting['Season']==rookie_season, 'PA'].iloc[0])
            minors_tags[player_tag[11:-6]] = soup.find('a', string=re.compile(r'.*Minor.*Stats'))['href']

    except:
        print(f'Error occurred for player {player_tag[11:-6]}')

    sleep(3)

minors_stats = {}

print('Scraping Minors Data')
for player_id in tqdm(list(minors_tags.keys())):

    minors_tag = minors_tags[player_id]
    minors_url = f"https://www.baseball-reference.com{minors_tag}"

    response = requests.get(minors_url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

    else:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")

    try:
        tables = pd.read_html(StringIO(str(soup)))
        if 'standard_batting' in [table['id'] for table in soup.find_all('table')]:
            standard_batting_minors = tables[[table['id'] for table in soup.find_all('table')].index('standard_batting')]
            standard_batting_minors['Year'] = pd.to_numeric(standard_batting_minors['Year'], errors='coerce').astype('Int64')
            pre_rookie_batting = standard_batting_minors.loc[standard_batting_minors['Year'] < rookie_seasons[player_id]]
            pre_rookie_batting = pre_rookie_batting.loc[(~pre_rookie_batting['Tm'].astype(str).str.contains('Teams')) & 
                                                (pre_rookie_batting['Lev'] != 'Maj')]
            
        else:
            pre_rookie_batting = pd.DataFrame()
            
        minors_stats[player_id] = pre_rookie_batting

    except:
        print(f'Error occurred for player {player_id}')
    
    sleep(3)

master_data = pd.DataFrame()
for player, data in minors_stats.items():
    if len(data) > 0:
        data['PlayerID'] = player
        data['Rookie_Season'] = rookie_seasons[player]
        data['Rookie_rOBA'] = rookie_robas[player]
        data['Rookie_PA'] = rookie_PAs[player]
        
    master_data = pd.concat([master_data, data])
    
master_data.to_csv('ds4420_minors_stats.csv', index=False)
