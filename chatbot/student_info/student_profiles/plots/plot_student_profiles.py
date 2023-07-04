import asyncio
import logging
from typing import Dict

import dash as dash
from dash import html, dcc
from plotly import graph_objects as go
from plotly.io import to_html
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
    create_combined_html_output(initial_figure_class, initial_figure_student)
    app.layout = html.Div([
        html.H1('Cumulative Word Count', style={'textAlign': 'center',
                                                'fontFamily': 'Helvetica', }),

        dcc.Graph(id='wordcount-plot-class', figure=initial_figure_class, style={'height': '40vh',
                                                                                 'width': '70%',
                                                                                 'align': 'center'}),
        dcc.Graph(id='wordcount-plot-student', figure=initial_figure_student, style={'height': '60vh',
                                                                                     'width': '70%',
                                                                                     'align': 'center'}),
    ], style={'height': '100vh', 'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center'})

    app.run_server(debug=True)


def create_combined_html_output(initial_figure_class, initial_figure_student):
    # convert both figures to HTML divs
    div1 = to_html(initial_figure_class, full_html=False)
    div2 = to_html(initial_figure_student, full_html=False)
    with open('html/combined_figures.html', 'w', encoding="utf-8") as file:
        # write the HTML page structure
        file.write(f"""
        <html>
        <head>
            <title>Neural Control of Real World Human Movement - Summer 1 - 2023</title>
            <style>
            body {{
                font-family: "Open Sans", Verdana, Arial, sans-serif;
            }}
            h1 {{
                text-align: center;
                color: #888888;
                font-size: 2em;
            }}
            h2 {{
                color: #008CBA;
                text-align: center;
            }}
            p {{
                text-indent: 5px;
                text-align: justify;
                align-content: center;
            }}
            .top_explanation {{
                text-indent: 5px;
                text-align: justify;
                width: 60%;
            }}
            .plot {{
                height: 50vh; 
                width: 60%;
            }}
            .explanation {{
                width: 30%;
                padding-left: 5px;
            }}
            .section {{
                display: flex;
                flex-direction: row;
                justify-content: center;
                align-items: center;
                margin-bottom: 10px;
            }}
            </style>
        </head>
        <body>
            <h1>Words Generated in Neural Control of Real World Human Movement - Summer 1 - 2023</h1>
            <div class="top_explanation">
             The visualizations depict data from an asynchronous online course conducted in the summer of 2043. The course utilized an AI-powered Discord bot to facilitate course content and assignments. The bot was programmed with the syllabus and interacted with students based on their individual interests. Course assignments, instantiated by the bot, required students to interact with it in various ways - The first assignment was an "introduction" conversation wherein the student discussed their interests and the bot attemptd to find relevance to the course material. Later assignment involved the bot helping the students search PubMed and Google Scholar for relvant research articles, and then helping them summarize, format, and provide 'topic tags'. The results of this asignment may be viewed here: https://neuralcontrolhumanmovement-2023-summer1.github.io/main_course_repo/CourseObsidianVault/paper_summaries/
             
             
            </div>
            <div class="section">
                <div class="plot">
                    {div1}
                </div>
                <div class="explanation">
                    <h2>Class Total Word Count</h2>
            <p>Total number of words generated in this course. <span style="color:green">Green</span> dots denote words accumulated from a single message written by the students, <span style="color:red">Red</span> dots denote messages written by the bot (presumably read by the students) and the <span style="color:blue">blue</span> dots show the total words over time (student + bot)</p>       
            </div>
            </div>
            <div class="section">
                <div class="plot">
                    {div2}
                </div>
                <div class="explanation">
                    <h2>Per Student Word Count</h2>
            <p>Words generated by each student (bot responses not shown). Different colored lines denote different students, with each dot representing the words accumulated from a single message. The vertical stripes represent times when the student was conversing with thebot in a thread. \n\n Note that one assignment involved copy-pasting paper abstracts into the chat, so not all of these words were specifically typed by students.</p>                </div>
            </div>
        </body>
        </html>
        """)


if __name__ == "__main__":
    main()
