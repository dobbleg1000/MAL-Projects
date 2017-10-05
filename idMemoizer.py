import pickle
import spice_api as spice
import sys
import json
import os
import progressbar
import lagents
import functools
import time


def catch_exception(f):
    @functools.wraps(f)
    def func(*args, **kwargs):
        count = 0
        while(count < 200):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                time.sleep(5)
            count += 1
        print("\n" + id + "\n")
    return func


path = os.path.dirname(os.path.abspath(__file__))

with open(path + '/config.json') as data_file:
    config = json.load(data_file)

creds = spice.init_auth(config["UserName"], config["Password"])

memoizedIDs = {}
sys.setrecursionlimit(10000)


@catch_exception
def scrapeId(id):
    if id not in memoizedIDs:
        nameInfo = spice.search_id(id, spice.get_medium('anime'), creds)
        memoizedIDs[id] = nameInfo


scraper = lagents.Agent(method=scrapeId, max_workers=20)


def progressbar_maker():
    max = scraper.get_work_count()
    bar = progressbar.ProgressBar(max_value=max)
    cur = max
    while cur > 0:
        cur = scraper.get_work_count()
        bar.update(abs(max - cur))
    scraper.finalize()


your_list = spice.get_list(spice.get_medium('anime'), creds[0], creds)
ids = your_list.get_ids()

for id in ids:
    scraper.execute_async(id)

progressbar_maker()

with open(path + "/bins/memoizedIDs.bin", "wb") as fp:   # Pickling
    pickle.dump(memoizedIDs, fp)
