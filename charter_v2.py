from __future__ import annotations

import datetime
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

from wanikani_api import UserHandle

import json

colors = [
    "black",
    "xkcd:dark red",
    "red",
    "orange",
    "xkcd:yellow",
    "xkcd:lime",
    "green",
    "xkcd:dark green",
    "xkcd:cyan",
    "xkcd:blue",
    "xkcd:dark blue",
]

temp = (Path(__file__) / ".." / "wanikani_token").resolve()
with open(temp, "r") as temp_file:
    wanikani_token = temp_file.read()


def iso_year_week_date_to_week_date(iso_year, iso_week, iso_day, current_year):
    return [iso_year * 52 + iso_week, iso_day]


def calendar_array(dates, data):
    current_year = datetime.datetime.now().isocalendar()[0]
    i, j = zip(*[iso_year_week_date_to_week_date(*d.isocalendar()[:], current_year) for d in dates])
    i = np.array(i) - min(i)
    j = np.array(j) - 1
    ni = max(i) + 1

    calendar = np.nan * np.zeros((ni, 7))
    calendar[i, j] = data
    return i, j, calendar


def calendar_heatmap(ax, dates, data):
    i, j, calendar = calendar_array(dates, data)
    im = ax.imshow(calendar, interpolation='none', cmap='summer')
    label_days(ax, data, i, j, calendar)
    label_months(ax, dates, i, j, calendar)
    ax.figure.colorbar(im)


def label_days(ax, dates, i, j, calendar):
    ni, nj = calendar.shape
    day_of_month = np.nan * np.zeros((ni, 7))
    day_of_month[i, j] = [d for d in dates]

    for (i, j), day in np.ndenumerate(day_of_month):
        if np.isfinite(day):
            ax.text(j, i, int(day), ha='center', va='center')

    ax.set(xticks=np.arange(7),
           xticklabels=['M', 'T', 'W', 'T', 'F', 'S', 'S'])
    ax.xaxis.tick_top()


