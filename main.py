import discord
from discord.ext import commands
from datetime import date
import time
import json
import schedule
import os
import sys
from dotenv import load_dotenv, find_dotenv
from prettytable import PrettyTable

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

bot = commands.Bot(command_prefix="$")
allowed_mentions = discord.AllowedMentions(everyone=True)

WINDOW_SIZE = "1920,1080"
PROFILE = "XXX"  # path to google chrome user profile (so ESPN passwords are saved)

options = webdriver.ChromeOptions()
#options.add_argument('headless')
#options.add_argument('disable-gpu')
#options.add_argument('--window-size=%s' % WINDOW_SIZE)
options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36')
options.add_argument('--disable-dev-shm-usage')
options.add_experimental_option("useAutomationExtension", False)
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_argument("user-data-dir=%s" % PROFILE)
driver = webdriver.Chrome("chromedriver", chrome_options=options)

usermap = {
  "discordUser#1234": 1,
  "discordUser1#5678": 2
}  # map discord usernames to ESPN Team IDs (found in the URL)

def scrape_all_rosters():

    leagueId = 00000
  
    with open('League.json') as inf:
        league = json.load(inf)
    inf.close()
  
    for z in league:
        url = 'https://fantasy.espn.com/baseball/team?leagueId='+leagueId+'&teamId='+str(usermap[str(z)])
        driver.get(url)

        print(url)
        time.sleep(1)
        players = driver.find_elements(By.CLASS_NAME, 'Table__TBODY')
        count = 0
        roster = []
        for i in players:
            #print(i)
            if count%2 > 0:
                continue
            player = i.find_elements(By.CLASS_NAME, 'Table__TR')
            for j in player:
                # print(cell)
                info = j.find_elements(By.CLASS_NAME, 'Table__TD')
                position = info[0].find_element(By.TAG_NAME, 'div').get_attribute('title')
                name = info[1].find_element(By.TAG_NAME, 'div').get_attribute('title')
                try:
                    if (position == 'Injured List') and (name == 'Player'):
                        team = 'None'
                        continue
                    else:
                        team = info[1].find_element(By.TAG_NAME, 'div').get_attribute('aria-label').split(' for ')[1].strip()
                    print((position, name, team))
                    roster.append('%s: %s, %s' % (name, position, team))
                except:
                    print('Nonetype')  # player stats
                    continue
        league[z] = roster
    print(league)
    with open('League.json', 'w') as outfile:
        json.dump(league, outfile)
    outfile.close()

@bot.command(name="myroster", brief="Prints out your current roster.")
async def myroster(ctx):
    with open('League.json') as league_file:
        data = json.load(league_file)
        League = data

        embed = discord.Embed(
            title=str(ctx.message.author)+'\'s Team:',
            url = 'https://fantasy.espn.com/baseball/team?leagueId=51729&teamId='+str(usermap[str(ctx.message.author)]),
            #description="blah",
            color=discord.Color.red()
        )
        team = League[str(ctx.message.author)]
        response_string = ''
        hitters = ''
        pitchers = ''
        rps = ''
        prosp = ''
        bench = ''
        il = ''
        for i in team:
            #response_string += i + ': **' + team[i]['position'] + '**, ' + team[i]['team'] + '\n'
            if team[i]['position'] == 'Starting Pitcher':
                pitchers += '**'+i+'**: '+team[i]['position']+', *'+team[i]['team']+'*\n'
            elif team[i]['position'] == 'Relief Pitcher':
                rps += '**'+i+'**: '+team[i]['position']+', *'+team[i]['team']+'*\n'
            elif team[i]['position'] == 'Prospect':
                prosp += '**'+i+'**: '+team[i]['position']+', *'+team[i]['team']+'*\n'
            elif team[i]['position'] == 'Bench':
                bench += '**'+i+'**: '+team[i]['position']+', *'+team[i]['team']+'*\n'
            elif team[i]['position'] == 'Injured List':
                il += '**'+i+'**: '+team[i]['position']+', *'+team[i]['team']+'*\n'
            else:
                hitters += '**'+i+'**: '+team[i]['position']+', *'+team[i]['team']+'*\n'

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

        #quote_text = str(ctx.message.author) + ':\n>>> {}'.format(response_string)
        await ctx.channel.send(embed=embed)
    league_file.close()

