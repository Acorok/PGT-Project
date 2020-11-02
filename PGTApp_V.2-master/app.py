#Standard library imports
from datetime import datetime
import io
import base64
#Dash Imports 
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_table
from dash.exceptions import PreventUpdate
#Plotly Imports
import plotly.express as px
import plotly.graph_objs as go
#Utils imports
import pandas as pd
import statsmodels

external_stylesheets = ['/static/plotly_style.css', '/static/styles.css']
#Flask Server configuration
app = dash.Dash(__name__, assets_url_path='/static', external_stylesheets=external_stylesheets)
app.config.suppress_callback_exceptions = True
server = app.server

#Banner
HMI_Banner = 'HMIBanner.png'
upload_instructions = 'upload-instructions.png'
selector_submit = 'selector-submit.png'
#* Helper Functions that perform various tasks, attached comments describe purpose
def datetime_index(df):
    """Splits time col into Date/Time, sets index to datetime

    Args:
        df (dataframe): [The dataframe you are working with]

    Returns:
        [converted dataframe]: [index, datetime, date/time cols added]
    """
    df['datetime'] = pd.to_datetime(df['Time'])
    df = df.set_index('datetime')
    new = df['Time'].str.split(' ', n=1, expand=True)
    df['Date'] = new[0]
    df['Time'] = new[1]
    df = df.sort_index()
    return df


def date_range(df):
    """Generates the maximum and minimum of the df daterange

    Args:
        df (dataframe): the working dataframe

    Returns:
        (max/min) datetime object: The maximum and minimum of the index, used to date range selector
    """
    end_date = df.index.max()
    start_date = df.index.min()
    return end_date, start_date


def parse_contents(contents, filename):
    """Searches the uploaded file, gather contents and filename

    Args:
        contents (base64 encoded strign): base64 encoded string
        filename (string): the filename of the uploaded file

    Returns:
        dataframe: returns the uploaded file
    """
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    if 'csv' in filename:
        # Assume that the user uploaded a CSV file
        return pd.read_csv(io.StringIO(decoded.decode('utf-8')))
    elif 'xls' in filename:
        # Assume that the user uploaded an excel file
        return pd.read_excel(io.BytesIO(decoded))



def get_name(df):
    """Helper function to find out the name of the vessel, loops through name_tags list and compare df labels with list content

    Args:
        df (dataframe): the raw uploaded dataframe

    Returns:
        vessel_name (string): vessel name as found in df
    """
    df = df.filter(regex='name{1}|Name{1}', axis=1)
    try:
        vessel_name = df.iat[-1, 0]
        return str(vessel_name)
    except:
        vessel_name = 'Not Found'
        return vessel_name


def get_IMO(df):
    """Helper function to find imo, loops through IMO list, compares with list and returns imo if found

    Args:
        df (dataframe): raw uploaded dataframe

    Returns:
        vessel_imo(string): the vessel IMO if found in df
    """
    df = df.filter(regex='imo{1}|IMO{1}', axis=1)
    if df.iat[0, 0]:
        vessel_imo = df.iat[-1, 0]
        return str(int(vessel_imo))
    else:
        vessel_imo = 'Not Found'
        return vessel_imo


#* Main app layout, all static components that persist on page
app.layout = html.Div([
        html.Div([
        html.Div(
            html.Img(
                src=app.get_asset_url(HMI_Banner)),
            className='twelve columns')],
        style={
        'color': '#002332',
        'background': '#FFFFFF',
        'justify-content': 'space-between'},
        className='row flex-display'),
    html.Div([
        html.Div(id='vessel-name',
               style={
                   'textAlign': 'center',
                   'fontFamily': 'Arial',
                   'fontWeight': '800'},
               className='one-third column'),
        html.Div(id='vessel-imo',
               style={
                   'textAlign': 'center',
                   'fontFamily': 'Arial',
                   'fontWeight': '800'},
               className='one-third column'),
        html.Div(id='time-stamp',
               style={
                   'textAlign': 'center',
                   'fontFamily': 'Arial',
                   'fontWeight': '800'},
               className='one-third column')],
             style={
        'background': '#FFFFFF'},
        className='row flex-display'),
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        # Allow multiple files to be uploaded
        multiple=True),
    dcc.Store(id='memory'),
    html.Div([
        dcc.Tabs(id="tabs", value='tab-3', children=[
            dcc.Tab(label='Data Trends', value='tab-1'),
            dcc.Tab(label='Data Tables', value='tab-2'),
            dcc.Tab(label='Instructions', value='tab-3')]),
        html.Div(id='tabs-content')],
        style={
        'margin-top': '0px',
        'margin-bottom': '50px'})
])

