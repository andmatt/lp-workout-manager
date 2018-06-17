'''functions for performing various datetime operations'''
import datetime
import pandas as pd
import pytz


def now(tz='US/Eastern', date=True):
    ts = datetime.datetime.now(pytz.timezone(tz))
    ts = ts.replace(tzinfo=None)
    if date == True:
        ts = ts.replace(hour=0, minute=0, second=0, microsecond=0)
    return ts


def buffer_week():
    start = pd.to_datetime(now())
    back_to_sunday = start.dayofweek + 1
    start = start - datetime.timedelta(days=back_to_sunday)
    end = start + datetime.timedelta(days=6)
    return start, end


def new_month(start=None, timeskip='forward'):
    '''
    Add a feature to use math to set the week of the new_month
    '''
    if start is not None:
        assert start.weekday() == 0, 'Week starts on Sunday'
    else:
        start = pd.to_datetime(now())

    assert timeskip in ['forward', 'back'], 'start must be "forward" or "back"'
    if timeskip == 'forward':
        to_sunday = 6 - start.dayofweek
        start = start + datetime.timedelta(days=to_sunday)
    else:
        back_to_sunday = start.dayofweek + 1
        start = start - datetime.timedelta(days=back_to_sunday)

    end = start + datetime.timedelta(days=27)
    return start, end


def get_month(one_rep_max, custom_dt=None):
    if custom_dt is None:
        dt = now(date=True)
    else:
        dt = custom_dt
    bix = one_rep_max.apply(
        lambda x: x['data_start_date'] <= dt <= x['data_end_date'], axis=1)
    month = one_rep_max[bix].reset_index(drop=True)
    if month.shape[0] == 0:
        return None
    else:
        return month


def get_week(one_rep_max):
    dt = now(date=False)
    month = get_month(one_rep_max)
    if month is None:
        return None
    month = month.reset_index(drop=True)
    start = month['data_start_date'][0]
    end = month['data_end_date'][0]
    if (end-start).days == 6:
        week = 1
        return week

    for week in range(1, 5):
        days = week * 7 - 1
        if start <= dt <= start + datetime.timedelta(days):
            return week


def get_latest(one_rep_max):
    if one_rep_max.shape[0] == 0:
        return None
    max_date = one_rep_max['data_end_date'].max()
    latest = one_rep_max[one_rep_max['data_end_date']
                         == max_date].reset_index(drop=True)
    return latest


def get_dates(user_id, con):
    orm = pd.read_sql(
        'SELECT * FROM one_rep_max WHERE user_id = ?', con, params=[user_id])
    if orm.shape[0] == 0:
        return None, None
    else:
        month = get_month(orm)
        week = get_week(orm)
        return month, week
