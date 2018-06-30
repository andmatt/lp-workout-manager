'''functions for retrieving and updating various database fields'''

import ast
import datetime
import json
import logging
import sqlite3
import sys
from logging import Formatter, StreamHandler
from logging.handlers import RotatingFileHandler

import numpy as np
import os
import pandas as pd

from functions.dt_funcs import (buffer_week, get_dates, get_latest, get_month,
                                get_week, new_month, now)

LOCAL_DIR = 'C:/Users/Matt/Dropbox/lp-workout/'
if os.path.isdir(LOCAL_DIR) == False:
    LOCAL_DIR = '.'


def get_logger():
    '''
    Returns
    -------
    logger: module
        custom logging module with stream
        and file handler
    '''
    logger = logging.getLogger('workout_logger')
    formatter = Formatter('%(asctime)s | %(levelname)s | %(message)s')
    sh = StreamHandler(stream=sys.stdout)
    sh.setFormatter(formatter)
    fh = RotatingFileHandler(
        os.path.join(LOCAL_DIR, 'workout.log'), maxBytes=10*1024*1024, backupCount=0)
    fh.setFormatter(formatter)
    logger.addHandler(sh)
    logger.addHandler(fh)
    logger.setLevel(logging.INFO)
    return logger


logger = get_logger()


def get_db_con(db='workout.db'):
    '''
    gets sqlite database connection with necessary adapters

    Parameters
    ----------
    db: str
        sqlite database name

    Returns
    -------
    con: sqlite3.Connection
    '''
    db_path = os.path.join(LOCAL_DIR, db)
    sqlite3.register_adapter(np.int64, lambda x: int(x))
    sqlite3.register_adapter(pd.Timestamp, lambda x: str(x))
    con = sqlite3.connect(db, detect_types=sqlite3.PARSE_DECLTYPES)
    return con


def create_db(con):
    '''
    Creates database tables if they do not exist

    Parameters
    ----------
    con: sqlite3.Connection
    '''
    with con:
        cur = con.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS dim_user(user_id INT, user_name STRING, email STRING)")
        cur.execute(
            "CREATE TABLE IF NOT EXISTS dim_progression(user_id INT, prog_dict JSON)")
        cur.execute("CREATE TABLE IF NOT EXISTS one_rep_max(user_id INT, data_start_date TIMESTAMP, data_end_date TIMESTAMP, orm_dict JSON, publish_time TIMESTAMP)")
        cur.execute("CREATE TABLE IF NOT EXISTS accessory(user_id INT, me_name STRING, ae_name STRING, ae_weight FLOAT, sets INT, reps INT, publish_time TIMESTAMP)")
        cur.execute("CREATE TABLE IF NOT EXISTS pause_workout(user_id INT, pause_date TIMESTAMP DEFAULT '2999-12-31 23:59:59', pause_flag BOOLEAN DEFAULT False)")


def table_pull(con, user_id, table):
    '''
    Wrapper function to pull an entire table given 
    a user_id and table name

    Parameters
    ----------
    con: sqlite3.Connection
    user_id: int
    table: str
    '''
    s = f'''
    SELECT * FROM
    {table}
    WHERE user_id = ?
    '''
    table = pd.read_sql(s, con, params=[user_id])
    return table


def table_update(con, user_id, table, var, val):
    '''
    Wrapper function for updating a table

    Parameters
    ----------
    con: sqlite3.Connection
    user_id: int
    table: str
    var: str
        column in table to update
    val: obj, varying
        value to update with
    '''
    s = f'''
    UPDATE {table}
    SET {var} = ?
    WHERE user_id = ?
    '''
    with con.cursor() as cur:
        cur.execute(s, params=[val, user_id])


def delete_params(df_slice):
    '''
    Returns sql arguments for table_overwrite
    function

    Parameters
    ----------
    df_slice: obj, pandas df
        one row dataframes containing columns that match
        the primary keys of a database table

    Returns
    -------
    arg: str
        WHERE argument to pass df_slice values
        into a DELETE sql query to 
    params: list
        list of params corresponding to df_slice values
        to delete from table if there is a match

    Raises
    ------
    AssertionError
        If df_slice is not one row
    '''
    assert df_slice.shape[0] in (1, 0), 'must be one row'
    arg = ' AND '.join([f'{col}=?' for col in df_slice.columns])
    params = list(df_slice[col][0] for col in df_slice.columns)
    return arg, params


