import os
import sys
import json
import time
import signal
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from openai import OpenAI
from colorama import Fore, Style, init as colorama_init

from settings import PROJECT_ROOT, LOGS_DIR, load_config, get_api_key
from memory_store import MemoryStore

colorama_init(autoreset=True)

class ClarityChat:
    def __init__(self):
        """Initialize the Clarity Chat application."""
        self.config = load_config()
        self.client = OpenAI(api_key=get_api_key())
        self.conversation_history: List[Dict[str, str]] = []
        self.log_file: Optional[Path] = None
        
        # Only initialize memory store if memory config exists and is enabled
        self.memory_store = None
        if 'memory' in self.config and self.config['memory'].get('enable_long_term_memory', False):
            self.memory_store = MemoryStore()
            
        signal.signal(signal.SIGINT, self._handle_exit)
        self.setup_logging()
        self.load_boot_doc()
        
        # Only load memory context if memory is enabled
        if self.memory_store is not None:
            self._load_memory_and_context()

    def load_boot_doc(self) -> None:
        """Load the boot document from the configured path."""
        boot_doc_path = Path(self.config['boot_doc_path'])
        if not boot_doc_path.exists():
            print(f"{Fore.RED}Error: Boot document not found at {boot_doc_path}")
            sys.exit(1)
            
        with open(boot_doc_path, 'r', encoding='utf-8') as f:
            self.boot_doc = f.read()
            
        print(f"{Fore.GREEN}✓ Loaded boot doc from {boot_doc_path}")
        print(f"{Fore.CYAN}Model: {self.config['model']} (temp: {self.config['temperature']})")
        print(f"{Style.DIM}Type your message or /help for commands{Style.RESET_ALL}\n")

    def setup_logging(self) -> None:
        """Set up logging for the current session."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        session_num = 1
        while True:
            self.log_file = LOGS_DIR / f"session-{date_str}-{session_num}.txt"
            if not self.log_file.exists():
                break
            session_num += 1
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"=== Session started at {datetime.now().isoformat()} ===\n")
            f.write(f"Boot doc: {self.config['boot_doc_path']}\n")
            f.write(f"Model: {self.config['model']} (temp: {self.config['temperature']})\n")
            f.write("-" * 50 + "\n\n")

    def log_message(self, role: str, content: str) -> None:
        """Log a message to the session log file."""
        if not self.log_file:
            return
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {role.upper()}:\n{content}\n\n")

    def _get_memory_context(self) -> List[Dict[str, str]]:
        """Get memory context to include in the conversation."""
        memory_messages = []
        if self.memory_store and self.config.get('memory', {}).get('enable_long_term_memory', False):
            memory = self.memory_store.load_long_term_memory()
            if memory:
                memory_messages.append({
                    "role": "system",
                    "content": f"""LONG-TERM MEMORY (Last updated: {memory.get('last_updated', 'unknown')}):
                    User Profile: {memory.get('user_profile', 'Not specified')}
                    
                    Preferences:
                    - {chr(10).join(f'• {p}' for p in memory.get('preferences', []) or ['None'])}
                    
                    Work in Progress:
                    - {chr(10).join(f'• {w}' for w in memory.get('work_in_progress', []) or ['None'])}
                    
                    Open Loops:
                    - {chr(10).join(f'• {o}' for o in memory.get('open_loops', []) or ['None'])}"""
                })
        return memory_messages

    def _load_memory_and_context(self) -> None:
        """Load memory and context from previous sessions if enabled."""
        if not self.memory_store or not self.config.get('memory', {}).get('enable_long_term_memory', False):
            return
            
        memory_config = self.config['memory']
        if memory_config.get('enable_last_session_context', False):
            max_turns = memory_config.get('max_last_session_turns', 20)
            last_session_messages = self.memory_store.load_last_session_context(
                str(LOGS_DIR), 
                max_turns
            )
            if last_session_messages:
                self.conversation_history.extend(last_session_messages)
                print(f"{Fore.CYAN}✓ Loaded context from last session ({len(last_session_messages)} messages)\n")

    def get_chat_response(self, user_input: str) -> str:
        """Get a response from the OpenAI API with memory context."""
        try:
            self.conversation_history.append({"role": "user", "content": user_input})
            
            messages = [{"role": "system", "content": self.boot_doc}]
            if self.config.get('memory', {}).get('enable_long_term_memory', False):
                messages.extend(self._get_memory_context())
            
            messages.extend(self.conversation_history)
            
            response = self.client.chat.completions.create(
                model=self.config['model'],
                messages=messages,
                temperature=self.config['temperature'],
                max_tokens=self.config['max_tokens']
            )
            
            assistant_reply = response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": assistant_reply})
            
            return assistant_reply
            
        except Exception as e:
            return f"Error getting response: {str(e)}"

    def reset_conversation(self) -> None:
        """Reset the conversation history."""
        self.conversation_history = []
        print(f"{Fore.YELLOW}Conversation history cleared. Starting a new conversation.\n")

    def reload_boot_doc(self) -> None:
        """Reload the boot document from disk."""
        self.load_boot_doc()
        self.reset_conversation()
        print(f"{Fore.GREEN}✓ Boot document reloaded\n")

    def show_help(self) -> None:
        """Show available commands."""
        print("\nAvailable commands:")
        print("  /help           - Show this help message")
        print("  /exit           - Exit the program (saves memory)")
        print("  /quit           - Alias for /exit")
        print("  /reset          - Clear conversation history")
        print("  /reload         - Reload the boot document")
        print("  /which_bootdoc  - Print current boot document path (alias: /bootdoc)")
        
        # Only show memory command if memory is enabled
        if hasattr(self, 'memory_store') and self.memory_store is not None and \
           self.config.get('memory', {}).get('enable_long_term_memory', False):
            print("  /memory         - Show current memory state")
            
        print()
        # Show memory status line only if memory is enabled
        memory_enabled = self.memory_store is not None and self.config.get('memory', {}).get('enable_long_term_memory', False)
        if memory_enabled:
            memory = self.memory_store.load_long_term_memory()
            if memory:
                print(f"{Fore.GREEN}✓ Long-term memory is enabled (last updated: {memory.get('last_updated', 'never')})\n{Style.RESET_ALL}")
                last_updated = memory.get('last_updated', 'never')
                print(f"{Fore.GREEN}✓ Long-term memory is enabled (last updated: {last_updated})\n{Style.RESET_ALL}")

    def show_memory(self) -> None:
        """Show the current memory state in a clean format."""
        if not hasattr(self, 'memory_store') or self.memory_store is None:
            print("Long-term memory is disabled in settings")
            return

        memory = self.memory_store.load_long_term_memory()
        if not memory:
            print("No long-term memory found. Share some information about yourself or your work to build memory.")
            return

        print("\n=== Long-term Memory ===")
        print(f"Last updated: {memory.get('last_updated', 'unknown')}")

        if memory.get('user_profile'):
            print(f"\nAbout You: {memory['user_profile']}")

        if memory.get('preferences'):
            print("\nYour Preferences:" + "-" * 50)
            for i, pref in enumerate(memory['preferences'], 1):
                print(f"{i}. {pref}")

        if memory.get('work_in_progress'):
            print("\nYour Projects:" + "-" * 50)
            for i, work in enumerate(memory['work_in_progress'], 1):
                print(f"{i}. {work}")

        if memory.get('open_loops'):
            print("\nOpen Items:" + "-" * 50)
            for i, loop in enumerate(memory['open_loops'], 1):
                print(f"{i}. {loop}")

        print("\n" + "=" * 70)

    def _summarize_session(self) -> bool:
        """Summarize the current session and update long-term memory using the model."""
        try:
            if not hasattr(self, 'memory_store') or self.memory_store is None or not self.conversation_history or not self.config.get('memory', {}).get('enable_long_term_memory', False):
                return False

            print("\nSaving conversation to memory...")
            result = self.memory_store.update_long_term_memory(self.conversation_history)
            if result:
                print("✓ Memory updated successfully")
            else:
                print("! Failed to update memory")
            return result

        except Exception as e:
            print(f"Error updating memory: {str(e)}")
            return False

    def _handle_exit(self, signum=None, frame=None) -> None:
        """Handle clean exit with session summarization."""
        print("\n" + Fore.YELLOW + "Saving session..." + Style.RESET_ALL)
        
        try:
            if hasattr(self, 'memory_store') and hasattr(self, 'conversation_history'):
                success = self._summarize_session()
                if success:
                    print(Fore.GREEN + "✓ Session saved successfully" + Style.RESET_ALL)
                else:
                    print(Fore.YELLOW + "! Session save completed with warnings" + Style.RESET_ALL)
        except Exception as e:
            print(Fore.RED + f"Error during exit: {str(e)}" + Style.RESET_ALL)
        finally:
            print("\nGoodbye!")
            sys.exit(0)

    def run(self) -> None:
        """Run the chat loop with memory support."""
        self.show_help()
        
        try:
            while True:
                try:
                    try:
                        user_input = input(f"{Fore.BLUE}Clarity OS > {Style.RESET_ALL}").strip()
                    except (EOFError, KeyboardInterrupt):
                        self._handle_exit(None, None)
                        break
                    
                    if not user_input:
                        continue
                    
                    self.log_message("user", user_input)
                    
                    if user_input.lower() in ('/exit', '/quit'):
                        self._summarize_session()
                        print("Goodbye!")
                        break
                        
                    elif user_input.lower() == '/reset':
                        self.reset_conversation()
                        continue
                        
                    elif user_input.lower() == '/reload':
                        self.reload_boot_doc()
                        continue
                        
                    elif user_input.lower() in ('/which_bootdoc', '/bootdoc'):
                        print(f"Current boot document: {self.config['boot_doc_path']}")
                        print(f"Last modified: {time.ctime(os.path.getmtime(self.config['boot_doc_path']))}\n")
                        continue
                        
                    elif user_input.lower() == '/help':
                        self.show_help()
                        continue
                        
                    elif user_input.lower().startswith('/memory'):
                        parts = user_input.split(maxsplit=1)
                        if len(parts) > 1:
                            cmd_parts = parts[1].split(maxsplit=2)
                            action = cmd_parts[0].lower()
                            
                            if action == 'set' and len(cmd_parts) > 2:
                                mem_type = cmd_parts[1].lower()
                                value = cmd_parts[2].strip('"\'')
                                memory = self.memory_store.load_long_term_memory()
                                if memory is None:
                                    memory = {
                                        'user_profile': '',
                                        'preferences': [],
                                        'work_in_progress': [],
                                        'open_loops': [],
                                        'last_updated': ''
                                    }
                                if mem_type == 'user_profile':
                                    memory['user_profile'] = value
                                    print(f"{Fore.GREEN}✓ Updated user profile{Style.RESET_ALL}")
                                self.memory_store.save_long_term_memory(memory)
                                
                            elif action == 'add' and len(cmd_parts) > 2:
                                mem_type = cmd_parts[1].lower()
                                value = cmd_parts[2].strip('"\'')
                                memory = self.memory_store.load_long_term_memory()
                                if memory is None:
                                    memory = {
                                        'user_profile': '',
                                        'preferences': [],
                                        'work_in_progress': [],
                                        'open_loops': [],
                                        'last_updated': ''
                                    }
                                if mem_type == 'preference' and value not in memory['preferences']:
                                    memory['preferences'].append(value)
                                    print(f"{Fore.GREEN}✓ Added preference: {value}{Style.RESET_ALL}")
                                    self.memory_store.save_long_term_memory(memory)
                        else:
                            memory = self.memory_store.load_long_term_memory()
                            if memory:
                                print(f"\n{Fore.CYAN}=== Long-term Memory ==={Style.RESET_ALL}")
                                print(f"Last updated: {memory.get('last_updated', 'Never')}")
                                print(f"User Profile: {memory.get('user_profile', 'Not specified')}")
                                print(f"Preferences: {', '.join(memory.get('preferences', [])) or 'None'}")
                                print(f"Work in Progress: {', '.join(memory.get('work_in_progress', [])) or 'None'}")
                                print(f"Open Loops: {', '.join(memory.get('open_loops', [])) or 'None'}\n")
                            else:
                                print(f"{Fore.YELLOW}No long-term memory found or memory is disabled.{Style.RESET_ALL}\n")
                        continue
                    
                    print(f"{Fore.GREEN}Assistant: ", end='', flush=True)
                    
                    response = self.get_chat_response(user_input)
                    
                    for char in response:
                        print(char, end='', flush=True)
                        time.sleep(0.01)
                    print("\n")
                    
                    self.log_message("assistant", response)
                    
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
                    self.log_message("system", error_msg)
        
        finally:
            self._summarize_session()


def main():
    """Main entry point for the Clarity Chat application."""
    try:
        chat = ClarityChat()
        chat.run()
    except Exception as e:
        print(f"{Fore.RED}Fatal error: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    main()
