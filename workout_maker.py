#! /usr/bin/python

import datetime
import os
import sys

import pandas as pd

from functions.db_funcs import DBHelper, get_db_con, LOCAL_DIR, logger, retrieve_json, table_pull
from functions.dt_funcs import get_week, get_full_dates, backfill_dates
from functions.html_funcs import (accessory_html_gen, border_apply, full_html,
                                  html_wrap, ref_html_gen)
from functions.workout_funcs import get_workout
from functions.viz_funcs import format_orm, plot_orm

con = get_db_con()


class WorkoutMaker(DBHelper):
    '''
    Class for performing all operations needed to generate the 
    workout HTML output

    Parameters
    ----------
    con: sqlite3.Connection
    user: str
        name of user in dim_users
    email: str, optional
        email of username - only needed if user has not yet
        been populated in dim_users

    Notes
    -----
    Inherits database query functions from functions.db_funcs.DBHelper
    '''

    def __init__(self, con, user, email=None):
        DBHelper.__init__(self, con, user, email)
        self.workout_df = None

    def create_workout_df(self):
        '''
        Runs code to generate the raw df for the 
        main workout
        '''
        self.progress_one_rep_max()
        orm = self.get_orm().reset_index(drop=True)
        week = get_week(orm)
        orm_dict = retrieve_json(orm, 'orm_dict')
        self.workout_df = get_workout(orm_dict, weeks=[week])
    
    def create_orm_html(self):
        '''
        converts orm df to html
        '''
        orm = pd.DataFrame(retrieve_json(self.get_orm(), 'orm_dict'), index=[0])
        orm = orm[['deadlift', 'squat', 'bench', 'ohp']]
        orm_html = html_wrap(orm)
        return orm_html

    def create_workout_html(self):
        '''
        Converts the workout df to html
        '''
        workout_html = html_wrap(self.workout_df)
        return workout_html

    def create_reference_html(self):
        '''
        Generates the raw df to calculate reference
        weights from the main workout df and formats
        it to html
        '''
        ref_html = ref_html_gen(self.workout_df)
        return ref_html

    def create_accessory_html(self):
        '''
        Pulls the accessory workout df from the database
        and formats it to html
        '''
        acc = self.get_accessory()
        acc_html = accessory_html_gen(acc)
        return acc_html

    def get_week_vals(self):
        '''
        Gets the current week information based on the
        `one_rep_max` pulled from the database
        '''
        orm = self.get_orm().reset_index(drop=True)
        week = get_week(orm)
        start = orm['data_start_date'][0] + datetime.timedelta(days=(week-1)*7)
        end = start + datetime.timedelta(days=7)
        return week, start.date(), end.date()

    def viz_orm(self):
        '''
        Returns a visualization of orm progression
        '''
        orm = table_pull(self.con, self.user_id, 'one_rep_max')
        orm = format_orm(orm)
        full_dt = get_full_dates(orm)
        backfilled = backfill_dates(orm, full_dt)
        plot_orm(orm)

    def run(self, file='lp-workout.html'):
        '''
        Runs all relevant funcions and saves the final
        html output to `path`
        '''
        self.create_workout_df()
        orm_html = self.create_orm_html()
        workout_html = self.create_workout_html()
        ref_html = self.create_reference_html()
        accessory_html = self.create_accessory_html()
        week, start, end = self.get_week_vals()
        html = full_html(orm_html, workout_html, ref_html,
                         accessory_html, week, start, end)
        fname = f'{self.user}-{file}'
        path = os.path.join(LOCAL_DIR, fname)
        with open(path, 'w') as f:
            f.write(html)
            logger.info(f'workout saved to {path}')


def get_kwargs(con, dim_user, index):
    '''
    Retrieves WorkoutMaker class kwargs from dim_user

    Parameters
    ----------
    con: sqlite3.Connection
    dim_user: obj, pandas df
        full dim_user pull
    index: int
        index value present in dim_user

    Returns
    -------
    kwargs: obj, dict
        kwargs for WorkoutMaker
    '''
    kwargs = {'con': con,
              'user': dim_user['user_name'][index],
              'email': dim_user['email'][index]}
    return kwargs


def get_iterable_kwargs(con):
    '''
    Pull active dim_user entries and generates kwargs for each entry

    Parameters
    ----------
    con: sqlite3.Connection

    Returns
    -------
    kwarg_iter: obj, iterable of dictionaries
        iterable of WorkoutMaker kwargs for each
        user in dim_user
    '''
    s = '''
    SELECT * FROM
    (SELECT user_id FROM pause_workout WHERE
    pause_flag = "False") a
    INNER JOIN
    dim_user b
    USING (user_id)
    '''
    dim_user = pd.read_sql(s, con)
    kwarg_iter = [get_kwargs(con, dim_user, i) for i in dim_user.index]
    return kwarg_iter


def main(con):
    '''
    Retrieves all user info from dim_user and passes
    them into the WorkoutMaker class as kwargs

    Parameters
    ----------
    con: sqlite3.Connection

    Returns
    -------
    WorkoutMaker
        job runner instance
    '''
    kwarg_iter = get_iterable_kwargs(con)
    for kwargs in kwarg_iter:
        runner = WorkoutMaker(**kwargs)
        runner.run()
    return runner


if __name__ == '__main__':
    main(con)
