'''

Some notes:
- refreshLeague is a mess but so is the ESPN website.

'''

import discord
from discord.ext import commands
from datetime import date
import time
import schedule
import os
import sys
from prettytable import PrettyTable

from helper_functions import openJSON, writeJSON
from display_functions import createPrettyTable, renderStatsImage, sortListBy
from scrape_functions import updateURL, getOffensiveFV, getPerformanceScore, checkLevel

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# bot_two = discord.Client()  # might be an issue
bot = commands.Bot(command_prefix="$")
allowed_mentions = discord.AllowedMentions(everyone=True)

user_settings = openJSON('conf.json')

WINDOW_SIZE = "1920,1080"
PROFILE = user_settings['profile']
USERMAP = user_settings['usermap']
DISCORD_TOKEN = user_settings["DISCORD_TOKEN"]

options = webdriver.ChromeOptions()
# options.add_argument('headless')
# options.add_argument('disable-gpu')
#options.add_argument('--window-size=%s' % WINDOW_SIZE)
options.add_argument(
    'user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36')
options.add_argument('--disable-dev-shm-usage')
options.add_experimental_option("useAutomationExtension", False)
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_argument("user-data-dir=%s" % PROFILE)
driver = webdriver.Chrome("chromedriver", chrome_options=options)


@bot.command(name="myroster", brief="Prints out your current roster.")
async def myroster(ctx):

    League = openJSON('League.json')

    embed = discord.Embed(
        title=str(ctx.message.author) + '\'s Team:',
        url='https://fantasy.espn.com/baseball/team?leagueId='+str(USERMAP['leagueID'])+'&teamId=' +
            str(USERMAP[str(ctx.message.author)]),
        # description="blah",
        color=discord.Color.red()
    )

    team = League[str(ctx.message.author)]
    hitters = ''
    pitchers = ''
    rps = ''
    prosp = ''
    bench = ''
    il = ''

    for i in team:
        if team[i]['position'] == 'Starting Pitcher':
            pitchers += '**' + i + '**: ' + \
                team[i]['position'] + ', *' + team[i]['team'] + '*\n'
        elif team[i]['position'] == 'Relief Pitcher':
            rps += '**' + i + '**: ' + \
                team[i]['position'] + ', *' + team[i]['team'] + '*\n'
        elif team[i]['position'] == 'Prospect':
            prosp += '**' + i + '**: ' + \
                team[i]['position'] + ', *' + team[i]['team'] + '*\n'
        elif team[i]['position'] == 'Bench':
            bench += '**' + i + '**: ' + \
                team[i]['position'] + ', *' + team[i]['team'] + '*\n'
        elif team[i]['position'] == 'Injured List':
            il += '**' + i + '**: ' + \
                team[i]['position'] + ', *' + team[i]['team'] + '*\n'
        else:
            hitters += '**' + i + '**: ' + \
                team[i]['position'] + ', *' + team[i]['team'] + '*\n'

    if len(hitters) > 0:
        embed.add_field(name='Lineup', value=hitters, inline=False)
    if len(pitchers) > 0:
        embed.add_field(name='Rotation', value=pitchers, inline=False)
    if len(rps) > 0:
        embed.add_field(name='Bullpen', value=rps, inline=False)
    if len(bench) > 0:
        embed.add_field(name='Bench', value=bench, inline=False)
    if len(prosp) > 0:
        embed.add_field(name='Farm', value=prosp, inline=False)
    if len(il) > 0:
        embed.add_field(name='IL', value=il, inline=False)

    await ctx.channel.send(embed=embed)

@bot.command(name="top100", brief="Top 100 prospects list.")
async def top(ctx, *args):

    top_list = openJSON('top100.json')
    #top_list = openJSON('2020top100.json')

    level_ref = {'A-': 1.0, 'A': 1.0, 'A+':1.0, 'AA': 1.4, 'AAA': 1.5}

    url = 'https://blogs.fangraphs.com/2022-top-100-prospects/'
    #url = 'https://blogs.fangraphs.com/2020-top-100-prospects/'
    driver.get(url)

    fangraphs_list = WebDriverWait(
        driver, 10).until(
        EC.presence_of_element_located(
            (By.CLASS_NAME, 'table-container.table-green')))
    fangraphs_list = fangraphs_list.find_element(By.TAG_NAME, 'tbody')
    fangraphs_list = fangraphs_list.find_elements(By.TAG_NAME, 'tr')

    for i in fangraphs_list:

        columns = i.find_elements(By.TAG_NAME, 'td')
        if len(columns) <= 0:
            print('divider')
            continue
        #print(columns[1].get_attribute('innerHTML'))
        rank = columns[0].text
        try:
            link = columns[1].find_element(By.TAG_NAME, 'a')
        except:
            continue
        name = link.text
        link = link.get_attribute('href')
        position = columns[5].text

        if 'P' in position:
            print('pitcher')
            continue

        top_list[name] = {'rank': rank, 'position': position, 'link': link}

    for j in top_list:
        url = top_list[j]['link']
        while True:
            try:
                driver.get(url)

                scouting_report = WebDriverWait(
                    driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CLASS_NAME, 'player-page-prospects-main')))
                scouting_report = scouting_report.find_elements(By.TAG_NAME, 'td')
                break
            except:
                continue

        offensive_FV = getOffensiveFV(scouting_report)

        top_list[j]['FV'] = offensive_FV
        offensive_FV = top_list[j]['FV']

        performance_metrics = WebDriverWait(
            driver, 10).until(
            EC.presence_of_element_located(
                (By.ID, 'dashboard')))
        performance_metrics = performance_metrics.find_element(By.CLASS_NAME, 'table-scroll')
        performance_metrics = performance_metrics.find_elements(By.CLASS_NAME, 'row-minors.is-selected__invalid')

        performance_score = getPerformanceScore(performance_metrics, level_ref)

        top_list[j]['Perform'] = performance_score
        top_list[j]['PDR'] = performance_score * offensive_FV / 10  # divide by 10 to make it a pretty number

    scout_table = PrettyTable()
    scout_table.field_names = ['#', 'rank', 'Player', 'position', 'FV', 'Perform', 'PDR']

    sortedL = sortListBy(top_list, 'PDR')
    print(sortedL)

    counter = 1
    for d in sortedL:
        pname = d[0]
        pstats = top_list[pname]
        temprow = []
        #print((pname, pstats))
        for f in scout_table.field_names:
            if f == 'Player':
                temprow.append(pname)
            elif f == 'rank':
                temprow.append('%s' % pstats[f])
            elif f == 'position':
                temprow.append('%s' % pstats[f])
            elif f == '#':
                temprow.append('%d' % counter)
            else:
                print(pstats[f])
                temprow.append('%.1f' % pstats[f])
        scout_table.add_row(temprow)
        counter+=1

    leaders = '''2022 Top 100 PDR:\n%s''' % (scout_table)

    renderStatsImage(leaders)  # data is saved in test.png

    await ctx.channel.send(file=discord.File(r'test.png'))

    writeJSON('top100.json', top_list)


