import requests
import json
import threading
import time
import random
import os
import re

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, that's okay - user can set env vars manually
    pass

chat_log = []
threads = []
lock = threading.Lock()

def log_diag(person_name, message):
    """Helper function to log diagnostic messages with timestamp and person name."""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [{person_name}] {message}")

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required. Make sure you have a .env file with OPENAI_API_KEY=your_key_here, or set it as an environment variable.")

# Validate API key format (starts with sk-)
if OPENAI_KEY and not OPENAI_KEY.startswith("sk-"):
    print(f"WARNING: API key doesn't start with 'sk-'. This might be invalid. Key starts with: {OPENAI_KEY[:5]}...")

ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"

FLASK_SERVER_URL = os.getenv("ENDPOINT", default="http://localhost:5000") # ENDPOINT=https://www.eavesdrop.club

print(f"Using endpoint: {FLASK_SERVER_URL}")
""" Ideas
:Have each bot have real world adventures they can talk about
:Prevent it from becoming 'cocktail chatter'
: Use 4090 downstairs for better AI

"""

USE_OPENAI = True  # Set this flag to switch between OpenAI and Ollama

def joiner_thread_starter():
    thread_name = "Joiner-Thread"
    thread = threading.Thread(target=joiner_worker, args=(thread_name,))
    thread.daemon = True  # Make the thread exit when the main program exits
    threads.append(thread)
    thread.start()

def leaver_thread_starter():
    thread_name = "Leaver-Thread"
    thread = threading.Thread(target=leaver_worker, args=(thread_name,))
    thread.daemon = True  # Make the thread exit when the main program exits
    threads.append(thread)
    thread.start()

def chat_thread_starter():
    thread_name = f"Thread-{len(threads)+1}"
    person_name = get_person_name()
    add_message_to_chatlog("has entered the chat", person_name)
    thread = threading.Thread(target=chat_worker, args=(thread_name,person_name,))
    thread.person_name = person_name
    thread.daemon = True  # Make the thread exit when the main program exits
    threads.append(thread)
    thread.start()

def joiner_worker(thread_name):
    while True:
        chat_thread_starter()
        random_wait = random.randint(30,90)
        time.sleep(random_wait)

def leaver_worker(thread_name):
    while True:
        with lock:
            if threads:
                thread_to_kill = random.choice(threads)
                if thread_to_kill.is_alive():
                    threads.remove(thread_to_kill)
                    # Stopping the thread by setting a flag
                    thread_to_kill.do_run = False

        random_wait = random.randint(30,90)
        time.sleep(random_wait)

def chat_worker(thread_name, person_name):
    t = threading.current_thread()
    while getattr(t, "do_run", True):
        random_wait = random.randint(30,120)
        log_diag(person_name, f"💤 Sleeping for {random_wait} seconds...")
        time.sleep(random_wait)
        should_stop_after_waiting = getattr(t, "do_run", True)
        if not should_stop_after_waiting:
            log_diag(person_name, "👋 Thread stopping, leaving chat")
            break
        log_diag(person_name, "⏰ Woke up! Checking chat and deciding what to say...")
        with lock:
            process_new_questions()
            send_and_print(person_name)
        log_diag(person_name, "✓ Cycle complete, going back to sleep")
    add_message_to_chatlog("has left the chat", person_name)

