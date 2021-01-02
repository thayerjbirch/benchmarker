import PySimpleGUI as sg

# Design pattern 2 - First window remains active

sg.theme('Reddit')
main_window_layout = [[sg.Text('Replay Directory:'), sg.Input(do_not_clear=True, key='REPLAY_DIR')],
          [sg.Text('Example Replays Directory:')],
          [sg.Input(do_not_clear=True, key="EXAMPLE_DIR")],
          [sg.Text(size=(15, 1), key='-OUTPUT-')],
          [sg.Button('Choose a replay'), sg.Button('Exit')]]


main_window = sg.Window('Replay Benchmarker', main_window_layout)

analysis_window_active = False
analysis_window = None
while True:
    ev1, vals1 = main_window.read(timeout=100)
    #main_window['-OUTPUT-'].update(vals1)
    if ev1 is None or ev1 == 'Exit':
        break

    if not analysis_window and ev1 == 'Launch 2':
        analysis_window_active = True
        layout2 = [[sg.Text('Window 2')],
                   [sg.Button('Exit')]]

        analysis_window = sg.Window('Window 2', layout2)

    if analysis_window_active:
        ev2, vals2 = analysis_window.read(timeout=100)
        if ev2 is None or ev2 == 'Exit':
            analysis_window_active = False
            analysis_window.close()