import asyncio
import logging
from typing import Dict

import dash as dash
from dash import html, dcc
from plotly import graph_objects as go
from plotly.subplots import make_subplots
from pydantic import BaseModel

from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager
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
    row: int
    col: int
    title: str
    xaxis_title: str
    yaxis_title: str
    autosize: bool = True


def plot_word_count_timelines(student_profiles: Dict[str, StudentProfile]):
    class_subplot = SubplotModel(row=1,
                                 col=1,
                                 title="Class Total",
                                 xaxis_title="Date",
                                 yaxis_title="Cumulative Word Count")
    student_subplot = SubplotModel(row=2,
                                   col=1,
                                   title="Per Student",
                                   xaxis_title="Date",
                                   yaxis_title="Cumulative Word Count(student+bot)")

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=(class_subplot.title, student_subplot.title))

    cumulative_word_count_by_datetimes_by_type = calculate_cumulative_wordcount(student_profiles)
    for count_type, cumulative_word_count_by_datetimes in cumulative_word_count_by_datetimes_by_type.items():
        datetimes, word_counts = zip(*cumulative_word_count_by_datetimes)
        fig.add_trace(go.Scatter(x=datetimes,
                                 y=word_counts,
                                 mode='lines+markers',
                                 marker=dict(size=5),
                                 name=f"{count_type}"),
                      row=class_subplot.row, col=class_subplot.col)
        fig.update_xaxes(title_text=class_subplot.xaxis_title, row=class_subplot.row, col=class_subplot.col)
        fig.update_yaxes(title_text=class_subplot.yaxis_title, row=class_subplot.row, col=class_subplot.col)

    for student_id, profile in student_profiles.items():
        cumulative_word_count_by_datetimes = profile.cumulative_word_count_by_datetimes_by_type
        word_count_by_datetimes = cumulative_word_count_by_datetimes['total']
        datetimes, word_counts = zip(*word_count_by_datetimes)

        fig.add_trace(go.Scatter(x=datetimes,
                                 y=word_counts,
                                 mode='lines+markers',
                                 marker=dict(size=5),
                                 name=f"{student_id}"),
                      row=student_subplot.row, col=student_subplot.col)
        fig.update_xaxes(title_text=student_subplot.xaxis_title, row=student_subplot.row, col=student_subplot.col)
        fig.update_yaxes(title_text=student_subplot.yaxis_title, row=student_subplot.row, col=student_subplot.col)

    fig.update_layout(
        title='Cumulative Word Count',
        autosize=True
    )
    return fig


async def get_student_profiles() -> Dict[str, StudentProfile]:
    mongo_database_manager = MongoDatabaseManager()
    collection = mongo_database_manager.get_collection(collection_name="student_profiles")
    profile_list = await collection.find().to_list(length=None)
    student_profiles = {profile["initials"]: StudentProfile(**profile) for profile in profile_list}

    to_delete = []
    for student_id in student_profiles.keys():
        if len(student_id) == 1:
            to_delete.append(student_id)
    for student_id in to_delete:
        del student_profiles[student_id]
    return student_profiles


def plot_student_profiles(student_profiles: Dict[str, StudentProfile]):
    fig = plot_word_count_timelines(student_profiles)
    fig.show()



def main():
    app = dash.Dash(__name__)
    @app.callback(
        dash.dependencies.Output('wordcount-plot', 'figure'),
        [dash.dependencies.Input('refresh-button', 'n_clicks')]
    )
    def update_figure(n_clicks):
        student_profiles = asyncio.run(get_student_profiles())
        return plot_word_count_timelines(student_profiles)


    initial_figure = update_figure(None)

    app.layout = html.Div([
        html.Button('Refresh data', id='refresh-button'),
        dcc.Graph(id='wordcount-plot', figure=initial_figure, style={'height': '90vh'}),
    ], style={'height': '100vh'})

    app.run_server(debug=True)

if __name__ == "__main__":
    main()