def perform_web_search(query, max_results=5):
    """Perform a web search using DuckDuckGo (free, no API key needed)."""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] 🔍 [SEARCH] Query: '{query}' (max_results={max_results})")
    try:
        # Use DuckDuckGo's instant answer API
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1"
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        results = []

        # Get the main abstract/answer if available
        if data.get("AbstractText"):
            results.append({
                "title": data.get("Heading", "Search Result"),
                "url": data.get("AbstractURL", ""),
                "content": data.get("AbstractText", "")
            })

        # Include related topics
        for topic in data.get("RelatedTopics", [])[:max_results-1]:
            if isinstance(topic, dict) and "Text" in topic:
                results.append({
                    "title": topic.get("Text", "").split(" - ")[0] if " - " in topic.get("Text", "") else "Result",
                    "url": topic.get("FirstURL", ""),
                    "content": topic.get("Text", "")
                })

        # If we don't have enough results, try HTML search results
        if len(results) < max_results:
            try:
                # Use DuckDuckGo HTML search as fallback
                html_url = "https://html.duckduckgo.com/html/"
                html_params = {"q": query}
                html_response = requests.get(html_url, params=html_params, timeout=10, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                # Note: HTML parsing would require BeautifulSoup, but for now we'll use what we have
            except:
                pass

        return {"success": True, "results": results[:max_results] if results else [{"title": "No results", "url": "", "content": f"Could not find information about: {query}"}]}
    except Exception as e:
        print(f"Web search error: {e}")
        return {"success": False, "results": [], "error": str(e)}

def send_prompt_to_openai(system_prompt, user_prompt, enable_web_search=True, person_name="Unknown", temperature=None):
    url = "https://api.openai.com/v1/chat/completions"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # Define web search tool if enabled
    tools = None
    if enable_web_search and ENABLE_WEB_SEARCH:
        log_diag(person_name, "🔍 Web search tool enabled - AI can search if needed")
        tools = [{
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for current, real-time information about recent events, news, facts, or any topic that requires up-to-date information. Use this when someone makes a claim about recent events or asks about something that happened recently.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to look up on the web"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of search results to return (default 5)",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            }
        }]

    # Use lower temperature for name generation, higher for chat
    if temperature is None:
        temperature = 0.3 if person_name == "NameGenerator" else 0.7
    
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),  # Can be upgraded to "gpt-4o" for better quality
        "messages": messages,
        "temperature": temperature,
    }

    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"  # Let the model decide when to use the tool

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_KEY}"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)  # Increased timeout for web searches
        response.raise_for_status()
        response_data = response.json()

        # Check if the model wants to call a function
        message = response_data["choices"][0]["message"]
        if message.get("tool_calls"):
            log_diag(person_name, f"🔧 AI wants to use tools: {len(message.get('tool_calls', []))} tool call(s)")
            # Handle function calls
            for tool_call in message["tool_calls"]:
                if tool_call["function"]["name"] == "web_search":
                    # Parse arguments
                    args = json.loads(tool_call["function"]["arguments"])
                    search_query = args.get("query")
                    max_results = args.get("max_results", 5)
                    
                    log_diag(person_name, f"🌐 Searching the web for: '{search_query}'")

                    # Perform the search
                    search_results = perform_web_search(search_query, max_results)
                    
                    if search_results.get("success"):
                        result_count = len(search_results.get("results", []))
                        log_diag(person_name, f"✅ Found {result_count} search result(s)")
                    else:
                        log_diag(person_name, f"⚠️ Web search failed: {search_results.get('error', 'Unknown error')}")

                    # Add function result to messages
                    messages.append(message)  # Add the assistant's message with tool_calls
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(search_results)
                    })

            # Make a second API call with the search results
            log_diag(person_name, "🔄 Getting final response with search results...")
            payload["messages"] = messages
            final_response = requests.post(url, json=payload, headers=headers, timeout=60)
            final_response.raise_for_status()
            log_diag(person_name, "✅ Got final response after function call")
            return final_response
        else:
            log_diag(person_name, "💬 AI responded directly (no tools used)")

        log_diag(person_name, f"📤 Returning response object (status: {response.status_code})")
        return response
    except requests.exceptions.RequestException as e:
        # Check if it's an HTTP error with 401 status
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 401:
            print(f"\n{'='*60}")
            print(f"ERROR: OpenAI API authentication failed (401 Unauthorized)")
            print(f"{'='*60}")
            print(f"This usually means:")
            print(f"  1. Your API key is invalid or expired")
            print(f"  2. Your API key doesn't have access to the model you're using")
            print(f"  3. The API key format is incorrect")
            print(f"\nTroubleshooting:")
            print(f"  - Check your .env file exists in the project root")
            print(f"  - Verify OPENAI_API_KEY starts with 'sk-'")
            print(f"  - Get a new key from: https://platform.openai.com/api-keys")
            print(f"  - Make sure you have credits/billing set up on your OpenAI account")
            key_preview = OPENAI_KEY[:7] + "..." if OPENAI_KEY and len(OPENAI_KEY) > 7 else "NOT FOUND"
            print(f"\nCurrent API key: {key_preview}")
            print(f"{'='*60}\n")
        else:
            print(f"Error calling OpenAI API: {e}")
        raise

