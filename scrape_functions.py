import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


def updateURL(driver, playerDict, playerName, SOURCE='Fangraphs',
              HREF="https://www.fangraphs.com/players/"):
    try:
        url = playerDict[playerName]['link']
        driver.get(url)
    except BaseException:
        try:
            del playerDict[playerName]
            print('link is old, refreshing...')
        except BaseException:
            print('Adding New Player...')
    if playerName not in playerDict:
        time.sleep(0.2)
        url = 'https://www.google.com'
        driver.get(url)

        time.sleep(0.2)
        name = SOURCE + ' ' + playerName
        print(name)
        e = driver.find_element(By.NAME, 'q')
        e.send_keys(name)
        e.send_keys(Keys.ENTER)
        time.sleep(0.2)
        f = driver.find_elements(By.TAG_NAME, 'a')
        for j in f:
            posslink = j.get_attribute('href')
            if posslink is None:
                continue
            href = HREF
            if href == posslink[:len(href)]:
                j.click()
                time.sleep(0.1)
                link = posslink  # save this in lookup table
                break
        playerDict[playerName] = {'link': link}
        # scrape
        time.sleep(0.1)

    return playerDict


def getOffensiveFV(scouting_report):
    hit_rating = scouting_report[0].text.split(' / ')
    hit_rating = (int(hit_rating[0]) + int(hit_rating[1])) / 2
    game_power = scouting_report[1].text.split(' / ')
    game_power = (int(game_power[0]) + int(game_power[1])) / 2
    raw_power = scouting_report[2].text.split(' / ')
    raw_power = (int(raw_power[0]) + int(raw_power[1])) / 2
    speed_rating = scouting_report[3].text.split(' / ')
    speed_rating = (int(speed_rating[0]) + int(speed_rating[1])) / 2

    if speed_rating > 60:
        speed_rating = 60

    offensive_FV = (hit_rating + game_power + raw_power + speed_rating) / 4
    return offensive_FV


def getPerformanceScore(performance_metrics, level_ref, year):

    total_pa = 0
    numerator = 0
    for b in performance_metrics:
        # print(b.get_attribute('innerHTML'))
        statistics = b.find_elements(By.TAG_NAME, 'td')
        if year != 'All':
            season = statistics[0].find_element(By.TAG_NAME, 'a')
            season = season.text
            if year == season:
                pass
            else:
                continue
        level = statistics[2].text
        if level in level_ref:
            level = level_ref[level]
        else:
            level = 1
        age = int(statistics[3].text)
        plate_appearances = int(statistics[5].text)
        wrcplus = int(statistics[21].text)
        total_pa += plate_appearances
        numerator += ((level * plate_appearances * wrcplus) / age)
    try:
        performance_score = numerator / total_pa
    except BaseException:
        performance_score = 0

    return performance_score


def checkLevel(driver):

    pl = driver.find_element(
        By.CLASS_NAME, 'player-info-box-name-team')

    level = pl.text
    items = level.split(' ')
    minors = items[-1]
    if (minors[0] == '(') and (minors[-1] == ')'):
        level = minors[1:-1]
    else:
        level = 'MLB'
    return level