#* Controls for all components are generated separately from layout 
# Regression controls
regressioncontrols = html.Div([
    html.P(
        'Custom Y vs X Relationship Analysis',
        style={'font-weight': 'bold'},
        className='four columns'
    ),
    html.Div([
        html.Div("Horizontal X Axis",
                 style={
                     'textAlign': 'center',
                     'font-weight': 'bold'},
                 className='six columns'),
        dcc.Dropdown(
            id='x-label-dropdown',
            className='six columns')],
        className='four columns'),
    html.Div([
        html.P("Vertical Y Axis",
               style={
                   'textAlign': 'center',
                   'font-weight': 'bold'},
               className='six columns'),
        dcc.Dropdown(
            id='y-label-dropdown',
            className='six columns')],
        className='four columns')],
    className='row flex-display')

#Multi controls
multicontrols = html.Div([
    html.P(
        'Parameters vs Time',
        style={'font-weight': 'bold'},
        className='two columns'
    ),
    html.Div([
        html.Div("Parameter Selector",
                 style={
                     'textAlign': 'center',
                     'font-weight': 'bold'},
                 className='six columns'),
        dcc.Dropdown(
            id='parameter-dropdown',
            multi=True,
            className='six columns')],
        className='four columns'),
    html.Div([
        html.P(
            "Date Range Selector",
               style={
                   'textAlign': 'center',
                   'font-weight': 'bold'},
               className='four columns'),
        dcc.DatePickerRange(
            id='date-range-selector',
            className='six columns'),
        html.Button('Submit', 
                    id='submit-val',
                    style={
                        'background-color': '#009BDF',
                        'color': 'white'},
                    n_clicks=0,
                    className='two columns')],
        style={
            'margin-left': '0px'},
        className='six columns')],
    style={
        'margin': '1rem 0'},
    className='row flex-display')

tablecontrols = html.Div([
    html.P(
        'Data Report Generator',
        style={'font-weight': 'bold'},
        className='two columns'
    ),
    html.Div([
        html.Div("Parameter Selector",
                 style={
                     'textAlign': 'center',
                     'font-weight': 'bold'},
                 className='six columns'),
        dcc.Dropdown(
            id='table-dropdown',
            multi=True,
            className='six columns')],
        className='four columns'),
    html.Div([
        html.P(
            "Date Range Selector",
               style={
                   'textAlign': 'center',
                   'font-weight': 'bold'},
               className='four columns'),
        dcc.DatePickerRange(
            id='table-date-range-selector',
            className='six columns'),
        html.Button('Submit', 
                    id='table-submit-val',
                    style={
                        'background-color': '#009BDF',
                        'color': 'white'},
                    n_clicks=0,
                    className='two columns')],
        style={
            'margin-left': '0px'},
        className='six columns')],
    style={
        'margin': '1rem 0'},
    className='row flex-display')

# Tab 1 Layout
tab1 = html.Div([
            html.Div(multicontrols,
                 className='twelve columns'),
        html.Div(
            id='multiplot-plot',
            className='twelve columns'),
        html.Div(regressioncontrols,
                 className='twelve columns'),
        html.Div(
            id='regression-plot',
            className='twelve columns')])

# Tab 2 layout
tab2 = html.Div([
    html.Div(tablecontrols,
             className='pretty_container twelve columns'),
    html.Div(
        id='data-table',
        className='pretty_container twelve columns')],
    style={
        'justify-content': 'space-between'},
    className='row flex-display')

# Tab 3 layout
tab3 = html.Div([
    html.Div([
      html.H1('Instructions'),
      dcc.Markdown('''
                   The instructions will detail how to use the application correctly.
                   '''),
      html.Img(src=app.get_asset_url(upload_instructions),
               style={
                 'width': '90%'}),
      dcc.Markdown('''
                   * Upload your datalogger file in **CSV** format
                   * Your upload will be confirmed when the vessel IMO, name, and timestamp appear blow the PGT banner
                   '''),
      html.Img(src=app.get_asset_url(selector_submit),
               style={
                 'width': '90%'}),
      dcc.Markdown('''
                   * When you have completed the upload select the parameters and time range you want to see
                   * Press **Submit** _after_ selecting all form information
                   ''')],
             className='pretty_container twelve columns')],
    style={
        'justify-content': 'space-between'},
    className='row flex-display')

#Tab Callback
@app.callback(Output('tabs-content', 'children'),
              [Input('tabs', 'value')])
def render_content(tab):
    if tab == 'tab-1':
        return tab1
    elif tab == 'tab-2':
        return tab2
    elif tab == 'tab-3':
        return tab3



#Data upload callback
@app.callback(Output('memory', 'data'),
              [Input('upload-data', 'contents')],
              [State('upload-data', 'filename')])
def update_output(contents, names):
    if contents is not None:
        contents = contents[0]
        names = names[0]
        df = parse_contents(contents, names)
        df = datetime_index(df)
        return df.to_json(orient='split')

#Dropdown graph Callback
@app.callback([Output('x-label-dropdown', 'options'),
               Output('y-label-dropdown', 'options'),
               Output('parameter-dropdown', 'options')],
               Input('memory', 'data'))