# add a 2022 argument
@bot.command(name="scout", brief="prospect rating based on 2:1 performance to scouting ratio")
async def PDR(ctx, *args):

    await ctx.channel.send('Please wait...')

    League = openJSON('League.json')
    milb_stats = openJSON('MiLB.json')

    author = str(ctx.message.author)

    milb_offense = {}

    level_ref = {'A-': 1.0, 'A': 1.0, 'A+':1.0, 'AA': 1.4, 'AAA': 1.5}

    num_players = 0
    total_pdr = 0

    year = 'All'

    for i in args:
        if i == '2022':
            year = '2022'

    for i in League[author]:
        if League[author][i]['position'] == 'Prospect':
            milb_stats = updateURL(driver, milb_stats, i)

            scouting_report = WebDriverWait(
                driver, 10).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, 'player-page-prospects-main')))
            scouting_report = scouting_report.find_elements(By.TAG_NAME, 'td')
            position = driver.find_element(By.CLASS_NAME, 'player-info-box-pos').text

            if position == 'P':
                continue

            offensive_FV = getOffensiveFV(scouting_report)
            #print(offensive_FV)

            milb_offense[i] = {}
            milb_offense[i]['FV'] = '%.1f' % offensive_FV

            performance_metrics = WebDriverWait(
                driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, 'dashboard')))
            performance_metrics = performance_metrics.find_element(By.CLASS_NAME, 'table-scroll')
            performance_metrics = performance_metrics.find_elements(By.CLASS_NAME, 'row-minors.is-selected__invalid')

            performance_score = getPerformanceScore(performance_metrics, level_ref, year)
            #print(performance_score)

            milb_offense[i]['Perform'] = '%.1f' % performance_score
            milb_offense[i]['PDR'] = '%.1f' % (performance_score * offensive_FV / 10)  # divide by 10 to make it a pretty number
            total_pdr += (performance_score * offensive_FV / 10)
            num_players += 1

    scout_table = PrettyTable()
    scout_table.field_names = ['Player', 'FV', 'Perform', 'PDR']

    sortColumn = 'PDR'

    for z in args:
        if z in scout_table.field_names:
            sortColumn = z

    sortedL = sortListBy(milb_offense, sortColumn)
    print(sortedL)

    scout_table = createPrettyTable(sortedL, scout_table, milb_offense)

    leaders = '''Scouting Report %s:\n```%s
               ```
               ''' % (year, scout_table)

    await ctx.send(leaders)

    print(milb_offense)
    await ctx.send('Avg PDR: %s' % (total_pdr/num_players))

    # try:
    #     leaderboard[author]['PDR'] = '%.1f' % (total_pdr/num_players)
    # except:
    #     pdr = '%.1f' % (total_pdr/num_players)
    #     leaderboard[author] = {'Team': author, 'WAR': 0, 'wRC+': 0, 'OPS': 0, 'FIP': 0, 'K9': 0, 'AvgAge': 0, 'PDR': pdr}