def send_prompt_to_ollama(system_prompt, user_prompt):
    #url = "http://192.168.1.36:11434/api/generate"
    url = "http://127.0.0.1:11434/api/generate"
    # prompt = f"""
    #     <|begin_of_text|>
    #     <|start_header_id|>system<|end_header_id|>
    #     { system_prompt }
    #     <|eot_id|>
    #     <|start_header_id|>user<|end_header_id|>
    #     { user_prompt }
    #     <|eot_id|>
    #     <|start_header_id|>assistant<|end_header_id|>
    #     """

    prompt = f"{system_prompt}\n\n{user_prompt}"

    payload = {
        #"model": "llama3.3",
        "model": "deepseek-r1",
        "prompt": prompt,
        "temperature": 0.8,  # Increased for more varied, less generic responses
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)
    return response

def send_chat_to_ollama(person_name):
    users_currently_in_chat = [thread.person_name for thread in threads if hasattr(thread, 'person_name')]
    current_time = time.strftime("%I:%M%p")
    
    recent_messages = chat_log[-5:] if len(chat_log) > 0 else []
    log_diag(person_name, f"📝 Preparing prompt... (Chat log has {len(chat_log)} total messages)")

    # Create a more engaging system prompt that makes the AI actually BE the person
    personality_traits = [
        "You are direct and don't shy away from controversial topics.",
        "You have strong opinions and aren't afraid to express them.",
        "You engage directly with what others say - if someone makes a claim, you address it specifically.",
        "You ask clarifying questions when something seems unclear or questionable.",
        "You bring up specific facts, examples, or counterpoints when relevant.",
        "You avoid generic diplomatic responses - be specific and engaging.",
        "You have a distinct personality and perspective that comes through in your responses.",
        "You keep responses conversational and relatively short (1-3 sentences typically)."
    ]

    system_prompt = f"""You are {person_name}, a real person in an online chatroom. The current time is {current_time}.

Your personality and communication style:
{chr(10).join(f"- {trait}" for trait in personality_traits)}

CRITICAL: When someone makes a claim or asks a question, engage with it DIRECTLY.
- If someone says "I heard X happened", don't just say "It's a complex situation" - either verify/question the claim, provide your perspective on it, or discuss what you know about X.
- If someone asks "Thoughts?", give your actual thoughts, not generic platitudes.
- Avoid phrases like "It's fascinating how...", "It's interesting to see...", "It's a reminder that..." unless you're actually adding something specific.
- Be direct, specific, and authentic. Real people don't talk like diplomats - they have opinions and engage with what others say.
- VARY YOUR PUNCTUATION: Don't end every message with an exclamation point. Use periods, question marks, and exclamation points naturally. Most messages should end with periods. Only use exclamation points when you're actually excited or emphatic.
- WEB SEARCH: If someone mentions a recent event, news, or makes a claim about something that happened recently, use the web_search function to look it up and verify or get accurate information. Real people look things up when they're unsure about recent events."""

    user_prompt = "Recent chat log from the chat room:\n\n"
    for line in chat_log[-20:]:
        user_prompt += f"{line}\n"
    user_prompt += "\n\nWhat would you say next in this conversation? \n\nIMPORTANT: If someone asked a question or made a specific claim, address it directly. Don't give generic responses - engage with what was actually said. Be specific, direct, and authentic.\n\nRespond with ONLY your message text (no timestamp, no name prefix). If you don't have anything meaningful to add right now, respond with: DO_NOTHING"

    if USE_OPENAI:
        log_diag(person_name, f"🚀 Calling OpenAI API (web_search={'enabled' if ENABLE_WEB_SEARCH else 'disabled'})...")
        response = send_prompt_to_openai(system_prompt, user_prompt, enable_web_search=ENABLE_WEB_SEARCH, person_name=person_name)
        log_diag(person_name, "✅ Received response from OpenAI")
    else:
        log_diag(person_name, "🚀 Calling Ollama API...")
        response = send_prompt_to_ollama(system_prompt, user_prompt)
    return response

