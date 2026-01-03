# Clarity Dev Harness – T1 & T2 Build


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

### Features

#### AI-Powered Memory
- Uses OpenAI's model to summarize conversations and extract key information
- Maintains context and learns from user interactions over time
- Automatically categorizes information into structured format
- Processes conversations using the same model as the chat client (default: gpt-4-1106-preview)

#### Memory Structure
- **User Profile**: Explicitly set user information (set via `/memory set user_profile`)
- **Preferences**: Automatically extracted from conversations (e.g., "I like...", "I prefer...")
- **Work in Progress**: Tracks ongoing tasks and projects (e.g., "I'm working on...")
- **Open Loops**: Remembers pending items needing follow-up
- **Conversation History**: Full conversations are chunked and stored in `memory/chunks/`

#### Memory Updates
Memory is automatically updated in these scenarios:
- On clean exit (`/exit` or `/quit`)
- When explicitly requested via memory commands
- Uses the same API key as the chat client for consistent authentication

#### Commands
- `/memory` - View current memory state
- `/memory set user_profile "Your profile"` - Set your user profile
- `/memory add preference "Your preference"` - Add a preference
- `/memory add work "Work item"` - Add a work in progress item
- `/memory add loop "Open loop"` - Add an open loop item

#### Configuration
Memory settings are configured in `config/config.json`:

```json
{
  "memory": {
    "enable_long_term_memory": true,
    "model": "gpt-4-1106-preview",
    "enable_last_session_context": true,
    "max_last_session_turns": 5
  }
}
```

- `enable_long_term_memory`: Enable/disable the memory system
- `model`: The OpenAI model to use for memory summarization
- `enable_last_session_context`: Load context from previous session on startup
- `max_last_session_turns`: Number of previous conversation turns to load

**Note:** The memory system uses the same API key as the chat client, configured in your `.env` file.

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

