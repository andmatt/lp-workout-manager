'''functions for wrapping df output in html'''

from functions.workout_funcs import reference_gen


default_style = 'th {background-color: #3498db;}'


def html_wrap(df):
    '''
    Converts a pandas dataframe to an html string with
    bootstrap formatting

    Parameters
    ----------
    df: obj, pandas df

    Returns
    -------
    html: str
    '''
    html = df.to_html(classes=["table-bordered", "table-striped", "table-hover",
                               "table-condensed", "span6", "text-center"], index=False)
    html = html.replace('<th>', '<th class="text-center">')
    return html


def border_apply(html, search_term, td_count):
    '''
    applies a border style to all <td> elements for the last occurance
    of a particular term in a table

    Parameters
    ----------
    html: str
        html string
    search_term: str
        value of a row to search for last occurences of
    td_count: int
        count of td objects to apply style to

    Returns
    -------
    parsed: str
        html string parsed with border <td> formatting

    Notes
    -----
    1. Requires column to seperate values by to be first column
    2. Kind of janky... should find a way to overwrite bootstrap
    style and apply directly to <tr>
    '''
    border = '<td style="border-bottom-style: solid; border-bottom: .5px solid black;">'
    position = html.rfind(f'<td>{search_term}')
    parsed = html[:position] + \
        html[position:].replace('<td>', border, td_count)
    return parsed


def ref_html_gen(workout_df):
    '''
    Creates reference workout and converts it to an 
    html string

    Parameters
    ----------
    workout_df: obj, pandas df

    Returns
    -------
    ref_html: str

    Notes
    -----
    should probably seperate the df generation...
    '''
    ref = reference_gen(workout_df)
    ref_html = html_wrap(ref)
    for workout in ['squat', 'deadlift', 'ohp', 'bench']:
        ref_html = border_apply(ref_html, workout, ref.shape[1])

    return ref_html


def accessory_html_gen(accessory):
    '''
    Converts accessory worokout to html string

    Parameters
    ----------
    accessory: obj, pandas df

    Returns
    -------
    accessory_html: str
    '''
    accessory_html = html_wrap(accessory)
    for workout in ['squat', 'deadlift', 'ohp', 'bench']:
        accessory_html = border_apply(
            accessory_html, workout, accessory.shape[1])

    return accessory_html


def full_html(workout_html, ref_html, accessory_html, week, start, end, style=default_style):
    '''
    Generates full html with input of the individual html string and date inputs

    Parameters
    ----------
    workout_html: str
    ref_html: str
    accessory_html: str
    week: str
    start: str
    end: str
    style: str

    Returns
    -------
    html: str
    '''
    html = f'''\
    <!doctype html>
    <html>
      <style>
      {style}
      </style>
      <head> 
      <title> 5-3-1 Workout of the Week </title>
      <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css">
      </head>
      <body style="float: left; margin-left: 15px;">
      <h2>5-3-1 Workout of the Week</h2>
        <p>PFA - the workout of the week. It is currently <b>Week {week}</b> <br>
           <b>Week {week}</b> goes from {start} till {end}
        </p>
        <h4>Main Workout:</h4>
        {workout_html}
        <br>
        <h4>Weight References:</h4>
        {ref_html}<br>
        <h4>Accessory Exercises:</h4>
        {accessory_html}<br>
      </body>
    </html>
    '''
    return html
