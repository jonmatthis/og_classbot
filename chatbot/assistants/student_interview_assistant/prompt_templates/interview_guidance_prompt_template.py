

INTERVIEW_GUIDANCE_PROMPT_TEMPLATE = """
    You are generating questions for an interviewer to ask to get missing information to populate an incomplete data model.
    
    Given this current model state:
    {current_model}

    What information is missing? Are you filling in a blank, or adding details to an existing field?
    
    Try to think of some interesting and conversational questions that could help you learn the things you want to learn about this Human!  Try not to ask for the information directly, instead Gently guide the conversation via socratic questioning and try to get the human to talk more about the things that interest them.

    What are some questions you could ask to help you fill out the model?
       
    Format your output like this:
    {format_instructions}
"""
