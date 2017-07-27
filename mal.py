import spice_api as spice
import tvdb_api
import re
import os
import threading
import time
import tvdb_api
from datetime import datetime
from datetime import timedelta
from pytz import all_timezones
import pytz
import tkinter as tk
import json
import pickle

exitFlag = 0
t = tvdb_api.Tvdb()

memoizedAir = {}

with open("bins/memoizedIDs.bin", "rb") as fp:   # Unpickling
    memoizedIDs = pickle.load(fp)

with open('broken.json') as data_file:
    broken = json.load(data_file)

with open('config.json') as data_file:
    config = json.load(data_file)

weekdayInt = {"Monday":0,"Tuesday":1,"Wednesday":2,"Thursday":3,"Friday":4,"Saturday":5,"Sunday":6}
def adjustDate(weekday,timeOfDay):

    def toMilitaryTime(splitTime):
        if('AM' in splitTime[1].upper()):
            splitTime[1]=splitTime[1].split(' ')[0]
            if(int(splitTime[0])==12):
                splitTime[0] == '0'
        if('PM' in splitTime[1].upper()):
            splitTime[1]=splitTime[1].split(' ')[0]
            if(int(splitTime[0])<12):
                temp = int(splitTime[0])
                temp+=12
                splitTime[0] = temp

    def calcDateDifference(weekday):
        curDayNum=datetime.today().weekday()
        japanUsDifference =(datetime.now(pytz.timezone('Japan')).day-datetime.now(pytz.timezone('US/Central')).day)
        if(japanUsDifference != 0) and (japanUsDifference !=1):
            japanUsDifference = 1
        curDayNum+=japanUsDifference
        newDay=weekdayInt[weekday]
        difference= (newDay-curDayNum)
        if(difference <0):
            difference = 7+ difference
        return difference

    splitTime=timeOfDay.split(":")
    toMilitaryTime(splitTime)

    time= datetime.now(pytz.timezone('Japan'))+timedelta(days=calcDateDifference(weekday))
    time-=timedelta(hours=datetime.now(pytz.timezone('Japan')).hour,seconds=datetime.now(pytz.timezone('Japan')).second,minutes=datetime.now(pytz.timezone('Japan')).minute,)
    time+=timedelta(hours=int(splitTime[0]),minutes=int(splitTime[1]))
    time = time.astimezone(pytz.timezone('US/Central'))
    t = time-datetime.now(pytz.timezone('US/Central'))
    if(t.days < 0):
        t+=timedelta(days=7)


    return str(t)

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
      #print ("Exiting " + self.name)

def scrapeInfo(threadName,showId,creds):
    #print(creds)
    if(showId in memoizedIDs):
        nameInfo = memoizedIDs[showId]
    else:
        nameInfo = spice.search_id(showId,spice.get_medium('anime'),creds)


    if ('Currently Airing' == nameInfo.status):
        name=re.sub(r'\([^)]*\)', '', nameInfo.title)
        season = 1

        if(name in broken):
            airDay = broken[name][0]
            airTime = broken[name][1]
        elif(name in memoizedAir):
            airDay = memoizedAir[name][0]
            airTime = memoizedAir[name][1]
        else:
            airDay = t[name]['airs_dayofweek']
            airTime = t[name]['airs_time']
            memoizedAir[name] = [airDay , airTime]
        tillAir=adjustDate(airDay,airTime)
        return (name,adjustDate(airDay,airTime),airDay)



creds = spice.init_auth(config["UserName"],config["Password"])


class SampleApp(tk.Tk):
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        self.list = tk.Label(self, text="",fg="white",bg="black")
        self.list.pack()
        self.label =""


        self.update_label()


    def update_label(self):
        your_list = spice.get_list(spice.get_medium('anime'),creds[0] ,creds)
        ids=your_list.get_status(1)
        animeList=[]
        threads=[]
        count = 1
        for id in ids:
            threads.append(myThread(count, "Thread-"+str(id),id,creds))
            count+=1

        for thread1 in threads:
            thread1.start()

        for thread1 in threads:
            thread1.join()
            if(thread1.info != None):
                if thread1.info != '':
                    animeList.append(thread1.info)


        animeList.sort(key=lambda tup: tup[0])


        self.label =""
        for show in animeList:
            try:
                self.label+=show[0]+'\n'
                self.label+=show[1]+'\n\n'
            except:
                pass
        self.list.configure(text=self.label)
        self.after(10000, self.update_label)




app = SampleApp()
if __name__ == "__main__":
    app.title("Show CountDown")
    app.configure(background="black")

    app.mainloop()

    print("after APP")
