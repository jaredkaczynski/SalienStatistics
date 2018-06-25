from flask import Flask
from flask import render_template
from time import time
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask_caching import Cache

import collections as ct
import dill as pickle

import glob
import requests
import json
import atexit

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
planet_data = DataObject()

def load_from_files():
    path = 'logger3/PlanetData1*.txt'
    files=glob.glob(path)
    for file in sorted(files):
        #print(file)
        with open(file, 'r', encoding='utf-8') as f:
            parse_json(f.read(),file)
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
jsonDict = {}
def parse_json(response,file):
    global planet_data
    global jsonDict

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
            jsonDict[planet['id']] = planet;
            #print(jsonDict[planet['id']])
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
                
        for planet_id in planet_data.planet_stats:
            #print(planet_json['response']['planets'])
            print(planet_id)
            contains = any(planet['id'] == planet_id for planet in planet_json['response']['planets'])
            #print(contains)
            #print(planet_id not in planet_json['response']['planets'])
            if contains == False:
                #print(jsonDict[planet_id])
                jsonDict[planet_id]['state']['capture_progress'] = 1;
                planet_json['response']['planets'].append(jsonDict[planet_id]);
                #print("after")
                #print(planet_json['response']['planets'])
                
        #print(planet_json)
                
        with open(../logger4/file, 'w') as f:
            json.dump(planet_json, f)
            #file.write(planet_json)
        print("writing")
        #print(jsonDict)            
        print( "jsondict")            
    except:
        pass 
    #If the planet is finished, set the end to null
    longest_list = get_longest_list()
    for planet_id,planet_stats in planet_data.planet_stats.items():
        if(len(planet_stats)<longest_list and planet_stats[-1].capture_progress != "null" and float(planet_stats[-1].capture_progress) > .98):
            planet_stats.append(PlanetData('null','null'))
            
load_from_files()
