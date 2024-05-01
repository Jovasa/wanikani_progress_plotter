import json


def main():
    subject_types = ["radical", "kanji", "vocabulary"]

    with open("assignments.json") as assin, open("simplejson_out.json", "w") as out:
        data = json.load(assin)
        out_data = dict()

        for date, d in data.items():
            daily_totals = do_one_instance(d, subject_types)
            out_data[date] = daily_totals

        json.dump(out_data, out)


def do_one_instance(d, subject_types):
    daily_totals = {t: {str(x): 0 for x in range(0, 10)} for t in subject_types}
    for subject in d:
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
        data_subject_type_ = subject["data"]["subject_type"]
        if data_subject_type_ == "kana_vocabulary":
            data_subject_type_ = "vocabulary"
        daily_totals[data_subject_type_][str(subject["data"]["srs_stage"])] += 1
    return daily_totals


if __name__ == '__main__':
    main()