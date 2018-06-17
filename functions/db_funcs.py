'''functions for retrieving and updating various database fields'''

import ast
import json
import logging
import sqlite3
import sys
from logging import Formatter, StreamHandler

import numpy as np
import pandas as pd

from functions.dt_funcs import buffer_week, get_month, get_week, new_month, now

logger = logging.getLogger('workout_logger')
formatter = Formatter('%(asctime)s | %(levelname)s | %(message)s')
sh = StreamHandler(stream=sys.stdout)
sh.setFormatter(formatter)
logger.addHandler(sh)

logger.setLevel(logging.INFO)

sqlite3.register_adapter(np.int64, lambda val: int(val))
sqlite3.register_adapter(pd.tslib.Timestamp, lambda val: str(val))
con = sqlite3.connect('workout.db', detect_types=sqlite3.PARSE_DECLTYPES)
cur = con.cursor()


def get_user_id(con, user):
    s = '''
    SELECT user_id FROM dim_user
    WHERE user_name = ?
    '''
    user_id = pd.read_sql(s, con, params=[user])
    user_id = user_id.reset_index(drop=True)
    return user_id['user_id'][0]


def table_pull(con, user_id, table):
    s = f'''
    SELECT * FROM
    {table}
    WHERE user_id = ?
    '''
    table = pd.read_sql(s, con, params=[user_id])
    return table


def table_update(con, user, table, var, val):
    user_id = get_user_id(con, user)
    s = f'''
    UPDATE {table}
    SET {var} = ?
    WHERE user_id = ?
    '''
    with con.cursor() as cur:
        cur.execute(s, params=[val, user_id])


def delete_params(df_slice):
    assert df_slice.shape[0] in (1, 0), 'must be one row'
    arg = ' AND '.join([f'{col}=?' for col in df_slice.columns])
    params = list(df_slice[col][0] for col in df_slice.columns)
    return arg, params


def table_overwrite(table, df, primary_keys, con):
    cur = con.cursor()
    existing = pd.read_sql(f'SELECT * from {table}', con)
    for i in df.index:
        df_slice = df.iloc[i:i+1].reset_index(drop=True)
        primary_slice = df_slice[primary_keys]
        match = pd.merge(primary_slice, existing, how='inner', indicator=True)
        if 'both' in match['_merge'].tolist():
            arg, params = delete_params(primary_slice)
            cur.execute(f'DELETE from {table} WHERE {arg}', params)
            print('duplicate entry deleted')
        print('new entry loaded')
        df_slice.to_sql(table, con, if_exists='append', index=False)


def retrieve_json(df, json_col):
    df = df[json_col].reset_index(drop=True)
    return ast.literal_eval(df[0])


def name_exists(name, con):
    s = '''
    SELECT DISTINCT user_name FROM dim_user
    '''
    distinct_users = pd.read_sql(s, con)
    if name in distinct_users['user_name'].tolist():
        return True
    else:
        return False


def create_user_entry(name, email, con):
    s = '''
    SELECT ? as user_name, MAX(user_id) as user_id FROM dim_user
    '''
    new_user = pd.read_sql(s, con, params=[name])

    if new_user.user_id[0] is None:
        new_user['user_id'] = 1
    else:
        new_user['user_id'] = new_user['user_id'] + 1
    new_user['email'] = email
    pause = new_user[['user_id']]
    pause.to_sql('pause_workout', con, if_exists='append', index=False)
    return new_user


def create_user(name, email, con):
    '''
    Adds new name entry to database
    '''
    assert type(name) == str, 'name must be a string'
    assert type(email) == str, 'email must be a string'

    entry = create_user_entry(name, email, con)
    entry.to_sql('dim_user', con, if_exists='append', index=False)
    print(name, 'added to dim_user')
    return entry


def pull_prog(user_id, con):
    prog = pd.read_sql(
        'SELECT * FROM dim_progression WHERE user_id = ?', con, params=[user_id])
    prog_dict = retrieve_json(prog, 'prog_dict')
    return prog_dict


def add_weight(prog_dict, orm_dict):
    new = {key: orm_dict[key]+prog_dict[key] for key in orm_dict.keys()}
    return new


def get_dates(user_id, con):
    orm = pd.read_sql(
        'SELECT * FROM one_rep_max WHERE user_id = ?', con, params=[user_id])
    if orm.shape[0] == 0:
        return None, None
    else:
        month = get_month(orm)
        week = get_week(orm)
        return month, week


def get_new_orm_dict(user_id, con):
    month, week = get_dates(user_id, con)
    if month is None:
        logger.warning('no info in one_rep_max - populate it first')
        return
    orm_dict = retrieve_json(month, 'orm_dict')
    prog_dict = pull_prog(user_id, con)
    new = add_weight(orm_dict, prog_dict)
    return new


