from PIL import Image
import spice_api as spice
import tvdb_api
import re
import json
import pickle
import mimetypes
import sys
import os
import requests
import image_stuff
import functools
import lagents
import string

path = os.path.dirname(os.path.abspath(__file__))

with open(path + "/bins/memoizedIDs.bin", "rb") as fp:   # Unpickling
    memoizedIDs = pickle.load(fp)

with open(path + "/bins/memoizedAir.bin", "rb") as fp:   # Unpickling
    memoizedAir = pickle.load(fp)

with open(path + '/broken.json') as data_file:
    broken = json.load(data_file)


with open(path + '/config.json') as data_file:
    config = json.load(data_file)

Show_List = []

current = not ("--old" in sys.argv)

if("--username" in sys.argv):
    username = sys.argv[sys.argv.index("--username") + 1]
else:
    username = input("Mal Username:[" + config["UserName"] + "]\n")

if username == "":
    username = config["UserName"]

if("--size" in sys.argv):
    size = sys.argv[sys.argv.index("--size") + 1]
else:
    size = input("Enter the screens widthxheight (ex. 1920x1080):\n")

size = size.split("x")
screensize = (int(size[0]), int(size[1]))

path = os.path.dirname(os.path.abspath(__file__))

sys.setrecursionlimit(10000)


def is_url_image(url):
    mimetype, encoding = mimetypes.guess_type(url)
    return (mimetype and mimetype.startswith('image'))


t = tvdb_api.Tvdb()


creds = spice.init_auth(config["UserName"], config["Password"])


weekdayInt = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
              "Friday": 4, "Saturday": 5, "Sunday": 6}


def toMilitaryTime(splitTime):
    if('AM' in splitTime[1].upper()):
        splitTime[1] = splitTime[1].split(' ')[0]
        if(int(splitTime[0]) == 12):
            splitTime[0] = '0'
    if('PM' in splitTime[1].upper()):
        splitTime[1] = splitTime[1].split(' ')[0]
        if(int(splitTime[0]) < 12):
            temp = int(splitTime[0])
            temp += 12
            splitTime[0] = str(temp)


def scrapeInfo(showId, creds):
    def timeAdjust(time, airDay):
        splitTime = time.split(":")
        toMilitaryTime(splitTime)
        time = splitTime[0] + splitTime[1]
        if(time < "1400"):
            airDay = list(weekdayInt)[(weekdayInt[airDay] - 1) % 7]
        return airDay

    if(showId in memoizedIDs):
        nameInfo = memoizedIDs[showId]
    else:
        nameInfo = spice.search_id(showId, spice.get_medium('anime'), creds)
        print(nameInfo.title + " " + nameInfo.status)
    if ('Currently Airing' == nameInfo.status and current):
        name = re.sub(r'\([^)]*\)', '', nameInfo.title)

        if(name in broken):
            airDay = broken[name][0]
            airDay = timeAdjust(broken[name][1], airDay)
        elif(name in memoizedAir):
            airDay = memoizedAir[name]
        else:
            try:
                airDay = t[name]['airsDayOfWeek']
                timeOfDay = t[name]['airsTime']
                airDay = timeAdjust(timeOfDay, airDay)
                memoizedAir[name] = airDay
            except Exception:
                print(name)

        Show_List.append((airDay, name, nameInfo.image_url))
    elif('Currently Airing' != nameInfo.status and not current):
        name = re.sub(r'\([^)]*\)', '', nameInfo.title)
        airDay = "Monday"
        Show_List.append((airDay, name, nameInfo.image_url))


valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
valid_chars = frozenset(valid_chars)


def download_images(list):
    for show in list:  # Save the Images
        if is_url_image(show[2]):
            name = show[1]
            pic_type = (show[2].split("."))[len((show[2].split("."))) - 1]
            name = ''.join(c for c in name if c in valid_chars)
            name += "." + pic_type
            file_path = path + "/covers/" + name

            file_path = file_path.replace("\\", "/")

            directory = os.path.dirname(file_path)
            if not os.path.exists(directory):
                os.makedirs(directory)
            image = show[2]
            try:
                response = requests.get(image, stream=True)
                with open(file_path, 'wb') as img:
                    for block in response.iter_content(1024):
                        if not block:
                            break
                        img.write(block)
            except Exception:
                sys.stdout.write('\rFailed to save: %s               ' % image)
                sys.stdout.flush()
                print('\nContinuing...')
                continue


your_list = spice.get_list(spice.get_medium('anime'), username, creds)
ids = your_list.get_status(1)
agent = lagents.Agent(method=scrapeInfo, max_workers=20)


for id in ids:
    agent.execute_async(id, creds)


agent.join()
agent.finalize()

with open(path + "/bins/memoizedAir.bin", "wb") as fp:   # Pickling
    pickle.dump(memoizedAir, fp)


Show_List.sort(key=lambda tup: tup[1])
Show_List.sort(key=lambda tup: weekdayInt[tup[0]])

download_images(Show_List)

show_by_day = {"Monday": [], "Tuesday": [], "Wednesday": [], "Thursday": [],
               "Friday": [], "Saturday": [], "Sunday": []}
for show in Show_List:
    fileName = show[1] + ".jpg"
    fileName = ''.join(c for c in fileName if c in valid_chars)
    show_by_day[show[0]].append(fileName)

# remove trailing empty image_stuff.Labels
for date, shows in reversed(list(show_by_day.items())):
    if len(shows) == 0:
        show_by_day.pop(date)
    else:
        break


GAP_horizontal = 10
GAP_vertical = 15