@bot.command(name="scout", brief="Scouting report for Farm.")
async def farmStats(ctx, *args):
#def farmStats():
    with open('League.json') as inf:
        league = json.load(inf)
    inf.close()

    with open('MiLB.json') as inf:
        player_stats = json.load(inf)
    inf.close()

    author = str(ctx.message.author)

    #url = 'https://www.google.com'
    #driver.get(url)
    for i in league[author]:
        if league[author][i]['position'] == 'Prospect':
            try:
                url = player_stats[i]['link']
                driver.get(url)
            except:
                try:
                    del player_stats[i]
                    print('link is old, refreshing...')
                except:
                    print('Adding New Player...')
            if i not in player_stats:
                url = 'https://www.google.com'
                driver.get(url)

                time.sleep(0.1)
                name = 'MiLB '+i
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
                    href="https://www.milb.com/player/"
                    if href == posslink[:28]:
                        j.click()
                        time.sleep(0.1)
                        link = posslink  # save this in lookup table
                        break
                player_stats[i] = {'link': link}
                # scrape
                time.sleep(0.1)

            pl = driver.find_element(By.CLASS_NAME, 'player-header--vitals')
            try:
                level = pl.find_element(By.CLASS_NAME, 'header__info-bar').text
                ismajor = False
            except:
                level = pl.find_element(By.CLASS_NAME, 'player-header--vitals-currentTeam-name').find_element(By.TAG_NAME, 'span').text
                ismajor = True
            position = pl.find_element(By.XPATH, '//div/ul/li[1]').text
            age = pl.find_element(By.XPATH, '//div/ul/li[4]').text
            player_stats[i]['position'] = position
            player_stats[i]['level'] = level
            player_stats[i]['ismajor'] = ismajor
            player_stats[i]['age'] = age

            dashboard = driver.find_element(By.CLASS_NAME, 'player-stats-summary-large')
            dashboard = dashboard.find_element(By.CLASS_NAME, 'responsive-datatable__scrollable')
            dashboard = dashboard.find_element(By.TAG_NAME, 'tbody')
            dashboard = dashboard.find_elements(By.TAG_NAME, 'tr')
            thisyear = dashboard[0].find_elements(By.TAG_NAME, 'td')
            try:
                mcareer = dashboard[1].find_elements(By.TAG_NAME, 'td')
            except:
                mcareer = ''
                print('no season stats')
            try:
                mlbcareer = dashboard[2].find_elements(By.TAG_NAME, 'td')
            except:
                mlbcareer = ''
                print('no mlb stats')
            try:
                fourcareer = dashboard[3].find_elements(By.TAG_NAME, 'td')
            except:
                fourcareer = ''
                print('no 4th stats')
            #print(thisyear.get_attribute('innerHTML'))

            if position == 'P':
                x = PrettyTable()
                x.field_names = ['Year', 'W', 'L', 'ERA', 'G', 'GS', 'SV', 'IP', 'SO', 'WHIP']
                temprow = []
                for j in thisyear:
                    statd = j.find_element(By.TAG_NAME, 'span').text
                    temprow.append(str(statd))
                x.add_row(temprow)
                temprow = []
                for k in mcareer:
                    statd = k.find_element(By.TAG_NAME, 'span').text
                    temprow.append(str(statd))
                if len(temprow) > 1:
                    x.add_row(temprow)
                temprow = []
                for l in mlbcareer:
                    statd = l.find_element(By.TAG_NAME, 'span').text
                    temprow.append(str(statd))
                if len(temprow) > 1:
                    x.add_row(temprow)
                temprow = []
                for m in fourcareer:
                    statd = m.find_element(By.TAG_NAME, 'span').text
                    temprow.append(str(statd))
                if len(temprow) > 1:
                    x.add_row(temprow)
                pitchers = '''%s, %s: %s\n```%s
                        ```
                        ''' % (i, position, level, x)
                print(pitchers)
                await ctx.send(pitchers)
            else:
                x = PrettyTable()
                x.field_names = ['Year', 'AB', 'R', 'H', 'HR', 'RBI', 'SB', 'AVG', 'OBP', 'OPS']
                temprow = []
                for j in thisyear:
                    statd = j.find_element(By.TAG_NAME, 'span').text
                    temprow.append(str(statd))
                x.add_row(temprow)
                temprow = []
                for k in mcareer:
                    statd = k.find_element(By.TAG_NAME, 'span').text
                    temprow.append(str(statd))
                if len(temprow) > 1:
                    x.add_row(temprow)
                temprow = []
                for l in mlbcareer:
                    statd = l.find_element(By.TAG_NAME, 'span').text
                    temprow.append(str(statd))
                if len(temprow) > 1:
                    x.add_row(temprow)
                temprow = []
                for m in fourcareer:
                    statd = m.find_element(By.TAG_NAME, 'span').text
                    temprow.append(str(statd))
                if len(temprow) > 1:
                    x.add_row(temprow)
                hitters = '''%s, %s (%s): %s\n```%s
                    ```
                    ''' % (i, position, age, level, x)
                print(hitters)
                await ctx.send(hitters)

    with open('MiLB.json', 'w') as outf:
        json.dump(player_stats,outf)
    outf.close()

