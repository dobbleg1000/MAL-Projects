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

path=os.path.dirname(os.path.abspath(__file__))

sys.setrecursionlimit(10000)

def get_input(string):
	''' Get input from console regardless of python 2 or 3 '''
	try:
		return raw_input(string)
	except:
		return input(string)

def is_url_image(url):
    mimetype,encoding = mimetypes.guess_type(url)
    return (mimetype and mimetype.startswith('image'))

t = tvdb_api.Tvdb()

with open(path+'/config.json') as data_file:
    config = json.load(data_file)

creds = spice.init_auth(config["UserName"],config["Password"])


with open(path+"/bins/memoizedIDs.bin", "rb") as fp:   # Unpickling
    memoizedIDs = pickle.load(fp)

with open(path+"/bins/memoizedAir.bin", "rb") as fp:   # Unpickling
    memoizedAir = pickle.load(fp)

with open(path+'/broken.json') as data_file:
    broken = json.load(data_file)

weekdayInt = {"Monday":0,"Tuesday":1,"Wednesday":2,"Thursday":3,"Friday":4,"Saturday":5,"Sunday":6}

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
            splitTime[0] = str(temp)

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

def download_images(list):
    for show in list: #Save the Images
        if is_url_image(show[2]):
            name=show[1]
            pic_type= (show[2].split("."))[len((show[2].split(".")))-1]
            name += "."+ pic_type

            file_path = path+"/covers/"+name
            file_path = file_path.replace(":","")
            directory = os.path.dirname(file_path)
            if not os.path.exists(directory):
                os.makedirs(directory)
            image=show[2]
            try:
                response = requests.get(image, stream=True)
            except:
                sys.stdout.write('\rFailed to save: %s                       ' % image)
                sys.stdout.flush()
                print('\nContinuing...')
                continue

            with open(file_path, 'wb') as img:
                for block in response.iter_content(1024):
                    if not block:
                        break
                    img.write(block)

your_list = spice.get_list(spice.get_medium('anime'),"Dobbleg1000" ,creds)
ids=your_list.get_status(1)
threads=[]
Show_List = []
count=1
for id in ids:
    threads.append(myThread(count, "Thread-"+str(id),id,creds))
    count+=1

for thread1 in threads:
    thread1.start()

for thread1 in threads:
    thread1.join()
    if(thread1.info != None):
        Show_List.append(thread1.info)




Show_List.sort(key=lambda tup: tup[1])
Show_List.sort(key=lambda tup: weekdayInt[tup[0]])

download_images(Show_List)

show_by_day = {"Monday": [], "Tuesday": [], "Wednesday": [], "Thursday": [], "Friday": [], "Saturday": [], "Sunday": []}
for show in Show_List:
    fileName = show[1]+".jpg"
    fileName = fileName.replace(":","")
    show_by_day[show[0]].append(fileName)



# remove trailing empty labels
for date, shows in reversed(list(show_by_day.items())):
    if len(shows) == 0:
        show_by_day.pop(date)
    else:
        break



GAP_horizontal = 10
GAP_vertical = 15
screensize = (1680, 1050)
showcover_resize = (225, 332) # Set to None to disable resizing, set to (width, height) to resize all covers to that size
numberOfRowsThresholds = [(0, 1), (5, 2), (9, 3)] # Tuples of (threshold-number-of-shows, corresponding-number-of-generated-rows)

# create label-picture bindings
renderitems = []
overflowitem = None
getshowcover = (lambda image: ResizePicture(image, showcover_resize)) if showcover_resize else (lambda image: Picture(image))
for date, shows in show_by_day.items():
    daylabel = Label(date+".png") # TODO get the day of week image
    def prependoverflow(nextitem):
        global overflowitem
        if overflowitem is None:
            return nextitem
        else:
            r = Bind(overflowitem, nextitem, GAP_horizontal)
            overflowitem = None
            return r

    if len(shows) == 0:
        overflowitem = prependoverflow(daylabel)
    else:
        renderitems.append(prependoverflow(Bind(daylabel, getshowcover(shows[0]), GAP_horizontal)))
        renderitems += map(getshowcover, shows[1:])

if overflowitem is not None:
    if len(renderitems) > 0:
        renderitems[-1] = Bind(renderitems[-1], overflowitem, GAP_horizontal)
    else:
        renderitems = [overflowitem]


# split into rows
rows = []
if len(renderitems) > 0:
    numberOfRowsThresholds.sort(key=lambda pair: pair[0])
    divisions = 3#list(filter((lambda pair: len(reduce(lambda x,y: x+y, show_by_day.values())) >= pair[0]), numberOfRowsThresholds))[-1][1]

    totalwidth = itemswidth(renderitems,GAP_horizontal)

    iItem = 0
    remainingwidth = int(totalwidth / divisions)
    for iRow in range(divisions - 1):
        row = []
        while True:
            item = renderitems[iItem]
            itemwidth = item.getWidth()

            if remainingwidth < itemwidth:
                if remainingwidth < itemwidth / 2:
                    # division is close to left side of item
                    # add item to next row
                    rows.append(row)
                    remainingwidth = int(totalwidth / divisions) + remainingwidth + GAP_horizontal
                else:
                    # division is close to right side of item
                    # add item to this row
                    row.append(item)
                    iItem += 1
                    remainingwidth -= itemwidth
                    rows.append(row)
                    remainingwidth = int(totalwidth / divisions) - remainingwidth
                break

            else:
                row.append(item)
                iItem += 1
                remainingwidth -= itemwidth + GAP_horizontal

    rows.append(renderitems[iItem:])

for row in rows:
    iItem = 1
    while iItem < len(row):
        item = row[iItem]
        previtem = row[iItem - 1]
        if type(item) is Label or (type(item) is Bind and type(item.recFirst()) is Label):
            if type(previtem) is not Label and (type(previtem) is not Bind or type(previtem.recSecond()) is not Label):
                row[iItem - 1] = Bind(previtem, item, GAP_horizontal * 5)
                row.remove(item)
                iItem -= 1
        iItem += 1

# render
image = Image.new("RGB",screensize)
background= Image.open(path+"/covers/base.png")
background= background.resize(screensize)
image.paste(background,(0,0))

y = int((screensize[1] - reduce(lambda x,y: x + GAP_vertical + y, map(itemsheight, rows))) / 2)
for row in rows:
    x = int((screensize[0] - itemswidth(row,GAP_horizontal)) / 2)
    rowheight = itemsheight(row)
    for item in row:
        item.render(image, (x, y + int((rowheight - item.getHeight()) / 2)))
        x += item.getWidth() + GAP_horizontal
    y += rowheight + GAP_vertical

image.save(path+"/Final.jpg")
