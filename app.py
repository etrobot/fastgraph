import json
from dotenv import load_dotenv
from datetime import datetime
from fasthtml.common import *
from fasthtml.components import Zero_md
from graph import getAgent
import shortuuid

load_dotenv()
from fasthtml.components import Script

db = database("database/chats.db")
chats = db.t.chats
if chats not in db.t:
    chats.create(id=str, title=str, created=datetime,messages=bytes, pk="id")
chatDataTransferObject = chats.dataclass()
messages = []
chat = chatDataTransferObject()

zeromd_headers = [Script(type="module", src="https://cdn.jsdelivr.net/npm/zero-md@3?register")]
app, rt = fast_app(
    live=True,  # type: ignore
    hdrs=(
        Script(src="https://unpkg.com/tailwindcss-cdn@3.4.3/tailwindcss.js"),
        zeromd_headers,
        picolink,
        MarkdownJS(),
    ),
    ws_hdr=True,  # web socket headers
)


def navigation():
    navigation = Nav(
        H1("FastGraph - A Plan-and-excute(search) demo with Langgraph and FastHTML",cls='text-white font-bold text-2xl text-center w-full'),
        cls='m-0 bg-teal-600'
    )
    return navigation


def ChatMessage(msg_idx, **kwargs):
    msg = messages[msg_idx]
    userbubblestyle='ml-auto bg-blue-500 bg-opacity-10 rounded-sm p-2'
    assistantbubblestyle='mr-auto bg-slate-500 bg-opacity-10 rounded-sm p-2'
    bubble_class = f"{userbubblestyle if msg['role'] == 'user' else assistantbubblestyle}"
    chat_class = f"{'end' if msg['role'] == 'user' else 'start'}"
    return Div(
    Div(
        render_md(msg["content"]),
            id=f"chat-content-{msg_idx}",  # Target if updating the content
            cls=f"chat-bubble {bubble_class}",
        ),
        id=f"chat-message-{msg_idx}",  # Target if replacing the whole message
        cls=f"chat {chat_class} my-2",
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

def render_md(md, css='.markdown-body {background-color: unset !important; color: unset !important;}'):
    css_template = Template(Style(css), data_append=True)
    return Zero_md(css_template, Script(md, type="text/markdown"))

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
            H3('History',cls='font-bold my-2'),
            *[Div(A(x.title,href=f"/chat/{x.id}"),P(x.created,cls='text-xs'),cls='py-1') for x in chats()],
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
                    A("New",href='/',cls='mt-2'),
                    Group(
                        ChatInput(),
                        Input(
                              type="text",
                              name='id',
                              id='id-input',
                              value=id,
                              cls='hidden'
                          ),
                          Button("Send", cls="px-2 btn btn-primary")),
                    ws_send="",
                    hx_ext="ws",
                    ws_connect="/ws_connect",
                    cls="flex space-x-2 mt-2",
                ),
                cls='w-3/4  mx-2'
        ),
        cls="flex",
    )
    )
    return  page

@app.ws("/ws_connect")
async def ws(msg: str,id:str,send):
    await update_chat(msg,id,send)

async def update_chat(msg: str,id:str,send):
    messages.append({"role": "user", "content": msg})
    await send(
        Div(ChatMessage(len(messages) - 1), hx_swap_oob="beforeend", id="messages")
    )

    # Send the clear input field command to the user
    await send(msg)

    # Model response (streaming)
    agent = getAgent()
    stream = agent.astream_events({"messages": messages, "past_steps": ""},version="v1",config={"recursion_limit": 10,"configurable": {"thread_id": id}})

    past_steps = []
    reply=""
    # Send an empty message with the assistant response
    messages.append({"role": "assistant", "content": ""})

    await send(
        Div(ChatMessage(len(messages) - 1), hx_swap_oob="beforeend", id="messages")
    )

    # Fill in the message content
    async for event in stream:
        if  event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"].content
            reply+=chunk
            await send(
                Span(chunk, id=f"chat-content-{len(messages)-1}", hx_swap_oob="beforeend")
            )
        elif event['event'] == 'on_chain_end' and 'metadata' in event:
            try:
                past_steps = event['data']['input']['past_steps']
            except:
                pass

    chat.title = messages[0]["content"]
    chat.created = datetime.now()
    chat.id = id
    messages[-1]["content"] = reply+'\n\n'+"\n".join(f"- [{step['title']}]({step['href']})" for step in past_steps)
    chat.messages = messages
    chats.upsert(chat)
    await send(
        Span(messages[-1]["content"], id=f"chat-content-{len(messages)-1}", hx_swap_oob="true")
    )
    await send(
        Div(A(chat.title, href=f"/chat/{chat.id}"), P(chat.created, cls='text-xs'), cls='py-1',hx_swap_oob="beforeend", id="chats")
    )
serve()