def table_overwrite(table, df, primary_keys, con):
    '''
    Appends a df to a table. Iterates through the df
    row-wise and overwrites primary-key matches

    Parameters
    ----------
    table: str
        table name
    df: obj, pandas df
        dataframe to add to db table
    primary_keys: list of str
        list of column name(s) that act as the
        table primary key
    con: sqlite3.Connection
    '''
    cur = con.cursor()
    existing = pd.read_sql(f'SELECT * from {table}', con)
    for i in df.index:
        df_slice = df.iloc[i:i+1].reset_index(drop=True)
        primary_slice = df_slice[primary_keys]
        match = pd.merge(primary_slice, existing, how='inner', indicator=True)
        if 'both' in match['_merge'].tolist():
            arg, params = delete_params(primary_slice)
            cur.execute(f'DELETE from {table} WHERE {arg}', params)
            logger.info('duplicate entry deleted')
        logger.info('new entry loaded')
        df_slice.to_sql(table, con, if_exists='append', index=False)


def retrieve_json(df, json_col):
    '''
    Retrieves a dictionary from a JSON
    column

    Parameters
    ----------
    df: obj, pandas df
        must be one row
    json_col: str
        column name with JSON

    Returns
    -------
    obj, dict
    '''
    df = df[json_col].reset_index(drop=True)
    return ast.literal_eval(df[0])


def name_exists(name, con):
    '''
    Checks if a name is already present in dim_user

    Parameters
    ----------
    name: str
    con: sqlite3.Connection

    Returns
    -------
    bool
        TRUE if name exists, else FALSE
    '''
    s = '''
    SELECT DISTINCT user_name FROM dim_user
    '''
    distinct_users = pd.read_sql(s, con)
    if name in distinct_users['user_name'].tolist():
        return True
    else:
        return False


def get_user_id(user, con):
    '''
    Gets the user_id that corresponds to a user_name
    in dim_user

    Parameters
    ----------
    user: str
    con: sqlite3.Connection
    '''
    s = '''
    SELECT user_id FROM dim_user
    WHERE user_name = ?
    '''
    user_id = pd.read_sql(s, con, params=[user])
    user_id = user_id.reset_index(drop=True)
    return user_id['user_id'][0]


def create_user_entry(name, email, con):
    '''
    Creates a new entry for dim_user

    Parameters
    ----------
    name: your name
    email: your email
    con: sqlite3.Connection

    Returns
    -------
    new_user: obj, pandas df
        the entry will be uploaded
    '''
    s = '''
    SELECT ? as user_name, MAX(user_id) as user_id FROM dim_user
    '''
    new_user = pd.read_sql(s, con, params=[name])

    if new_user.user_id[0] is None:
        new_user['user_id'] = 1
    else:
        new_user['user_id'] = new_user['user_id'] + 1
    new_user['email'] = email
    return new_user


def create_user(name, email, con):
    '''
    Uploads new user entry to dim_users and creates the
    corresponding default entry in `pause_workout`

    Parameters
    ----------
    name: your name
    email: your email
    con: sqlite3.Connection

    Returns
    -------
    entry: obj, pandas df
        the entry will be uploaded

    Raises
    ------
    AssertionError
        if name is not a string
    AssertionError
        if email is not a string
    '''
    assert type(name) == str, 'name must be a string'
    assert type(email) == str, 'email must be a string'

    entry = create_user_entry(name, email, con)
    entry.to_sql('dim_user', con, if_exists='append', index=False)

    pause = entry[['user_id']]
    pause.to_sql('pause_workout', con, if_exists='append', index=False)

    logger.info('%s added to dim_user', name)
    return entry


def pull_prog(user_id, con):
    '''
    Pulls progression dictionary for a user_id

    Parameters
    ----------
    user_id: int
    con: sqlite3.Connection

    Returns
    -------
    prog_dict: obj, dict
    '''
    prog = pd.read_sql(
        'SELECT * FROM dim_progression WHERE user_id = ?', con, params=[user_id])
    if prog.shape[0] == 0:
        logger.warning('No progression dict loaded')
        return None
    prog_dict = retrieve_json(prog, 'prog_dict')
    return prog_dict


def add_dicts(dict1, dict2):
    '''
    Adds values of two dictionaries together
    by keys in the first dictionary

    Parameters
    ----------
    dict1: obj, dict
    dict2: obj, dict

    Returns
    -------
    new: obj, dict
        dict1 + values from dict2
    '''
    new = {key: dict1[key]+dict2[key] for key in dict1.keys()}
    return new


