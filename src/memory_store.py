import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from openai import OpenAI

class MemoryStore:
    def __init__(self, memory_dir: str = "memory", model: str = "gpt-4-1106-preview", api_key: str = None):
        self.memory_dir = Path(memory_dir).resolve()
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.long_term_memory_path = self.memory_dir / "long_term.json"
        self.client = OpenAI(api_key=api_key) if api_key else OpenAI()
        self.model = model
    
    def add_log_chunks(self, log_path: str) -> None:
        pass
    
    def search_relevant_chunks(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        return []
    
    def load_long_term_memory(self) -> Optional[Dict[str, Any]]:
        if not self.long_term_memory_path.exists():
            return None
            
        try:
            with open(self.long_term_memory_path, 'r', encoding='utf-8') as f:
                memory = json.load(f)
                
            if not self._validate_memory_format(memory):
                return None
                
            return memory
            
        except (json.JSONDecodeError, IOError, Exception):
            return None
    
    def save_long_term_memory(self, memory: Dict[str, Any]) -> bool:
        """Save the long-term memory to disk."""
        try:
            print(f"Debug: Saving memory to {self.long_term_memory_path}")
            memory['last_updated'] = datetime.now().isoformat()
            
            # Ensure the directory exists
            self.memory_dir.mkdir(parents=True, exist_ok=True)
            
            # Write to a temporary file first, then rename (atomic operation)
            temp_path = self.long_term_memory_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(memory, f, indent=2, ensure_ascii=False)
            
            # On Windows, we need to handle file replacement carefully
            if self.long_term_memory_path.exists():
                self.long_term_memory_path.unlink()
            temp_path.rename(self.long_term_memory_path)
            
            print(f"Debug: Memory saved successfully to {self.long_term_memory_path}")
            return True
        except Exception as e:
            print(f"Debug: Error saving memory: {str(e)}")
            return False
    
    def _validate_memory_format(self, memory: Dict[str, Any]) -> bool:
        required_keys = {
            'user_profile': str,
            'preferences': list,
            'work_in_progress': list,
            'open_loops': list,
            'last_updated': str
        }
        
        if not isinstance(memory, dict):
            return False
            
        for key, value_type in required_keys.items():
            if key not in memory or not isinstance(memory[key], value_type):
                return False
        
        # Additional validation for list items
        for key in ['preferences', 'work_in_progress', 'open_loops']:
            if not all(isinstance(item, str) for item in memory[key]):
                return False
                
        return True
    
    def _get_summarization_prompt(self, conversation_history: List[Dict[str, str]]) -> str:
        """
        Generate a prompt for summarizing the conversation with strict requirements for stable facts.
        
        IMPORTANT: This prompt must be designed to work with the T2 spec requirement of no heuristic fallback.
        The prompt must be strict enough to ensure the model returns valid JSON in the first attempt.
        """
        # Convert conversation to text, excluding system messages
        conversation_text = "\n".join(
            f"{msg['role'].upper()}: {msg['content']}" 
            for msg in conversation_history 
            if msg['role'] in ['user', 'assistant']
        )
        
        return f"""
        Analyze the following conversation and extract ONLY stable facts, preferences, and ongoing work items.
        
        STABLE FACTS CRITERIA:
        - Must be information that is unlikely to change over time
        - Must be verifiable and objective
        - Must not include personal opinions, feelings, or temporary states
        - Must not include time-sensitive information
        - Must be generally applicable across different contexts
        
        EXAMPLES OF STABLE FACTS:
        - "I prefer Python over JavaScript" (preference)
        - "I'm working on a web application" (work in progress)
        - "I have experience with machine learning" (profile)
        
        EXAMPLES OF UNSTABLE INFORMATION (DO NOT INCLUDE):
        - "I'm feeling tired today" (temporary state)
        - "I'll finish this by Friday" (time-sensitive)
        - "This code is giving me errors" (temporary issue)
        - "I think we should refactor this" (opinion)
        
        Conversation to analyze:
        {conversation_text}
        
        Return a JSON object with the following structure:
        {{
            // A brief, stable description of the user (e.g., skills, background, etc.)
            "user_profile": "string",
            
            // List of stable preferences (e.g., technology choices, workflow preferences)
            // Only include preferences that are consistent over time
            "preferences": ["string"],
            
            // List of ongoing work items or projects
            // Only include items that represent actual work in progress
            "work_in_progress": ["string"],
            
            // List of unresolved topics or questions that need follow-up
            // Only include topics that are still relevant and not time-sensitive
            "open_loops": ["string"]
        }}
        
        IMPORTANT:
        - Only include information that meets the stable facts criteria
        - If no information meets the criteria for a field, use an empty array []
        - Do not include any explanations or additional text outside the JSON
        - The response must be valid JSON that can be parsed by json.loads()
        - If unsure whether something is a stable fact, do not include it
        """

    def summarize_conversation(self, conversation_history: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """
        Summarize the conversation using the model.
        
        NOTE: Per T2 specification, there is NO heuristic fallback for memory updates.
        If the model does not return valid JSON or if there are any errors,
        this method will return None rather than falling back to heuristics.
        
        Returns:
            Optional[Dict[str, Any]]: Parsed summary as a dictionary if successful, None otherwise.
        """
        try:
            prompt = self._get_summarization_prompt(conversation_history)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}  # Enforce JSON response
            )
            
            # Extract the response content
            content = response.choices[0].message.content
            
            # Parse the JSON response
            try:
                summary = json.loads(content)
                
                # Validate required fields
                required_fields = {
                    'user_profile': str,
                    'preferences': list,
                    'work_in_progress': list,
                    'open_loops': list
                }
                
                # Check if all required fields are present and of correct type
                for field, field_type in required_fields.items():
                    if field not in summary or not isinstance(summary[field], field_type):
                        print(f"Error: Invalid or missing required field in summary: {field}")
                        return None
                
                # Add timestamp
                summary['last_updated'] = datetime.now().isoformat()
                
                return summary
                
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON response from model: {str(e)}")
                return None
                
        except Exception as e:
            print(f"Error in summarize_conversation: {str(e)}")
            return None

    def update_long_term_memory(self, conversation_history: List[Dict[str, str]]) -> bool:
        """
        Update long-term memory with new information from the conversation.
        Returns False if the conversation couldn't be summarized or if saving fails.
        """
        if not conversation_history:
            print("No conversation history provided to update memory")
            return False

        # Get model-based summary - this will be None if JSON validation fails
        new_memory = self.summarize_conversation(conversation_history)
        if not new_memory:
            print("Memory not updated: Could not generate valid summary from conversation")
            return False

        # Get existing memory or create new
        current_memory = self.load_long_term_memory()
        if not current_memory:
            # If no existing memory, use the new memory as is
            updated_memory = new_memory
        else:
            # Merge with existing memory, removing duplicates
            updated_memory = {
                'user_profile': new_memory['user_profile'] or current_memory['user_profile'],
                'preferences': list(set(current_memory['preferences'] + new_memory['preferences'])),
                'work_in_progress': list(set(current_memory['work_in_progress'] + new_memory['work_in_progress'])),
                'open_loops': list(set(current_memory['open_loops'] + new_memory['open_loops'])),
                'last_updated': datetime.now().isoformat()
            }

        # Save the updated memory
        if not self.save_long_term_memory(updated_memory):
            print("Failed to save updated memory")
            return False
            
        print("Memory updated successfully")
        return True
    
    def load_last_session_context(self, logs_dir: str, max_turns: int = 20) -> List[Dict[str, str]]:
        try:
            logs_path = Path(logs_dir)
            if not logs_path.exists() or not logs_path.is_dir():
                print(f"Logs directory not found: {logs_dir}")
                return []
                
            # Look for log files with various patterns
            log_patterns = ["session-*.txt", "session-*.log"]
            log_files = []
            
            for pattern in log_patterns:
                log_files.extend(logs_path.glob(pattern))
                
            if not log_files:
                print(f"No session log files found in {logs_dir}")
                return []
                
            # Sort by modification time, newest first
            log_files = sorted(
                log_files,
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )
            
            print(f"Found {len(log_files)} log files. Most recent: {log_files[0].name}")
            
            # If there's only one log file, it's the current session
            if len(log_files) < 2:
                print("No previous session logs found")
                return []
                
            # Get the second most recent log file (most recent is current session)
            last_session_log = log_files[1]
            print(f"Loading context from previous session: {last_session_log.name}")
            
            return self._parse_session_log(last_session_log, max_turns)
            
        except Exception as e:
            print(f"Error loading last session context: {str(e)}")
            return []
    
    def _parse_session_log(self, log_path: Path, max_turns: int) -> List[Dict[str, str]]:
        messages = []
        current_role = None
        current_content = []
        valid_roles = {'user', 'assistant', 'system', 'function', 'tool', 'developer'}
        message_count = 0
        
        def add_message(role: str, content: str) -> None:
            nonlocal message_count
            if role in valid_roles and content.strip():
                messages.append({
                    'role': role,
                    'content': content.strip()
                })
                message_count += 1
        
        try:
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Check for role markers (e.g., "USER:", "ASSISTANT:")
                    if ':' in line:
                        role_part = line.split(':', 1)[0].strip().lower()
                        if any(role_part.startswith(role) for role in valid_roles):
                            # Save previous message if exists
                            if current_role and current_content:
                                add_message(current_role, '\n'.join(current_content))
                                current_content = []
                                
                                if message_count >= max_turns * 2:
                                    break
                            
                            current_role = role_part.split()[0]  # Get the base role
                            content_part = line.split(':', 1)[1].strip()
                            if content_part:  # Handle content on same line as role
                                current_content.append(content_part)
                            continue
                    
                    # If we're here, it's a continuation line for the current role
                    if current_role is not None:
                        current_content.append(line)
            
            # Add the last message if it exists
            if current_role and current_content:
                add_message(current_role, '\n'.join(current_content))
            
            print(f"Parsed {len(messages)} messages from log file")
            
        except Exception as e:
            print(f"Error parsing log file {log_path.name}: {str(e)}")
            return []
        
        # Return only the most recent messages up to max_turns * 2 (user + assistant)
        return messages[-(max_turns * 2):] if messages else []