#@bot.command(name="stats", brief='Team stats for the season.')
#async def teamStats(ctx, *args):
def teamStats(ctx, *args):

    League = openJSON('League.json')
    mlb_links = openJSON('MLB.json')
    leaders = openJSON('Leaderboard.json')

    author = str(ctx.message.author)

    mlb_offense = {}
    mlb_defense = {}
    milb_offense = {}
    milb_defense = {}

    # Cumulative numbers
    milb_pitching = {
        'W': 0,
        'L': 0,
        'ERA': 0.0,  # 9 x earned runs allowed / IP
        'G': 0,
        'GS': 0,
        'SV': 0,
        'IP': 0,
        'SO': 0,
        'WHIP': 0,  # (n hits allowed + n walks allowed) / IP
        'K9': 0,  # (SO*9) / IP
        'H': 0,
        'BB': 0,
        'ER': 0
    }

    milb_hitting = {
        'AB': 0,
        'R': 0,
        'H': 0,
        'TB': 0,
        'doub': 0,
        'trip': 0,
        'HR': 0,
        'RBI': 0,
        'BB': 0,
        'IBB': 0,
        'SO': 0,
        'SB': 0,
        'AVG': 0.0,  # H / AB
        'OBP': 0.0,  # (H + BB + HBP) / (AB + BB + HBP + SF)
        'OPS': 0.0,  # OBP + SLG
        'SLG': 0.0,  # (1B + 2B*2 + 3B*3 + HR*4)/AB

        'HBP': 0,
        'SF': 0,
    }

    mlb_hitting = {
        'AB': 0,
        'R': 0,
        'H': 0,
        'TB': 0,
        'doub': 0,
        'trip': 0,
        'HR': 0,
        'RBI': 0,
        'BB': 0,
        'IBB': 0,
        'SO': 0,
        'SB': 0,
        'AVG': 0.0,  # H / AB
        'OBP': 0.0,  # (H + BB + HBP) / (AB + BB + HBP + SF)
        'OPS': 0.0,  # OBP + SLG
        'SLG': 0.0,  # (1B + 2B*2 + 3B*3 + HR*4)/AB

        'HBP': 0,
        'SF': 0,
    }

    mlb_pitching = {
        'W': 0,
        'L': 0,
        'ERA': 0.0,  # 9 x earned runs allowed / IP
        'G': 0,
        'GS': 0,
        'SV': 0,
        'IP': 0,
        'SO': 0,
        'WHIP': 0,  # (n hits allowed + n walks allowed) / IP
        'K9': 0,  # (SO*9) / IP
        'H': 0,
        'BB': 0,
        'ER': 0
    }

    # Counters to calculate totals
    avg_age, activeroster, war, wrc, m_wrc, fip, m_fip, hitters, pitchers, m_hitters, m_pitchers, owar, oage, moage, dwar, dage, mdage = 0

    for player_name in League[author]:
        if League[author][player_name]['position'] == 'Prospect':

            mlb_links = updateURL(driver, mlb_links, player_name)

            pl = WebDriverWait(
                driver, 10).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, 'player-info-box-header')))
            player_position = pl.find_element(
                By.CLASS_NAME, 'player-info-box-pos').text
            player_age = pl.find_elements(
                By.CLASS_NAME, 'player-info-box-item')[0].text

            try:
                dashboard = WebDriverWait(
                    driver, 10).until(
                    EC.presence_of_element_located(
                        (By.ID, 'dashboard')))
            except BaseException:
                print('%s is not in the League yet, Skipping' % player_name)
                continue
            table_scroll = dashboard.find_element(
                By.CLASS_NAME, 'table-scroll')
            tbody = table_scroll.find_element(By.TAG_NAME, 'tbody')
            try:
                mlb_season = tbody.find_elements(By.CLASS_NAME, 'row-minors.is-selected__invalid')
            except BaseException:
                print(
                    '%s is not in the Minors yet, but also not a declared prospect. Skipping' % player_name)
                continue

            this_season = []
            for k in mlb_season:
                yr = k.find_elements(By.TAG_NAME, 'td')[0]
                yr = yr.find_element(By.TAG_NAME, 'a').text
                if yr == '2022':
                    this_season.append(k)
                    break
            else:
                print('2022 Season not found')
                continue

            for season in this_season:
                rows = season.find_elements(By.TAG_NAME, 'td')
                tempwar = 0
                tempwrc = 0
                if rows[0].text == '2022':
                    #tempwar = float(rows[27].text)
                    try:
                        tempwrc = float(rows[21].text)
                    except BaseException:
                        tempwrc = 0
                        print('no wrc')
                    try:
                        tempfip = float(rows[23].text)
                    except BaseException:
                        tempfip = 0
                        print('no fip')

            dashboard = WebDriverWait(
                driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, 'standard')))
            table_scroll = dashboard.find_element(
                By.CLASS_NAME, 'table-scroll')
            mlb_season = table_scroll.find_elements(
                By.CLASS_NAME, 'row-minors')

            # problem area
            thisseason = []
            for j in mlb_season:
                yr = j.find_elements(By.TAG_NAME, 'td')[0]
                yr = yr.find_element(By.TAG_NAME, 'a').text
                if yr == '2022':
                    thisseason.append(j)
                    break
            else:
                print(i)
                print('Player hasnt played in 2022 yet, skipping')
                continue

            if position == 'P':
                wins, losses, games, games_started, saves, innings_pitched, strikeouts, hits, walks, earned_runs = 0
                for s in thisseason:
                    cols = s.find_elements(By.TAG_NAME, 'td')

                    wins += int(cols[3].get_attribute('innerHTML'))
                    losses += int(cols[4].get_attribute('innerHTML'))
                    games += int(cols[6].get_attribute('innerHTML'))
                    games_started += int(cols[7].get_attribute('innerHTML'))
                    saves += int(cols[10].get_attribute('innerHTML'))
                    innings_pitched += (int(cols[13].get_attribute('innerHTML').split(
                        '.')[0]) + int(cols[13].get_attribute('innerHTML').split('.')[1]) * 0.333)
                    strikeouts += int(cols[24].get_attribute('innerHTML'))
                    hits += int(cols[15].get_attribute('innerHTML'))
                    walks += int(cols[19].get_attribute('innerHTML'))
                    earned_runs += int(cols[17].get_attribute('innerHTML'))

                milb_pitching['W'] += wins
                milb_pitching['L'] += losses
                milb_pitching['G'] += games
                milb_pitching['GS'] += games_started
                milb_pitching['SV'] += saves
                milb_pitching['IP'] += innings_pitched
                milb_pitching['SO'] += strikeouts
                milb_pitching['H'] += hits
                milb_pitching['BB'] += walks
                milb_pitching['ER'] += earned_runs
                m_fip += tempfip

                milb_defense[i] = {
                    'Pos': position,
                    'Age': int(
                        age.split(': ')[1]),
                    'WAR': tempwar,
                    'FIP': tempfip,
                    'W': wins,
                    'L': losses,
                    'G': games,
                    'GS': games_started,
                    'SV': saves,
                    'IP': innings_pitched,
                    'SO': strikeouts,
                    'H': hits,
                    'BB': walks,
                    'ER': earned_runs,
                    'ERA': '%.2f' % ((earned_runs * 9) / innings_pitched),
                    'WHIP': '%.2f' % ((hits + walks) / innings_pitched),
                    'K9': '%.2f' % ((strikeouts * 9) / innings_pitched)}

                    #dwar += tempwar
                mdage += int(age.split(': ')[1])
                m_pitchers += 1

            else:
                cols = thisseason.find_elements(By.TAG_NAME, 'td')

                at_bats = int(cols[4].get_attribute('innerHTML'))
                hits = int(cols[6].get_attribute('innerHTML'))
                doubles = int(cols[8].get_attribute('innerHTML'))
                triples = int(cols[9].get_attribute('innerHTML'))
                homeruns = int(cols[10].get_attribute('innerHTML'))
                runs = int(cols[11].get_attribute('innerHTML'))
                rbis = int(cols[12].get_attribute('innerHTML'))
                walks = int(cols[13].get_attribute('innerHTML'))
                strikeouts = int(cols[15].get_attribute('innerHTML'))
                hit_by_pitch = int(cols[16].get_attribute('innerHTML'))
                sac_fly = int(cols[17].get_attribute('innerHTML'))
                stolen_base = int(cols[20].get_attribute('innerHTML'))

                milb_hitting['AB'] += at_bats
                milb_hitting['H'] += hits
                milb_hitting['doub'] += doubles
                milb_hitting['trip'] += triples
                milb_hitting['HR'] += homeruns
                milb_hitting['R'] += runs
                milb_hitting['RBI'] += rbis
                milb_hitting['BB'] += walks
                milb_hitting['SO'] += strikeouts
                milb_hitting['HBP'] += hit_by_pitch
                milb_hitting['SF'] += sac_fly
                milb_hitting['SB'] += stolen_base
                m_wrc += tempwrc * at_bats
                m_hitters += 1

                obp = (hits + walks + hit_by_pitch) / \
                    (at_bats + walks + hit_by_pitch + sac_fly)
                slg = ((hits - doubles - triples - homeruns) + doubles * 2 +
                       triples * 3 + homeruns * 4) / at_bats  # (1B + 2B*2 + 3B*3 + HR*4)/AB

                milb_offense[i] = {
                    'Pos': position,
                    'Age': int(
                        age.split(': ')[1]),
                    'WAR': tempwar,
                    'wRC+': tempwrc,
                    'AB': at_bats,
                    'H': hits,
                    'doub': doubles,
                    'trip': triples,
                    'HR': homeruns,
                    'R': runs,
                    'RBI': rbis,
                    'BB': walks,
                    'SO': strikeouts,
                    'HBP': hit_by_pitch,
                    'SF': sac_fly,
                    'SB': stolen_base,
                    'AVG': '%.3f' % (hits / at_bats),
                    'OBP': '%.3f' % obp,
                    'SLG': '%.3f' % slg,
                    'OPS': '%.3f' % (obp + slg)}

                #owar += tempwar
                moage += int(age.split(': ')[1])

        elif League[author][i]['position'] == 'Injured List':
            print('%s: Player Injured, Skipping...' % i)
            continue
        else:  # major leaguers
            try:
                url = stats[i]['link']
                driver.get(url)
            except BaseException:
                try:
                    del stats[i]
                    print('link is old, refreshing...')
                except BaseException:
                    print('Adding New Player...')
            if i not in stats:
                url = 'https://www.google.com'
                driver.get(url)

                time.sleep(0.1)
                name = 'fangraphs ' + i
                print(name)
                e = driver.find_element(By.NAME, 'q')
                e.send_keys(name)
                e.send_keys(Keys.ENTER)
                time.sleep(0.1)
                f = driver.find_elements(By.TAG_NAME, 'a')
                for j in f:
                    posslink = j.get_attribute('href')
                    if posslink is None:
                        continue
                    href = "https://www.fangraphs.com/players/"
                    if href == posslink[:34]:
                        j.click()
                        time.sleep(0.1)
                        link = posslink  # save this in lookup table
                        break
                # navigates to baseball reference.
                stats[i] = {'link': link}
                # scrape
                time.sleep(0.1)

                #pl = driver.find_element(By.CLASS_NAME, 'player-header--vitals')
            pl = WebDriverWait(
                driver, 10).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, 'player-info-box-header')))
            position = pl.find_element(
                By.CLASS_NAME, 'player-info-box-pos').text
            age = pl.find_elements(
                By.CLASS_NAME, 'player-info-box-item')[0].text

            try:
                dashboard = WebDriverWait(
                    driver, 10).until(
                    EC.presence_of_element_located(
                        (By.ID, 'dashboard-skinny')))
            except BaseException:
                print(i)
                print('Player is not in the MLB yet, Skipping')
                continue
            table_scroll = dashboard.find_element(
                By.CLASS_NAME, 'table-scroll')
            tbody = table_scroll.find_element(By.TAG_NAME, 'tbody')
            try:
                mlb_season = tbody.find_element(
                    By.CLASS_NAME, 'row-mlb-season')
            except BaseException:
                print(i)
                print(
                    'Player is not in the MLB yet, but also not a declared prospect. Skipping')
                continue
            rows = mlb_season.find_elements(By.TAG_NAME, 'td')
            tempwar = 0
            tempwrc = 0
            if rows[0].text == '2022':
                tempwar = float(rows[11].text)
                tempwrc = float(rows[10].text)

            dashboard = WebDriverWait(
                driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, 'standard')))
            table_scroll = dashboard.find_element(
                By.CLASS_NAME, 'table-scroll')
            mlb_season = table_scroll.find_elements(
                By.CLASS_NAME, 'row-mlb-season')

            # problem area
            for j in mlb_season:
                yr = j.find_elements(By.TAG_NAME, 'td')[0]
                yr = yr.find_element(By.TAG_NAME, 'a').text
                if yr == '2022':
                    thisseason = j
                    break
            else:
                print(i)
                print('Player hasnt played in 2022 yet, skipping')
                continue

            if position == 'P':
                cols = thisseason.find_elements(By.TAG_NAME, 'td')

                wins = int(cols[3].get_attribute('innerHTML'))
                losses = int(cols[4].get_attribute('innerHTML'))
                games = int(cols[6].get_attribute('innerHTML'))
                games_started = int(cols[7].get_attribute('innerHTML'))
                saves = int(cols[10].get_attribute('innerHTML'))
                innings_pitched = (int(cols[13].get_attribute('innerHTML').split(
                    '.')[0]) + int(cols[13].get_attribute('innerHTML').split('.')[1]) * 0.333)
                strikeouts = int(cols[24].get_attribute('innerHTML'))
                hits = int(cols[15].get_attribute('innerHTML'))
                walks = int(cols[19].get_attribute('innerHTML'))
                earned_runs = int(cols[17].get_attribute('innerHTML'))

                mlb_pitching['W'] += wins
                mlb_pitching['L'] += losses
                mlb_pitching['G'] += games
                mlb_pitching['GS'] += games_started
                mlb_pitching['SV'] += saves
                mlb_pitching['IP'] += innings_pitched
                mlb_pitching['SO'] += strikeouts
                mlb_pitching['H'] += hits
                mlb_pitching['BB'] += walks
                mlb_pitching['ER'] += earned_runs
                fip += tempwrc
                pitchers += 1

                mlb_defense[i] = {
                    'Pos': position,
                    'Age': int(
                        age.split(': ')[1]),
                    'WAR': tempwar,
                    'FIP': tempwrc,
                    'W': wins,
                    'L': losses,
                    'G': games,
                    'GS': games_started,
                    'SV': saves,
                    'IP': innings_pitched,
                    'SO': strikeouts,
                    'H': hits,
                    'BB': walks,
                    'ER': earned_runs,
                    'ERA': '%.2f' % ((earned_runs * 9) / innings_pitched),
                    'WHIP': '%.2f' % ((hits + walks) / innings_pitched),
                    'K9': '%.2f' % ((strikeouts * 9) / innings_pitched)}

                dwar += tempwar
                dage += int(age.split(': ')[1])

            else:
                cols = thisseason.find_elements(By.TAG_NAME, 'td')

                at_bats = int(cols[4].get_attribute('innerHTML'))
                hits = int(cols[6].get_attribute('innerHTML'))
                doubles = int(cols[8].get_attribute('innerHTML'))
                triples = int(cols[9].get_attribute('innerHTML'))
                homeruns = int(cols[10].get_attribute('innerHTML'))
                runs = int(cols[11].get_attribute('innerHTML'))
                rbis = int(cols[12].get_attribute('innerHTML'))
                walks = int(cols[13].get_attribute('innerHTML'))
                strikeouts = int(cols[15].get_attribute('innerHTML'))
                hit_by_pitch = int(cols[16].get_attribute('innerHTML'))
                sac_fly = int(cols[17].get_attribute('innerHTML'))
                stolen_base = int(cols[20].get_attribute('innerHTML'))

                mlb_hitting['AB'] += at_bats
                mlb_hitting['H'] += hits
                mlb_hitting['doub'] += doubles
                mlb_hitting['trip'] += triples
                mlb_hitting['HR'] += homeruns
                mlb_hitting['R'] += runs
                mlb_hitting['RBI'] += rbis
                mlb_hitting['BB'] += walks
                mlb_hitting['SO'] += strikeouts
                mlb_hitting['HBP'] += hit_by_pitch
                mlb_hitting['SF'] += sac_fly
                mlb_hitting['SB'] += stolen_base
                wrc += tempwrc * at_bats
                hitters += 1

                obp = (hits + walks + hit_by_pitch) / \
                    (at_bats + walks + hit_by_pitch + sac_fly)
                slg = ((hits - doubles - triples - homeruns) + doubles * 2 +
                       triples * 3 + homeruns * 4) / at_bats  # (1B + 2B*2 + 3B*3 + HR*4)/AB

                mlb_offense[i] = {
                    'Pos': position,
                    'Age': int(
                        age.split(': ')[1]),
                    'WAR': tempwar,
                    'wRC+': tempwrc,
                    'AB': at_bats,
                    'H': hits,
                    'doub': doubles,
                    'trip': triples,
                    'HR': homeruns,
                    'R': runs,
                    'RBI': rbis,
                    'BB': walks,
                    'SO': strikeouts,
                    'HBP': hit_by_pitch,
                    'SF': sac_fly,
                    'SB': stolen_base,
                    'AVG': '%.3f' % (hits / at_bats),
                    'OBP': '%.3f' % obp,
                    'SLG': '%.3f' % slg,
                    'OPS': '%.3f' % (obp + slg)}

                owar += tempwar
                oage += int(age.split(': ')[1])

            stats[i]['position'] = position
            stats[i]['age'] = age
            avg_age += int(age.split(': ')[1])
            activeroster += 1
            war += tempwar

    try:
        avg = '%.3f' % (milb_hitting['H'] / milb_hitting['AB'])
        obp = '%.3f' % ((milb_hitting['H'] + milb_hitting['BB'] + milb_hitting['HBP']) / (
            milb_hitting['AB'] + milb_hitting['BB'] + milb_hitting['HBP'] + milb_hitting['SF']))
        singles = milb_hitting['H'] - milb_hitting['doub'] - \
            milb_hitting['trip'] - milb_hitting['HR']
        slg = '%.3f' % (
            (singles + 2 * milb_hitting['doub'] + 3 * milb_hitting['trip'] + 4 * milb_hitting['HR']) / milb_hitting['AB'])
        ops = '%.3f' % (float(obp) + float(slg))
        milb_hitting['AVG'] = avg
        milb_hitting['OBP'] = obp
        milb_hitting['SLG'] = slg
        milb_hitting['OPS'] = ops
        print(milb_hitting)
        x = PrettyTable()
        x.field_names = [
            'Player',
            'Pos',
            'Age',
            'WAR',
            'wRC+',
            'AB',
            'R',
            'H',
            'HR',
            'RBI',
            'SB',
            'BB',
            'AVG',
            'OBP',
            'SLG',
            'OPS']
        milb_hitting['Pos'] = 'Team'
        milb_hitting['Age'] = '%.1f' % (moage / m_hitters)
        milb_hitting['WAR'] = 0
        milb_hitting['wRC+'] = int(m_wrc / int(milb_hitting['AB']))
        milb_offense['TEAM'] = milb_hitting
        for j in milb_offense:
            temprow = []
            for i in x.field_names:
                if i == 'Player':
                    temprow.append(j)
                else:
                    temprow.append(milb_offense[j][i])
            print(temprow)
            x.add_row(temprow)
        mi_hitters = '''MiLB Hitting Team Stats:\n%s\n''' % (x)
    except Exception as e:
        print(e)
        mi_hitters = '''MiLB Hitting Team Stats: \n'''
        print('No hitting prospects')

    try:
        milb_pitching['ERA'] = '%.3f' % (
            (9 * milb_pitching['ER']) / milb_pitching['IP'])
        milb_pitching['WHIP'] = '%.3f' % (
            (milb_pitching['H'] + milb_pitching['BB']) / milb_pitching['IP'])
        milb_pitching['K9'] = '%.3f' % (
            (9 * milb_pitching['SO']) / milb_pitching['IP'])
        print(milb_pitching)
        y = PrettyTable()
        y.field_names = [
            'Player',
            'Pos',
            'Age',
            'WAR',
            'FIP',
            'W',
            'L',
            'ERA',
            'G',
            'GS',
            'SV',
            'IP',
            'SO',
            'BB',
            'WHIP',
            'K9']
        milb_pitching['Pos'] = 'Team'
        milb_pitching['Age'] = '%.1f' % (mdage / m_pitchers)
        milb_pitching['WAR'] = 0
        milb_pitching['FIP'] = '%.2f' % (m_fip / m_pitchers)
        milb_defense['TEAM'] = milb_pitching
        for k in milb_defense:
            temprow = []
            for j in y.field_names:
                if j == 'Player':
                    temprow.append(k)
                else:
                    if j == 'IP':
                        temprow.append('%.1f' % milb_defense[k][j])
                    else:
                        temprow.append(milb_defense[k][j])
            y.add_row(temprow)
        mi_pitchers = '''MiLB Pitching Team Stats:\n%s\n''' % (y)
    except Exception as e:
        print(e)
        mi_pitchers = '''MiLB Pitching Team Stats: \n'''
        print('No pitching prospects')

    # MLB stats
    avg = '%.3f' % (mlb_hitting['H'] / mlb_hitting['AB'])
    obp = '%.3f' % ((mlb_hitting['H'] + mlb_hitting['BB'] + mlb_hitting['HBP']) / (
        mlb_hitting['AB'] + mlb_hitting['BB'] + mlb_hitting['HBP'] + mlb_hitting['SF']))
    singles = mlb_hitting['H'] - mlb_hitting['doub'] - \
        mlb_hitting['trip'] - mlb_hitting['HR']
    slg = '%.3f' % ((singles + 2 * mlb_hitting['doub'] + 3 * \
                    mlb_hitting['trip'] + 4 * mlb_hitting['HR']) / mlb_hitting['AB'])
    ops = '%.3f' % (float(obp) + float(slg))
    mlb_hitting['AVG'] = avg
    mlb_hitting['OBP'] = obp
    mlb_hitting['SLG'] = slg
    mlb_hitting['OPS'] = ops
    print(mlb_hitting)
    x = PrettyTable()
    x.field_names = [
        'Player',
        'Pos',
        'Age',
        'WAR',
        'wRC+',
        'AB',
        'R',
        'H',
        'HR',
        'RBI',
        'SB',
        'BB',
        'AVG',
        'OBP',
        'SLG',
        'OPS']
    mlb_hitting['Pos'] = 'Team'
    mlb_hitting['Age'] = '%.1f' % (oage / hitters)
    mlb_hitting['WAR'] = '%.1f' % owar
    mlb_hitting['wRC+'] = int(wrc / int(mlb_hitting['AB']))
    mlb_offense['TEAM'] = mlb_hitting
    for j in mlb_offense:
        temprow = []
        for i in x.field_names:
            if i == 'Player':
                temprow.append(j)
            else:
                temprow.append(mlb_offense[j][i])
        x.add_row(temprow)
    str_hitters = '''MLB Hitting Team Stats:\n%s\n''' % (x)
    # await ctx.send(str_hitters)

    mlb_pitching['ERA'] = '%.3f' % (
        (9 * mlb_pitching['ER']) / mlb_pitching['IP'])
    mlb_pitching['WHIP'] = '%.3f' % (
        (mlb_pitching['H'] + mlb_pitching['BB']) / mlb_pitching['IP'])
    mlb_pitching['K9'] = '%.3f' % (
        (9 * mlb_pitching['SO']) / mlb_pitching['IP'])
    print(mlb_pitching)
    y = PrettyTable()
    y.field_names = [
        'Player',
        'Pos',
        'Age',
        'WAR',
        'FIP',
        'W',
        'L',
        'ERA',
        'G',
        'GS',
        'SV',
        'IP',
        'SO',
        'BB',
        'WHIP',
        'K9']
    mlb_pitching['Pos'] = 'Team'
    mlb_pitching['Age'] = '%.1f' % (dage / pitchers)
    mlb_pitching['WAR'] = '%.1f' % dwar
    mlb_pitching['FIP'] = '%.2f' % (fip / pitchers)
    mlb_defense['TEAM'] = mlb_pitching
    for k in mlb_defense:
        temprow = []
        for j in y.field_names:
            if j == 'Player':
                temprow.append(k)
            else:
                if j == 'IP':
                    temprow.append('%.1f' % mlb_defense[k][j])
                else:
                    temprow.append(mlb_defense[k][j])
        y.add_row(temprow)
    str_pitchers = '''MLB Pitching Team Stats:\n%s\n''' % (y)

    download = False
    for i in args:
        if i == 'file':
            download = True

    today = date.today()
    with open('stats_history/%s_stats_%s.txt' % (author, today), 'w') as inf:
        inf.write(
            '%s' %
            (str_hitters +
             str_pitchers +
             mi_hitters +
             mi_pitchers))
    inf.close()

    #if download:
    #    with open('stats_history/%s_stats_%s.txt' % (author, today), "rb") as file:
    #        await ctx.channel.send("%s Team Stats: " % author, file=discord.File(file, ("%s_stats.txt" % author)))
    #else:
    #    renderStatsImage((str_hitters + str_pitchers + mi_hitters + mi_pitchers))
    #    await ctx.channel.send("%s Team Stats: " % author, file=discord.File(r'test.png'))

    print(milb_defense)

    leaders[author] = {}
    leaders[author]['AvgAge'] = '%.2f' % (avg_age / activeroster)
    leaders[author]['WAR'] = '%.1f' % war
    leaders[author]['wRC+'] = '%d' % int(wrc / int(mlb_hitting['AB']))
    leaders[author]['OPS'] = mlb_hitting['OPS']
    leaders[author]['ISO'] = mlb_hitting['SLG'] - mlb_hitting['AVG']
    leaders[author]['K9'] = mlb_pitching['K9']
    leaders[author]['FIP'] = '%.2f' % (fip / pitchers)

    writeJSON('Leaderboard.json', leaders)
    writeJSON('MLB.json', stats)
    writeJSON('MiLB.json', milb_stats)