@bot.command(name="stats", brief='Team stats for the season.')
async def teamStats(ctx):
#def teamStats():
    await ctx.channel.send('Please wait (~2min)...')
    with open('League.json', 'r') as inf:
        League = json.load(inf)
    inf.close()

    with open('MLB.json', 'r') as inf:
        stats = json.load(inf)
    inf.close()

    with open('MiLB.json', 'r') as inf:
        milb_stats = json.load(inf)
    inf.close()

    with open('Leaderboard.json', 'r') as inf:
        leaders = json.load(inf)
    inf.close()

    author = str(ctx.message.author)

    # embed = discord.Embed(
    #     title=str(ctx.message.author)+'\'s Team:',
    #     url = 'https://fantasy.espn.com/baseball/team?leagueId=51729&teamId='+str(usermap[str(ctx.message.author)]),
    #     #description="blah",
    #     color=discord.Color.red()
    # )

    activeplayers = 0

    pitching = {
    'W': 0,
    'L': 0,
    'ERA': 0.0,  # 9 x earned runs allowed / IP
    'G': 0,
    'GS': 0,
    'SV': 0,
    'IP': 0,
    'SO': 0,
    'WHIP': 0  # (n hits allowed + n walks allowed) / IP
    }

    hitting = {
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

    avg_age = 0
    activeroster = 0
    war = 0.0
    for i in League[author]:
        if League[author][i]['position'] == 'Prospect':
            try:
                url = milb_stats[i]['link']
                driver.get(url)
            except:
                try:
                    del milb_stats[i]
                    print('link is old, refreshing...')
                except:
                    print('Adding New Player...')
            if i not in milb_stats:
                url = 'https://www.google.com'
                driver.get(url)

                time.sleep(0.1)
                name = 'MiLB '+i
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
                    href="https://www.milb.com/player/"
                    if href == posslink[:28]:
                        j.click()
                        time.sleep(0.1)
                        link = posslink  # save this in lookup table
                        break
                milb_stats[i] = {'link': link}
                # scrape
                time.sleep(0.1)

            #pl = driver.find_element(By.CLASS_NAME, 'player-header--vitals')
            pl = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'player-header--vitals')))
            try:
                level = pl.find_element(By.CLASS_NAME, 'header__info-bar').text
                ismajor = False
            except:
                level = pl.find_element(By.CLASS_NAME, 'player-header--vitals-currentTeam-name').find_element(By.TAG_NAME, 'span').text
                ismajor = True
            position = pl.find_element(By.XPATH, '//div/ul/li[1]').text
            age = pl.find_element(By.XPATH, '//div/ul/li[4]').text
            milb_stats[i]['position'] = position
            milb_stats[i]['level'] = level
            milb_stats[i]['ismajor'] = ismajor
            milb_stats[i]['age'] = age

            time.sleep(3)
            #dashboard = driver.find_element(By.ID, 'careerTable')
            dashboard = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'careerTable')))
            try:
                dashboard = dashboard.find_element(By.CLASS_NAME, 'responsive-datatable__scrollable')
            except:
                print('MiLB player has no stats, skipping')
                continue
            dashboard = dashboard.find_element(By.TAG_NAME, 'tbody')
            dashboard = dashboard.find_elements(By.TAG_NAME, 'tr')

            advanced = driver.find_element(By.ID, 'careerAdvancedTable')
            advanced = advanced.find_element(By.CLASS_NAME, 'responsive-datatable__scrollable')
            advanced = advanced.find_element(By.TAG_NAME, 'tbody')
            advanced = advanced.find_elements(By.TAG_NAME, 'tr')

            if position == 'P':
                for d in dashboard:
                    isyear = True
                    thisyear = d.find_elements(By.TAG_NAME, 'td')
                    temp_era = 0.0
                    temp_whip = 0.0
                    for j in range(len(thisyear)):
                        if isyear:
                            try:
                                statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            except:
                                continue
                            if statd == '2022':
                                isyear = False
                                continue
                            else:
                                break
                        if j == 4:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            pitching['W'] += int(statd)
                        if j == 5:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            pitching['L'] += int(statd)
                        if j == 6:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            #pitching['ERA'] += float(statd)
                            temp_era = float(statd)
                        if j == 7:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            pitching['G'] += int(statd)
                        if j == 8:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            pitching['GS'] += int(statd)
                        if j == 12:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            pitching['SV'] += int(statd)
                        if j == 14:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            ip = float(statd)
                            round_ip = int(ip)
                            fraction = (ip - round_ip) * 0.3333
                            temp_ip = round_ip + fraction
                            pitching['IP'] += float(temp_ip)
                        if j == 23:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            pitching['SO'] += int(statd)
                        if j == 25:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            #pitching['WHIP'] += float(statd)
                            temp_whip = float(statd)
                    if not isyear:
                        activeplayers +=1
                        pitching['ERA'] += temp_era * temp_ip
                        pitching['WHIP'] += temp_whip * temp_ip

            else:
                for d in dashboard:
                    isyear = True
                    thisyear = d.find_elements(By.TAG_NAME, 'td')
                    for j in range(len(thisyear)):
                        if isyear:
                            try:
                                statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            except:
                                continue
                            if statd == '2022':
                                isyear = False
                                continue
                            else:
                                break
                        if j == 5:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            hitting['AB'] += int(statd)
                        if j == 6:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            hitting['R'] += int(statd)
                        if j == 7:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            hitting['H'] += int(statd)
                        if j == 8:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            hitting['TB'] += int(statd)
                        if j == 9:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            hitting['doub'] += int(statd)
                        if j == 10:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            hitting['trip'] += int(statd)
                        if j == 11:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            hitting['HR'] += int(statd)
                        if j == 12:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            hitting['RBI'] += int(statd)
                        if j == 13:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            hitting['BB'] += int(statd)
                        if j == 14:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            hitting['IBB'] += int(statd)
                        if j == 15:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            hitting['SO'] += int(statd)
                        if j == 16:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            hitting['SB'] += int(statd)
                    if not isyear:
                        activeplayers +=1

                for a in advanced:
                    isyear = True
                    thisyear = a.find_elements(By.TAG_NAME, 'td')
                    for j in range(len(thisyear)):
                        if isyear:
                            try:
                                statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            except:
                                continue
                            if statd == '2022':
                                isyear = False
                                continue
                            else:
                                break
                        if j == 6:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            hitting['HBP'] += int(statd)
                        if j == 8:
                            statd = thisyear[j].find_element(By.TAG_NAME, 'span').text
                            hitting['SF'] += int(statd)


            print(hitting)
            print(activeplayers)
        elif League[author][i]['position'] == 'Injured List':
            print('Player Injured, Skipping...')
            continue
        else:  # major leaguers
            try:
                url = stats[i]['link']
                driver.get(url)
            except:
                try:
                    del stats[i]
                    print('link is old, refreshing...')
                except:
                    print('Adding New Player...')
            if i not in stats:
                url = 'https://www.google.com'
                driver.get(url)

                time.sleep(0.1)
                name = 'fangraphs '+i
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
                    href="https://www.fangraphs.com/players/"
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
            pl = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'player-info-box-header')))
            position = pl.find_element(By.CLASS_NAME, 'player-info-box-pos').text
            age = pl.find_elements(By.CLASS_NAME, 'player-info-box-item')[0].text
            stats[i]['position'] = position
            stats[i]['age'] = age
            avg_age += int(age.split(': ')[1])
            activeroster += 1

            try:
                dashboard = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'dashboard-skinny')))
            except:
                print(i)
                print('Player is not in the MLB yet, Skipping')
                continue
            table_scroll = dashboard.find_element(By.CLASS_NAME, 'table-scroll')
            tbody = table_scroll.find_element(By.TAG_NAME, 'tbody')
            try:
                mlb_season = tbody.find_element(By.CLASS_NAME, 'row-mlb-season')
            except:
                print(i)
                print('Player is not in the MLB yet, but also not a declared prospect. Skipping')
                continue
            rows = mlb_season.find_elements(By.TAG_NAME, 'td')
            if rows[0].text == '2022':
                war += float(rows[11].text)

            dashboard = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'standard')))
            table_scroll = dashboard.find_element(By.CLASS_NAME, 'table-scroll')
            mlb_season = table_scroll.find_elements(By.CLASS_NAME, 'row-mlb-season')

            for j in mlb_season:
                yr = j.find_elements(By.TAG_NAME, 'td')[0]
                yr = yr.find_element(By.TAG_NAME, 'a').text
                if yr == '2022':
                    thisseason = j
                    break
            else:
                print('Player hasnt played in 2022 yet, skipping')
                continue

            if position == 'P':
                cols = thisseason.find_elements(By.TAG_NAME, 'td')

                mlb_pitching['W'] += int(cols[3].get_attribute('innerHTML'))
                mlb_pitching['L'] += int(cols[4].get_attribute('innerHTML'))
                mlb_pitching['G'] += int(cols[6].get_attribute('innerHTML'))
                mlb_pitching['GS'] += int(cols[7].get_attribute('innerHTML'))
                mlb_pitching['SV'] += int(cols[10].get_attribute('innerHTML'))
                mlb_pitching['IP'] += (int(cols[13].get_attribute('innerHTML').split('.')[0]) + int(cols[13].get_attribute('innerHTML').split('.')[1])*0.333)
                mlb_pitching['SO'] += int(cols[24].get_attribute('innerHTML'))
                mlb_pitching['H'] += int(cols[15].get_attribute('innerHTML'))
                mlb_pitching['BB'] += int(cols[19].get_attribute('innerHTML'))
                mlb_pitching['ER'] += int(cols[17].get_attribute('innerHTML'))

            else:
                cols = thisseason.find_elements(By.TAG_NAME, 'td')

                mlb_hitting['AB'] += int(cols[4].get_attribute('innerHTML'))
                mlb_hitting['H'] += int(cols[6].get_attribute('innerHTML'))
                mlb_hitting['doub'] += int(cols[8].get_attribute('innerHTML'))
                mlb_hitting['trip'] += int(cols[9].get_attribute('innerHTML'))
                mlb_hitting['HR'] += int(cols[10].get_attribute('innerHTML'))
                mlb_hitting['R'] += int(cols[11].get_attribute('innerHTML'))
                mlb_hitting['RBI'] += int(cols[12].get_attribute('innerHTML'))
                mlb_hitting['BB'] += int(cols[13].get_attribute('innerHTML'))
                mlb_hitting['SO'] += int(cols[15].get_attribute('innerHTML'))
                mlb_hitting['HBP'] += int(cols[16].get_attribute('innerHTML'))
                mlb_hitting['SF'] += int(cols[17].get_attribute('innerHTML'))
                mlb_hitting['SB'] += int(cols[20].get_attribute('innerHTML'))


    try:
        avg = '%.3f' % (hitting['H'] / hitting['AB'])
        obp = '%.3f' % ((hitting['H'] + hitting['BB'] + hitting['HBP']) / (hitting['AB'] + hitting['BB'] + hitting['HBP'] + hitting['SF']))
        singles = hitting['H'] - hitting['doub'] - hitting['trip'] - hitting['HR']
        slg = '%.3f' % ((singles + 2*hitting['doub'] + 3*hitting['trip'] + 4*hitting['HR']) / hitting['AB'])
        ops = '%.3f' % (float(obp) + float(slg))
        hitting['AVG'] = avg
        hitting['OBP'] = obp
        hitting['SLG'] = slg
        hitting['OPS'] = ops
        print(hitting)
        x = PrettyTable()
        x.field_names = ['Year', 'AB', 'R', 'H', 'HR', 'RBI', 'SB', 'AVG', 'OBP', 'SLG', 'OPS']
        temprow = []
        for i in x.field_names:
            if i == 'Year':
                temprow.append('2022 MiLB')
            else:
                temprow.append(hitting[i])
        x.add_row(temprow)
        str_hitters = '''MiLB Hitting Team Stats:\n```%s
                        ```
                        ''' % (x)
        #embed.add_field(name='MiLB Hitting', value=x, inline=False)
        await ctx.send(str_hitters)
    except:
        print('no hitting prospects')

    try:
        pitching['ERA'] = '%.3f' % (pitching['ERA'] / pitching['IP'])
        pitching['WHIP'] = '%.3f' % (pitching['WHIP'] / pitching['IP'])
        print(pitching)
        y = PrettyTable()
        y.field_names = ['Year', 'W', 'L', 'ERA', 'G', 'GS', 'SV', 'IP', 'SO', 'WHIP']
        temprow = []
        for j in y.field_names:
            if j == 'Year':
                temprow.append('2022 MiLB')
            else:
                if j == 'IP':
                    temprow.append('%.1f' % pitching[j])
                else:
                    temprow.append(pitching[j])
        y.add_row(temprow)
        str_pitchers = '''MiLB Pitching Team Stats:\n```%s
                   ```
                   ''' % (y)
        await ctx.send(str_pitchers)
        #embed.add_field(name='MiLB Pitching', value=y, inline=False)
    except:
        print('No pitching prospects')

    # MLB stats
    avg = '%.3f' % (mlb_hitting['H'] / mlb_hitting['AB'])
    obp = '%.3f' % ((mlb_hitting['H'] + mlb_hitting['BB'] + mlb_hitting['HBP']) / (mlb_hitting['AB'] + mlb_hitting['BB'] + mlb_hitting['HBP'] + mlb_hitting['SF']))
    singles = mlb_hitting['H'] - mlb_hitting['doub'] - mlb_hitting['trip'] - mlb_hitting['HR']
    slg = '%.3f' % ((singles + 2*mlb_hitting['doub'] + 3*mlb_hitting['trip'] + 4*mlb_hitting['HR']) / mlb_hitting['AB'])
    ops = '%.3f' % (float(obp) + float(slg))
    mlb_hitting['AVG'] = avg
    mlb_hitting['OBP'] = obp
    mlb_hitting['SLG'] = slg
    mlb_hitting['OPS'] = ops
    print(mlb_hitting)
    x = PrettyTable()
    x.field_names = ['Year', 'AB', 'R', 'H', 'HR', 'RBI', 'SB', 'AVG', 'OBP', 'SLG', 'OPS']
    temprow = []
    for i in x.field_names:
        if i == 'Year':
            temprow.append('2022 MLB')
        else:
            temprow.append(mlb_hitting[i])
    x.add_row(temprow)
    str_hitters = '''MLB Hitting Team Stats:\n```%s
                    ```
                    ''' % (x)
    await ctx.send(str_hitters)
    #embed.add_field(name='MLB Hitting', value=x, inline=False)

    mlb_pitching['ERA'] = '%.3f' % ((9*mlb_pitching['ER']) / mlb_pitching['IP'])
    mlb_pitching['WHIP'] = '%.3f' % ((mlb_pitching['H'] + mlb_pitching['BB']) / mlb_pitching['IP'])
    mlb_pitching['K9'] = '%.3f' % ((9*mlb_pitching['SO']) / mlb_pitching['IP'])
    print(mlb_pitching)
    y = PrettyTable()
    y.field_names = ['Year', 'W', 'L', 'ERA', 'G', 'GS', 'SV', 'IP', 'SO', 'BB', 'WHIP', 'K9']
    temprow = []
    for j in y.field_names:
        if j == 'Year':
            temprow.append('2022 MLB')
        else:
            if j == 'IP':
                temprow.append('%.1f' % mlb_pitching[j])
            else:
                temprow.append(mlb_pitching[j])
    y.add_row(temprow)
    str_pitchers = '''MLB Pitching Team Stats:\n```%s
               ```
               ''' % (y)
    await ctx.send(str_pitchers)
    #embed.add_field(name='MLB Pitching', value=y, inline=False)

    #embed.add_field(name='Active Roster Average Age', value='%.2f' % (avg_age/activeroster), inline=False)
    #embed.add_field(name='Active Roster Team WAR', value='%.1f' % war, inline=False)

    #await ctx.send(embed=embed)
    await ctx.send('Active Roster Average Age: %.2f' % (avg_age/activeroster))
    await ctx.send('Active Roster Team WAR: %.1f' % war)

    leaders[author] = {}
    leaders[author]['AvgAge'] = '%.2f' % (avg_age/activeroster)
    leaders[author]['WAR'] = '%.1f' % war
    leaders[author]['OPS'] = mlb_hitting['OPS']
    leaders[author]['K9'] = mlb_pitching['K9']

    with open('Leaderboard.json', 'w') as outf:
        json.dump(leaders, outf)
    outf.close()

    with open('MLB.json', 'w') as outf:
        json.dump(stats, outf)
    outf.close()

    with open('MiLB.json', 'w') as outf:
        json.dump(milb_stats, outf)
    outf.close()

