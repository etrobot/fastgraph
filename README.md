# FastGraph
A Plan-and-excute(search) demo with Langgraph and FastHTML.

- <strong>No function-call feature required.</strong>
- Use any LLM api that follows the OpenAI format.

```mermaid
graph TD;
	__start__([__start__]):::first
	planNode(planNode)
	serpTool(serpTool)
	decisionNode(decisionNode)
	__end__([__end__]):::last
	__start__ --> planNode;
	planNode --> serpTool;
	serpTool --> decisionNode;
	decisionNode -.-> planNode;
	decisionNode -.-> serpTool;
	decisionNode -.-> __end__;	
```
https://github.com/user-attachments/assets/f2362729-60c4-45a1-94f1-af700d4d3b43

## Usage

1. Copy .env_example to .env and fill out the necessary information.
2. Run ```poetry install```
3. Run ```poetry run python app.py```

## Inspiration

[curiosity](https://github.com/jank/curiosity)
