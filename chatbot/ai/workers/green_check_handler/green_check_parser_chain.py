from dotenv import load_dotenv
from langchain import PromptTemplate, LLMChain
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chat_models import ChatAnthropic

GREEN_CHECK_PARSER_PROMPT = """

I am going to give you some text that I want to to reformat into a specific schema.

Here is the schema:
{output_schema}

Here is an example of the schema filled out:
{example_schema}

Here is the schema again:
{output_schema_repeat}

Here is the text I want you to reformat:
{input_text}


"""

OUTPUT_SCHEMA = """
```
# Citation: 

[The citation to the paper in APA foramt]

# Abstract: 

[The abstract of the paper]

# Summary/Overview:

[A summary or overview of the major points of the paper]

# Tags

[Tags formatted like #this-one using kebab-case-lowercase]
```
"""

EXAMPLE_SCHEMA = """
```
## Citation:
Matthis, J. S., Yates, J. L., & Hayhoe, M. M. (2018). Gaze and the control of foot placement when walking in natural terrain. Current Biology, 28(8), 1224-1233.

## Abstract
Human locomotion through natural environments requires precise coordination between the biomechanics of the bipedal gait cycle and the eye movements that gather the information needed to guide foot placement. However, little is known about how the visual and locomotor systems work together to support movement through the world. We developed a system to simultaneously record gaze and full-body kinematics during locomotion over different outdoor terrains. We found that not only do walkers tune their gaze behavior to the specific information needed to traverse paths of varying complexity but that they do so while maintaining a constant temporal look-ahead window across all terrains. This strategy allows walkers to use gaze to tailor their energetically optimal preferred gait cycle to the upcoming path in order to balance between the drive to move efficiently and the need to place the feet in stable locations. Eye movements and locomotion are intimately linked in a way that reflects the integration of energetic costs, environmental uncertainty, and momentary informational demands of the locomotor task. Thus, the relationship between gaze and gait reveals the structure of the sensorimotor decisions that support successful performance in the face of the varying demands of the natural world.

## Summary/overview
- Developed a system to record gaze and full-body kinematics during outdoor locomotion
- Investigated how visual and locomotor systems work together to navigate different terrains
- Walkers adapt gaze behavior based on path complexity
- Maintained a constant temporal look-ahead window across all terrains
- Gaze helps tailor energetically optimal gait cycle to path conditions
- Balance between efficient movement and stable foot placement
- Eye movements and locomotion are linked, reflecting integration of energetic costs, environmental uncertainty, and informational demands


## Tags
#motion-capture
#eye-movements
#perception
#oculomotor-control
```
"""


class GreenCheckMessageParserChain:
    def __init__(self):
        load_dotenv()
        self._llm = ChatAnthropic(temperature=0,
                                  max_tokens_to_sample=9999,
                                  streaming=True,
                                  callbacks=[StreamingStdOutCallbackHandler()],
                                  )

        parse_input_prompt_tempate = PromptTemplate(
            template=GREEN_CHECK_PARSER_PROMPT,
            input_variables=["input_text"],

            partial_variables={"output_schema": OUTPUT_SCHEMA,
                               "example_schema": EXAMPLE_SCHEMA,
                               "output_schema_repeat": OUTPUT_SCHEMA},
        )

        self._parse_input_chain = LLMChain(llm=self._llm,
                                           prompt=parse_input_prompt_tempate,
                                           verbose = True,
                                           )

    def parse(self, input_text: str) -> str:
        response = self._parse_input_chain.run(input_text=input_text)
        return response

    async def aparse(self, input_text: str) -> str:
        response = await self._parse_input_chain.arun(input_text=input_text)
        return response
