import re,os,ast
from langchain_openai import ChatOpenAI

#prompt
plannerPrompt:str = """
For the given object, make a group of keywords for the search engine. \
for example, the object is "write a wiki for google.com",and the keywors group should be in list format: \
["google.com funciton","google.com history","google.com tech stack","google.com bussiness mode"]

Here's the object: 

{object}

Finish it well and I will tip you $100.

"""

#output parser
def planParsed2list(output:str)->list:
    keywords_match = re.search(r'\[(.*?)\]', output.replace('\n',''))
    if keywords_match:
        keywords_str = keywords_match.group(0)  # 获取完整的方括号内容
        keywords_list = ast.literal_eval(keywords_str)
        return keywords_list
    return []

#llm
def plan(input:str) -> list:
    llm = ChatOpenAI(model=os.getenv("MODEL"), api_key=os.getenv("LLM_KEY"), base_url=os.getenv("LLM_BASE"))
    prompt = plannerPrompt.format(object=input)
    result = llm.invoke(prompt).content
    return planParsed2list(result)
