import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
#import layout.layout as layout
from dash.dependencies import Input, Output
from file_manager.file_manager import FileManager
from replay_analysis.replay_analyzer import ReplayAnalyzer
from yaml import load as load_yaml, FullLoader
from cachetools import cached, TTLCache

app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Benchmarker"
file_manager = None
replay_analyzer = None

# the style arguments for the sidebar. We use position:fixed and a fixed width
SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "22rem",
    "padding": "2rem 1rem",
    "background-color": "#f8f9fa",
}

# the styles for the main content position it to the right of the sidebar and
# add some padding.
CONTENT_STYLE = {
    "position": "absolute",
    "z-index": 1000,
    "margin-left": "22rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}


def serve_layout():
    nav_elements = [dbc.NavLink("Home", href="/", active="exact")]
    if file_manager is not None:
        for nav_element in file_manager.get_replays_reverse_chronological():
            nav_elements.append(dbc.NavLink(nav_element.display_name, href=nav_element.url, active="exact"))
    sidebar = html.Div(
        [
            html.H2("Benchmarker", className="display-4"),
            html.Hr(),
            html.P(
                "Compare builds better.", className="lead"
            ),
            dbc.Nav(nav_elements, vertical=True, pills=True),
        ],
        style=SIDEBAR_STYLE,
    )
    content = html.Div(id="page-content", style=CONTENT_STYLE)

    return html.Div([dcc.Location(id="url"), sidebar, content])


app.layout = serve_layout


@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
@cached(cache=TTLCache(maxsize=16, ttl=1000))
def render_page_content(pathname):
    if pathname == "/":
        return html.P("This is the content of the home page!")
    else:
        replay_file = file_manager.get_replay_from_url(pathname)
        return replay_analyzer.get_analysis_for_file(replay_file)
    # If the user tries to reach a different page, return a 404 message
    return dbc.Jumbotron(
        [
            html.H1("404: Not found", className="text-danger"),
            html.Hr(),
            html.P(f"The pathname {pathname} was not recognised..."),
        ]
    )


if __name__ == "__main__":
    player_names = []
    try:
        with open("config.yaml", "r") as yamlfile:
            cfg = load_yaml(yamlfile, Loader=FullLoader)
    except FileNotFoundError:
        print("Config file doesn't exist, please create a file named 'config.yaml' in the same directory as "
              "benchmarker.py")
        exit(1)

    if 'directories' not in cfg:
        print("Config file does not contain a directories section.")
        exit(1)

    try:
        player_names = cfg['general']['player_names'].split(',')
    except KeyError as e:
        print("Unable to parse player name(s). Must be under general and formatted as a comma separated list.")
    file_manager = FileManager(cfg['directories'])
    replay_analyzer = ReplayAnalyzer(player_names, file_manager.canonical_dir)

    app.run_server(port=8888)
