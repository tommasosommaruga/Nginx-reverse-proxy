import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.express as px
import re
from datetime import datetime
import dash_bootstrap_components as dbc # Using bootstrap for better layout

log_file = "../nginx_logs/shield_access.log"

log_pattern = re.compile(
    r'(?P<ip>\S+) - - \[(?P<time>.*?)\] "(?P<method>\S+) (?P<url>\S+) (?P<protocol>[^"]+)" '
    r'(?P<status>\d{3}) (?P<size>\d+) "[^"]*" "(?P<user_agent>[^"]*)"'
)

def parse_log_line(line):
    match = log_pattern.match(line)
    if not match:
        return None
    data = match.groupdict()
    try:
        # Handle potential timezone parsing issues if necessary
        data["time"] = datetime.strptime(data["time"], "%d/%b/%Y:%H:%M:%S %z").replace(tzinfo=None) # Make timezone naive for easier comparison
    except ValueError:
        return None # Skip lines with unexpected date formats
    data["status"] = int(data["status"]) # Convert status to int
    data["size"] = int(data["size"]) # Convert size to int
    return data

def load_data():
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: Log file not found at {log_file}")
        return pd.DataFrame() # Return empty DataFrame if file not found
    data = [parse_log_line(line) for line in lines]
    df = pd.DataFrame([d for d in data if d])
    if not df.empty:
        df["time"] = pd.to_datetime(df["time"]) # Ensure time column is datetime
    return df

# Initialize the app with Bootstrap themes
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Load initial data to populate filters
initial_df = load_data()
initial_ips = initial_df['ip'].unique() if not initial_df.empty else []
initial_statuses = initial_df['status'].unique() if not initial_df.empty else []
initial_min_date = initial_df['time'].min() if not initial_df.empty else datetime.now()
initial_max_date = initial_df['time'].max() if not initial_df.empty else datetime.now()


app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("NGINX Shield Dashboard"), width=12)),
    dcc.Interval(id="interval", interval=30000, n_intervals=0), # Update every 30 seconds

    dbc.Row([
        dbc.Col([
            html.Label("Date Range:"),
            dcc.DatePickerRange(
                id='date-picker-range',
                min_date_allowed=initial_min_date,
                max_date_allowed=initial_max_date,
                initial_visible_month=initial_min_date,
                start_date=initial_min_date,
                end_date=initial_max_date,
                display_format='YYYY-MM-DD'
            )
        ], width=4),
        dbc.Col([
            html.Label("IP Address:"),
            dcc.Dropdown(
                id='ip-filter',
                options=[{'label': ip, 'value': ip} for ip in initial_ips],
                multi=True,
                placeholder="Filter by IP Address..."
            )
        ], width=3),
        dbc.Col([
            html.Label("Status Code:"),
            dcc.Dropdown(
                id='status-filter',
                options=[{'label': str(status), 'value': status} for status in sorted(initial_statuses)],
                multi=True,
                placeholder="Filter by Status Code..."
            )
        ], width=2),
        dbc.Col([
            html.Label("URL Path Contains:"),
            dbc.Input(id='url-filter', type='text', placeholder='Filter by URL path...'),
        ], width=3)
    ], className="mb-4"), # Add margin bottom

    dbc.Row([
        dbc.Col(dcc.Graph(id="reqs-over-time"), width=6),
        dbc.Col(dcc.Graph(id="top-ips"), width=6),
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(id="top-paths"), width=6),
        dbc.Col(dcc.Graph(id="status-codes"), width=6),
    ])
], fluid=True) # Use fluid container for full width

@app.callback(
    Output("reqs-over-time", "figure"),
    Output("top-ips", "figure"),
    Output("top-paths", "figure"),
    Output("status-codes", "figure"),
    # Update dropdown options dynamically if needed (optional for now)
    # Output("ip-filter", "options"),
    # Output("status-filter", "options"),
    Input("interval", "n_intervals"),
    Input("date-picker-range", "start_date"),
    Input("date-picker-range", "end_date"),
    Input("ip-filter", "value"),
    Input("status-filter", "value"),
    Input("url-filter", "value")
)
def update_graphs(n, start_date, end_date, selected_ips, selected_statuses, url_contains):
    df = load_data()
    if df.empty:
        # Return empty figures or messages if no data
        no_data_fig = {'layout': {'title': 'No data available'}}
        return no_data_fig, no_data_fig, no_data_fig, no_data_fig

    # --- Apply Filters ---
    # Date Filter
    if start_date and end_date:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        # Add time component to end_date to include the whole day
        end_date = end_date.replace(hour=23, minute=59, second=59)
        df = df[(df['time'] >= start_date) & (df['time'] <= end_date)]

    # IP Filter
    if selected_ips: # Check if list is not empty
        df = df[df['ip'].isin(selected_ips)]

    # Status Code Filter
    if selected_statuses: # Check if list is not empty
        df = df[df['status'].isin(selected_statuses)]

    # URL Filter
    if url_contains: # Check if string is not empty
        df = df[df['url'].str.contains(url_contains, case=False, na=False)]

    # --- Regenerate Figures with Filtered Data ---
    if df.empty:
        # Return empty figures or messages if no data *after filtering*
        no_data_fig = {'layout': {'title': 'No data matches filters'}}
        return no_data_fig, no_data_fig, no_data_fig, no_data_fig

    # Requests Over Time (consider adjusting bins based on date range)
    time_range_days = (df['time'].max() - df['time'].min()).days
    nbins = max(10, min(60, time_range_days * 2 if time_range_days > 0 else 30)) # Dynamic bins
    fig1 = px.histogram(df, x="time", nbins=nbins, title="Requests Over Time (Filtered)")
    fig1.update_layout(bargap=0.1)

    # Top IPs
    top_ips_data = df['ip'].value_counts().nlargest(15).reset_index()
    top_ips_data.columns = ['ip', 'count']
    fig2 = px.bar(top_ips_data, x='ip', y='count', title="Top 15 IPs (Filtered)")

    # Top Paths
    top_paths_data = df['url'].value_counts().nlargest(15).reset_index()
    top_paths_data.columns = ['url', 'count']
    fig3 = px.bar(top_paths_data, x='url', y='count', title="Top 15 Requested Paths (Filtered)")

    # Status Codes
    status_counts = df['status'].value_counts().reset_index()
    status_counts.columns = ['status', 'count']
    fig4 = px.pie(status_counts, names="status", values="count", title="Status Codes Distribution (Filtered)")

    # Update dropdown options (optional - could be based on the full dataset or filtered)
    # current_ips = [{'label': ip, 'value': ip} for ip in df['ip'].unique()]
    # current_statuses = [{'label': str(status), 'value': status} for status in sorted(df['status'].unique())]

    return fig1, fig2, fig3, fig4 #, current_ips, current_statuses

if __name__ == "__main__":
    app.run(debug=True, port=8050) # Use a different port if 8050 is busy
    