# ScrittaBot

ScrittaBot is a test platform for using large language models
(LLMs) as agents executing multi-step actions. It supports
any LLM behind OpenAI-compatible API and provides a basic
set of tools. Currently there are tools for chatting with
user via Matrix protocol (using the nio library).

## How is this different from other bots?

ScrittaBot is inspired by *Letta* and even more by *Huggingface*'s
*smolagents*. It does **not** use OpenAI API for tool definitions,
but instead instructs the LLM to generate Python code which
is then executed using the `smolagents.local_python_executor`
library (for some degree of safety).

Development is made using *Gemma3* running locally, so the bot works
also with smaller models. Performance is certainly better with
larger models, but this is not so well tested.

Some design has been made to make it easy for implementing and
providing more Python functions for the LLM to use. This is done
now by editing directly the source code.

## Prerequisites

You need to have access to OpenAI-compatible LLM endpoint,
whether having bought access to *OpenAI*, *Gemini*, or whatever,
or having set up local LLM with eg. *llama.cpp*. You also
need to have a *Matrix* account and having created a room for
your bot on the server. I recommend installing both server
(eg. *matrix-synapse*) and a client (eg. *Cinny*) locally and
then you can play freely with them.

## Installing

At this early version, users should be experienced Python/AI
developers. Instructions here are sparse and you **need**
Python skills to do anything meaningful with the code.

First, install the required Python packages with
```
make install
```

Then you need to set up Matrix account for the bot and creating
`credentials.json` file using `matrix-commander --login PASSWORD`.
Use `matrix-commander` to test that you can send and receive messages.
After `credentials.json` has been created, copy it to `config.json`
and add following fields:

```
{
  "homeserver": "https://zeonzone.zonet",
  "device_id": "RXXXXXXXXO",
  "user_id": "@scrittabot:zeonzone.zonet",
  "room_id": "#zonet:zeonzone.zonet",
  "access_token": "syt_eXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXA",
  "openai_url": "https://zeonzone.zonet:4001",
  "openai_key": "sk-pZXXXXXXXXXXXXXXXXXXXw",
  "model_llm": "your_preferred_model",
  "context_llm": 8000,
  "model_embedding": "multilingual-e5-large-instruct"
  "context_embedding": 512
}

```

Customize as needed. If you want to run LLM locally, I recommend
`llama-server` (from *llama.cpp*). It's what has been tested and it
supports also images (at least with *Gemma3*). (I am using it
over *LiteLLM* proxy, but it shouldn't matter.)

## Running

After everything above has been done, run with `make run`.
Typically the bot starts taking notes, setting goals, and
trying to reach humans by messaging. Since lots of actual
functionality in the tools is still missing, the bot gets
quite frustrated, at least until you start chatting with it.
Log messages about what is happening (in particular LLM
output) are displayed on the console.

## Future plans

* Indexing received documents into PostgreSQL RAG database and
  being able to access those.

* Ability for the LLM to browse received files and to make RAG queries.

* Ability for the LLM to send user files from its storage.

* Some kind of monitoring UI (now it just spits debug information
  to console).

* Improving intelligence, decreasing load. Now the models seems to
  do a lot of hazy and useless stuff.
