import plotly.graph_objects as graph_objects
import random

tableau20 = ['rgb(%s,%s,%s)' % (r, g, b) for r, g, b in
             [(31, 119, 180), (174, 199, 232), (255, 127, 14), (255, 187, 120),
              (44, 160, 44), (152, 223, 138), (214, 39, 40), (255, 152, 150),
              (148, 103, 189), (197, 176, 213), (140, 86, 75), (196, 156, 148),
              (227, 119, 194), (247, 182, 210), (127, 127, 127), (199, 199, 199),
              (188, 189, 34), (219, 219, 141), (23, 190, 207), (158, 218, 229)]]
random.shuffle(tableau20)
TICKS_PER_SECOND = 22.4


def create_plotly_timeseries_graph(data: [(str, [])], title: str = ""):
    # We calculate the length of the longer replay to determine how big the graph
    # needs to be.
    length = 0
    fig = graph_objects.Figure()
    players = []
    for rank, series in enumerate(data):
        last_second = -1
        filtered_values = []
        # Just keeping resolution to the second to reduce data size
        for t, value in enumerate(series[1]):
            if int(t / TICKS_PER_SECOND) != last_second:
                filtered_values.append(value)
                last_second = int(t / TICKS_PER_SECOND)
        player = (rank, series[0], filtered_values)

        if len(player[2]) > length:
            length = len(player[2])
        players.append(player)

    formatted_seconds = []
    ticks = []
    for i in range(length):
        minutes, seconds = divmod(i, 60)
        formatted_seconds.append('%s:%02d' % (minutes, seconds))
        if minutes not in ticks:
            ticks.append('%s:00' % minutes)
    for player in players:
        fig.add_traces(graph_objects.Scatter(x=formatted_seconds, y=player[2],
                                             name=player[1],
                                             line={"color": tableau20[player[0]]},
                                             mode="lines"))
    fig.update_layout(hovermode="x unified",
                      xaxis=dict(
                          tickmode='array',
                          tickvals=ticks
                      ),
                      width=1366,
                      height=768)
    return fig
