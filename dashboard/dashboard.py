import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import re
from datetime import datetime

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
    data["time"] = datetime.strptime(data["time"], "%d/%b/%Y:%H:%M:%S %z")
    return data

def load_data():
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    data = [parse_log_line(line) for line in lines]
    return pd.DataFrame([d for d in data if d])

app = dash.Dash(__name__)
app.layout = html.Div([
    html.H1("NGINX Shield Dashboard"),
    dcc.Interval(id="interval", interval=5000, n_intervals=0),
    dcc.Graph(id="reqs-over-time"),
    dcc.Graph(id="top-ips"),
    dcc.Graph(id="top-paths"),
    dcc.Graph(id="status-codes"),
])

@app.callback(
    Output("reqs-over-time", "figure"),
    Output("top-ips", "figure"),
    Output("top-paths", "figure"),
    Output("status-codes", "figure"),
    Input("interval", "n_intervals")
)
def update_graphs(n):
    df = load_data()
    if df.empty:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    df["time"] = pd.to_datetime(df["time"])

    fig1 = px.histogram(df, x="time", nbins=30, title="Requests Over Time")
    fig2 = px.bar(df["ip"].value_counts().nlargest(10), title="Top IPs")
    fig3 = px.bar(df["url"].value_counts().nlargest(10), title="Top Requested Paths")
    fig4 = px.pie(df, names="status", title="Status Codes")

    return fig1, fig2, fig3, fig4

if __name__ == "__main__":
    app.run(debug=True)