showcover_resize = (225, 332)  # Set to None to disable resizing, set to (width, height) to resize all covers to that size
numberOfRowsThresholds = [(0, 1), (5, 2), (9, 3), (22, 4)]  # Tuples of (threshold-number-of-shows, corresponding-number-of-generated-rows)
if(screensize[0] < screensize[1]):
    numberOfRowsThresholds = [(0, 1), (5, 4), (9, 6)]
# create image_stuff.Label-picture image_stuff.Bindings

overflowitem = None


def buildRenderItems(showcover_resize_var):
    renderitems = []
    global overflowitem
    getshowcover = (lambda image: image_stuff.ResizePicture(image, showcover_resize_var)) if showcover_resize_var else (lambda image: image_stuff.Picture(image))
    for date, shows in show_by_day.items():
        dayLabel = image_stuff.Label(date + ".png")

        def prependoverflow(nextitem):
            global overflowitem
            if overflowitem is None:
                return nextitem
            else:
                r = image_stuff.Bind(overflowitem, nextitem, GAP_horizontal)
                overflowitem = None
                return r

        if len(shows) == 0:
            overflowitem = prependoverflow(dayLabel)
        else:
            if(current):
                renderitems.append(prependoverflow(image_stuff.Bind(dayLabel, getshowcover(shows[0]), GAP_horizontal)))
                renderitems += map(getshowcover, shows[1:])
            else:
                renderitems += map(getshowcover, shows)

    if overflowitem is not None:
        if len(renderitems) > 0:
            renderitems[-1] = image_stuff.Bind(renderitems[-1], overflowitem, GAP_horizontal)
        else:
            renderitems = [overflowitem]
    return renderitems


def findSizeandBuildRender():
    divisions = list(filter((lambda pair: len(functools.reduce(lambda x, y: x + y, show_by_day.values())) >= pair[0]), numberOfRowsThresholds))[-1][1]
    global showcover_resize
    global screensize
    showcover_resize_float = showcover_resize
    renderitems = buildRenderItems(showcover_resize)
    totalwidth = image_stuff.itemswidth(renderitems, GAP_horizontal)
    remainingwidth = int(totalwidth / divisions) + (showcover_resize[0]) + 50
    remainingHeight = image_stuff.itemsheight(renderitems) * divisions + (GAP_vertical * divisions - 1)
    screensize = (screensize[0] - 30, screensize[1] - 30)
    while((remainingwidth < screensize[0]) and (remainingHeight < screensize[1])):
        showcover_resize_float = (showcover_resize_float[0] * 1.01, showcover_resize_float[1] * 1.01)
        showcover_resize = (int(showcover_resize_float[0]), int(showcover_resize_float[1]))
        renderitems = buildRenderItems(showcover_resize)
        totalwidth = image_stuff.itemswidth(renderitems, GAP_horizontal)
        remainingwidth = int(totalwidth / divisions) + (showcover_resize[0]) + 50
        remainingHeight = image_stuff.itemsheight(renderitems) * divisions + (GAP_vertical * divisions - 1)

    while(remainingwidth > screensize[0]):
        showcover_resize_float = (showcover_resize_float[0] * .99, showcover_resize_float[1] * .99)
        showcover_resize = (int(showcover_resize_float[0]), int(showcover_resize_float[1]))
        renderitems = buildRenderItems(showcover_resize)
        totalwidth = image_stuff.itemswidth(renderitems, GAP_horizontal)
        remainingwidth = int(totalwidth / divisions) + (showcover_resize[0]) + 50

    while(remainingHeight > screensize[1]):
        showcover_resize_float = (showcover_resize_float[0] * .999, showcover_resize_float[1] * .999)
        showcover_resize = (int(showcover_resize_float[0]), int(showcover_resize_float[1]))
        renderitems = buildRenderItems(showcover_resize)
        remainingHeight = image_stuff.itemsheight(renderitems) * divisions + (GAP_vertical * divisions - 1)

    return renderitems


renderitems = findSizeandBuildRender()
screensize = (screensize[0] + 30, screensize[1] + 30)
# split into rows
rows = []
if len(renderitems) > 0:
    numberOfRowsThresholds.sort(key=lambda pair: pair[0])
    divisions = list(filter((lambda pair: len(functools.reduce(lambda x, y: x + y, show_by_day.values())) >= pair[0]), numberOfRowsThresholds))[-1][1]
    iItem = 0

    totalwidth = image_stuff.itemswidth(renderitems, GAP_horizontal)
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
        if type(item) is image_stuff.Label or (type(item) is image_stuff.Bind and type(item.recFirst()) is image_stuff.Label):
            if type(previtem) is not image_stuff.Label and (type(previtem) is not image_stuff.Bind or type(previtem.recSecond()) is not image_stuff.Label):
                row[iItem - 1] = image_stuff.Bind(previtem, item, GAP_horizontal * 5)
                row.remove(item)
                iItem -= 1
        iItem += 1

# render
image = Image.new("RGB", screensize)
background = Image.open(path + "/covers/base.png")
background = background.resize(screensize)
image.paste(background, (0, 0))

y = int((screensize[1] - functools.reduce(lambda x, y: x + GAP_vertical + y,
                                          map(image_stuff.itemsheight, rows))) / 2)
for row in rows:
    x = int((screensize[0] - image_stuff.itemswidth(row, GAP_horizontal)) / 2)
    rowheight = image_stuff.itemsheight(row)
    for item in row:
        item.render(image, (x, y + int((rowheight - item.getHeight()) / 2)))
        x += item.getWidth() + GAP_horizontal
    y += rowheight + GAP_vertical

if(current):
    image.save(path + "/CurrentlyAiring.jpg")
else:
    image.save(path + "/Watching.jpg")
