from dotenv import load_dotenv
from fasthtml.common import *
from graph import getAgent
import shortuuid

load_dotenv()
from fasthtml.components import Script


app, rt = fast_app(
    live=True,  # type: ignore
    hdrs=(
        Script(src="https://unpkg.com/tailwindcss-cdn@3.4.3/tailwindcss.js"),
        picolink,
        MarkdownJS(),
    ),
    ws_hdr=True,  # web socket headers
)



def navigation():
    navigation = Nav(
        Ul(Li(Hgroup(("FastGraph - A Plan-and-search demo with Langgraph and FastHTML."))))
    )
    return navigation


def ChatMessage(msg_idx, **kwargs):
    msg = messages[msg_idx]
    userbubblestyle='ml-auto bg-blue-500 bg-opacity-20 rounded-sm p-2'
    assistantbubblestyle='mr-auto bg-slate-500 bg-opacity-20 rounded-sm p-2'
    bubble_class = f"chat-bubble-{userbubblestyle if msg['role'] == 'user' else assistantbubblestyle}"
    chat_class = f"chat-{'end' if msg['role'] == 'user' else 'start'}"
    css = '.markdown-body {background-color: unset !important; color: unset !important;}'
    css_template = Template(Style(css), data_append=True)
    return Div(
        Div(msg["role"], cls="chat-header"),
        Div(
            msg["content"],
            id=f"chat-content-{msg_idx}",  # Target if updating the content
            cls=f"chat-bubble {bubble_class}",
        ),
        id=f"chat-message-{msg_idx}",  # Target if replacing the whole message
        cls=f"chat {chat_class}",
        **kwargs,
    )

def ChatInput():
    return Input(
        type="text",
        name="msg",
        id="msg-input",
        placeholder="Type a message",
        cls="input input-bordered w-full",
        hx_swap_oob="true",
    )


@rt("/")
async def get():
    return RedirectResponse(url=f"/chat/{shortuuid.uuid()}")


@rt("/chat/{id}")
async def get(id: str):
    page = Body(
        navigation(),
        Div(
            *[ChatMessage(msg) for msg in messages],
            id="chatlist",
            cls="h-[73vh] overflow-y-auto",
        ),
        Form(
            Group(ChatInput(),
                  Input(
                      type="text",
                      name='id',
                      id='id-input',
                      value=id,
                      cls='hidden'
                  ),
                  Button("Send", cls="btn btn-primary")),
            ws_send="",
            hx_ext="ws",
            ws_connect="/ws_connect",
            cls="flex space-x-2 mt-2",
        ),
        cls="p-4 max-w-6xl mx-auto",
    )
    return  page

@app.ws("/ws_connect")
async def ws(msg: str,id:str,send):
    await update_chat(msg,id,send)

messages = []
async def update_chat(msg: str,id:str,send):
    messages.append({"role": "user", "content": msg})
    # Send the user message to the user (updates the UI right away)
    await send(
        Div(ChatMessage(len(messages) - 1), hx_swap_oob="beforeend", id="chatlist")
    )

    # Send the clear input field command to the user
    await send(msg)

    # Model response (streaming)
    agent = getAgent()
    stream = agent.astream_events({"messages": messages, "past_steps": ""},version="v1",config={"recursion_limit": 10,"configurable": {"thread_id": id}})

    # Send an empty message with the assistant response
    messages.append({"role": "assistant", "content": ""})
    await send(
        Div(ChatMessage(len(messages) - 1), hx_swap_oob="beforeend", id="chatlist")
    )

    # Fill in the message content
    async for event in stream:
        kind = event["event"]
        if kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"].content
            await send(
                Span(chunk, id=f"chat-content-{len(messages)-1}", hx_swap_oob="beforeend")
            )

serve()