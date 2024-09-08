from dotenv import load_dotenv
from fasthtml.common import *
from starlette.websockets import WebSocketState
from graph import getAgent
from datetime import datetime
import shortuuid,asyncio

load_dotenv()
from fasthtml.components import Zero_md, Script


# persistent storage of chat sessions
db = database("data/curiosity.db")
chats = db.t.chats
if chats not in db.t:
    chats.create(id=str, title=str, updated=datetime, pk="id")
ChatDTO = chats.dataclass()



# Set up the app, including daisyui and tailwind for the chat component


app, rt = fast_app(
    live=True,  # type: ignore
    hdrs=(
        Script(src="https://unpkg.com/tailwindcss-cdn@3.4.3/tailwindcss.js"),
        picolink,
        MarkdownJS(),
    ),
    ws_hdr=True,  # web socket headers
)


def question_list():
    return Details(
        Ul(*chats(order_by="updated DESC"), dir="rtl"),
        id="question-list",
        cls="dropdown",
        hx_swap_oob="true",
    )
def navigation():
    navigation = Nav(
        Ul(Li(Hgroup(H3("FastGraph"), P("A Plan-and-search demo with Langgraph and FastHTML."))))
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
            Zero_md(css_template, Script(msg["content"], type="text/markdown")),
            id=f"chat-content-{msg_idx}",  # Target if updating the content
            cls=f"chat-bubble {bubble_class}",
        ),
        id=f"chat-message-{msg_idx}",  # Target if replacing the whole message
        cls=f"chat {chat_class}",
        **kwargs,
    )


# The input field for the user message. Also used to clear the
# input field after sending a message via an OOB swap
def ChatInput():
    return Input(
        type="text",
        name="msg",
        id="msg-input",
        placeholder="Type a message",
        cls="input input-bordered w-full",
        hx_swap_oob="true",
    )


# The main screen
@app.route("/")
def get():
    page = Body(
        navigation(),
        Div(
            *[ChatMessage(msg) for msg in messages],
            id="chatlist",
            cls="chat-box h-[73vh] overflow-y-auto",
        ),
        Form(
            Group(ChatInput(), Button("Send", cls="btn btn-primary")),
            ws_send="",
            hx_ext="ws",
            ws_connect="/ws_connect",
            cls="flex space-x-2 mt-2",
        ),
        cls="p-4 max-w-lg mx-auto",
    )  # Open a websocket connection on page load
    return page

@rt("/")
async def get():
    return RedirectResponse(url=f"/chat/{shortuuid.uuid()}")


@rt("/chat/{id}")
async def get(id: str):

    body = Body(
        cls="container",
        hx_ext="ws",
        ws_connect="/ws_connect",
    )
    return Title("Plan-and-Search"), body


async def on_connect(send):
    ws_connections[send.args[0].client] = send
    print(f"WS    connect: {send.args[0].client}, total open: {len(ws_connections)}")


async def on_disconnect(send):
    global ws_connections
    ws_connections = {
        key: value
        for key, value in ws_connections.items()
        if send.args[0].client_state == WebSocketState.CONNECTED
    }
    print(f"WS disconnect: {send.args[0].client}, total open: {len(ws_connections)}")

# WebSocket connection bookkeeping
ws_connections = {}

@app.ws("/ws_connect", conn=on_connect, disconn=on_disconnect)
async def ws(msg: str, send):
    await update_chat(msg, send)


messages = []
async def update_chat(msg: str, send):
    messages.append({"role": "user", "content": msg})

    # Send the user message to the user (updates the UI right away)
    await send(
        Div(ChatMessage(len(messages) - 1), hx_swap_oob="beforeend", id="chatlist")
    )

    # Send the clear input field command to the user
    await send(ChatInput())

    # Model response (streaming)
    agent = getAgent()
    stream = agent.astream_events({"messages": messages, "past_steps": ""},version="v1",config={"recursion_limit": 10,"configurable": {"thread_id": "1"}})

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