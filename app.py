from flask import Flask, request, render_template
from time import time
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask_caching import Cache

import collections as ct
import dill as pickle

import locale
import spectra
import glob
import requests
import json
import atexit

import os

sorted(glob.glob('*.html'), key=os.path.getmtime)

 
app = Flask(__name__)
# For more configuration options, check out the documentation
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

class DataObject:
    def __init__(self):
        self.planet_names = dict()
        self.planet_stats = ct.defaultdict(list)
        self.dts = []
        self.colors = dict()
        self.clan_colors = ['#3366CC','#DC3912','#FF9900','#109618','#990099','#3B3EAC','#0099C6','#DD4477','#66AA00','#B82E2E','#316395','#994499','#22AA99','#AAAA11','#6633CC','#E67300','#8B0707','#329262','#5574A6','#3B3EAC']
        #Add position 0 value as diffiutlies are 1 indexed
        self.zone_colors = ["","#5cb85c","#f0ad4e","#d9534f"]
        self.top_clans = []
        self.top_clans_rotated = []
        self.zone_data = []
        self.time_data = dict()
class PlanetData():
    def __init__(self,capture_progress,current_players,top_clans=[],zones=[]):
        self.capture_progress = capture_progress
        self.current_players = current_players
        self.top_clans = top_clans
        self.zones = zones
        
        
class ZoneData():
    def __init__(self,planet_id):
        self.planet_id = planet_id
        self.zone_data = 0.0
        
        
class ClanData():
    def __init__(self,clan_name,clan_url):
        self.clan_name = clan_name
        self.clan_url = clan_url
        self.clan_data = []
        
#hold lists of completion % of planets
planet_data = None

def datetime_range(start, end, delta):
    current = start
    while current < end:
        yield current
        current += delta 

def load_from_web():
    response = requests.get("https://community.steam-api.com/ITerritoryControlMinigameService/GetPlanets/v0001/")
    parse_json_planets(response.content)

def get_zone_json(zone):
    response = requests.get("https://community.steam-api.com/ITerritoryControlMinigameService/GetPlanet/v0001/?id=" + zone)
    parse_json_planet(response.content)


    
def load_from_files():
    path = 'logger3/PlanetData1*.txt'
    files=glob.glob(path)
    for file in sorted(files)[0::2]:
        #print(file)
        with open(file, 'r', encoding='utf-8') as f:
            parse_json_planets(f.read())
            
def load_from_files_zone(zone):
    path = 'zonelog/**/' + zone + '.html'
    files=glob.glob(path)
    #delete data if it's already out and the cache is old
    if(planet_data.planet_stats[zone][-1].zones):
        planet_data.planet_stats[zone][-1].zones = []
    
    for file in sorted(files)[0::4]:
        foldername=""
        try:
            foldername = file.split("\\")[1]
        except:
            foldername = file.split("/")[1]
        foldername = "2018 " + foldername
        #print(foldername)
        file_datetime = None
        try:
            file_datetime = (datetime.strptime(foldername,"%Y %j-%H%M"))
        except:
            file_datetime = (datetime.strptime(foldername,"%Y %j-%H:%M"))
        filetime = file_datetime.timestamp()
        #print(filetime)       
        if((filetime+1800) > planet_data.time_data[zone][0]):
            with open(file, 'r', encoding='utf-8') as f:
                parse_json_planet(f.read())
#for each planet, make a zone object and insert zone completion % in it
#at end, insert all 
def get_zone_count_at_time():
    for i in range(1,47):
        load_from_files_zone(i)
    pass
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
        
def get_longest_list_clans():
    global planet_data
    try:
        return len(planet_data.top_clans)
    except ValueError:
        print("First Run no List Length")    
        return 0       
        
#take object in form of, time[clan[data at time]] convert to clan[clan name/id[clan data all]]
def rotate_data():
    global planet_data
    rotated_data = {}
    for time in planet_data.top_clans:
        #print(type(time))
        for clan_name,clan_data in time.items():
            #print(clan_data)
            if clan_name not in rotated_data:
                rotated_data[clan_name] = ClanData(clan_name,clan_data[0])
            rotated_data[clan_name].clan_data.append(clan_data[1])
    planet_data.top_clans_rotated = rotated_data
    
    #print(planet_data.top_clans_rotated[0])
