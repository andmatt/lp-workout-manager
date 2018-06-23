'''functions for visualizing weight progression'''

import ast

import pandas as pd
import plotly.graph_objs as go
from plotly.offline import iplot


def format_orm(orm):
    '''
    formats orm dictionary field into something more appropriate
    for visualization
    '''
    orm['orm_dict'] = orm['orm_dict'].apply(lambda x: ast.literal_eval(x))
    weights = pd.DataFrame.from_dict(orm['orm_dict'].to_dict(), orient='index')
    formatted = orm[['data_start_date', 'data_end_date']].join(weights)
    return formatted


def plot_orm(df):
    '''
    Plots progression for each orm exercise
    '''
    data_params = [('squat', '#4c72b0'), ('bench', '#55a868'),
                   ('deadlift', '#c44e52'), ('ohp', '#8172b2')]

    plot_data = [go.Scatter(
        x=df['data_start_date'],
        y=df[param[0]],
        name=param[0],
        line={'color': param[1]},
        mode='lines+markers')
        for param in data_params]

    plot_layout = go.Layout(title='One Rep Max Progression',
                            xaxis={'title': 'date'},
                            yaxis={'title': 'weight (lb)'},
                            height=600,
                            width=700,)

    plot_params = {'data': plot_data,
                   'layout': plot_layout}

    iplot(plot_params)
