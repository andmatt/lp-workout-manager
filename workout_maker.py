import datetime

from functions.db_funcs import DBHelper, logger, retrieve_json
from functions.dt_funcs import get_week
from functions.html_funcs import (accessory_html_gen, border_apply, full_html,
                                  html_wrap, ref_html_gen)
from functions.workout_funcs import get_workout


class WorkoutMaker(DBHelper):
    def __init__(self, con, user, email=None):
        DBHelper.__init__(self, con, user, email)
        self.workout_df = None

    def create_workout_df(self):
        self.progress_one_rep_max()
        orm = self.get_orm().reset_index(drop=True)
        week = get_week(orm)
        orm_dict = retrieve_json(orm, 'orm_dict')
        self.workout_df = get_workout(orm_dict, weeks=[week])

    def create_workout_html(self):
        workout_html = html_wrap(self.workout_df)
        return workout_html

    def create_reference_html(self):
        ref_html = ref_html_gen(self.workout_df)
        return ref_html

    def create_accessory_html(self):
        acc = self.get_accessory()
        acc_html = accessory_html_gen(acc)
        return acc_html

    def get_week_vals(self):
        orm = self.get_orm().reset_index(drop=True)
        week = get_week(orm)
        start = orm['data_start_date'][0] + datetime.timedelta(days=week*7)
        end = start + datetime.timedelta(days=7)
        return week, start.date(), end.date()

    def main(self, path='./lp-workout.html'):
        self.create_workout_df()
        workout_html = self.create_workout_html()
        ref_html = self.create_reference_html()
        accessory_html = self.create_accessory_html()
        week, start, end = self.get_week_vals()
        html = full_html(workout_html, ref_html,
                         accessory_html, week, start, end)
        with open(path, 'w') as f:
            f.write(html)
            logger.info(f'workout saved to {path}')
