# =============================================================================
# COVID-19
# =============================================================================

# =============================================================================
# DATA CLEANSING
# =============================================================================

import pandas as pd
from datetime import datetime

df = pd.read_csv('OxCGRT_summary20200520.csv')
mapping = pd.read_csv('country-and-continent.csv')

# check for nans and remove 
nans = len(mapping) - mapping.count() # Nans early and late thus ffill required
mapping = mapping.dropna() # drops 4 nans

# remove duplicate country codes (AZE, ARM, CYP, GEO, KAZ, UMI, RUS, TUR)
mapping = mapping.drop_duplicates('CountryCode')

# the mapping is missing Kosovo (RKS) thus, add country and continent to mapping
newrow = pd.DataFrame({'CountryCode':['RKS'], 
                       "Continent_Name":['Europe']}) 
# append new row to mapping
mapping = mapping.append(newrow, ignore_index = True)

# join continent name onto dataframe
df = df.merge(mapping, how = 'left') # left instead of outer to avoid duplicate countries.

# checks dataframes for nans (i.e. confirm continet names no longer holds nans)
nans = len(df) - df.count() # Nans early and late thus ffill required


# adjust dataframe to support forward fill
df_cc = df[['CountryCode','Date','ConfirmedCases']]
df_cc = df_cc.pivot(index='CountryCode', columns='Date', values='ConfirmedCases')
df_cd = df[['CountryCode','Date','ConfirmedDeaths']]
df_cd = df_cd.pivot(index='CountryCode', columns='Date', values='ConfirmedDeaths')

# forward fill nans after with the precedding value (i.e. to continue cumulative theme)
df_cc = df_cc.fillna(method='ffill', axis=1) # axis 1 = rows, axis 0 = columns
df_cd = df_cd.fillna(method='ffill', axis=1) # axis 1 = rows, axis 0 = columns

# fill remaining nans with 0 (i.e. no cases in that country as yet)
df_cc = df_cc.fillna(0)
df_cd = df_cd.fillna(0)

# calculate new cases and new deaths
df_cc_new = df_cc.sub(df_cc.shift(axis=1)) # axis 1 = rows, axis 0 = columns
df_cd_new = df_cd.sub(df_cd.shift(axis=1)) # axis 1 = rows, axis 0 = columns

# fill remaining nans with 0 (i.e. data for 01/03/2020 which has nothing to subtract against so returns nan)
df_cc_new = df_cc_new.fillna(0)
df_cd_new = df_cd_new.fillna(0)

# reset index to enable melt
df_cc = df_cc.reset_index()
df_cd = df_cd.reset_index()
df_cc_new = df_cc_new.reset_index()
df_cd_new = df_cd_new.reset_index()

# melt dataframes
df_cc = pd.melt(df_cc, id_vars=['CountryCode'], var_name='Date', value_name='ConfirmedCases')
df_cd = pd.melt(df_cd, id_vars=['CountryCode'], var_name='Date', value_name='ConfirmedDeaths')
df_cc_new = pd.melt(df_cc_new, id_vars=['CountryCode'], var_name='Date', value_name='NewConfirmedCases')
df_cd_new = pd.melt(df_cd_new, id_vars=['CountryCode'], var_name='Date', value_name='NewConfirmedDeaths')

# drop old columns
df = df.drop(columns=['ConfirmedCases','ConfirmedDeaths'])

# merge new data onto original dataset
df = df.merge(df_cc, how = 'left')
df = df.merge(df_cd, how = 'left')
df = df.merge(df_cc_new, how = 'left')
df = df.merge(df_cd_new, how = 'left')

# re-check dataframes for nans
nans = len(df) - df.count() # Nans early and late thus ffill required

# format date to datetime
print(df.dtypes)

DateString = []
DateFormat = []
for x in df['Date']:
    y = str(x)
    z = datetime.strptime(y, '%Y%m%d')
    DateString.append(y)
    DateFormat.append(z)
    
# Option 1
df['DateFormat1'] = DateString
df['DateFormat1'] = pd.to_datetime(df['DateFormat1'])
df['DateFormat1'] = df['DateFormat1'].dt.strftime('%Y-%m-%d')

# Option 2
df['DateFormat2'] = DateFormat
df['DateFormat2'] = df['DateFormat2'].dt.strftime('%b-%d')

# sort values by date for animation
df = df.sort_values(by='DateFormat1')

# =============================================================================
# FIGURE 1
# =============================================================================
import plotly.express as px

fig1 = px.scatter_geo(df,
                     title='ConfirmedCases (world)',
                     locations='CountryCode',
                     color='Continent_Name',
                     hover_name='CountryName',
                     size='ConfirmedCases',
                     size_max=100,
                     animation_frame='DateFormat1',
                     projection='equirectangular',
                     scope='world',
                     opacity=0.8)


# =============================================================================
# FIGURE 2
# =============================================================================

# identify countries with the most confirmed cases in 20th May
df_top5 = df[df.DateFormat1 == '2020-05-20']
df_top5 = df_top5.sort_values(by=['ConfirmedCases'], ascending=False)
df_top5 = df_top5.head()
df_top5 = df_top5.reset_index(drop=True)
# store countries in a list
top5 = df_top5['CountryName'].to_list()
# build the dataframe with the top 5 countries (with all date values)
df_top5 = df[df.CountryName.isin(top5)]
df_top5 = df_top5.reset_index(drop=True)

# plot
fig2 = px.line(df_top5,
               title='ConfirmedCases (Top 5 Countries)',
               x='DateFormat1', 
               y='ConfirmedCases', 
               color='CountryName',
               line_group='CountryName', 
               hover_name='CountryName',
               log_y=True,
               labels={'CountryName':'Country',
                       'DateFormat1':'Date'})

