import asyncio
import logging
from typing import List, Dict, Union

from plotly import graph_objects as go

from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager
from chatbot.student_info.student_profiles.student_profile_models import StudentProfile

logger = logging.getLogger(__name__)
def plot_word_count_timelines(student_profiles: Dict[str, StudentProfile]):


    fig = go.Figure()

    for student_id, profile in student_profiles.items():
        cumulative_word_count_by_datetimes = profile.cumulative_word_count_by_datetimes_by_type


        word_count_by_datetimes = cumulative_word_count_by_datetimes['total']

        datetimes, word_counts = zip(*word_count_by_datetimes)

        # Convert the RGB tuple to an RGBA tuple and then to a CSS compatible string
        fig.add_trace(go.Scatter(x=datetimes,
                                 y=word_counts,
                                 mode='lines+markers',
                                 marker=dict(size=6),
                                 name=f"{student_id}"))

    fig.update_layout(
        title='Cumulative Word Count by Student',
        xaxis_title='Date',
        yaxis_title='Cumulative Word Count (Student+Bot)',
        autosize=True
    )

    fig.show()


async def get_student_profiles()->Dict[str, StudentProfile]:
    mongo_database_manager = MongoDatabaseManager()
    collection = mongo_database_manager.get_collection(collection_name="student_profiles")
    profile_list =  await collection.find().to_list(length=None)
    student_profiles = {profile["initials"]: StudentProfile(**profile) for profile in profile_list}

    to_delete = []
    for student_id in student_profiles.keys():
        if len(student_id)==1:
            to_delete.append(student_id)
    for student_id in to_delete:
        del student_profiles[student_id]
    return student_profiles


def plot_student_profiles(student_profiles: Dict[str, StudentProfile]):
    plot_word_count_timelines(student_profiles)


if __name__ == "__main__":
    import asyncio

    student_profiles = asyncio.run(get_student_profiles())
    plot_student_profiles(student_profiles)