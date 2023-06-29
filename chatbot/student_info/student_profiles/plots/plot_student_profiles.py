import asyncio
import logging
from typing import List, Dict, Union

from plotly import graph_objects as go
from plotly.subplots import make_subplots

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


def plot_word_count_timelines(student_profiles: Dict[str, StudentProfile]):
    fig = make_subplots(rows=1, cols=2, shared_xaxes=True)

    row = 1
    cumulative_word_count_by_datetimes_by_type = calculate_cumulative_wordcount(student_profiles)
    for count_type, cumulative_word_count_by_datetimes in cumulative_word_count_by_datetimes_by_type.items():
        datetimes, word_counts = zip(*cumulative_word_count_by_datetimes)
        fig.add_trace(go.Scatter(x=datetimes,
                                 y=word_counts,
                                 mode='lines+markers',
                                 marker=dict(size=6),
                                 name=f"{count_type}"),
                      row=row, col=1)

    row = 2
    for student_id, profile in student_profiles.items():
        cumulative_word_count_by_datetimes = profile.cumulative_word_count_by_datetimes_by_type
        word_count_by_datetimes = cumulative_word_count_by_datetimes['total']
        datetimes, word_counts = zip(*word_count_by_datetimes)

        fig.add_trace(go.Scatter(x=datetimes,
                                 y=word_counts,
                                 mode='lines+markers',
                                 marker=dict(size=6),
                                 name=f"{student_id}"),
                      row=row, col=1)


    fig.update_layout(
        title='Cumulative Word Count by Student',
        xaxis_title='Date',
        yaxis_title='Cumulative Word Count (Student+Bot)',
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


if __name__ == "__main__":
    import asyncio

    student_profiles = asyncio.run(get_student_profiles())
    plot_student_profiles(student_profiles)
