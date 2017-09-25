import spice_api as spice
import os
from collections import defaultdict
import json
import Agents

import functools

path = os.path.dirname(os.path.abspath(__file__))
animeList = defaultdict(list)

with open(path + '/config.json') as data_file:
    config = json.load(data_file)

creds = spice.init_auth(config["UserName"], config["Password"])


def catch_exception(f):
    @functools.wraps(f)
    def func(*args, **kwargs):
        count = 0
        while(count < 5):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                print(count)
            count += 1
    return func


@catch_exception
def scrapeInfo(showId, creds):
    nameInfo = spice.search_id(showId, spice.get_medium('anime'), creds)

    if ('Currently Airing' != nameInfo.status):
        animeList[nameInfo.anime_type].append(nameInfo.title)


if __name__ == "__main__":
    agent = Agents.Agent(method=scrapeInfo, n_threads=20)
    your_list = spice.get_list(spice.get_medium('anime'), creds[0], creds)
    ids = your_list.get_status(1)
    animeList.clear()

    count = 1
    for id in ids:
        agent.execute_async(id, creds)

    agent.finalize()

    final = ""
    for key in animeList.keys():
        animeList[key].sort()
        final += "\n\n" + key + "\n" + "\n".join(animeList[key])

    thefile = open(path + '/animeList.txt', 'w')
    thefile.write(final[2:])