def get_new_orm(user_id, con):
    month, week = get_dates(user_id, con)
    if month is None:
        logger.warning('no info in one_rep_max - populate it first')
        return
    start = month['data_end_date'][0] + datetime.timedelta(days=1)
    new_dates = new_month(start)
    new_orm = get_new_orm_dict(user_id, con)
    entry = pd.DataFrame({'user_id': user_id,
                          'data_start_date': new_dates[0],
                          'data_end_date': new_dates[1],
                          'orm_dict': json.dumps(new_orm),
                          'publish_time': now(date=False)}, index=[0])

    return entry[['user_id', 'data_start_date', 'data_end_date', 'orm_dict', 'publish_time']]


class DBHelper(object):
    def __init__(self, con, user, email=None):
        self._user_name = user
        self.con = con
        if name_exists(user, con) == False:
            create_user(user, email, con)
        else:
            print(f'Welcome back {user}!')
        self.user_id = get_user_id(con, user)
        # assert type(self.user_id) == int, 'user_id must be int'

    def set_dim_prog(self, prog_dict):
        assert type(prog_dict) == dict, 'prog_dict must be dict'
        entry = pd.DataFrame.from_dict(
            {0: {'user_id': self.user_id, 'prog_dict': json.dumps(prog_dict)}}, orient='index')
        table_overwrite('dim_progression', entry, ['user_id'], self.con)
        logger.info('dict is valid - dim_progression populated')
        return entry

    def set_accessory(self, accessory_df):
        cols = ['me_name', 'ae_name', 'ae_weight', 'sets', 'reps']
        for col in cols:
            assert col in accessory_df.columns, f'{col} is missing from df'
        assert accessory_df.shape == (16, 5), 'df is not the correct shape'
        for exercise in ['deadlift', 'squat', 'ohp', 'bench']:
            shape = accessory_df[accessory_df['me_name'] == exercise].shape[0]
            assert shape == 4, f'{exercise} has {shape} rows - needs to be 4'

        accessory_df = accessory_df.reset_index(drop=True)
        accessory_df['user_id'] = self.user_id
        accessory_df['publish_time'] = now(date=False)
        accessory_df.to_sql('accessory', con,
                            if_exists='append', index=False)
        logger.info('dataframe is valid - accessory populated')
        return accessory_df.head(3)

    def set_one_rep_max(self, orm_dict):
        month, week = get_dates(self.user_id, con)
        orm_dict = json.dumps(orm_dict)
        if month is not None:
            update = month.copy()
            update['orm_dict'] = orm_dict
            table_overwrite('one_rep_max', update, [
                            'user_id', 'data_start_date'], self.con)
            logger.info('dict is valid - one_rep_max overwitten')
        else:
            buffer = buffer_week()
            month = new_month()
            for dates in buffer, month:
                update = pd.DataFrame.from_dict({0: {'user_id': self.user_id,
                                                     'data_start_date': dates[0],
                                                     'data_end_date': dates[1],
                                                     'orm_dict': orm_dict,
                                                     'publish_time': now(date=False)}}, orient='index')
                table_overwrite('one_rep_max', update, [
                    'user_id', 'data_start_date'], self.con)
            logger.info('dict is valid - new entries added to one_rep_max')

    def progress_one_rep_max(self):
        orm = self.get_orm()
        if orm.shape == 0:
            new_orm = get_new_orm(self.user_id, self.con)
            new_orm.to_sql('one_rep_max', self.con,
                           if_exists='append', index=False)

    def get_orm(self):
        month, week = get_dates(self.user_id, self.con)
        if month is None:
            month = buffer_week()
        month = month.reset_index(drop=True)
        s = '''
        SELECT * FROM
        one_rep_max
        WHERE user_id = ?
        AND data_start_date = ?
        AND data_end_date = ?
        '''
        start = month['data_start_date'][0]
        end = month['data_end_date'][0]
        orm = pd.read_sql(s, con, params=[self.user_id, start, end])
        return orm

    def get_accessory(self):
        s = '''
        WITH max_time as 
        (select MAX(publish_time) as dt_max
        from accessory
        where user_id = ?)
        SELECT * from accessory
        WHERE user_id = ?
        AND publish_time = (select dt_max from max_time)
        '''
        acc = pd.read_sql(s, self.con, params=[self.user_id, self.user_id])
        cols = ['me_name', 'ae_name', 'ae_weight', 'sets', 'reps']
        return acc[cols]

    def get_active_users(self):
        entries = pd.read_sql(
            'SELECT * FROM pause_workout WHERE pause_flag = "False"', self.con)
        users = entries['user_id'].unique().tolist()
        return users