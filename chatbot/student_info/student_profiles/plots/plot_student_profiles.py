from plotly import graph_objects as go


def plot_word_count_timelines(cumulative_word_count_by_student):

    # Define a list of colors from the colormap
    colors = [cmap(i) for i in range(cmap.N)]

    fig = go.Figure()

    for idx, (student, cumulative_word_count_by_datetimes) in enumerate(cumulative_word_count_by_student.items()):
        if len(student) == 1:
            continue
        word_count_by_datetimes = cumulative_word_count_by_datetimes['total']

        datetimes, word_counts = zip(*word_count_by_datetimes)

        # Convert the RGB tuple to an RGBA tuple and then to a CSS compatible string
        color = 'rgba' + str(colors[idx % len(colors)] + (0.5,))
        fig.add_trace(go.Scatter(x=datetimes,
                                 y=word_counts,
                                 color = word_counts,
                                 mode='lines+markers',
                                 marker=dict(size=6, color=color),
                                 line=dict(color=color),
                                 name=f"{student}"))

    fig.update_layout(
        title='Cumulative Word Count by Student',
        xaxis_title='Date',
        yaxis_title='Cumulative Word Count (Student+Bot)',
        autosize=True
    )

    fig.show()
