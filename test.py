from PIL import Image
import spice_api as spice
import tvdb_api
import re
import threading
import json
import pickle
import mimetypes
import sys
import os
import requests
from collections import defaultdict
from image_stuff import *

with open('config.json') as data_file:
    config = json.load(data_file)

creds = spice.init_auth(config["UserName"],config["Password"])

class myThread (threading.Thread):
   def __init__(self, threadID, name, showId,creds):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
      self.showId = showId
      self.credential = creds
      self.info = ""
   def run(self):
      #print ("Starting " + self.name)
      self.info = scrapeInfo(self.name, self.showId,self.credential)


def scrapeInfo(threadName,showId,creds):
    def timeAdjust(time,airDay):
        splitTime=time.split(":")
        toMilitaryTime(splitTime)
        time = splitTime[0]+splitTime[1]
        if(time < "1400"):
            airDay = list(weekdayInt)[(weekdayInt[airDay]-1)%7]
        return airDay

    #print(creds)
    if(showId in memoizedIDs):
        nameInfo = memoizedIDs[showId]
    else:
        nameInfo = spice.search_id(showId,spice.get_medium('anime'),creds)


    if ('Currently Airing' == nameInfo.status):
        name=re.sub(r'\([^)]*\)', '', nameInfo.title)

        if(name in broken):
            airDay = broken[name][0]
            airDay = timeAdjust(broken[name][1],airDay)
        elif(name in memoizedAir):
            airDay = memoizedAir[name]
        else:
            airDay = t[name]['airs_dayofweek']
            timeOfDay = t[name]['airs_time']
            airDay = timeAdjust(timeOfDay,airDay)
            memoizedAir[name] = airDay

        return (airDay,name,nameInfo.image_url)