@bot.command(name="leaderboard", brief="Displays current leaderboard (run $stats to enter the leaderboard)")
async def leaderboard(ctx):

    author = str(ctx.message.author)

    with open('Leaderboard.json', 'r') as inf:
        leaderboard = json.load(inf)
    inf.close()

    l = PrettyTable()
    l.field_names = ['Team', 'WAR', 'OPS', 'K9', 'AvgAge']
    sortedL = []
    for i in leaderboard:
        for j in range(len(sortedL)):
            lWAR = float(leaderboard[i]['WAR'])
            sWAR = sortedL[j][1]

            if lWAR > sWAR:
                sortedL.insert(j, (i, lWAR))
                break
        else:
            sortedL.append((i, float(leaderboard[i]['WAR'])))

    print(sortedL)
    for i in sortedL:
        team = i[0]
        tstats = leaderboard[team]
        temprow = []
        for j in l.field_names:
            if j == 'Team':
                temprow.append(team)
            else:
                temprow.append(tstats[j])
        l.add_row(temprow)

    leaders = '''Daily Leaderboard:\n```%s
           ```
           ''' % (l)
    await ctx.send(leaders)


@bot.command(name="refresh", brief="Scrapes ESPN for any new roster changes.")
async def refreshLeague(ctx):  # if position is prospect and player has new position other than prospect, raise alert

    leagueId = 00000
  
    with open('League.json') as cacheteams:
        League = json.load(cacheteams)
    cacheteams.close()

    delinquents = []
    await ctx.channel.send('Refreshing, please dont run any commands...')
    for z in League:
        url = 'https://fantasy.espn.com/baseball/team?leagueId='+leagueId+'&teamId='+str(usermap[str(z)])
        driver.get(url)

        print(url)
        time.sleep(1.5)
        players = driver.find_elements(By.CLASS_NAME, 'Table__TBODY')
        time.sleep(0.1)
        count = -1
        roster = {}
        for i in players:
            #print(i)
            count+=1
            if count%2 > 0:
                continue
            player = i.find_elements(By.CLASS_NAME, 'Table__TR')
            time.sleep(0.1)
            for j in player:
                # print(cell)
                info = j.find_elements(By.CLASS_NAME, 'Table__TD')
                position = info[0].find_element(By.TAG_NAME, 'div').get_attribute('title')
                name = info[1].find_element(By.TAG_NAME, 'div').get_attribute('title')
                try:
                    if (position == 'Injured List') and (name == 'Player'):
                        team = 'None'
                        continue
                    else:
                        team = info[1].find_element(By.TAG_NAME, 'div').get_attribute('aria-label').split(' for ')[1].strip()
                    #print((position, name, team))
                    roster[str(name)] = {'position': position, 'team': team}
                except:
                    #print('Nonetype')  # player stats
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
            except:
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
                        #user = discord.utils.get(ctx.server.members, name=z.split('#')[0], discriminator=z.split('#')[1])
                        await ctx.channel.send(f"BEEP BEEP: {pname} is declared a prospect but is on @{z} \'s active roster", allowed_mentions=allowed_mentions)
                        delinquents.append('@'+z)
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
        with open('League.json', 'w') as outfile:
            json.dump(League, outfile)
        outfile.close()
    else:
        await ctx.channel.send('ERROR: scraped too quickly, please re-run the command (sorry)')
    if len(delinquents) > 0:
        await ctx.channel.send(f'@everyone Please fix your rosters: {", ".join(delinquents)}', allowed_mentions=allowed_mentions)

    with open('Leaderboard.json', 'w') as outfile:
        json.dump({}, outfile)
    outfile.close()
    await ctx.channel.send('All Rosters Updated, Thanks!')