def get_new_orm_dict(one_rep_max, user_id, con, prog_dict=None):
    '''
    Adds progression weights to the latest entry
    from a df pulled from one_rep_max

    Parameters
    ----------
    one_rep_max: obj, pandas df
        df pulled from one_rep_max table
        for one user
    user_id: int
    con: sqlite3.Connection

    Returns
    -------
    new: obj, dict
        new orm dict with progression weights added
    '''
    latest = get_latest(one_rep_max)
    if latest is None:
        logger.warning('no info in one_rep_max - populate it first')
        return
    orm_dict = retrieve_json(latest, 'orm_dict')
    if prog_dict is None:
        prog_dict = pull_prog(user_id, con)
        assert prog_dict is not None, 'dim_progression is not populated'
    new = add_dicts(orm_dict, prog_dict)
    return new


def get_new_orm(one_rep_max, user_id, con, week=1):
    '''
    Retrieves one_rep_max entry, and creates
    a new entry for the next month

    Parameters
    ----------
    one_rep_max: obj, pandas df
        one_rep_max table
    user_id: int
    con: sqlite3.Connection
    week: int, optional
        week to start month on

    Returns
    -------
    obj, pandas df
        new entry for one_rep_max
    '''
    latest = get_latest(one_rep_max)
    if latest is None:
        logger.warning('no info in one_rep_max - populate it first')
        return
    start = latest['data_end_date'][0] + datetime.timedelta(days=1)
    new_dates = new_month(start, timeskip='forward', week=week)
    new_orm = get_new_orm_dict(one_rep_max, user_id, con)
    entry = pd.DataFrame({'user_id': user_id,
                          'data_start_date': new_dates[0],
                          'data_end_date': new_dates[1],
                          'orm_dict': json.dumps(new_orm),
                          'publish_time': now(date=False)}, index=[0])

    return entry[['user_id', 'data_start_date', 'data_end_date', 'orm_dict', 'publish_time']]