def parse_json_planets(response):
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
                    temp_list.append(PlanetData(None,None, []))                  
            try:
                planet_data.time_data[planet['id']] = [planet['state']['activation_time'],0]
                #print(planet['state']['activation_time'])
                #temp_list.activation_time = planet['state']['activation_time']
            except:
                pass
                
                
            #global has to be a single sorted list of all the top clans
            for clan in planet['top_clans']:
                #if the clan already exists, add to the existing count
                #apparently they sometimes returned bad data
                if("url" in clan['clan_info']):      
                    try:
                        #print(top_clans_global[clan['clan_info']['url']][1])
                        top_clans_global[clan['clan_info']['url']][0] = clan['clan_info']['name']
                    except:
                        #print("List not initialized")
                        top_clans_global[clan['clan_info']['url']] = ["name",0]
                        top_clans_global[clan['clan_info']['url']][0] = clan['clan_info']['name']

                    if clan['clan_info']['url'] in top_clans_global:
                        top_clans_global[clan['clan_info']['url']][1] += clan["num_zones_controled"]
                    #doesn't exist, make it's data point
                    else:
                        top_clans_global[clan['clan_info']['url']][1] = clan["num_zones_controled"];                        
            #if it's already got to 100% don't log it
            if(temp_list and (temp_list[-1].capture_progress == '1' or (temp_list[-1].capture_progress == None and temp_list[-2].capture_progress != None))):
                pass
            else:
                temp_list.append(PlanetData(planet['state']['capture_progress'],planet['state']['current_players'],top_clans_local))
        #iterate over stored clan data if exists
        if(planet_data.top_clans and planet_data.top_clans[0]):
            for clan_name,clan_data in planet_data.top_clans[0].items():
                    #if the clan wasn't top in this time slice
                    if(clan_name not in top_clans_global):
                            top_clans_global[clan_name] = [clan_data[0],clan_data[1]]
                  
    except:
        print("Error")
        pass
    planet_data.top_clans.append(top_clans_global)
    rotate_data()
    
        
    #If the planet is finished, set the end to null
    longest_list = get_longest_list()
    for planet_id,planet_stats in planet_data.planet_stats.items():
        if(planet_stats[-1].capture_progress != None and planet_stats[-1].capture_progress == 1):
            planet_stats.append(PlanetData(None,None,None))
    #print(planet_data.top_clans[-1])

def parse_json_planet(response):
    global planet_data

    #store into planet_data_object
    longest_list = get_longest_list()
    planet_json = None
    top_clans_global = {}
    #print(type(planet_data.planet_stats['2']))
    try:
        planet_json = json.loads(response)
    except:
        print("Bad HTML")
        pass

    #Should get the single planet in the json
    for planet in planet_json['response']['planets']: 
        #grab the planet_data zones object which is a list where each element is a time slice
        temp_list = planet_data.planet_stats[planet['id']]
        #print("temp list")
        #print(temp_list)
        #make a temp zone data object which holds a list of zone data for a moment in time
        temp_zone_list = []
        #for each zone on the current planet json, ordered from 0-T 
        for idx, zone in enumerate(planet['zones']):
            zone_value = 0;
            if(zone['captured'] == "true" or zone['captured'] == True):
                zone_value = "null"
            elif("capture_progress" not in zone):
                zone_value = 0
            else:
                #print(zone['capture_progress'])
                zone_value = zone['capture_progress']
            #append the data to the end of the list
            temp_zone_list.append([zone['zone_position'],zone_value,zone['difficulty']]) 
        temp_list[-1].zones.append(temp_zone_list)
        #print(temp_list)
        try:
            new_val = planet_data.time_data[planet['id']][0] + (1200 * len(temp_list[-1].zones))
            planet_data.time_data[planet['id']][1] = new_val 
        except:
             pass

    
def update_time_scale():
    global planet_data
    #get new labels for time axis
    #Y M D H M
    #dts = [dt.strftime('%Y-%m-%d T%H:%M Z') for dt in
    dts = [dt.strftime('%d T%H:%M') for dt in  
       datetime_range(datetime(2018, 6, 22, 4, 5), datetime.utcnow(), 
       timedelta(minutes=10))]  
    planet_data.dts = dts
    #save the data to file
def colorScale(i):
    ##3B3EAC, #3366CC, #109618
    default_colors_regular = ['#0099C6','#109618','#DC3912','#FF9900','#990099','#DD4477','#66AA00','#B82E2E','#316395','#994499','#22AA99','#AAAA11','#6633CC','#E67300','#8B0707','#329262','#5574A6','#3366CC','#3B3EAC','#3B3EAC']
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
        if(planet_stats[-1].capture_progress != None and float(planet_stats[-1].capture_progress) > 0 and float(planet_stats[-1].capture_progress) < 1):
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

