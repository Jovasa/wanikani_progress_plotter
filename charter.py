import json
import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

colors = [
    "black",
    "xkcd:dark red",
    "red",
    "orange",
    "yellow",
    "xkcd:lime",
    "green",
    "xkcd:dark green",
    "xkcd:cyan",
    "xkcd:blue",
    "xkcd:dark blue",
]


def do_chart():
    with open("wanikani_perf.json") as d:
        data = json.load(d)

    fig = plt.figure(figsize=[8, 12])
    for i, t in enumerate(["radical", "kanji", "vocabulary"]):
        ax = fig.add_subplot(311 + i)
        ax.set_title(t.capitalize())
        for x in range(0, 11):
            f = []
            s = []
            for k, v in data.items():
                f.append(datetime.datetime.fromisoformat(k))
                try:
                    s.append(v[t].get(f"{x}"))
                except KeyError:
                    s.append(0)
            if not any(a != 0 for a in s):
                continue
            ax.plot(f, s, color=colors[x])
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.show()


if __name__ == '__main__':
    do_chart()