@bot.command(name="declare", brief="Adds a player to your 8 man prospect pool.")
async def declareProspect(ctx, *, args=None):

    with open('MiLB.json') as milbplayers:
        player_stats = json.load(milbplayers)
    milbplayers.close()

    with open('MLB.json') as inf:
        mlb_stats = json.load(inf)
    inf.close()

    with open('League.json') as league_file:
        data = json.load(league_file)
        League = data

        input_player = f'{args}'
        author = ctx.message.author

        team = League[str(author)]

        playerprospect = ''
        for i in team:
            playername = i
            if playername.lower() == input_player.lower():
                await ctx.channel.send('Adding player...')
                try:
                    url = player_stats[i]['link']
                    driver.get(url)
                except:
                    try:
                        del player_stats[i]
                        print('link is old, refreshing...')
                    except:
                        print('Adding New Player...')
                if i not in player_stats:
                    url = 'https://www.google.com'
                    driver.get(url)

                    time.sleep(0.1)
                    name = 'MiLB '+i
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
                        href="https://www.milb.com/player/"
                        if href == posslink[:28]:
                            j.click()
                            time.sleep(0.1)
                            link = posslink  # save this in lookup table
                            break
                    player_stats[i] = {'link': link}
                    # scrape
                    time.sleep(0.1)

                pl = driver.find_element(By.CLASS_NAME, 'player-header--vitals')
                try:
                    level = pl.find_element(By.CLASS_NAME, 'header__info-bar').text
                    ismajor = False
                except:
                    if i not in mlb_stats:
                        mlb_stats[i] = {}
                    level = pl.find_element(By.CLASS_NAME, 'player-header--vitals-currentTeam-name').find_element(By.TAG_NAME, 'span').text
                    ismajor = True
                    position = pl.find_element(By.XPATH, '//div/ul/li[1]').text
                    age = pl.find_element(By.XPATH, '//div/ul/li[4]').text
                    mlb_stats[i]['link'] = link
                    mlb_stats[i]['level'] = level
                    mlb_stats[i]['ismajor'] = ismajor
                    mlb_stats[i]['position'] = position
                    mlb_stats[i]['age'] = age
                    with open('MLB.json', 'w') as outf:
                        json.dump(mlb_stats,outf)
                    outf.close()
                    await ctx.channel.send('%s is already in the Bigs, dumbass' % (i))
                    playerprospect = ''
                    break
                position = pl.find_element(By.XPATH, '//div/ul/li[1]').text
                age = pl.find_element(By.XPATH, '//div/ul/li[4]').text
                player_stats[i]['position'] = position
                player_stats[i]['level'] = level
                player_stats[i]['ismajor'] = ismajor
                player_stats[i]['age'] = age

                position = 'Prospect'
                playerprospect = playername
                League[str(author)][i]['position'] = position

                with open('MiLB.json', 'w') as outf:
                    json.dump(player_stats,outf)
                outf.close()

    league_file.close()

    with open('League.json', 'w') as outfile:
        json.dump(League, outfile)
    if len(playerprospect) <= 1:
        await ctx.channel.send('scratch your ass %s' % (author))
    else:
        await ctx.channel.send('%s declared as prospect' % (playerprospect))
    outfile.close()

