import pandas as pd
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import re
from datetime import datetime, timedelta
import dash_bootstrap_components as dbc
import IP2Location
from device_detector import DeviceDetector
import IP2Proxy

log_file = r"C:\nginx\logs\access.log"
ip2loc = IP2Location.IP2Location("IP2LOCATION-LITE-DB9\IP2LOCATION-LITE-DB9.BIN")
ip2proxy = IP2Proxy.IP2Proxy("IP2PROXY-LITE-PX6\IP2PROXY-LITE-PX6.BIN")

log_pattern = re.compile(
    r'(?P<ip>\S+) - - \[(?P<time>.*?)\] "(?P<method>\S+) (?P<url>\S+) (?P<protocol>[^"]+)" '
    r'(?P<status>\d{3}) (?P<size>\d+) "[^"]*" "(?P<user_agent>[^"]*)"'
)

# Global cache dictionaries
ip2location_cache = {}
ip2proxy_cache = {}

def is_bot_user_agent(ua):
    parsed = DeviceDetector(ua).parse()
    return parsed.is_bot()

def get_ip2location_info(ip):
    if ip in ip2location_cache:
        return ip2location_cache[ip]
    ip_info = ip2loc.get_all(ip)
    ip2location_cache[ip] = ip_info  # Cache the result
    return ip_info

def get_ip2proxy_info(ip):
    if ip in ip2proxy_cache:
        return ip2proxy_cache[ip]
    proxy_info = ip2proxy.get_all(ip)
    ip2proxy_cache[ip] = proxy_info  # Cache the result
    return proxy_info

def parse_log_line(line):
    match = log_pattern.match(line)
    if not match:
        return None
    data = match.groupdict()
    try:
        data["time"] = datetime.strptime(data["time"], "%d/%b/%Y:%H:%M:%S %z").replace(tzinfo=None)
    except ValueError:
        return None
    data["status"] = int(data["status"])
    data["size"] = int(data["size"])
    ip_info = get_ip2location_info(data["ip"])
    data["country"] = ip_info.country_long
    data["latitude"] = ip_info.latitude
    data["longitude"] = ip_info.longitude
    data["is_bot"] = is_bot_user_agent(data["user_agent"])

    # Get additional information from IP2Proxy
    proxy_info = get_ip2proxy_info(data["ip"])
    data["isp"] = proxy_info['isp']  # ISP information from IP2Proxy
    data["usage_type"] = proxy_info['usage_type']  # Usage type (e.g., residential, business)

    return data

def load_data():
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return pd.DataFrame()
    data = [parse_log_line(line) for line in lines]
    df = pd.DataFrame([d for d in data if d])
    if not df.empty:
        df["time"] = pd.to_datetime(df["time"])
    return df

def load_error_logs():
    error_log_file = r"C:\nginx\logs\error.log"  # Adjust the path to your error log
    error_pattern = re.compile(r'(?P<timestamp>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}) \[error\] \d+#\d+: \*[\d]+ .*, client: (?P<ip>[\d.]+),.*')
    
    error_data = []
    try:
        with open(error_log_file, 'r') as log_file:
            for line in log_file:
                match = error_pattern.search(line)
                if match:
                    timestamp = match.group('timestamp')
                    ip = match.group('ip')
                    error_message = line.strip()  # The entire line is the error message
                    error_data.append({'timestamp': timestamp, 'ip': ip, 'error_message': error_message})
    except FileNotFoundError:
        print(f"Error: The log file {error_log_file} was not found.")
    except Exception as e:
        print(f"An error occurred while reading the log file: {e}")
    
    return error_data

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

initial_df = load_data()
initial_min_date = initial_df['time'].min() if not initial_df.empty else datetime.now()
initial_max_date = initial_df['time'].max() if not initial_df.empty else datetime.now()