@bot.command(name="leaderboard",
             brief="Displays current leaderboard (run $stats to enter the leaderboard)")
async def leaderboard(ctx, *args):

    leaderboard = openJSON('Leaderboard.json')

    l = PrettyTable()
    l.field_names = ['Team', 'WAR', 'wRC+', 'OPS', 'ISO', 'FIP', 'K9', 'AvgAge']

    sortColumn = 'WAR'

    for i in args:
        if i in l.field_names:
            sortColumn = i

    sortedL = sortListBy(leaderboard, sortColumn)

    print(sortedL)

    l = createPrettyTable(sortedL, l, leaderboard)

    leaders = '''Daily Leaderboard:\n```%s
           ```
           ''' % (l)
    await ctx.send(leaders)


@bot.command(name="refresh", brief="Scrapes ESPN for any new roster changes.")
# This one is messy, dont bother tweaking the time.sleep, its just the way she goes
async def refreshLeague(ctx):

    League = openJSON('League.json')

    delinquents = []
    await ctx.channel.send('Refreshing, please dont run any commands...')
    for z in League:
        url = 'https://fantasy.espn.com/baseball/team?leagueId='+str(usermap['leagueID'])+'&teamId=' + \
            str(usermap[str(z)])
        driver.get(url)
        # dashboard = WebDriverWait(
        #     driver, 10).until(
        #     EC.presence_of_element_located(
        #         (By.CLASS_NAME, 'layout.is-full')))

        print(url)
        time.sleep(1.5)
        players = driver.find_elements(By.CLASS_NAME, 'Table__TBODY')
        time.sleep(0.2)
        count = -1
        roster = {}
        for i in players:
            # print(i)
            count += 1
            if count % 2 > 0:
                continue
            player = i.find_elements(By.CLASS_NAME, 'Table__TR')
            time.sleep(0.2)
            for j in player:
                info = j.find_elements(By.CLASS_NAME, 'Table__TD')
                time.sleep(0.2)
                position = info[0].find_element(
                    By.TAG_NAME, 'div').get_attribute('title')
                name = info[1].find_element(
                    By.TAG_NAME, 'div').get_attribute('title')
                try:
                    if (position == 'Injured List') and (name == 'Player'):
                        team = 'None'
                        continue
                    else:
                        team = info[1].find_element(By.TAG_NAME, 'div').get_attribute(
                            'aria-label').split(' for ')[1].strip()
                    #print((position, name, team))
                    roster[str(name)] = {'position': position, 'team': team}
                except BaseException:
                    # print('Nonetype')  # player stats
                    continue
        oldteam = League[z]
        additions = {}
        subtractions = {}
        positionchange = {}
        #newteam = {}
        for y in roster:
            pname = y
            ppos = roster[y]['position']

            try:
                opos = oldteam[pname]['position']
            except BaseException:
                opos = ''

            #print((pdata, qdata))
            if ppos == opos:  # no change
                del oldteam[pname]
                continue
            else:
                if len(opos) < 1:
                    # player added
                    additions[pname] = roster[pname]
                else:
                    # player position change
                    if (opos == 'Prospect') and (ppos == 'Bench'):
                        roster[pname]['position'] = 'Prospect'
                    elif (opos == 'Prospect'):  # declared prospect in an undeclared slot
                        # user = discord.utils.get(ctx.server.members,
                        # name=z.split('#')[0], discriminator=z.split('#')[1])
                        await ctx.channel.send(f"BEEP BEEP: {pname} is declared a prospect but is on @{z} \'s active roster", allowed_mentions=allowed_mentions)
                        delinquents.append('@' + z)
                        roster[pname]['position'] = 'Prospect'
                    else:
                        positionchange[pname] = roster[pname]
                    del oldteam[pname]

        for t in oldteam:  # subtractions
            subtractions[t] = oldteam[t]

        add = '%s: Additions: %s' % (z, additions)
        sub = '%s: Subtractions: %s' % (z, subtractions)
        change = '%s: Position Changes: %s' % (z, len(positionchange))
        print(add)
        print(sub)
        print(change)
        if (len(additions) > 0) and (len(additions) < 30):
            await ctx.channel.send(add)
        if len(additions) > 30:
            League[z] = roster
            break
        if (len(subtractions) > 0) and (len(subtractions) < 30):
            await ctx.channel.send(sub)
        if len(subtractions) > 30:
            break
        if len(positionchange) > 0:
            await ctx.channel.send(change)

        League[z] = roster

    if len(subtractions) < 30:
        writeJSON('League.json', League)
    else:
        await ctx.channel.send('ERROR: scraped too quickly, please re-run the command (sorry)')

    if len(delinquents) > 0:
        await ctx.channel.send(f'@everyone Please fix your rosters: {", ".join(delinquents)}', allowed_mentions=allowed_mentions)

    writeJSON('Leaderboard.json', {})

    await ctx.channel.send('All Rosters Updated, Thanks!')


