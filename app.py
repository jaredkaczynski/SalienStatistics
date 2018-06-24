from flask import Flask
from flask import render_template
from time import time
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

import collections as ct
import dill as pickle

import glob
import requests
import json
import atexit

 
app = Flask(__name__)

class DataObject:
    def __init__(self):
        self.planet_names = dict()
        self.planet_stats = ct.defaultdict(list)
        self.dts = []
        self.colors = dict()
        #cmap(np.linspace(0, 1, 5))
class PlanetData():
    def __init__(self,capture_progress,current_players):
        self.capture_progress = capture_progress
        self.current_players = current_players
    
#hold lists of completion % of planets
planet_data = None

def datetime_range(start, end, delta):
    current = start
    while current < end:
        yield current
        current += delta 

def load_from_web():
    response = requests.get("https://community.steam-api.com/ITerritoryControlMinigameService/GetPlanets/v0001/?active_only=1&language=english")
    parse_json(response.content)
        
def load_from_files():
    path = 'logger/PlanetData1*.txt'
    files=glob.glob(path)
    for file in sorted(files):
        #print(file)
        with open(file, 'r', encoding='utf-8') as f:
            parse_json(f.read())
def get_longest_list():
    global planet_data
    try:
        d = planet_data.planet_stats
        max_key, max_value = max(d.items(), key = lambda x: len(set(x[1])))
        longest_list = len(max_value)
        return longest_list
    except ValueError:
        print("First Run no List Length")    
        return 0
def parse_json(response):
    global planet_data

    #store into planet_data_object
    longest_list = get_longest_list()
    planet_json = None
    #print(longest_list)
    #print(type(planet_data.planet_stats['2']))
    try:
        planet_json = json.loads(response)
    except:
        pass
    try:
        #print(planet_json)
        for planet in planet_json['response']['planets']: 
            temp_list = planet_data.planet_stats[planet['id']]
            #new planet, needs nulls at the beginning
            if(planet['id'] not in planet_data.planet_names):
                print("New Planet " + planet['id'])
                planet_data.planet_names[planet['id']] = planet['state']['name']
                #prepend nulls to list of data
                for i in range(0,int(longest_list)):
                    #print("Filling nulls")
                    temp_list.append(PlanetData('null','null')) 
            #if it's already got to 100% don't log it
            if(temp_list and (temp_list[-1].capture_progress == '1' or (temp_list[-1].capture_progress == 'null' and temp_list[-2].capture_progress != 'null'))):
                pass
            else:
                temp_list.append(PlanetData(planet['state']['capture_progress'],planet['state']['current_players']))
    except:
        pass 
    #If the planet is finished, set the end to null
    longest_list = get_longest_list()
    for planet_id,planet_stats in planet_data.planet_stats.items():
        if(len(planet_stats)<longest_list and planet_stats[-1].capture_progress != "null" and float(planet_stats[-1].capture_progress) > .98):
            planet_stats.append(PlanetData('null','null'))

def update_time_scale():
    global planet_data
    #get new labels for time axis
    #Y M D H M
    #dts = [dt.strftime('%Y-%m-%d T%H:%M Z') for dt in
    dts = [dt.strftime('%d T%H:%M') for dt in  
       datetime_range(datetime(2018, 6, 22, 4, 5), datetime.now(), 
       timedelta(minutes=20))]  
    planet_data.dts = dts
    #save the data to file
 
def update_colors():
    global planet_data
    colors = ["#540D6E","#EE4266","#FFD23F","#72ff77","#1F271B"]
    for planet_id,planet_stats in planet_data.planet_stats.items():
        print("Planet Stats Coloring: " + str(planet_stats[-1]))
        if(planet_stats[-1].capture_progress != "null" and float(planet_stats[-1].capture_progress) > 0 and float(planet_stats[-1].capture_progress) < 1):
            print("set active color " + planet_id)
            planet_data.colors[planet_id] = colors.pop()
        else:
            planet_data.colors[planet_id] = "rgba(192,192,192,1)"
    #print(planet_data.planet_stats)
    #print(planet_data.planet_stats['6'])
def update_data():
    global planet_data
    del(planet_data)
    planet_data = loadData()
    load_from_files()
    update_time_scale()
    update_colors()

    
@app.route("/planet_charts")
def chart():
    legend = 'Capture Data'
    #if it needs to update the data
    return render_template('chart.html', legend=legend,planet_names=planet_data.planet_names,planet_data=planet_data)
 
@app.route("/player_charts")
def chart2():
    legend = 'Player Data'
    #if it needs to update the data
    return render_template('chart_players.html', legend=legend,planet_names=planet_data.planet_names,planet_data=planet_data)
 
def setup_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.start()
    scheduler.add_job(
        func=update_data,
        trigger=IntervalTrigger(minutes=5),
        id='Data Update Job',
        name='Get new chart data every 5 minutes',
        replace_existing=True)
#if __name__ == "__main__":
#    app.run(debug=True)
def loadData():
    try:
        return pickle.load(open("stats.pickle", "rb"))
    except FileNotFoundError:
        return DataObject()
def saveData(object):
    pickle.dump(object, open("stats.pickle", "wb"))
    
def exit_handler():
    global planet_data
    lambda: scheduler.shutdown()
    #saveData(planet_data)
def main():
    global planet_data
    atexit.register(exit_handler)
    planet_data = loadData()
    #check pickle data
    #print(loadData().planet_stats)
    setup_scheduler()
    update_data()
    app.run(host="0.0.0.0",port=8001)
main()

# Shut down the scheduler when exiting the app
