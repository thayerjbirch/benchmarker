import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import threading
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
from file_manager.file_manager import FileManager
from replay_analysis.replay_analyzer import ReplayAnalyzer, UNIT_DISPLAY_PAIRS_BY_RACE
from replay_analysis.background_analyzer import analyze_files_in_background, create_encodings_in_background
from replay_analysis.sc2_replay.units import UNITS
from yaml import load as load_yaml, FullLoader
from cachetools import cached, TTLCache

app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Benchmarker"
file_manager = None
replay_analyzer = None

PROTOSS_UNITS = ["Probe"] + UNITS["Protoss"]['army']
TERRAN_UNITS = ["SCV"] + UNITS["Terran"]['army']
ZERG_UNITS = ["Drone"] + UNITS["Zerg"]['army']

PROTOSS_STRUCTURES = UNITS["Protoss"]['structures']
TERRAN_STRUCTURES = UNITS["Terran"]['structures']
ZERG_STRUCTURES = UNITS["Zerg"]['structures']

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
        for nav_element in file_manager.get_replays_navs():
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

general_elements = [
    'Supply',
    'Income',
    'MineralIncome',
    'VespeneIncome',
    'ArmyValue',
    'ResourcesLost'
]


@app.callback([Output(component_id=element, component_property='style') for element in general_elements],
              [Input(component_id='general-dropdown', component_property='value')])
def general_dropdown_callback(dropdown_value):
    return_dict = {element: {'display': 'none'} for element in general_elements}
    if dropdown_value in return_dict.keys():
        return_dict[dropdown_value] = {'display': 'block'}
    else:
        raise PreventUpdate
    return tuple(return_dict.values())


@app.callback([Output(component_id=unit, component_property='style') for unit in PROTOSS_UNITS],
              [Input(component_id='Protoss-units-dropdown', component_property='value')])
def protoss_unit_dropdown_callback(dropdown_value):
    return_dict = {element: {'display': 'none'} for element in PROTOSS_UNITS}
    if dropdown_value in return_dict.keys():
        return_dict[dropdown_value] = {'display': 'block'}
    else:
        raise PreventUpdate
    return tuple(return_dict.values())


@app.callback([Output(component_id=unit, component_property='style') for unit in TERRAN_UNITS],
              [Input(component_id='Terran-units-dropdown', component_property='value')])
def terran_unit_dropdown_callback(dropdown_value):
    return_dict = {element: {'display': 'none'} for element in TERRAN_UNITS}
    if dropdown_value in return_dict.keys():
        return_dict[dropdown_value] = {'display': 'block'}
    else:
        raise PreventUpdate
    return tuple(return_dict.values())


@app.callback([Output(component_id=unit, component_property='style') for unit in ZERG_UNITS],
              [Input(component_id='Zerg-units-dropdown', component_property='value')])
def zerg_unit_dropdown_callback(dropdown_value):
    return_dict = {element: {'display': 'none'} for element in ZERG_UNITS}
    if dropdown_value in return_dict.keys():
        return_dict[dropdown_value] = {'display': 'block'}
    else:
        raise PreventUpdate
    return tuple(return_dict.values())


@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
@cached(cache=TTLCache(maxsize=16, ttl=1000))
def render_page_content(pathname):
    if pathname == "/":
        return html.P("This is the content of the home page!")
    else:
        return file_manager.load_analysis_from_url(pathname)
        # replay_file = file_manager.get_replay_from_url(pathname)
        # return replay_analyzer.get_analysis_for_file(replay_file)
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
    replay_analyzer = ReplayAnalyzer(player_names, file_manager)
    background_analyzer = threading.Thread(target=analyze_files_in_background, args=(file_manager, replay_analyzer))
    background_analyzer.start()
    background_encoder = threading.Thread(target=create_encodings_in_background, args=(file_manager,))
    background_encoder.start()

    app.run_server(port=8888)