def rotate(matrix, degree):
    if abs(degree) not in [0, 90, 180, 270, 360]:
        return
    if degree == 0:
        return matrix
    elif degree > 0:
        return rotate(list(zip(*matrix))[::-1], degree-90)
    else:
        return rotate(list(zip(*matrix))[::-1], degree+90)    
    

@app.route("/planet_charts")
@cache.cached(timeout=300)
def chart1():
    legend = 'Capture Data'
    #if it needs to update the data
    capture_data = ct.defaultdict(list)
    capture_data_day = ct.defaultdict(list)
    for key in planet_data.planet_stats:
        for index, time in enumerate(planet_data.planet_stats[key]):
            capture_data[key].append(time.capture_progress)
            if(index > len(planet_data.dts) - 72):
                capture_data_day[key].append(time.capture_progress)
    for key in planet_data.planet_stats:
        capture_data[key] = json.dumps(capture_data[key])
        capture_data_day[key] = json.dumps(capture_data_day[key])

        
    return render_template('chart.html', legend=legend,planet_names=planet_data.planet_names,planet_data=planet_data,capture_data=capture_data,capture_data_day=capture_data_day)
 
@app.route("/player_charts")
@cache.cached(timeout=300)
def chart2():
    #if it needs to update the data
    capture_data = ct.defaultdict(list)
    capture_data_day = ct.defaultdict(list)
    for key in planet_data.planet_stats:
        for index, time in enumerate(planet_data.planet_stats[key]):
            capture_data[key].append(time.current_players)
            if(index > len(planet_data.dts) - 72):
                capture_data_day[key].append(time.current_players)
    for key in planet_data.planet_stats:
        capture_data[key] = json.dumps(capture_data[key])
        capture_data_day[key] = json.dumps(capture_data_day[key])
    return render_template('chart_players.html',planet_names=planet_data.planet_names,planet_data=planet_data,capture_data=capture_data,capture_data_day=capture_data_day)
    
@app.route('/') 
@app.route("/planet_live")
@cache.cached(timeout=300)
def chart3():
    legend = 'Player Data'
    #if it needs to update the data
    return render_template('chart_planet_data.html', legend=legend,planet_names=planet_data.planet_names,planet_data=planet_data)
    
@app.route("/clan_charts")
@cache.cached(timeout=300)
def chart4():
    newA = dict(sorted(planet_data.top_clans_rotated.items(), key=lambda e: e[-1].clan_data, reverse=True)[:20])
    planet_data.top_clans_rotated = newA  
    
    capture_data = ct.defaultdict(list)
    capture_data_day = ct.defaultdict(list)
    for key,value in planet_data.top_clans_rotated.items():
        for index,count in enumerate(value.clan_data):
            capture_data[key].append(count)
            if(index > len(planet_data.dts) - 72):
                capture_data_day[key].append(count)
    for key in planet_data.top_clans_rotated:
        capture_data[key] = json.dumps(capture_data[key])
        capture_data_day[key] = json.dumps(capture_data_day[key])
    return render_template('chart_clans.html',planet_names=planet_data.planet_names,planet_data=planet_data,capture_data=capture_data,capture_data_day=capture_data_day)

def custom_time_scale(start, end):
    dts = [dt.strftime('%d T%H:%M') for dt in  
           datetime_range(datetime.fromtimestamp(int(start)), datetime.fromtimestamp(int(end)), 
           timedelta(minutes=20))]  
    return(dts)    
    
def make_cache_key(*args, **kwargs):
    path = request.path
    args = str(hash(frozenset(request.args.items())))
    return (path + args).encode('utf-8')
    
@app.route("/view_planet")
@cache.cached(timeout=300, key_prefix=make_cache_key)
def chart5():
    planet_id = request.args.get('planet_id');
    load_from_files_zone(planet_id);
    #custom_time_scale(planet_data.planet_stats[planet_id][-1].activation_time,capture_time)
    zone_rotated = rotate(planet_data.planet_stats[planet_id][-1].zones,-90);
    #print(planet_data.planet_stats[planet_id][0].zones)
    legend = 'Player Data'
    timescale = custom_time_scale(planet_data.time_data[planet_id][0],planet_data.time_data[planet_id][1] + 1800)    
    
    #if it needs to update the data
    return render_template('chart_planet_dash.html', zone_rotated=zone_rotated,planet_data=planet_data,time_scale=timescale)    
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
    app.run(host="0.0.0.0",port=80)
main()

# Shut down the scheduler when exiting the app