@bot.command(name="declare",
             brief="Adds a player to your 8 man prospect pool.")
async def declareProspect(ctx, *, args=None):

    mlb_links = openJSON('MLB.json')
    League = openJSON('League.json')

    input_player = f'{args}'
    author = str(ctx.message.author)

    author_team = League[author]

    for player_name in author_team:
        if player_name.lower() == input_player.lower():
            await ctx.channel.send('Adding player...')

            mlb_links = updateURL(driver, mlb_links, player_name)
            level = checkLevel(driver)

            if level == "MLB":
                if player_name not in mlb_links:
                    mlb_links[player_name] = {}

                await ctx.channel.send('%s is already in the Bigs, dumbass' % (player_name))
            else:
                position = 'Prospect'
                League[author][player_name]['position'] = position
                await ctx.channel.send('%s declared as prospect' % (player_name))
            break
    else:
        await ctx.channel.send('scratch your ass %s' % (author))

    writeJSON('MLB.json', mlb_links)
    writeJSON('League.json', League)


@bot.command(name="promote",
             brief="Promotes a man to your 27 man active roster.")
async def promoteProspect(ctx, *, args=None):

    League = openJSON('League.json')

    input_player = f'{args}'
    author = str(ctx.message.author)

    author_team = League[author]

    for player_name in author_team:
        if player_name.lower() == input_player.lower():
            position = 'Bench'
            League[str(author)][player_name]['position'] = position
            await ctx.channel.send('%s promoted to the bigs!' % (player_name))
            break
    else:
        await ctx.channel.send('scratch your ass %s' % (author))

    writeJSON('League.json', League)