def label_months(ax, dates, i, j, calendar):
    month_labels = np.array(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul',
                             'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
    months = np.array([d.month for d in dates])
    uniq_months = sorted(set(months))
    yticks = [i[months == m].mean() for m in uniq_months]
    labels = [month_labels[m - 1] for m in uniq_months]
    ax.set(yticks=yticks)
    ax.set_yticklabels(labels, rotation=90)


def get_subjects(user: UserHandle):
    cached = {int(x["id"]): x
              for x in user._subject_cache.find({"object": {"$in": ["radical", "kanji", "vocabulary"]}})}
    if len(cached) > 1000:
        return cached

    subjects = user.get_subjects()
    temp2 = [x for x in subjects]
    for k in temp2:
        k["_id"] = str(k["_id"])
    s = {int(x["id"]): x for x in temp2}
    return s


def get_levels(user: UserHandle, last_updated: datetime.datetime):
    up = user.get_level_progressions(updated_after=last_updated)
    print(f"updated {len([x for x in up])} levels")
    return [x for x in user._personal_cache.find({"object": "level_progression"})]


def get_reviews(user: UserHandle, last_updated: datetime.datetime):
    up = user.get_reviews(updated_after=last_updated)
    print(f"updated {len([x for x in up])} reviews")
    return [x for x in user._personal_cache.find({"object": "review"})]


def get_assignments(user: UserHandle, last_updated: datetime.datetime):
    up = user.get_assignments(updated_after=last_updated)
    print(f"updated {len([x for x in up])} assignments")
    return [x for x in user._personal_cache.find({"object": "assignment"})]


def main():
    try:
        with open("last_done.txt") as l:
            last_done = datetime.datetime.fromisoformat(l.read())
    except FileNotFoundError:
        last_done = None

    user = UserHandle(wanikani_token)
    data = get_reviews(user=user, last_updated=last_done)
    subjects = get_subjects(user)
    subjects = {int(k): v for k, v in subjects.items()}

    level_ups = get_levels(user, last_done)

    assignments = get_assignments(user, last_updated=last_done)
    with open("assignments.json", "r") as f:
        old = json.load(f)
        temp = assignments.copy()
        for a in temp:
            del a["_id"]
        old[str(datetime.datetime.utcnow())] = temp
    with open("assignments.json", "w") as f:
        json.dump(old, f, default=str)

    hourly_data = defaultdict(lambda: defaultdict(dict))
    hourly_answer_ratio = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    subject_spent_on_stage = defaultdict(lambda: defaultdict(float))
    subject_previous_completion = dict()
    weekly_wrong_answers_by_starting_level = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    weekly_correct_answers_by_starting_level = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    daily_level_change = defaultdict(lambda: defaultdict(int))
    daily_review_count = defaultdict(lambda: defaultdict(int))
    for r in data:
        # {"_id": "6366400b421d07cd976aeff9", "id": 2751167231, "object": "review",
        # "data": {"created_at": "2022-08-15T13:49:17.663000",
        #          "assignment_id": 303237383,
        #          "subject_id": 8,
        #          "spaced_repetition_system_id": 2,
        #          "starting_srs_stage": 1,
        #          "ending_srs_stage": 2,
        #          "incorrect_meaning_answers": 0, "incorrect_reading_answers": 0},
        # "data_updated_at": "2022-08-15T13:49:17.682000", "url": "https://api.wanikani.com/v2/reviews/2751167231"},
        d = r["data"]
        date_and_hour: datetime.datetime = r["data_updated_at"]
        date_and_hour -= datetime.timedelta(minutes=date_and_hour.minute, seconds=date_and_hour.second,
                                            microseconds=date_and_hour.microsecond)
        date = date_and_hour - datetime.timedelta(hours=date_and_hour.hour)

        object_type = subjects[int(d["subject_id"])]["object"]

        ending_srs_stage = d["ending_srs_stage"]

        hourly_data[object_type][date_and_hour][d["subject_id"]] = ending_srs_stage
        hourly_answer_ratio[object_type][date_and_hour]["meaning_answers"] += d["incorrect_meaning_answers"] + 1
        hourly_answer_ratio[object_type][date_and_hour]["incorrect_meaning_answers"] += d["incorrect_meaning_answers"]
        hourly_answer_ratio[object_type][date_and_hour]["reading_answers"] += d["incorrect_reading_answers"] + 1
        hourly_answer_ratio[object_type][date_and_hour]["incorrect_reading_answers"] += d["incorrect_reading_answers"]

        if d["starting_srs_stage"] >= d["ending_srs_stage"]:
            weekly_wrong_answers_by_starting_level \
                [object_type][(date_and_hour.isocalendar().year, date_and_hour.isocalendar().week)][
                d["starting_srs_stage"]] += 1
        else:
            weekly_correct_answers_by_starting_level \
                [object_type][(date_and_hour.isocalendar().year, date_and_hour.isocalendar().week)][
                d["starting_srs_stage"]] += 1

        if d["subject_id"] in subject_previous_completion:
            subject_spent_on_stage[d["subject_id"]][d["starting_srs_stage"]] \
                += (date_and_hour - subject_previous_completion[d["subject_id"]]).total_seconds() / 60
        subject_previous_completion[d["subject_id"]] = date_and_hour

        daily_review_count[object_type][date] += 1
        daily_level_change[object_type][date] += d["ending_srs_stage"] - d["starting_srs_stage"]

    accumulated = dict()
    object_types = ["radical", "kanji", "vocabulary"]
    for t in object_types:
        accumulated[t] = dict()
        keys = sorted(hourly_data[t].keys())
        current_states = dict()
        for k in keys:
            totals = [0 for x in range(10)]
            for subject_id, srs_stage in hourly_data[t][k].items():
                current_states[subject_id] = srs_stage
            for stage in current_states.values():
                totals[stage] += 1
            accumulated[t][k] = totals

    for o_t in object_types:
        for date, data in old.items():
            date = datetime.datetime.fromisoformat(date)
            totals = [0 for x in range(10)]
            for o in data:
                t = o["data"]["subject_type"]
                if t != o_t:
                    continue
                totals[o["data"]["srs_stage"]] += 1
            accumulated[o_t][date] = totals

    accumulated_accuracy = dict()
    for t in object_types:
        accumulated_accuracy[t] = defaultdict(lambda: defaultdict(int))
        keys: Iterable[datetime.datetime] = sorted(hourly_answer_ratio[t].keys())
        for k in keys:
            week = k.isocalendar().week
            year = k.isocalendar().year
            for answer_type in ["meaning_answers", "incorrect_meaning_answers",
                                "reading_answers", "incorrect_reading_answers"]:
                accumulated_accuracy[t][(year, week)][answer_type] += hourly_answer_ratio[t][k][answer_type]

    fig = plt.figure(num=0, figsize=[15, 13])
    for i, t in enumerate(object_types):
        ax = fig.add_subplot(311 + i)
        ax.set_title(t.capitalize())
        labels = []
        xticks = []
        place = 0
        coloring = {
            "meaning_answers": "orange",
            "reading_answers": "blue"
        }
        for (year, week), weekly_data in accumulated_accuracy[t].items():
            for m in ["reading_answers", "meaning_answers"]:
                if t == "radical" and m == "reading_answers":
                    continue
                place += 1
                if weekly_data[m] == 0:
                    continue
                ax.bar(place, 1 - weekly_data[f"incorrect_{m}"] / weekly_data[m], color=coloring[m], width=1)
                ax.annotate(f'{weekly_data[m] - weekly_data[f"incorrect_{m}"]}\n/\n{weekly_data[m]}',
                            (place, 0.5),
                            (place, 0.5),
                            horizontalalignment="center",
                            color="black" if m == "meaning_answers" else "white")
            xticks.append(place if t == "radical" else place - 0.5)
            labels.append(f"{year}\nw{week}")
            place += 0.5
        ax.set_xticks(xticks)
        ax.set_xticklabels(labels)

        ax.set_yticks([x / 10 for x in range(0, 11)])
        ax.set_yticklabels([f"{x * 10}%" for x in range(0, 11)])

        ax.yaxis.grid(True)
        if t == "radical":
            ax.legend(["meaning"], loc="lower left")
        else:
            ax.legend(["meaning", "reading"], loc="lower left")
    fig.show()

    for o in object_types:
        for day in daily_review_count[o]:
            daily_level_change[o][day] /= daily_review_count[o][day]

    fig = plt.figure(num=5, figsize=[10, 13])
    for i, t in enumerate(object_types):
        ax = fig.add_subplot(311 + i)
        ax.set_title(t.capitalize())
        ax.plot(daily_level_change[t].keys(), daily_level_change[t].values())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y\n%m-%d'))

    fig.show()

    window_width = 7
    fig = plt.figure(num=6, figsize=[10, 13])
    for i, t in enumerate(object_types):
        ax = fig.add_subplot(311 + i)
        ax.set_title(t.capitalize())
        cum_sum = np.cumsum(np.insert([x for x in daily_level_change[t].values()], 0, 0))
        ma_vec = (cum_sum[window_width:] - cum_sum[:-window_width]) / window_width
        ax.plot([x for x in daily_level_change[t].keys()][window_width // 2:-((window_width - 1) // 2)], ma_vec)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y\n%m-%d'))

    fig.show()

    fig = plt.figure(num=1, figsize=[10, 13])
    for i, t in enumerate(object_types):
        has_data = [False for x in range(10)]
        ax = fig.add_subplot(311 + i)
        ax.set_title(t.capitalize())
        labels = []
        maximum = 0
        for x in range(1, 10):
            f = []
            s = []
            for k, v in accumulated[t].items():
                if v[x] == 0 and not has_data[x]:
                    if len(f) == 0:
                        f.append(k)
                        s.append(0)
                    else:
                        f[0] = k
                    continue
                f.append(k)
                s.append(v[x])
                maximum = max(maximum, v[x])
                has_data[x] = True
            if not any(a != 0 for a in s):
                continue
            ax.plot(f, s, color=colors[x])
            labels.append(str(x))
        ax.legend(labels, loc="upper left", ncol=3 if has_data[9] else 4)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y\n%m-%d'))
        ax.vlines([x["data"]["passed_at"] for x in level_ups], 0, maximum, linestyles="dashed", zorder=-1)
        print(maximum)
    fig.show()

    fig = plt.figure(num=2, figsize=[12, 13])
    for i, t in enumerate(object_types):
        ax = fig.add_subplot(311 + i)
        ax.set_title(t.capitalize())
        place = 0
        legend = [_ for _ in range(1, 9)]
        labels = []
        for k, v in weekly_correct_answers_by_starting_level[t].items():
            if k[0] != 2023:
                continue

            labels.append(f"{k[0]}\nw{k[1]}")
            place += 2
            correct = [0 for x in range(10)]
            total = [0 for x in range(10)]
            for x in range(1, 10):
                correct[x] += v[x]
                total[x] += v[x] + weekly_wrong_answers_by_starting_level[t][k][x]

                if total[x] > 0:
                    legend[x - 1] = ax.bar(place, correct[x] / total[x], color=colors[x], width=1)
                place += 1

        ax.legend(legend, [x for x in range(1, 9)], ncol=9, loc="lower center")
        ax.set_xticks([x * 11 + 5.5 for x in range(len(labels))])
        ax.set_xticklabels(labels)
        ax.set_yticks([x / 10 for x in range(0, 11)])
        ax.set_yticklabels([f"{x * 10}%" for x in range(0, 11)])
        ax.yaxis.grid(True)
        ax.set_ybound(0, 1.05)
    fig.show()

    apprentice = list()
    guru = list()
    master = list()
    enlightened = list()
    burned = list()
    for subject, d in subject_spent_on_stage.items():
        apprentice.append((subject, sum(d[x] for x in range(1, 5))))
        guru.append((subject, sum(d[x] for x in range(5, 7))))
        master.append((subject, sum(d[x] for x in range(7, 8))))
        enlightened.append((subject, sum(d[x] for x in range(8, 9))))
        burned.append((subject, sum(d[x] for x in range(9, 10))))

    apprentice.sort(key=lambda x: x[1], reverse=True)
    guru.sort(key=lambda x: x[1], reverse=True)
    master.sort(key=lambda x: x[1], reverse=True)
    enlightened.sort(key=lambda x: x[1], reverse=True)
    burned.sort(key=lambda x: x[1], reverse=True)

    for k in [apprentice, guru, master, enlightened, burned]:
        for (subject, time) in k[:20]:
            print(f"{time} {subjects[subject]} ")
        print()

    today = datetime.datetime.now()
    today -= datetime.timedelta(seconds=today.second,
                                hours=today.hour,
                                minutes=today.minute,
                                microseconds=today.microsecond)
    assignment_due_date_counts_by_subject_and_stage = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for a in assignments:
        """
        {
          "id": 80463006,
          "object": "assignment",
          "url": "https://api.wanikani.com/v2/assignments/80463006",
          "data_updated_at": "2017-10-30T01:51:10.438432Z",
          "data": {
            "created_at": "2017-09-05T23:38:10.695133Z",
            "subject_id": 8761,
            "subject_type": "radical",
            "srs_stage": 8,
            "unlocked_at": "2017-09-05T23:38:10.695133Z",
            "started_at": "2017-09-05T23:41:28.980679Z",
            "passed_at": "2017-09-07T17:14:14.491889Z",
            "burned_at": null,
            "available_at": "2018-02-27T00:00:00.000000Z",
            "resurrected_at": null,
            "hidden": false
          }
        }
        """
        due_date = a["data"]["available_at"]
        if due_date is None:
            continue
        due_date -= datetime.timedelta(hours=due_date.hour,
                                       minutes=due_date.minute,
                                       seconds=due_date.second,
                                       microseconds=due_date.microsecond)
        due_date = max(due_date, today)
        assignment_due_date_counts_by_subject_and_stage[
            a["data"]["subject_type"]
        ][
            a["data"]["srs_stage"]
        ][
            due_date
        ] += 1

    fig = plt.figure(figsize=(17, 12), num=4)
    for j, t in enumerate(object_types):
        for i in range(1, 6):

            if i == 1:
                data = assignment_due_date_counts_by_subject_and_stage[t][i].copy()
                for k, v in assignment_due_date_counts_by_subject_and_stage[t][i + 1].items():
                    data[k] += v
                for k, v in assignment_due_date_counts_by_subject_and_stage[t][i + 2].items():
                    data[k] += v
                for k, v in assignment_due_date_counts_by_subject_and_stage[t][i + 3].items():
                    data[k] += v
            if i == 2:
                data = assignment_due_date_counts_by_subject_and_stage[t][5].copy()
            if i == 3:
                data = assignment_due_date_counts_by_subject_and_stage[t][6].copy()
            if i == 4:
                data = assignment_due_date_counts_by_subject_and_stage[t][7].copy()
            if i == 5:
                data = assignment_due_date_counts_by_subject_and_stage[t][8].copy()

            if len(data) == 0:
                continue
            ax = plt.subplot2grid((3, 5), (j, i - 1))
            calendar_heatmap(ax,
                             data.keys(),
                             [x for x in data.values()]
                             )
    fig.show()
    # plt.waitforbuttonpress()

    with open("last_done.txt", "w") as l:
        l.write(datetime.datetime.utcnow().isoformat())


if __name__ == '__main__':
    main()
