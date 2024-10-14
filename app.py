import json
from dotenv import load_dotenv
from datetime import datetime
from fasthtml.common import *
from fasthtml.components import Script
from graph import getAgent
import shortuuid

load_dotenv()

db = database("database/chats.db")
chats = db.t.chats
if chats not in db.t:
    chats.create(id=str, title=str, created=datetime, messages=bytes, pk="id")
chatDataTransferObject = chats.dataclass()
messages = []
chat = chatDataTransferObject()

# Headers for zero-md and other scripts
mdjs = MarkdownJS()
app, rt = fast_app(
    live=True,
    hdrs=(
        Script(src="https://unpkg.com/tailwindcss-cdn@3.4.3/tailwindcss.js"),
        mdjs,  # 使用 MarkdownJS
        picolink,
        Script(src="https://unpkg.com/htmx-ext-sse@2.2.1/sse.js"),
    ),
)

def navigation():
    return Nav(
        H1("FastGraph - A Plan-and-execute(search) demo with Langgraph and FastHTML", cls='text-white font-bold text-2xl text-center w-full'),
        cls='m-0 bg-teal-600'
    )

def ChatMessage(msg_idx, **kwargs):
    msg = messages[msg_idx]
    bubble_class = "bg-teal-300 bg-opacity-20 rounded-lg p-3 max-w-5xl" if msg['role'] == 'user' else 'bg-blue-400 bg-opacity-20 rounded-lg p-3 max-w-5xl'
    chat_class = "flex justify-end mb-4" if msg['role'] == 'user' else 'flex justify-start mb-4'
    return Div(
        Div(
            Div(msg['role'], cls="text-sm text-gray-600 mb-1"),
            Div(render_md(msg["content"]), id=f"chat-content-{msg_idx}", cls=f"{bubble_class}"),
            cls="flex flex-col"
        ),
        id=f"chat-message-{msg_idx}",
        cls=f"{chat_class}",
        hx_swap="beforeend show:bottom",
        **kwargs,
    )

def ChatInput():
    return Input(
        type="text",
        name="msg",
        id="msg-input",
        placeholder="Type a message",
        cls="input input-bordered w-full",
    )

@rt("/")
async def get():
    return RedirectResponse(url=f"/chat/{shortuuid.uuid()}")

def render_md(md):
    return Div(md, id="markdown-content", cls="marked")

@rt("/chat/{id}")
async def get(id: str):
    try:
        chat = chats[id]
        global messages
        messages = json.loads(chat.messages)
    except:
        messages = []
    page = Body(
        navigation(),
        Main(
            Div(
                H3('History', cls='font-bold my-2'),
                *[Div(A(x.title, href=f"/chat/{x.id}"), P(x.created, cls='text-xs'), cls='py-1') for x in chats()],
                id="chats",
                cls='w-1/4 h-[85vh] overflow-y-auto border-r-2 border-gray-300 border-opacity-50 px-2'
            ),
            Div(
                H3('Messages', cls='font-bold my-2'),
                Div(
                    *[ChatMessage(x) for x in range(len(messages))],
                    id="messages",
                    cls="h-[75vh] overflow-y-auto w-full",
                ),
                Form(
                    A("New", href='/', cls='mt-2'),
                    Group(
                        ChatInput(),
                        Input(
                            type="text",
                            name='id',
                            id='id-input',
                            value=id,
                            cls='hidden'
                        ),
                        Button("Send", cls="px-2 btn btn-primary", id="send-button")
                    ),
                    hx_post="/send-message",
                    hx_target="#messages",
                    hx_swap="beforeend",
                    cls="flex space-x-2 mt-2",
                ),
                cls='w-3/4 mx-2'
            ),
            cls="flex",
        )
    )
    return page

@rt("/send-message")
async def send_message(msg: str, id: str):
    messages.append({"role": "user", "content": msg})
    user_msg = ChatMessage(len(messages) - 1)
    messages.append({"role": "assistant", "content": ""})
    assistant_msg = ChatMessage(
        len(messages) - 1,
        hx_ext="sse",
        sse_connect=f"/sse-connect?msg={msg}&id={id}",
        sse_swap="message",
        hx_swap="beforeend",
        sse_error="close"
    )
    return (
        user_msg,
        assistant_msg,
        Script("document.getElementById('send-button').disabled = true;")
    )

@rt("/sse-connect")
async def sse_connect(msg: str, id: str):
    return EventStream(update_chat(msg, id))

async def update_chat(msg: str, id: str):
    agent = getAgent()
    stream = agent.astream_events({"messages": messages, "past_steps": ""}, version="v1", config={"recursion_limit": 10, "configurable": {"thread_id": id}})

    past_steps = []
    reply = ""

    async for event in stream:
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"].content
            reply += chunk
            yield sse_message(chunk)
        elif event['event'] == 'on_chain_end' and 'metadata' in event:
            try:
                past_steps = event['data']['input']['past_steps']
            except:
                pass

    chat.title = messages[0]["content"]
    chat.created = datetime.now()
    chat.id = id
    messages[-1]["content"] = reply + '\n\n' + "\n".join(f"- [{step['title']}]({step['href']})" for step in past_steps)
    chat.messages = messages
    chats.upsert(chat)

    yield sse_message(messages[-1]["content"], event="update_content")
    yield sse_message(
        Div(A(chat.title, href=f"/chat/{chat.id}"), P(chat.created, cls='text-xs'), cls='py-1', hx_swap_oob="beforeend", id="chats"),
        event="update_chats"
    )
    yield sse_message(Script("document.getElementById('send-button').disabled = false;"))
    yield 'event: close\ndata:\n\n'

serve()
