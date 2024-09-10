import re,os,ast
from langchain_openai import ChatOpenAI

searchOrAnswer:str ="""\
For the given objective, search the keywords group by group and then make the final answer.  

Your objective was this:
{input}

planned search keyword groups was this:
{plan}

You have currently finish the search with "{current_plan}", the search results are here:
{past_steps}

If no more search are needed and you can summarize the data and make a final answer, finally end with {finishWord}. \
Otherwise, output the next keyword group in the last line with this format:
{shouldLoopWord} next keywords group here" \
"""

finishWord = "Misson Complete!"
shouldLoopWord = "Further Search:"

def thinkNanswer(input:str,plan:str,current_plan:str,past_steps:str) -> (str,str):
    llm = ChatOpenAI(model=os.getenv("MODEL"), api_key=os.getenv("LLM_KEY"), base_url=os.getenv("LLM_BASE"))
    prompt = searchOrAnswer.format(input=input,plan=plan,current_plan=current_plan,past_steps=past_steps,finishWord=finishWord,shouldLoopWord=shouldLoopWord)
    result = llm.invoke([{'role':'user','content':prompt}]).content
    nextPlan = None
    resultDealed =result.split(shouldLoopWord)
    answer = resultDealed[0]
    if len(resultDealed)>1 and finishWord not in result:
        nextPlan = resultDealed[1]
    return answer,nextPlan


