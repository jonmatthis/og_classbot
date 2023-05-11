# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Add current directory code to working directory in Docker image
ADD . /app

#Install Poetry  so we can use it to install dependencies
RUN pip install poetry

# Install package dependencies with `pyproject.toml` file
RUN pip install .

# Make port  available to the world outside this container
EXPOSE 1123

# Run the command to start your application
CMD [ "python", "chatbot/discord_bot/discord_bot_main.py" ]