def clean_up_message(message):
    message = re.sub(r"<think>.*?</think>", "", message, flags=re.DOTALL)
    message = message.strip()
    if message.startswith('"') and message.endswith('"'):
        message = message[1:-1]
    return message

def extract_just_response(response):
    if USE_OPENAI:
        try:
            response_json = response.json()
            message = response_json["choices"][0]["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            print(f"Error parsing OpenAI response: {e}")
            return "I'm having trouble processing that right now."
    else:
        try:
            response_text = response.text
            response_lines = response_text.splitlines()
            response_json = [json.loads(line) for line in response_lines]
            message = ""
            for line in response_json:
                message += line.get("response", "")
            message = clean_up_message(message)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing Ollama response: {e}")
            return "I'm having trouble processing that right now."

    return message

def print_response(response, person_name):
    try:
        if USE_OPENAI:
            log_diag(person_name, "📄 Parsing OpenAI response...")
            response_json = response.json()
            message = response_json["choices"][0]["message"]["content"]
            
            # Validate message
            if not message or message.strip() == "":
                log_diag(person_name, "⚠️ WARNING: Empty message received!")
                return
            
            # Show token usage if available
            usage = response_json.get("usage", {})
            if usage:
                tokens = usage.get("total_tokens", 0)
                log_diag(person_name, f"📊 Token usage: {tokens} tokens")
        else:
            response_text = response.text
            response_lines = response_text.splitlines()
            response_json = [json.loads(line) for line in response_lines]
            message = ""
            for line in response_json:
                message += line.get("response", "")
            message = clean_up_message(message)

        if message == "DO_NOTHING":
            log_diag(person_name, "😴 Decided to do nothing (no meaningful response)")
            return
        
        # Show a preview of what they're about to say
        preview = message[:50] + "..." if len(message) > 50 else message
        log_diag(person_name, f"💭 Response extracted: '{preview}' (length: {len(message)})")
        
        # Actually add the message
        log_diag(person_name, "📤 Calling add_message_to_chatlog...")
        add_message_to_chatlog(message, person_name)
        log_diag(person_name, "✅ Message added to chat successfully")
    except Exception as e:
        log_diag(person_name, f"❌ Error processing response: {e}")
        import traceback
        traceback.print_exc()

def send_and_print(person_name):
    log_diag(person_name, "🤔 Thinking about what to say...")
    try:
        response = send_chat_to_ollama(person_name)
        if response is None:
            log_diag(person_name, "❌ ERROR: Response is None!")
            return
        log_diag(person_name, f"📥 Got response object, status: {response.status_code if hasattr(response, 'status_code') else 'N/A'}")
        print_response(response, person_name)
    except Exception as e:
        log_diag(person_name, f"❌ Error in send_and_print: {e}")
        import traceback
        traceback.print_exc()

def send_message_to_server(message):
    url = f"{FLASK_SERVER_URL}/broadcast"
    payload = {"message": message}
    headers = {"Content-Type": "application/json"}
    try:
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] 📤 Sending to server: {message[:60]}...")
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        response.raise_for_status()
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] ✅ Server responded: {response.status_code}")
    except requests.exceptions.RequestException as e:
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] ❌ Error sending message to server: {e}")
        import traceback
        traceback.print_exc()

def send_users_to_server():
    url = f"{FLASK_SERVER_URL}/update_users"
    users = [thread.person_name for thread in threads if hasattr(thread, 'person_name')]
    payload = {"users": users}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error sending users to server: {e}")