class DBHelper(object):
    '''
    Class for performing all database operations for
    the workout puller process

    Parameters
    ----------
    con: sqlite3.Connection
    user: str
        name of user in dim_users
    email: str, optional
        email of username - only needed if user has not yet
        been populated in dim_users
    '''

    def __init__(self, con, user, email=None):
        self._user_name = user
        self.con = con
        if name_exists(user, con) == False:
            create_user(user, email, con)
        else:
            print(f'Welcome back {user}!')
        self.user_id = get_user_id(user, con)
        self.user = user
        # assert type(self.user_id) == int, 'user_id must be int'

    def set_dim_prog(self, prog_dict):
        '''
        Sets dim_progression

        Parameters
        ----------
        prog_dict: obj, dict

        Raises
        ------
        AssertionError
            if prog_dict is not a dict
        '''
        assert type(prog_dict) == dict, 'prog_dict must be dict'
        entry = pd.DataFrame.from_dict(
            {0: {'user_id': self.user_id, 'prog_dict': json.dumps(prog_dict)}}, orient='index')
        table_overwrite('dim_progression', entry, ['user_id'], self.con)
        logger.info('dict is valid - dim_progression populated')
        return entry

    def set_accessory(self, accessory_df):
        '''
        Loads entries to accessory table

        Parameters
        ----------
        accessory_df: obj, pandas df

        Raises
        ------
        AssertionError: if accessory_df is not the correct dimensions
        and does not have the correct column names
        '''
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
        accessory_df.to_sql('accessory', self.con,
                            if_exists='append', index=False)
        logger.info('dataframe is valid - accessory populated')
        return accessory_df.head(3)

    def set_one_rep_max(self, orm_dict, start_week=None):
        '''
        Sets one_rep_max for the current month

        Parameters
        ----------
        orm_dict: obj, dict
        week: int, optional
            starting week

        Notes
        -----
        * If an entry exists for this month, it will be overwritten
        * If an entry does not exist, it will create a new month entry 
        starting on next Sunday
        * If there is no entry for this current week, it will create a 
        "buffer_week" entry with the same weights so something will still
        be able to be pulled
        *TODO: Add functionality to set what week the workout starts on
        (parameterize month creation)
        '''
        month, week = get_dates(self.user_id, self.con)
        full_orm = table_pull(self.con, self.user_id, 'one_rep_max')
        orm_dict = json.dumps(orm_dict)
        buffer = buffer_week()
        if month is not None:
            if month['data_start_date'][0] == buffer[0] and month['data_end_date'][0] == buffer[1]:
                logger.warning(
                    'Overwriting entry after buffer week - make sure this is what you wanted')
                month = None
        if month is not None:
            update = month.copy()
            if start_week is not None:
                new_dates = new_month(week=start_week)
                update['data_end_date'] = new_dates[1]
                logger.info('start week set to %s', start_week)
            update['orm_dict'] = orm_dict
            table_overwrite('one_rep_max', update, [
                            'user_id', 'data_start_date'], self.con)
            logger.info('dict is valid - one_rep_max overwitten')
        else:
            need_buffer = True
            # only add buffer week if needed
            if full_orm.shape[0] > 0:
                for i in [0, 1]:
                    match = get_month(full_orm, custom_dt=buffer[i])
                    if match.shape[0] > 0:
                        need_buffer = False
            if need_buffer == False:
                logger.info('buffer week not needed')
            if start_week is None:
                start_week = 1
            new_dates = [new_month(week=start_week)]
            if need_buffer == True:
                new_dates = new_dates + [buffer]
            for dates in new_dates:
                update = pd.DataFrame.from_dict({0: {'user_id': self.user_id,
                                                     'data_start_date': dates[0],
                                                     'data_end_date': dates[1],
                                                     'orm_dict': orm_dict,
                                                     'publish_time': now(date=False)}}, orient='index')
                table_overwrite('one_rep_max', update, [
                    'user_id', 'data_start_date'], self.con)
            logger.info('dict is valid - new entries added to one_rep_max')

    def progress_one_rep_max(self):
        '''
        Adds progression_dict onto one_rep_max until the current
        month is populated. 

        Notes
        -----
        Does nothing if one_rep_max is empty or the current month is already populated
        '''
        orm = self.get_orm()
        if orm is None:
            full_orm = table_pull(self.con, self.user_id, 'one_rep_max')
            if full_orm.shape[0] == 0:
                logger.warning(
                    'No orm weights are set - you must seed the db with your starting weight using self.set_one_rep_max')
                return None
            else:
                while orm is None:
                    latest = get_latest(full_orm)
                    new_orm = get_new_orm(full_orm, self.user_id, self.con)
                    new_orm.to_sql('one_rep_max', self.con,
                                   if_exists='append', index=False)
                    logger.info('orm progressed by one month')
                    orm = self.get_orm()
        else:
            logger.info(
                'using current orm - use self.set_one_rep_max if you wish to modify it')

    def get_orm(self):
        '''
        Gets one_rep_max for this month

        Returns
        -------
        orm: obj, pandas df
        None
            If there is no one_rep_max populated
        '''
        month, week = get_dates(self.user_id, self.con)
        if month is None:
            return None
        s = '''
        SELECT * FROM
        one_rep_max
        WHERE user_id = ?
        AND data_start_date = ?
        AND data_end_date = ?
        '''
        start = month['data_start_date'][0]
        end = month['data_end_date'][0]
        orm = pd.read_sql(s, self.con, params=[self.user_id, start, end])
        return orm

    def get_accessory(self):
        '''
        Gets most recently published accessory df from database

        Returns
        -------
        obj, pandas df
        '''
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

    def pause_workout(self):
        '''
        Flags workout as paused
        '''
        table_update(self.con, self.user_id,
                     'pause_workout', 'pause_flag', 'True')
        table_update(self.con, self.user_id,
                     'pause_workout', 'pause_date', now())
        logger.info('Workout paused')

    def unpause_workout(self):
        '''
        Flags workout as unpaused and attempts to set new orm
        using the latest value in the db
        '''
        table_update(self.con, self.user_id,
                     'pause_workout', 'pause_flag', 'False')
        no_prog = {'squat': 0, 'deadlift': 0, 'ohp': 0, 'bench': 0}
        orm_dict = get_new_orm_dict(
            one_rep_max, user_id, con, prog_dict=no_prog)
        self.set_one_rep_max(orm_dict, start_week=1)
        logger.info('Workout unpaused')

    def get_active_users(self):
        '''
        Gets users that have not paused their workout

        Returns
        -------
        users: list of int
            list of user_ids
        '''
        entries = pd.read_sql(
            'SELECT * FROM pause_workout WHERE pause_flag = "False"', self.con)
        users = entries['user_id'].unique().tolist()
        return users
