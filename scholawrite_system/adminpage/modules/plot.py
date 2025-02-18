from .utils import console, titles


def plot_stack_chart(chart_data):
    dates = []
    pids = []

    for key in chart_data:
        dates.append(key)

    for date in dates:
        try:
            for pid in chart_data[date][1]:
                if (pid not in pids) and (pid != "null"):
                    pids.append(pid)
        except IndexError:
            continue

    bar_data = []
    # stack_color = generate_category_colors(len(pids))
    for pid in pids:
        edits = []
        for date in dates:
            try:
                if pid in chart_data[date][1]:
                    edits.append(chart_data[date][1][pid])
                else:
                    edits.append(0)
            except IndexError:
                edits.append(0)
        bar_data.append(edits)

    result_list = [titles.get(element, element) for element in dates]
    graph_data = {'labels': result_list, 'datasets': []}

    result_list = [titles.get(element, element) for element in pids]
    for i in range(len(bar_data)):
        bar = {'label': result_list[i], 'data': bar_data[i], 'borderWidth': 0}
        graph_data['datasets'].append(bar)

    return graph_data


def plot_chart(chart_data):
    try:
        chart_data = chart_data[0]
    except IndexError:
        chart_data = []

    labels = []
    bar_data = []
    for key in chart_data:
        if key != "null":
            labels.append(key)
            bar_data.append(chart_data[key])

    result_list = [titles.get(element, element) for element in labels]
    graph_data = {'labels': result_list, 'datasets': []}
    bar = {'data': bar_data, 'borderWidth': 0}
    graph_data['datasets'].append(bar)

    return graph_data