# ScrittaBot

ScrittaBot is a test platform for using large language models
(LLMs) as agents executing multi-step actions. It supports
any LLM behind OpenAI-compatible API and provides a basic
set of tools. Currently there are tools for chatting with
user via *Matrix* protocol (using the *nio* library).

## How is this different from other bots?

ScrittaBot is inspired by *Letta* and by *Huggingface*'s
*smolagents*. It does **not** use OpenAI API for tool definitions,
but instead instructs the LLM to generate Python code which
is then executed using the `smolagents.local_python_executor`
library (for some degree of safety). Its design principle is
to handle events and tasks, a bit similarly to operating systems, where
the kernel handles interrupts/events and schedules processes/tasks.
We are still far from that goal, but it is a guiding principle.

Other guiding principle is that memory is crucial -- even the larger
models have a limited context memory and local models even more so.
And even if all data would fit into context, it will slow down
inference and possibly confuse the LLM. So, we want to try to insert
only essential information into context on each step and maintain
a (possibly huge) RAG which contains vast amount of data, potentially
never forgetting anything. RAG should work mostly autonomously,
just like human memory -- you remember things usually without needing
to consciously recall memories. LLM should have the ability to also
search the RAG, though.

Development is made using *Gemma3* as LLM running locally, so the bot
works also with smaller models. Performance is certainly better with
larger models, but this is not so well tested. For RAG we use
*bge-m3* embedding and *bge-reranker-v2-m3* reranker, the latter still
only in the plans. These are multilingual models, and having support
for multiple languages is a design goal, although this pretty much
depends on the models used which can be freely chosen.
The REST APIs have been tested with *llama.cpp* and *LiteLLM* working as
proxy.

Some design has been made to make it easy for implementing and
providing more Python functions for the LLM to use. This is done
now by editing directly the source code.

We also want to avoid dependencies as much as reasonable. Many things,
eg. calling OpenAI REST APIs, don't take more lines of code if done by calling
directly lower level APIs instead of using higher abstractions, but it
makes it easier to understand what the code is actually doing, easier
to debug when something fails, and it also makes it possible to try new
ideas and experiments without modifying large, complicated libraries.
Maintenance and setup is also easier with less dependencies.

For accessing LLM APIs, we're using directly Python standard *requests*
module. The code should be light, simple, and straightforward to help
understanding it and modifying the underlaying algoritms easily. The code
should be good for trying out easily new algorithms and ideas.

## Prerequisites

- OpenAI-compatible LLM endpoint, whether having bought
  access to *OpenAI*, *Gemini*, or whatever, or having set up local LLM
  with eg. *llama.cpp*.
- Embedding endpoint. With *llama.cpp*, you can use bge-m3 model
  and run *llama.cpp* with option --embedding.
- (In future) Reranking endpoint. With *llama.cpp*, you can use
  bge-reranker-v2-m3 and option --reranking.
- The above endpoints must (for now) exist behind the same URL and port.
  To combine all three endpoints into one, I'm using LiteLLM. This will
  be fixed soon so that a different URL and port can be defined for each.
- *Matrix* account and having created a room for
  your bot on the server. I recommend installing both server
  (eg. *matrix-synapse*) and a client (eg. *Cinny*) locally and
  then you can play freely with them.
- PostgreSQL installed.

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
After `credentials.json` has been created, convert it to yaml with
`./yjconverter.py credentials.json >config.yaml` and set up
the following fields:

```
access_token: syt_emxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxPEA # For Matrix
room_id: '#zonet:zeonzone.zonet' # For Matrix
user_id: '@zoebot:zeonzone.zonet' # For Matrix
device_id: RXXXXXXXXO # For Matrix
context_embedding: 512
context_llm: 8000
homeserver: https://zeonzone.zonet # For Matrix
model_embedding: bge-m3
model_rerank: bge-reranker-v2-m3
model_llm: zeonzone
#model_llm: gemini-2.5-flash-preview-04-17
openai_key: sk-pxxxxxxxxxxxxxxxxxxxxw # For LLM, embedding, and rerank
openai_url: https://zeonzone.zonet:4001 # For LLM, embedding, and rerank
database_url: 'postgresql://scrittabot:a_secure_password@zeonzone.zonet:5432/scrittabot'

```

Customize as needed. If you want to run LLM locally, I recommend
`llama-server` (from *llama.cpp*). It's what has been tested and it
supports also images (at least with *Gemma3*). (I am using it
over *LiteLLM* proxy, but it shouldn't matter.)

You also need to have *PostgreSQL* installed and *PostgreSQL* user and
database with *pgvector* extension:

```
su postgres -c psql
CREATE USER scrittabot WITH LOGIN PASSWORD 'a_secure_password';
CREATE DATABASE scrittabot OWNER scrittabot;
GRANT CONNECT ON DATABASE scrittabot TO scrittabot;
\c scrittabot
CREATE EXTENSION vector;
```

Scrittabot will create the actual tables into the database on bootup
if they don't already exist (use `python3 database.py --reset` to
reset and clear all stored information). PostgreSQL is used for storing
meta-information on files, not the actual files that are sent to the agent.
The files are saved into `files` directory.

Here's example of LiteLLM configuration:

```
general_settings:
  master_key: sk-AxxxxxxxxxxxxxeN   # LiteLLM admin key
  database_url: "postgresql://litellm:pxxxxxxu@localhost:5432/litellm"
  store_model_in_db: true
  store_prompts_in_spend_logs: true  # Useful for debugging LLM communication

model_list:
# Local Models
  - model_name: zeonzone
    litellm_params:
      model: openai/zeonzone
      api_base: http://zeonzone.zonet:8080/v1
      api_key: "NONE"
  - model_name: bge-m3
    litellm_params:
      model: openai/bge-m3
      api_base: http://zeonzone.zonet:8081/v1
      api_key: "NONE"
  - model_name: bge-reranker-v2-m3
    litellm_params:
      model: jina_ai/bge-reranker-v2-m3
      api_base: http://zeonzone.zonet:8082
      api_key: "NONE"

# Google API models
  - model_name: gemini-1.5-flash-latest
    litellm_params: &google
      model: gemini/gemini-1.5-flash-latest
      api_key: "AIxxxxxxxxxxxxxxxxxxxxxxxxxxT_6xxxxxxPg"  # Google AI Studio key
  - model_name: gemini-1.5-flash-001
    litellm_params:
      <<: *google
      model: gemini/gemini-1.5-flash-001
  - model_name: gemini-1.5-flash-001-tuning
    litellm_params:
      <<: *google
      model: gemini/gemini-1.5-flash-001-tuning
  - model_name: gemini-1.5-flash
    litellm_params:
      <<: *google
      model: gemini/gemini-1.5-flash
```

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
  being able to access those (partially done).

* Ability for the LLM to browse received files and to make RAG queries.

* Ability for the LLM to send user files from its storage.

* Some kind of monitoring UI (now it just spits debug information
  to console). (Idea: let the Agent modify its own access page?)

* Improving intelligence, decreasing load. Now the models seems to
  do a lot of hazy and useless stuff.

* More tools to work file system or browsing the web. Security?
