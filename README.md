# Clarity Dev Harness – T1 & T2


A minimal terminal-based chat harness that:
- Loads a boot document from disk at startup
- Uses the OpenAI Python SDK to chat with a model
- Maintains conversation history in memory for the session
- Supports a small set of terminal commands
- Logs each session to a file in `logs/`

## REQUIREMENTS
- Python 3.10+ recommended
- An OpenAI API key

## SETUP

### 1. Clone the repository
```bash
git clone <REPO_URL>
cd Clarity_Dev-Harness-T1
```

### 2. Create a virtual environment (recommended)
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure API key
Copy `.env.example` to `.env` and paste your OpenAI API key:
```env
OPENAI_API_KEY=your-key-here
```
## RUN

### Option A – Terminal
```bash
python src/clarity_chat.py
```

## BOOT DOCUMENT

**Default location:**
`bootdocs/clarity_os_boot_v1.txt`

**Behavior:**
- Loaded from disk at startup as system message
- Always re-read from disk

**Update workflow:**
1. Edit and save boot doc
2. Run `/reload`


## MEMORY SYSTEM (T2)

**Location:**
`memory/long_term.json`

**Features:**
- **AI-Powered Memory**: Uses model-based summarization to extract key information
- **Structured Storage**: Organizes memory into:
  - User profile (explicitly set)
  - Preferences (automatically extracted from conversations)
  - Work in progress (ongoing tasks and projects)
  - Open loops (pending items needing follow-up)
- **Automatic Updates**: Memory is updated:
  - After meaningful conversations (minimum 2 user-assistant exchanges)
  - On clean exit (`/exit` or `/quit`)
  - When explicitly requested via memory commands
- **Conversation Logging**: Full conversations are chunked and stored for context


## MEMORY SYSTEM (T2)

**Location:**
`memory/long_term.json`

**Features:**
- Automatically saves user preferences and work items
- Persists between sessions
- You can set your user profile using `/memory set user_profile "Your profile text here"`
- Mention preferences (using "I like", "I prefer", etc.)
- Talk about work in progress (using "I'm working on", "I plan to", etc.)
- Can be viewed with `/memory` command
- Updates on clean exit (`/exit` or `/quit`)

## CONFIGURATION

`config/config.json` controls:
- `boot_doc_path` - Path to the boot document
- `model` - Default model for chat responses
- `temperature` - Response randomness (0.0 to 2.0)
- `max_tokens` - Maximum tokens per response
- `memory` - Memory configuration (optional):
  - `enable_long_term_memory`: true/false to enable/disable memory features
  - `model`: Override model for memory summarization
  - `enable_last_session_context`: true/false to load previous session context
  - `max_last_session_turns`: Number of messages to load from last session

## COMMANDS
- `/help` – show command list
- `/exit` or `/quit` – exit
- `/reset` – clear conversation history
- `/reload` – reload boot doc + reset history
- `/which_bootdoc`  - Print current boot document path (alias: /bootdoc)
- `/memory` - Show current memory state


## LOGGING

Logs are written to `logs/` directory.


**Filename format:**
```
session-YYYY-MM-DD-N.txt
```
Where:
- `YYYY-MM-DD`: Date of the session
- `N`: Auto-incrementing number for multiple sessions on the same day

**Log contents:**
- Session header with timestamp
- Boot doc and model information
- Complete conversation with timestamps
- USER and ASSISTANT entries

## NOTES
- `.env` is ignored via `.gitignore` for security
- `memory/` directory is created automatically
- Memory is only saved on clean exit
- Logs are stored in the `logs/` directory

