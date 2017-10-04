import pickle
import spice_api as spice
import sys
import json
import os
import progressbar

path = os.path.dirname(os.path.abspath(__file__))

with open(path + '/config.json') as data_file:
    config = json.load(data_file)

creds = spice.init_auth(config["UserName"], config["Password"])

memoizedIDs = {}
sys.setrecursionlimit(10000)

your_list = spice.get_list(spice.get_medium('anime'), creds[0], creds)
ids = your_list.get_ids()
count=1
with progressbar.ProgressBar(max_value=len(ids)) as bar:
    for id in ids:
        if id not in memoizedIDs:
            nameInfo = spice.search_id(id, spice.get_medium('anime'), creds)
            memoizedIDs[id] = nameInfo
        bar.update(count)
        count = count + 1
with open(path + "/bins/memoizedIDs.bin", "wb") as fp:   # Pickling
    pickle.dump(memoizedIDs, fp)