@bot.command(name="promote", brief="Promotes a man to your 27 man active roster.")
async def promoteProspect(ctx, *, args=None):
    with open('League.json') as league_file:
        data = json.load(league_file)
        League = data

        input_player = f'{args}'
        author = ctx.message.author

        team = League[str(author)]

        playerprospect = ''
        for i in team:
            playername = i
            if playername.lower() == input_player.lower():
                position = 'Bench'
                playerprospect = playername
                League[str(author)][i]['position'] = position

    league_file.close()
    with open('League.json', 'w') as outfile:
        json.dump(League, outfile)
    if len(playerprospect) <= 1:
        await ctx.channel.send('scratch your ass %s' % (author))
    else:
        await ctx.channel.send('%s promoted to the bigs!' % (playerprospect))
    outfile.close()

@bot.command(name="farm", brief="displays your current prospect pool.")
async def showProspects(ctx):
    with open('League.json') as league_file:
        data = json.load(league_file)
        League = data

        author = ctx.message.author
        team = League[str(author)]

        temp = []
        for i in team:
            playername = i
            position = team[i]['position']
            playerteam = team[i]['team']
            if position == 'Prospect':
                entry = '**'+str(playername)+'**: '+str(position)+', '+str(playerteam)
                temp.append(entry)

    league_file.close()
    quote_text = str(author)+'\'s Prospects: \n>>> {}'.format('\n'.join(temp))
    await ctx.channel.send(quote_text)

@bot.command(name="police", brief="Checks for owners with delinquent rosters.")
async def checkRosters(ctx):
    with open('League.json') as league_file:
        data = json.load(league_file)
        League = data

        delinquent_owners = []
        for z in League:
            owner = z
            team = League[z]
            prospectcount=0
            activecount=0
            for i in team:
                position = team[i]['position']
                if position == 'Prospect':
                    prospectcount+=1
                elif position != 'Injured List':
                    activecount+=1
                else:
                    pass
            if prospectcount > 8:
                delinquent_owners.append('__'+str(owner)+'__: Too many prospects: %d' % prospectcount)
            if activecount > 27:
                delinquent_owners.append('__'+str(owner)+'__: Too many active roster: %d' % activecount)

    league_file.close()
    quote_text = 'Delinquent Owners: \n>>> {}'.format('\n'.join(delinquent_owners))
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

# @bot.event
# async def on_message(message):
#     words = message.content.lower().split(' ')
#     if "degrom" in words:
#         await message.channel.send("de:goat:")


if __name__ == '__main__':
    # load_dotenv(sys.path[1])
    # DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

    DISCORD_TOKEN = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
    bot.run(DISCORD_TOKEN)