@bot.command(name="farm", brief="displays your current prospect pool.")
async def showProspects(ctx):

    League = openJSON('League.json')

    author = str(ctx.message.author)
    team = League[author]

    temp = []
    for player_name in team:
        player_position = team[player_name]['position']
        player_team = team[player_name]['team']
        if player_position == 'Prospect':
            entry = '**' + str(player_name) + '**: ' + \
                str(player_position) + ', ' + str(player_team)
            temp.append(entry)

    quote_text = author + \
        '\'s Prospects: \n>>> {}'.format('\n'.join(temp))
    await ctx.channel.send(quote_text)


@bot.command(name="police", brief="Checks for owners with delinquent rosters.")
async def checkRosters(ctx):

    League = openJSON('League.json')

    delinquent_owners = []
    for owner in League:
        owner_team = League[owner]
        prospect_count = 0
        active_count = 0
        for player_name in owner_team:
            player_position = owner_team[player_name]['position']
            if player_position == 'Prospect':
                prospect_count += 1
            elif player_position != 'Injured List':
                pass
            else:
                active_count += 1
        if prospect_count > 10:
            delinquent_owners.append(
                '__' +
                str(owner) +
                '__: Too many prospects: %d' %
                prospect_count)
        if active_count > 27:
            delinquent_owners.append(
                '__' +
                str(owner) +
                '__: Too many active roster: %d' %
                active_count)

    quote_text = 'Delinquent Owners: \n>>> {}'.format(
        '\n'.join(delinquent_owners))
    await ctx.channel.send(quote_text)


@bot.event
async def on_ready():
    guild_count = 0

    for guild in bot.guilds:
        # PRINT THE SERVER'S ID AND NAME.
        print(f"- {guild.id} (name: {guild.name})")

        # INCREMENTS THE GUILD COUNTER.
        guild_count = guild_count + 1

        # PRINTS HOW MANY GUILDS / SERVERS THE BOT IS IN.
    print("SampleDiscordBot is in " + str(guild_count) + " guilds.")


if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
