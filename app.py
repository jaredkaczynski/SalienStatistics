from flask import Flask
from flask import render_template
from time import time
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask_caching import Cache

import collections as ct
import dill as pickle

import spectra
import glob
import requests
import json
import atexit

 
app = Flask(__name__)
# For more configuration options, check out the documentation
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

class DataObject:
    def __init__(self):
        self.planet_names = dict()
        self.planet_stats = ct.defaultdict(list)
        self.dts = []
        self.colors = dict()
        self.top_clans = []
        #cmap(np.linspace(0, 1, 5))
class PlanetData():
    def __init__(self,capture_progress,current_players,top_clans):
        self.capture_progress = capture_progress
        self.current_players = current_players
        self.top_clans = top_clans
    
#hold lists of completion % of planets
planet_data = None

def datetime_range(start, end, delta):
    current = start
    while current < end:
        yield current
        current += delta 

def load_from_web():
    response = requests.get("https://community.steam-api.com/ITerritoryControlMinigameService/GetPlanets/v0001/&language=english")
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
    top_clans_global = {}
    #print(type(planet_data.planet_stats['2']))
    try:
        planet_json = json.loads(response)
    except:
        pass
    try:
    #print(planet_json)
        for planet in planet_json['response']['planets']: 
            temp_list = planet_data.planet_stats[planet['id']]
            top_clans_local = []
            #new planet, needs nulls at the beginning
            if(planet['id'] not in planet_data.planet_names):
                print("New Planet " + planet['id'])
                planet_data.planet_names[planet['id']] = planet['state']['name']
                #prepend nulls to list of data
                for i in range(0,int(longest_list)):
                    #print("Filling nulls")
                    temp_list.append(PlanetData('null','null', []))
            #local append
            #print(planet)
            #for clan in planet['top_clans']:
            #    top_clans_local.append(clan)
            #print("test2")
            #print(type(planet.top_clans))
            #planet.top_clans.append(top_clans)

            #if it's already got to 100% don't log it
            if(temp_list and (temp_list[-1].capture_progress == '1' or (temp_list[-1].capture_progress == 'null' and temp_list[-2].capture_progress != 'null'))):
                pass
            else:
                temp_list.append(PlanetData(planet['state']['capture_progress'],planet['state']['current_players'],top_clans_local))
            #global has to be a single sorted list of all the top clans
            #
            temp_global = []
            for clan in planet['top_clans']:
                #if the clan already exists, add to the existing count
                #apparently they sometimes returned bad data
                if("url" in clan['clan_info']):
                    if clan['clan_info']['url'] in top_clans_global:
                        top_clans_global[clan['clan_info']['url']] += clan["num_zones_controled"]
                    #doesn't exist, make it's data point
                    else:
                        top_clans_global[clan['clan_info']['url']] = clan["num_zones_controled"];
            #top_clans_global[-1] = top_clans_local[]
            #top_clans_global = sorted(top_clans_global, key=lambda k: k['num_zones_controled']) 
        planet_data.top_clans.append(top_clans_global)
        print("")
        print(planet_data.top_clans[-1])
    except Exception as e:
        print(e) 
    #If the planet is finished, set the end to null
    longest_list = get_longest_list()
    for planet_id,planet_stats in planet_data.planet_stats.items():
        if(planet_stats[-1].capture_progress != "null" and planet_stats[-1].capture_progress == 1):
            planet_stats.append(PlanetData('null','null',None))

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
def colorScale(i):
    default_colors_regular = ['#3366CC','#DC3912','#FF9900','#109618','#990099','#3B3EAC','#0099C6','#DD4477','#66AA00','#B82E2E','#316395','#994499','#22AA99','#AAAA11','#6633CC','#E67300','#8B0707','#329262','#5574A6','#3B3EAC']
    return default_colors_regular[i % 20];
def colorScaleDesat(i):
    default_colors_regular = ['#6b6a6c', '#986b5c', '#cbab8b', '#71876e', '#694c65', '#4f4b58', '#a9866b', '#837c7e', '#8e9d7e', '#6a605f', '#6b5f32', '#626762', '#bd8a98', '#a6a594', '#674d7e', '#ab8c76', '#484240', '#98788e', '#7b7440', '#4f4b58']
    return default_colors_regular[i % 20];    
#Used this to desaturate the colors available
def convertColors():
    out = []
    for i in range(0,20):
        out.append(spectra.html(colorScale(i)).desaturate(amount=60).hexcode)
    print(out)
 
def update_colors():
    global planet_data
    #colors = ["#F9C80E","#72ff77","#EA3546","#662E9B","#43BCCD"]
    #colors = ["#540D6E","#EE4266","#FFD23F","#72ff77","#1F271B"]
    for planet_id,planet_stats in planet_data.planet_stats.items():
        print("Planet Stats Coloring: " + str(planet_stats[-1]))
        if(planet_stats[-1].capture_progress != "null" and float(planet_stats[-1].capture_progress) > 0 and float(planet_stats[-1].capture_progress) < 1):
            print("set active color " + planet_id)
            planet_data.colors[planet_id] = colorScale(int(planet_id))
        else:
            planet_data.colors[planet_id] = colorScaleDesat(int(planet_id))
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
@cache.cached(timeout=5)
def chart1():
    legend = 'Capture Data'
    #if it needs to update the data
    return render_template('chart.html', legend=legend,planet_names=planet_data.planet_names,planet_data=planet_data)
 
@app.route("/player_charts")
@cache.cached(timeout=5)
def chart2():
    legend = 'Player Data'
    #if it needs to update the data
    return render_template('chart_players.html', legend=legend,planet_names=planet_data.planet_names,planet_data=planet_data)
    
@app.route("/planet_live")
@cache.cached(timeout=5)
def chart3():
    legend = 'Player Data'
    #if it needs to update the data
    return render_template('chart_planet_data.html', legend=legend,planet_names=planet_data.planet_names,planet_data=planet_data)
 
 
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
    app.run(host="127.0.0.1",port=8001,debug=True)
main()

# Shut down the scheduler when exiting the app