app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("NGINX Global Traffic Dashboard"), width=12)),
    dbc.Row(dbc.Col(html.H5(id='total-requests'), width=12)),
    dcc.Interval(id="interval", interval=30000, n_intervals=0),

    dbc.Row([
        dbc.Col(dcc.DatePickerRange(
            id='date-picker-range',
            min_date_allowed=initial_min_date,
            max_date_allowed=initial_max_date,
            start_date=initial_min_date,
            end_date=initial_max_date,
            display_format='YYYY-MM-DD',
            end_date_placeholder_text='Select end date or last n minutes',
            clearable=True,
            with_portal=True
        ), width=2),
        dbc.Col(dcc.Input(id='last-n-minutes', type='number', placeholder='Last N minutes'), width=2),
        dbc.Col(dcc.Input(id='ip-filter', type='text', placeholder='IP contains...'), width=2),
        dbc.Col(dcc.Input(id='url-filter', type='text', placeholder='URL contains...'), width=2),
        dbc.Col(dcc.Input(id='ua-filter', type='text', placeholder='User agent contains...'), width=2),
        dbc.Col(dcc.Dropdown(id='method-filter', multi=True, placeholder='HTTP Method...'), width=2),
        dbc.Col(dcc.Dropdown(id='status-filter', multi=True, placeholder='Status Code...'), width=2),
        dbc.Col(dcc.Dropdown(id='country-filter', multi=True, placeholder='Country...'), width=2),
        dbc.Col(dcc.Dropdown(id='bot-filter',options=[{'label': 'Humans only', 'value': 'human'},{'label': 'Bots only', 'value': 'bot'},],placeholder='Bot traffic filter...'), width=2),
        dbc.Col(dcc.Dropdown(id='usage-type-filter', multi=True, placeholder='Usage Type...'), width=2),
        dbc.Col(dcc.Dropdown(id='isp-filter', multi=True, placeholder='ISP...'), width=2),
        dbc.Col(dcc.Input(id='bin-size', type='number', value=30, min=1), width=2)
    ], className="mb-4"),

    dbc.Row([dbc.Col(dcc.Graph(id="world-map"), width=12, style={'display': 'flex', 'justify-content': 'center'}),]),
    dbc.Row([dbc.Col(dcc.Graph(id="reqs-over-time"), width=6), dbc.Col(dcc.Graph(id="status-codes"), width=6),]),
    dbc.Row([dbc.Col(dcc.Graph(id="top-ips"), width=6), dbc.Col(dcc.Graph(id="top-paths"), width=6),]),
    dbc.Row([dbc.Col(dash_table.DataTable(
        id='ip-table',
        page_size=15,
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left', 'maxWidth': '400px', 'whiteSpace': 'normal'},
        tooltip_data=[], tooltip_delay=0, tooltip_duration=None
    ), width=12)]),
    dbc.Row([dbc.Col(dash_table.DataTable(
        id='error-log-table',
        page_size=15,
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left', 'maxWidth': '400px', 'whiteSpace': 'normal'},
        columns=[  # Define the columns for the error log table
            {'name': 'Timestamp', 'id': 'timestamp'},
            {'name': 'Error Message', 'id': 'error_message'}
        ],
        tooltip_data=[], tooltip_delay=0, tooltip_duration=None
    ), width=12)]),
], fluid=True)

@app.callback(
    Output("world-map", "figure"),
    Output("reqs-over-time", "figure"),
    Output("status-codes", "figure"),
    Output("top-ips", "figure"),
    Output("top-paths", "figure"),
    Output("ip-table", "data"),
    Output("ip-table", "tooltip_data"),
    Output("method-filter", "options"),
    Output("country-filter", "options"),
    Output("status-filter", "options"),
    Output("total-requests", "children"),
    Output("error-log-table", "data"),  # Add this output for error log table
    Input("interval", "n_intervals"),
    Input("date-picker-range", "start_date"),
    Input("date-picker-range", "end_date"),
    Input("last-n-minutes", "value"),
    Input("ip-filter", "value"),
    Input("url-filter", "value"),
    Input("ua-filter", "value"),
    Input("method-filter", "value"),
    Input("status-filter", "value"),
    Input("country-filter", "value"),
    Input("bot-filter", "value"),
    Input("bin-size", "value")
)

