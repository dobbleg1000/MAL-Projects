import spice_api as spice

import re
import os


import json
import Agents

import functools

path=os.path.dirname(os.path.abspath(__file__))
animeList=[]

with open(path+'/config.json') as data_file:
    config = json.load(data_file)

creds = spice.init_auth(config["UserName"],config["Password"])

def catch_exception(f):
    @functools.wraps(f)
    def func(*args, **kwargs):
        count = 0
        while(count<5):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                print(count)
            count+=1
    return func

@catch_exception
def scrapeInfo(showId,creds):
    nameInfo = spice.search_id(showId,spice.get_medium('anime'),creds)

    if ('Currently Airing' != nameInfo.status):
        name=re.sub(r'\([^)]*\)', '', nameInfo.title)
        animeList.append(name)

if __name__ == "__main__":
    agent = Agents.Agent(method=scrapeInfo,n_threads=20)
    your_list = spice.get_list(spice.get_medium('anime'),creds[0] ,creds)
    ids=your_list.get_status(1)
    animeList.clear()
    threads=[]
    count = 1
    for id in ids:
        agent.execute_async(id,creds)

    agent.finalize()
    animeList.sort()


    label =""
    for show in animeList:
        label+=show+'\n'
    print(label)
    thefile = open('animeList.txt', 'w')
    thefile.write("\n".join(animeList))
