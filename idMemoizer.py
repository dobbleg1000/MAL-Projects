import pickle
import spice_api as spice
import sys
import json
import os

path=os.path.dirname(os.path.abspath(__file__))

with open(path+'/config.json') as data_file:
    config = json.load(data_file)

creds = spice.init_auth(config["UserName"],config["Password"])

memoizedIDs={}
sys.setrecursionlimit(10000)

your_list = spice.get_list(spice.get_medium('anime'),creds[0] ,creds)
ids=your_list.get_ids()
for id in ids:
    if id not in memoizedIDs:
        print(id)
        nameInfo = spice.search_id(id,spice.get_medium('anime'),creds)
        memoizedIDs[id] = nameInfo

with open(path+"/bins/memoizedIDs.bin", "wb") as fp:   #Pickling
    pickle.dump(memoizedIDs, fp)
