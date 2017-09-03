import spice_api as spice

import re
import os
from collections import defaultdict
import json
import Agents

import functools

path=os.path.dirname(os.path.abspath(__file__))
mangaList=defaultdict(list)
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
                pass

            count+=1

        print(args[0])
    return func

@catch_exception
def scrapeInfo(showId,creds):
    nameInfo = spice.search_id(showId,spice.get_medium('manga'),creds)
    mangaList[nameInfo.manga_type].append(nameInfo.title)


if __name__ == "__main__":
    agent = Agents.Agent(method=scrapeInfo,n_threads=20)
    your_list = spice.get_list(spice.get_medium('manga'),creds[0],creds)
    ids=your_list.get_ids()
    mangaList.clear()

    count = 1
    for id in ids:
        agent.execute_async(id,creds)

    agent.finalize()
    final=""
    for key in mangaList.keys():
        mangaList[key].sort()
        mangaList[key]=["\n\n"+key+"\n"] + mangaList[key]
        final+="\n".join(mangaList[key])




    thefile = open('mangaList.txt', 'w',encoding="utf8")
    thefile.write(final[2:])
