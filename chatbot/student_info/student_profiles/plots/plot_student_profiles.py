import asyncio
import logging
from typing import Dict

import dash as dash
from dash import html, dcc
from plotly import graph_objects as go
from plotly.offline import plot
from plotly.subplots import make_subplots
from pydantic import BaseModel

from chatbot.mongo_database.data_getters import get_student_profiles
from chatbot.student_info.student_profiles.student_profile_models import StudentProfile

logger = logging.getLogger(__name__)


def calculate_cumulative_wordcount(student_profiles: Dict[str, StudentProfile]):
    word_count_by_datetimes_by_type = {"total": [], "student": [], "bot": []}
    for student_id, profile in student_profiles.items():
        for count_type, wordcount_by_datetimes in profile.word_count_by_datetimes_by_type.items():
            word_count_by_datetimes_by_type[count_type].extend(wordcount_by_datetimes)
            word_count_by_datetimes_by_type[count_type].sort(key=lambda x: x[0])

    cumulative_word_count_by_datetimes_by_type = {"total": [], "student": [], "bot": []}
    for count_type, word_count_by_datetimes in word_count_by_datetimes_by_type.items():
        cumulative_word_count = 0
        for datetime, word_count in word_count_by_datetimes:
            cumulative_word_count += word_count
            cumulative_word_count_by_datetimes_by_type[count_type].append(
                (datetime, cumulative_word_count))

    return cumulative_word_count_by_datetimes_by_type


class SubplotModel(BaseModel):
    row: int = 1
    col: int = 1
    title: str = None
    xaxis_title: str = None
    yaxis_title: str = None
    autosize: bool = True
    showlegend: bool = True


def plot_word_count_timelines(student_profiles: Dict[str, StudentProfile]):
    class_subfig = make_class_subfig(student_profiles)

    student_subfig = make_student_subfig(student_profiles)
    return class_subfig, student_subfig


def make_class_subfig(student_profiles):
    subplot_model = SubplotModel(row=1,
                                 col=1,
                                 title="Class Total Word Count",
                                 yaxis_title="Cumulative Word Count")

    fig1 = make_subplots(rows=1, cols=1, subplot_titles=(subplot_model.title,))
    cumulative_word_count_by_datetimes_by_type = calculate_cumulative_wordcount(student_profiles)
    for count_type in ["total", "bot", "student"]:
        cumulative_word_count_by_datetimes = cumulative_word_count_by_datetimes_by_type[count_type]
        datetimes, word_counts = zip(*cumulative_word_count_by_datetimes)
        fig1.add_trace(go.Scatter(x=datetimes,
                                  y=word_counts,
                                  mode='lines+markers',
                                  marker=dict(size=5),
                                  name=f"{count_type}"))
        fig1.update_xaxes(tickfont=dict(size=14))
        fig1.update_yaxes(title_text=subplot_model.yaxis_title,
                          tickfont=dict(size=14))
    fig1.update_layout(
        title_x=0.5,
        autosize=True,
        margin=dict(l=10, r=10, t=80, b=20),
        legend=dict(
            x=0,
            y=1,
            traceorder="normal",
            font=dict(
                size=12,
            ),
            bgcolor=None,
        )
    )
    return fig1


def make_student_subfig(student_profiles):
    student_subplot = SubplotModel(row=2,
                                   col=1,
                                   title="Per Student",
                                   xaxis_title="Date",
                                   yaxis_title="Word Count (student only)",
                                   )

    fig2 = make_subplots(rows=1, cols=1, subplot_titles=(student_subplot.title,))
    for student_id, profile in student_profiles.items():
        cumulative_word_count_by_datetimes = profile.cumulative_word_count_by_datetimes_by_type
        word_count_by_datetimes = cumulative_word_count_by_datetimes['student']
        datetimes, word_counts = zip(*word_count_by_datetimes)

        fig2.add_trace(go.Scatter(x=datetimes,
                                  y=word_counts,
                                  mode='lines+markers',
                                  marker=dict(size=5)))
        fig2.update_xaxes(title_text=student_subplot.xaxis_title,
                          tickfont=dict(size=14)
                          )
        fig2.update_yaxes(title_text=student_subplot.yaxis_title,
                          tickfont=dict(size=14))
    fig2.update_layout(
        autosize=True,
        showlegend=False,
        margin=dict(l=10, r=10, t=40, b=40),
        title=dict(
            x=0.5,
            font=dict(
                size=24
            ),
        ),

    )

    return fig2


def main():
    app = dash.Dash(__name__)

    def update_figure(n_clicks):
        student_profiles = asyncio.run(get_student_profiles())
        fig1, fig2 = plot_word_count_timelines(student_profiles)
        return fig1, fig2

    initial_figure_class, initial_figure_student = update_figure(None)

    app.layout = html.Div([
        html.H1('Cumulative Word Count', style={'textAlign': 'center',
                                                'fontFamily': 'Helvetica',}),

        dcc.Graph(id='wordcount-plot-class', figure=initial_figure_class, style={'height': '40vh',
                                                                                 'width': '70%',
                                                                                 'align': 'center'}),
        dcc.Graph(id='wordcount-plot-student', figure=initial_figure_student, style={'height': '60vh',
                                                                                     'width': '70%',
                                                                                     'align': 'center'}),
    ], style={'height': '100vh', 'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center'})
    plot(initial_figure_class, filename='html/figure_class.html')
    plot(initial_figure_student, filename='html/figure_student.html')
    app.run_server(debug=True)


if __name__ == "__main__":
    main()
