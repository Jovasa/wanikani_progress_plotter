from collections import defaultdict
from pathlib import Path

import urllib3
import json
from time import sleep
from datetime import datetime

temp = (Path(__file__) / ".." / "wanikani_token").resolve()
with open(temp, "r") as t:
    wanikani_token = t.read()


def test(refresh_data=True):
    if refresh_data:
        http = urllib3.PoolManager()
        next_url = "https://api.wanikani.com/v2/assignments"
        assignments = []
        while next_url is not None:
            t = http.request("GET",
                             next_url,
                             headers={"Authorization": f"Bearer {wanikani_token}"}
                             )
            data = json.loads(t.data.decode("utf-8"))
            assignments.extend(data["data"])
            next_url = data["pages"]["next_url"]
            print("Got one page. Next ", next_url)
            sleep(2)

        with open("out_ass.json", "w") as d:
            json.dump(assignments, d)
    else:
        with open("out_ass.json", "r") as d:
            assignments = json.load(d)

    coll = defaultdict(lambda: defaultdict(int))
    for a in assignments:
        d = a["data"]
        t = d["subject_type"]
        s = d["srs_stage"]

        coll[t][s] += 1

    return coll


def collect_data():
    now = datetime.now()
    with open("wanikani_perf.json", "r") as f:
        data = json.load(f)

    n = test(True)

    data[str(now)] = n

    with open("wanikani_perf.json", "w") as f:
        json.dump(data, f)


if __name__ == '__main__':
    collect_data()
