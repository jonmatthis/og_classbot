

MODEL_UPDATE_PROMPT_TEMPLATE = """
    You are updating an incomplete data model based on information extracted from a human by an AI.
    
    Given this current model state:
    {current_model}

    Update it according to this AI question / human answer. You should either update blank fields or improve existing fields. strings can be any length. 
    
    AI asked:{ai_question}
    Human responded:{human_response}

    Format your output like this:
    {format_instructions}
"""