def update_dropdown(data):
    if data is None:
        raise PreventUpdate
    df = pd.read_json(data, orient='split')
    options = [{'label': i, 'value': i}
                 for i in df.columns]
    return options, options, options

#Dropdown table Callback
@app.callback(Output('table-dropdown', 'options'),
               Input('memory', 'data'))
def update_table_dropdown(data):
    if data is None:
        raise PreventUpdate
    df = pd.read_json(data, orient='split')
    options = [{'label': i, 'value': i} for i in df.columns]
    return options

#Date Range Graph Callback
@app.callback([Output('date-range-selector', 'min_date_allowed'),
               Output('date-range-selector', 'max_date_allowed')],
               Input('memory', 'data'))
def update_daterange(data):
    if data is None:
        raise PreventUpdate
    df = pd.read_json(data, orient='split')
    maximum, minimum = date_range(df)
    return minimum, maximum

#Date Range Table Callback
@app.callback([Output('table-date-range-selector', 'min_date_allowed'),
               Output('table-date-range-selector', 'max_date_allowed')],
               Input('memory', 'data'))
def update_table_daterange(data):
    if data is None:
        raise PreventUpdate
    df = pd.read_json(data, orient='split')
    maximum, minimum = date_range(df)
    return minimum, maximum

# Regression Plot Callback
@app.callback(Output('regression-plot', 'children'),
              [Input('submit-val', 'n_clicks')],
              [State('memory', 'data'),
               State('x-label-dropdown', 'value'),
               State('y-label-dropdown', 'value'),
               State('date-range-selector', 'start_date'),
               State('date-range-selector', 'end_date')])
def update_regression(n_clicks, data, x_label, y_label, start_date, end_date):
    if n_clicks == 0: 
        raise PreventUpdate
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
    df = pd.read_json(data, orient='split')
    df = df[start_date_obj: end_date_obj]
    fig = px.scatter(
        x=df[x_label],
        y=df[y_label],
        labels={
            'x': x_label,
            'y': y_label},
        trendline='ols')
    return html.Div(dcc.Graph(figure=fig))

#Multi-param plot Callback
@app.callback(Output('multiplot-plot', 'children'),
              Input('submit-val', 'n_clicks'),
                [State('date-range-selector', 'start_date'),
                State('date-range-selector', 'end_date'),
                State('parameter-dropdown', 'value'),
                State('memory', 'data')])
def update_timeseries(n_clicks, start_date, end_date, parameters, data):
    if n_clicks == 0:
        raise PreventUpdate
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
    df = pd.read_json(data, orient='split')
    filtered_df = df[start_date_obj: end_date_obj]
    fig = go.Figure()
    if isinstance(parameters, str):
        fig.add_trace(go.Scatter(x=filtered_df.index,
                                 y=filtered_df[parameters], name=parameters))
        fig.update_layout(title_text='Parameter vs Time', title_x=0.5)
    else:
        for parameter in parameters:
            fig.add_trace(go.Scatter(x=filtered_df.index,
                                     y=filtered_df[parameter], name=parameter))
            fig.update_layout(title_text='Parameters vs Time', title_x=0.5)
    return html.Div([
        dcc.Graph(
            id='time-series',
            figure=fig,)
    ])

#Header Callback
@app.callback([Output('vessel-name', 'children'),
               Output('vessel-imo', 'children'),
               Output('time-stamp', 'children')],
               Input('memory', 'data'))
def update_heading(data):
    if data is None:
        raise PreventUpdate
    df = pd.read_json(data, orient='split')
    vessel_name = F"Vessel Name: {get_name(df)}"
    vessel_imo = F"Vessel IMO: {get_IMO(df)}"
    now = datetime.now()
    time_stamp = F"Printed On: {now.strftime('%d/%m/%Y %H:%M:%S')}"
    return vessel_name, vessel_imo, time_stamp


#Data Table Callback
@app.callback(Output('data-table', 'children'),
              Input('table-submit-val', 'n_clicks'),
              [State('memory', 'data'),
               State('table-date-range-selector', 'start_date'),
               State('table-date-range-selector', 'end_date'),
               State('table-dropdown', 'value')])
def update_table(n_clicks, data, start_date, end_date, parameters):
    if n_clicks == 0: 
        raise PreventUpdate

    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
    df = pd.read_json(data, orient='split')
    df = df.loc[start_date_obj: end_date_obj, parameters[0]:parameters[-1]]
    return html.Div(dash_table.DataTable(
        id='returned-table',
        columns=[
            {'name': i, 'id': i, 'deletable': True} for i in df],
        data=df.to_dict('records'),
        style_cell={
            'textAlign': 'center'},
        style_header={
            'fontWeight': 'bold',
            'backgroundColor': 'rgb(230, 230, 230)'},
        style_data_conditional=[{
            'if': {'row_index': 'odd'},
            'backgroundColor': 'rgb(248, 248, 248)'}]))


if __name__ == '__main__':
    app.run_server(debug=True)