def add_message_to_chatlog(message, person_name):
    # Sanitize message to prevent XSS and limit length
    message = str(message)[:500]  # Limit message length
    person_name = str(person_name)[:50]  # Limit name length

    current_time = time.strftime("%I:%M%p")
    thing_to_print = f"{current_time} {person_name}: {message}"

    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] 📝 Adding to chat log: {person_name} -> {message[:50]}...")

    with lock:
        chat_log.append(thing_to_print)
        # Keep chat log size manageable
        if len(chat_log) > 100:
            chat_log.pop(0)

    print(thing_to_print)
    send_message_to_server(thing_to_print)
    send_users_to_server()
    
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] ✅ Chat log updated and sent to server")

def get_person_name():
    with lock:
        existing_names = [thread.person_name for thread in threads if hasattr(thread, 'person_name')]
        try:
            response = requests.get(f"{FLASK_SERVER_URL}/update_users", timeout=5)
            if response.status_code == 200:
                existing_names.extend(response.json())
        except requests.exceptions.RequestException as e:
            print(f"Error fetching existing users: {e}")

        system_prompt = """You are generating a realistic internet username that a real person would choose for a chatroom.

Good examples of realistic usernames:
- coffee_lover, bookworm42, musicfan23
- jake123, sarah_m, mike2024
- guitarplayer, runner99, cookiemonster
- shadow87, river_blue, midnight_user
- alex_t, jenny42, chris_m

Bad examples (too AI-like, avoid these):
- GalacticGummyBear, CosmicCottonCandy, NebulaNoodleDance
- StarlitSundaeSurfer, CosmicCactus88, StellarSasquatch99
- Any alliterative patterns with capital letters

Guidelines:
- Use lowercase or simple capitalization
- Often include numbers (especially at the end)
- Simple word combinations, not overly creative
- References to hobbies, interests, or casual names
- Sound like a real person, not an AI-generated name"""
        
        existing_list = ", ".join(existing_names[:10]) if existing_names else "none"
        user_prompt = f"Generate a realistic, human-like username. Do NOT use any of these existing usernames: {existing_list}. Respond with ONLY the username, nothing else. Format: USERNAME"

        try:
            # Sometimes use a simpler pattern for more realism (30% chance)
            if random.random() < 0.3:
                simple_patterns = [
                    f"user{random.randint(10, 999)}",
                    f"person{random.randint(1, 99)}",
                    f"guest{random.randint(100, 9999)}",
                    f"anon{random.randint(1, 999)}",
                ]
                name = random.choice(simple_patterns)
                if name not in existing_names:
                    return name
            
            if USE_OPENAI:
                name = extract_just_response(send_prompt_to_openai(system_prompt, user_prompt, enable_web_search=False, person_name="NameGenerator"))
            else:
                name = extract_just_response(send_prompt_to_ollama(system_prompt, user_prompt))
            
            # Clean up the name - remove quotes, extra whitespace, etc.
            name = name.strip().strip('"').strip("'")
            
            # Fallback if name generation fails
            if not name or name.strip() == "" or name in existing_names:
                name = f"user{random.randint(100, 9999)}"
            return name.strip()
        except Exception as e:
            print(f"Error generating person name: {e}")
            return f"User_{random.randint(1000, 9999)}"

def get_new_questions():
    url = f"{FLASK_SERVER_URL}/get_questions"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching questions: {e}")
        return []

def process_new_questions():
    new_questions = get_new_questions()
    if new_questions:
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] 📥 Processing {len(new_questions)} new question(s) from users...")
    for question in new_questions:
        nickname = question['nickname']
        question_text = question['question']
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}]   → Question from {nickname}: {question_text[:50]}...")
        add_message_to_chatlog(question_text, nickname)

if __name__ == "__main__":
    for i in range(4):
        chat_thread_starter()

    #joiner_thread_starter()

    #leaver_thread_starter()

    try:
        while True:
            time.sleep(1)
            process_new_questions()
    except KeyboardInterrupt:
        print("Stopping threads and exiting...")