def update(n, start_date, end_date, last_n_minutes, ip_contains, url_contains, ua_contains, methods, statuses, countries, bot_filter, bin_size):
    df = load_data()
    if df.empty:
        return *[{'layout': {'title': 'No data'}}]*5, [], [], [], "Total Requests: 0"

    # Handle 'Last N minutes' condition
    if last_n_minutes:
        end_date = datetime.now()
        start_date = end_date - timedelta(minutes=int(last_n_minutes))
    else:
        start_date = pd.to_datetime(start_date) if start_date else datetime.now()
        end_date = pd.to_datetime(end_date).replace(hour=23, minute=59, second=59) if end_date else datetime.now()

    df = df[(df['time'] >= start_date) & (df['time'] <= end_date)]

    if ip_contains:
        df = df[df['ip'].str.contains(ip_contains, case=False, na=False)]
    if url_contains:
        df = df[df['url'].str.contains(url_contains, case=False, na=False)]
    if ua_contains:
        df = df[df['user_agent'].str.contains(ua_contains, case=False, na=False)]
    if methods:
        df = df[df['method'].isin(methods)]
    if statuses:
        df = df[df['status'].isin(statuses)]
    if countries:
        df = df[df['country'].isin(countries)]
    if bot_filter == "bot":
        df = df[df["is_bot"] == True]
    elif bot_filter == "human":
        df = df[df["is_bot"] == False]
    if df.empty:
        return (
            [{'layout': {'title': 'No matching data'}}], 
            [{'layout': {'title': 'No matching data'}}], 
            [{'layout': {'title': 'No matching data'}}], 
            [{'layout': {'title': 'No matching data'}}], 
            [{'layout': {'title': 'No matching data'}}], 
            [],  # ip-table.data
            [],  # ip-table.tooltip_data
            [],  # method-filter.options
            [],  # country-filter.options
            [],  # status-filter.options
            "Total Requests: 0",  # total-requests.children
            []  # error-log-table.data
        )
    error_data = load_error_logs()

    world_fig = px.density_map(
        lat=df["latitude"],
        lon=df["longitude"],
        z=None,
        radius=10,
        center={"lat": 20, "lon": 0},
        zoom=1,
        title="Geolocation Heatmap (IP-based)"
    )
    world_fig.update_layout(
        height=600,  # Adjust the height (in pixels)
        width=1200,   # Adjust the width (in pixels)
        margin={"r": 0, "t": 30, "l": 0, "b": 0},  # Optional: adjust margins for better layout
        geo=dict(
            showcoastlines=True, coastlinecolor="Black",
            projection_type="natural earth"  # You can change projection type as needed
        )
    )

    df['binned_time'] = df['time'].dt.floor(f'{bin_size}min')  # 'T' stands for minutes
    time_counts = df['binned_time'].value_counts().sort_index().reset_index()
    time_counts.columns = ['time', 'count']
    time_fig = px.bar(time_counts, x='time', y='count', title=f"Requests Over Time (Bin: {bin_size}min)")

    status_counts = df['status'].value_counts().reset_index()
    status_counts.columns = ['status', 'count']
    status_fig = px.pie(status_counts, names="status", values="count", title="Status Code Distribution")

    ip_data = df['ip'].value_counts().nlargest(15).reset_index()
    ip_data.columns = ['ip', 'count']
    top_ip_fig = px.bar(ip_data, x='ip', y='count', title="Top IPs")

    path_data = df['url'].value_counts().nlargest(15).reset_index()
    path_data.columns = ['url', 'count']
    top_path_fig = px.bar(path_data, x='url', y='count', title="Top Paths")
    ip_table = df.groupby(['ip', 'time','country', 'latitude', 'longitude', 'user_agent', 'is_bot', 'isp', 'usage_type']).size().reset_index(name='count')

    table_data = ip_table.to_dict("records")

    tooltip_data = [{
        'user_agent': {'value': row['user_agent'], 'type': 'markdown'},
        'isp': {'value': row['isp'], 'type': 'markdown'},
        'usage_type': {'value': row['usage_type'], 'type': 'markdown'}
    } for row in table_data]

    method_opts = [{'label': m, 'value': m} for m in sorted(df['method'].unique())]
    country_opts = [{'label': c, 'value': c} for c in sorted(df['country'].dropna().unique())]
    status_opts = [{'label': s, 'value': s} for s in sorted(df['status'].unique())]

    return world_fig, time_fig, status_fig, top_ip_fig, top_path_fig, table_data, tooltip_data, method_opts, country_opts, status_opts, f"Total Requests: {len(df)}", error_data

if __name__ == "__main__":
    app.run(debug=True, port=8050)
