'''functions for performing various datetime operations'''
import datetime
import pytz


def now(tz='US/Eastern', date=True):
    ts = datetime.datetime.now(pytz.timezone(tz))
    ts = ts.replace(tzinfo=None)
    if date == True:
        ts = ts.replace(hour=0, minute=0, second=0, microsecond=0)
    return ts


def buffer_week():
    back_to_sunday = now().weekday() + 1
    start = now() - datetime.timedelta(days=back_to_sunday)
    end = start + datetime.timedelta(days=6)
    return start, end


def new_month(start=None):
    if start is not None:
        assert start.weekday() == 6, 'Week starts on Sunday'
    else:
        to_sunday = 6 - now().weekday()
        start = now() + datetime.timedelta(days=to_sunday)
    end = start + datetime.timedelta(days=27)
    return start, end


def get_month(one_rep_max):
    dt = now(date=True)
    bix = one_rep_max.apply(
        lambda x: x['data_start_date'] <= dt <= x['data_end_date'], axis=1)
    return one_rep_max[bix].reset_index(drop=True)


def get_week(one_rep_max):
    dt = now(date=False)
    month = get_month(one_rep_max).reset_index(drop=True)
    start = month['data_start_date'][0]
    end = month['data_end_date'][0]
    if (end-start).days == 6:
        week = 1
        return week

    for week in range(1, 5):
        days = week * 7 - 1
        if start <= dt <= start + datetime.timedelta(days):
            return week