# =============================================================================
# DASH
# =============================================================================
import flask
import dash
import dash_html_components as html
import dash_core_components as dcc 
from dash.dependencies import Input, Output

server = flask.Flask(__name__)
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css'] # Bootstrap use for layour 12 column by 5 row grid
app = dash.Dash(__name__, server=server, external_stylesheets=external_stylesheets)

app.title = 'COVID-19'

app.layout = html.Div([
                        # first row: Title
                        html.Div([
                            html.Div([
                                html.H1('COVID-19')
                                ], className = 'eleven columns'),
                            html.Div([
                                html.Img(src='http://pngimg.com/uploads/coronavirus/coronavirus_PNG46.png',
                                         style={'height'      :'100%',
                                                'width'       :'100%',
                                                'float'       :'right'})
                                ], className = 'one column'),
                            ], className = 'row'),
                                                
                        # second row: Filters
                        html.Div([
                            html.Div([
                                # dropdown
                                html.Label('Select a world map view:'), 
                                dcc.Dropdown(
                                    id='scope',
                                    options=[{'label': 'World',  'value': 'world'}, 
                                             {'label': 'Asia',   'value': 'asia'}, 
                                             {'label': 'Africa', 'value': 'africa'},
                                             {'label': 'Europe', 'value': 'europe'},
                                             {'label': 'North America', 'value': 'north america'},
                                             {'label': 'South America', 'value': 'south america'}], 
                                    value='world')
                                ], className = 'four columns'),
                            html.Div([
                                # radio-button
                                html.Label('Select a measure:'), 
                                dcc.Dropdown(
                                    id='measure', 
                                    options=[{'label': 'Confirmed Cases',  'value': 'ConfirmedCases'},
                                             {'label': 'Confirmed Deaths', 'value': 'ConfirmedDeaths'},
                                             {'label': 'Stringecy Index',  'value': 'StringencyIndex'}], 
                                    value='ConfirmedCases')
                                ], className = 'four columns'),
                            html.Div([
                                # radio-button
                                html.Label('Select a policy:'), 
                                dcc.Dropdown(
                                    id='policy', 
                                    options=[{'label': 'No selection',    'value': 'No selection'},
                                             {'label': 'School closing',  'value': 'School closing'},
                                             {'label': 'Staying at home', 'value': 'Stay at home requirements'}], 
                                    value='No selection')
                                ], className = 'four columns')
                            ], className = 'row'),
                        # third row: Graph
                        html.Div([
                            html.Div([
                                # graph
                                dcc.Graph(
                                    id='fig1', 
                                    figure=fig1)
                                ], className = 'six columns'),
                            html.Div([
                                # graph
                                dcc.Graph(
                                    id='fig2', 
                                    figure = fig2)
                                ], className = 'six columns'),
                            ], className = 'row'),
                        ],  
                    className='ten columns offset-by-one',
                    style={'backgroundColor': '#FFFFFF'})

@app.callback(Output('fig1', 'figure'),
              [Input('scope', 'value'), Input('measure', 'value'), Input('policy', 'value')])

def updateFigure1(scope, measure, policy):
    if policy == 'No selection':
        if scope == 'world' and measure == 'ConfirmedCases':
            return fig1
        else:
            return  px.scatter_geo(df,
                                   title=str(measure)+' ('+str(scope)+') ', # change title depending on measure & scope
                                   locations='CountryCode',
                                   color='Continent_Name',
                                   hover_name='CountryName',
                                   size=measure, # if measure is not equal to confirmed cases return selection
                                   size_max=100,
                                   animation_frame='DateFormat1',
                                   projection='equirectangular',
                                   scope=scope, # if scope is not equal to world adjust to selection
                                   opacity=0.8)
    elif policy != 'No selection':
        return px.choropleth(df, 
                             title=str(policy)+' ('+str(scope)+') ', # change title depending on policy & scope
                             locations='CountryCode', 
                             color=policy, # if policy is not equal to no selection return the policy selected
                             color_continuous_scale='rdylgn_r', # pubugn , tealrose, rdylgn, ylorrd
                             range_color=(0, 3),
                             hover_name='CountryName',
                             animation_frame='DateFormat1',
                             projection='equirectangular',
                             scope=scope, # if scope is not equal to world adjust to selection
                             labels={'CountryCode':'Country Code',
                                     'DateFormat1' : 'Date'})

@app.callback(Output('fig2', 'figure'),
              [Input('measure', 'value'), Input('policy', 'value')])

def updateFigure2(measure, policy):
    if policy == 'No selection':
        if measure == 'ConfirmedCases':
            return fig2
        else:
            return px.line(df_top5,
                           title=str(measure)+' (Top 5 Countries)',
                           x='DateFormat1', 
                           y=measure, # if measure is not equal to confirmed cases return selection
                           color='CountryName',
                           line_group='CountryName', 
                           hover_name='CountryName',
                           log_y=True,
                           labels={'CountryName':'Country',
                                   'DateFormat1':'Date'})
    elif policy != 'No selection':
        return px.line(df_top5,
                       title=str(policy)+' (Top 5 Countries)',
                       x='DateFormat1', 
                       y=policy, # if measure is not equal to confirmed cases return selection
                       color='CountryName',
                       line_group='CountryName', 
                       hover_name='CountryName',
                       log_y=False,
                       labels={'CountryName':'Country',
                               'DateFormat1':'Date'})

# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=True, use_reloader=False)    