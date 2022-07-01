import json


def openJSON(filename):
    with open(filename) as league_file:
        data = json.load(league_file)
    league_file.close()
    return data


def writeJSON(filename, data):
    with open(filename, 'w') as outfile:
        json.dump(data, outfile)
    outfile.close()
    return
