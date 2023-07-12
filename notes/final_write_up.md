
# First Deployment of AI-Powered Chatbot in Online Asynchronous University Class

<img width="1698" alt="image" src="https://github.com/jonmatthis/chatbot/assets/15314521/e4cdaea4-c7f2-4dca-9050-2d3f487ea389">


### Introduction

This report outlines the first deployment of a novel human-in-the-loop, artificial-intelligence (AI) augmented educational methodology in an an online asynchronous class taught at an R1 university in Boston MA USA in May-June 2023.  

In this course (title: 'The Neural Control of Real World Human Movement'), a human professor utilized a variety of Large Language Model (LLM) powered methods to augment traditional online async teaching methods (i.e. video lectures) in order to  provide a personalized educational experience to each student and steer course content according to the individually expressed student interests.

## Methods & Materials

The source code for this software is freely available under an AGPLv3 on Github - https://github.com/jonmatthis/chatbot

The prompt that powered the main course assistant bot is shown here: 
https://github.com/jonmatthis/chatbot/blob/main/chatbot/ai/assistants/course_assistant/prompts/general_course_assistant_prompt.py

The AI-augmented aspects of this course was developed using Python and utilized the LangChain package to interact with OpenAI's `gpt-4`, `gpt-3.5-turbo`, and Anthropic's `claude-v1` large language models (LLM's) to interact with the students using natural language chat features in a Discord server ("the course server"). The `Course Assistant` chatbot ("the bot", link to the bot's code and prompt) software was run in a local Docker image on the professor's personal computer  (though it really should have been on AWS or GCP or something). Conversations between students and the bot were periodically scraped from the course Discord server into a MongoDB non-relational database for storage, analysis, and processing via a variety of LLM-enabled methods


### Course Structure and Methodology

The students interacted with the bot for most assignments, which were configured with various system prompts that would elicit different behaviors. The bot was instructed to steer conversations towards specific assignment goals. Student responses were then scraped and analyzed using summarization and schematization algorithms to understand their interests and guide lecture topics.

### Results
Over the course of the 8-week course,  the 20 enrolled students cumulatively wrote approximately 50,000 words (NOTE - add averages, max, min, std-dev, reference a figure, mention and correct for the copy-paste-an-abstract assignment) in 113 total conversations (NOTE - get exact number, average per student, etc) with the AI-powered chatbot that was configured as a primary "Course Assistant" interface. The bot, in turn, produced approximately 100k words (NOTE - averages, etc) in response. This level of student engagement is notoriously difficult to elicit in online asynchronous courses, which suggests that AI-assisted, human-in-the-loop teaching practices could be developed to improve outcomes across a wide range of educational contexts



## Discusssion

### Weaknesses to be addressed in later iterations
- never managed to pull the students together into groups
- didn't have much of an "output"
- Bot didn't really incorporate its previous interactions with the students into its conversations
- The human side of the teaching experience was thin (because the professor was too overwhelmed coding up the bot/analyses lol)

### Some ethical considerations

- **This is not a 'set-and-forget' method**,  a human educator is needed to ensure that the students get an actual educational experience and not just sessions with a mechanical parrot (i.e. human in the loop)
	- The course becomes a conversation between teacher and student, where the professor makes it clear that they are using and tuning the bot as a way of interacting with the student in a process of semi-automated pseudo-mentorship
		- Basically, I'm the prof and I decide what shape of bot I want the students to interact with in order to elicit the educational experience I desire to impart
		- This establishes the classes as an interactive collaboration, rather than the strictly hierarchical "passive consumption and regurgitation" methods of a standard educational experience. 

- **Risk of bias when using AI to *evaluate* student performance** 
	- There is a significant potential  ethical risk if these methods are used to develop an "assessment" of student work in the course (due to known and unknown biases in the bot's LLM backed brain)
		- Potential solutions:
			- Drop tradition concept of grading and assessment, focus on quantitative measurements (i.e. word count, etc)
			- Student will have the opportunity to stand out via "portfolio" style assignments (i.e. stuff they can show off in a website or whatever - You'll be able to tell the good ones because they will have done cool stuff)

### Future Work/Roadmap

The basic methodology developed in this first deployment will be iteratively improved prior to deployment in future iterations of this same class. The underlying AI infrasructure will be refactored to allow for more general application for other course material and related actvities (such as managing an online community centered around an open source software)



---

