import asyncio
import os
from pathlib import Path
from typing import Union, List

import numpy as np
import plotly.graph_objects as go
from langchain.embeddings import OpenAIEmbeddings
from langchain.schema import Document
from langchain.vectorstores import Chroma
from scipy.spatial import ConvexHull
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE

from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager
from chatbot.system.filenames_and_paths import get_thread_backups_collection_name


async def create_student_message_vector_store(collection_name: str = get_thread_backups_collection_name()):
    mongo_database = MongoDatabaseManager()
    collection = mongo_database.get_collection(collection_name)
    all_thread_entries = await collection.find().to_list(length=None)

    print(f"Creating document list from {collection_name} collection with {len(all_thread_entries)} entries")

    student_vector_stores = {}
    student_documents = {}
    for thread_entry in all_thread_entries:
        student_name = thread_entry["_student_name"]
        if student_name not in student_documents:
            student_documents[student_name] = []

        list_of_strings = thread_entry["thread_as_list_of_strings"]
        chunks = chunk_list_of_strings(list_of_strings)
        print(f"Creating vector store for student: {student_name}  with {len(list_of_strings)} chunks")

        metadata = {"_student_name": student_name,
                    "_student_uuid": thread_entry["_student_uuid"],
                    "server_name": thread_entry["server_name"],
                    "channel_name": thread_entry["channel"],
                    "thread_id": thread_entry["thread_id"],
                    "thread_url": thread_entry["thread_url"],
                    "thread_as_list_of_strings": list_of_strings,
                    "thread_as_one_string": thread_entry["thread_as_one_string"],
                    }

        for chunk in chunks:
            student_documents[student_name].append(Document(page_content="\n".join(chunk),
                                                            metadata={"student_name": student_name}))

    print("------------------------------------\n",
          "------------------------------------\n")

    for student_name, student_message_documents in student_documents.items():
        print(f"Creating vector store from {student_name} collection with {len(student_message_documents)} entries")
        embeddings_model = OpenAIEmbeddings()
        student_vector_stores[student_name] = Chroma.from_documents(
            documents=student_message_documents,
            embedding=embeddings_model,
            collection_name="student_message_vector_store",
            persist_directory=str(Path(os.getenv("PATH_TO_CHROMA_PERSISTENCE_FOLDER")) / "student_message_vector_store")
        )

    return student_vector_stores


def chunk_list_of_strings(list_of_strings):
    def chunk_string_list(lst):
        return [lst[i - 1:i + 2] for i in range(1, len(lst) - 1)]

    chunks = chunk_string_list(list_of_strings)
    return chunks


async def create_green_check_vector_store(collection_name: str = "green_check_messages"):
    mongo_database = MongoDatabaseManager()
    collection = mongo_database.get_collection(collection_name)
    all_entries = await collection.find().to_list(length=None)
    print("Creating vector store from {collection_name} collection with {len(all_entries)} entries")
    documents = []
    for entry in all_entries:
        documents.append(Document(page_content=entry["parsed_output_dict"]["abstract"],
                                  metadata={"_student_uuid": entry["_student_uuid"],
                                            "thread_url": entry["thread_url"],
                                            "source": entry["parsed_output_dict"]["citation"],
                                            **entry["parsed_output_dict"], }))
    embeddings_model = OpenAIEmbeddings()
    chroma_vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings_model,
        collection_name=collection_name,
        # persist_directory=str(Path(os.getenv("PATH_TO_CHROMA_PERSISTENCE_FOLDER")) / collection_name),
    )
    return chroma_vector_store


def visualize_clusters(embeddings: Union[List[List[float]], np.ndarray],
                       labels: List[str], n_clusters: int):
    tsne = TSNE(n_components=2,
                random_state=42,
                perplexity=5)

    if embeddings.__class__ == list:
        embeddings = np.array(embeddings)

    embeddings_2d = tsne.fit_transform(embeddings)

    # Apply KMeans clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    kmeans_labels = kmeans.fit_predict(embeddings_2d)

    data = []
    cluster_colors = ['#1f77b4',
                      '#ff7f0e',
                      '#2ca02c',
                      '#d62728',
                      '#9467bd',
                      '#8c564b',
                      '#e377c2',
                      '#7f7f7f',
                      '#bcbd22',
                      '#17becf']  # colors for up to 10 clusters

    for cluster in range(n_clusters):
        cluster_indices = np.where(kmeans_labels == cluster)
        x = embeddings_2d[cluster_indices, 0].ravel()
        y = embeddings_2d[cluster_indices, 1].ravel()

        data.append(go.Scatter(x=x,
                               y=y,
                               mode='markers',
                               marker=dict(size=10,  # makes markers bigger
                                           color=cluster_colors[cluster],
                                           line=dict(width=2, color='Black')),  # outlines the marker with black
                               text=[f'Label: {labels[i]}' for i in cluster_indices[0]],  # adding labels
                               hoverinfo='text',
                               name=f'Cluster {cluster}'))

        if len(x) >= 3:  # Convex hull needs at least 3 points
            hull = ConvexHull(np.column_stack([x, y]))
            for simplex in hull.simplices:
                data.append(go.Scatter(x=x[simplex],
                                       y=y[simplex],
                                       mode='lines',
                                       line=dict(color=cluster_colors[cluster]),
                                       hoverinfo='skip'))

    layout = go.Layout(title='t-SNE Visualization of Vectorstore Clustering with KMeans',
                       xaxis=dict(title='Dimension 1'),
                       yaxis=dict(title='Dimension 2'),
                       showlegend=True)

    fig = go.Figure(data=data, layout=layout)
    fig.show()


async def main():
    # vector_store = await create_green_check_vector_store()
    vector_stores = await create_student_message_vector_store()
    for student_name, vector_store in vector_stores.items():
        collection = vector_store._collection.get(include=["embeddings", "documents", "metadatas"])
        embeddings = collection["embeddings"]
        labels = [document for document in collection["documents"]]
        visualize_clusters(embeddings=embeddings, labels=labels, n_clusters=4)


if __name__ == "__main__":
    asyncio.run(main())
