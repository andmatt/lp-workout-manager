''' dataframe and dictionary manipulation functions to get workout weights'''
import pandas as pd

week_mapping = {1:{'mod':[.65, .75, .85], 'reps':[5,5,5]},
                2:{'mod':[.7, .8, .9], 'reps':[3,3,3]},
                3:{'mod':[.75, .85, .95], 'reps':[5,3,1]},
                4:{'mod':[.4, .5, .6], 'reps':[10,10,10]}}

def explode_df(df):
    '''
    Explodes a pandas dataframe with `list` columns

    Parameters
    ----------
    df: obj, pandas df

    Returns
    -------
    obj, pandas df
        exploded df
    '''
    explode = pd.DataFrame()
    for i in df.index:
        entry = df.loc[i]
        to_ex = {i:entry[i] for i in entry.keys() if type(entry[i])==list}
        no_ex = [i for i in entry.keys() if i not in to_ex.keys()]
        explosion = pd.DataFrame(to_ex)
        for i in no_ex:
            explosion[i] = entry[i]
        explode = pd.concat([explode, explosion])

    return explode.reset_index(drop=True)

def get_mapping_df(orm_dict):
    '''
    Creates a staging df containing orm_weights
    along with raw `week_mapping` values  

    Parameters
    ----------
    orm_dict: dict
        dict containing orm weights
    
    Returns
    -------
    mapping_df: obj, pandas df
    '''
    week_df = pd.DataFrame.from_dict(week_mapping, orient='index')
    week_df['week'] = week_df.index
    orm_df = pd.concat([pd.DataFrame(orm_dict, index=[i]) for i in week_df.index])
    mapping_df = week_df.join(orm_df)
    
    return mapping_df

def map_weights(mapping_df, weeks):
    '''
    Explodes and generates actual weights given the staging df
    outputted from `get_mapping_df`

    Parameters
    ----------
    mapping_df: obj, pandas df
        output from get_mapping_df()
    weeks: list
        weeks to return workout for
    
    Returns
    -------
    workout: obj, pandas df
    '''
    full_df = explode_df(mapping_df)
    workout = full_df[full_df.week.isin(weeks)].reset_index(drop=True)
    for col in ['bench', 'deadlift', 'ohp', 'squat']:
        workout[col] = round(workout[col] * workout['mod']/5)*5
        workout[col] = workout[col].astype(int)
    workout['set'] = workout.index + 1
    workout = workout[['week', 'set', 'reps', 'deadlift', 'squat', 'bench', 'ohp']]
    
    return workout

def get_workout(orm_dict, weeks):
    '''
    Wrapper function to perform all operations
    to generate worokout df

    Parameters
    ----------
    orm_dict: dict
        dict containing orm weights
    weeks: list
        weeks to return workout for
    
    Returns
    -------
    workout: obj, pandas df
    '''
    if type(weeks) != list:
        weeks = [weeks]
    mapping_df = get_mapping_df(orm_dict)
    workout = map_weights(mapping_df, weeks)
    
    return workout

def reference_gen(workout_df):
    '''
    Generates a workout weight reference chart from
    the full workout df

    Parameters
    ----------
    workout_df: obj, pandas df

    Returns
    ------
    obj, pandas df
        reference df
    '''
    ref_df = pd.melt(workout_df, id_vars=['week', 'set', 'reps'], var_name='exercise', value_name='weight')
    ref_df['weight_no_bar'] = ref_df['weight'] - 45
    ref_df['weight_each_side'] = -(ref_df['weight_no_bar'] // -2)
    cols = ['exercise', 'set', 'reps', 'weight', 'weight_no_bar', 'weight_each_side']
    
    return ref_df[cols]
