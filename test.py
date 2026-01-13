import requests
import json
import threading
import time
import random
import os
import re

chat_log = []
threads = []
lock = threading.Lock()

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

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
        #print(f"{thread_name}: sleeping for {random_wait} seconds...")
        time.sleep(random_wait)
        should_stop_after_waiting = getattr(t, "do_run", True)
        if not should_stop_after_waiting:
            break
        #print(f"{thread_name}: Doing something...")
        with lock:
            process_new_questions()
            #print(f"{thread_name}: got the lock")
            send_and_print(person_name)
    add_message_to_chatlog("has left the chat", person_name)

def send_prompt_to_openai(system_prompt, user_prompt):
    url = "https://api.openai.com/v1/chat/completions"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),  # Can be upgraded to "gpt-4o" for better quality
        "messages": messages,
        "temperature": 0.5,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_KEY}"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response
    except requests.exceptions.RequestException as e:
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
        "temperature": 0.6,
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)
    return response

def send_chat_to_ollama(person_name):
    users_currently_in_chat = [thread.person_name for thread in threads if hasattr(thread, 'person_name')]
    current_time = time.strftime("%I:%M%p")
    system_prompt = f"You represent {person_name} and you advise people on what they should say next in a conversation.  You advise people to state opinions on worldy matters and to be conversational with what else is being said in the chat log.  You don't advise people to ask quesitons.  You advise people to say short conversational things.  The current time is {current_time}.\n\n"

    user_prompt = "Chat log from the chat room:\n\n"
    for line in chat_log[-20:]:
        user_prompt += f"{line}\n"
    user_prompt += "\n\nRespond in the following format: MESSAGE, where MESSAGE is what you want to add to the chat log.  Do not respond: TIME NAME: MESSAGE."

    if USE_OPENAI:
        response = send_prompt_to_openai(system_prompt, user_prompt)
    else:
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
            response_json = response.json()
            message = response_json["choices"][0]["message"]["content"]
        else:
            response_text = response.text
            response_lines = response_text.splitlines()
            response_json = [json.loads(line) for line in response_lines]
            message = ""
            for line in response_json:
                message += line.get("response", "")
            message = clean_up_message(message)

        if message == "DO_NOTHING":
            print(f"{person_name} did nothing.")
            return
        add_message_to_chatlog(message, person_name)
    except Exception as e:
        print(f"Error processing response for {person_name}: {e}")

def send_and_print(person_name):
    response = send_chat_to_ollama(person_name)
    print_response(response, person_name)

def send_message_to_server(message):
    url = f"{FLASK_SERVER_URL}/broadcast"
    payload = {"message": message}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to server: {e}")

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

    with lock:
        chat_log.append(thing_to_print)
        # Keep chat log size manageable
        if len(chat_log) > 100:
            chat_log.pop(0)

    print(thing_to_print)
    send_message_to_server(thing_to_print)
    send_users_to_server()

def get_person_name():
    with lock:
        existing_names = [thread.person_name for thread in threads if hasattr(thread, 'person_name')]
        try:
            response = requests.get(f"{FLASK_SERVER_URL}/update_users", timeout=5)
            if response.status_code == 200:
                existing_names.extend(response.json())
        except requests.exceptions.RequestException as e:
            print(f"Error fetching existing users: {e}")

        system_prompt = f"You are a human on Earth."
        user_prompt = f"Respond with a fun, creative username that is not one of these: {existing_names}.  Response in the format: USERNAME.  Where USERNAME is the username that you have chosen.  Do not respond with any other text."

        try:
            if USE_OPENAI:
                name = extract_just_response(send_prompt_to_openai(system_prompt, user_prompt))
            else:
                name = extract_just_response(send_prompt_to_ollama(system_prompt, user_prompt))
            # Fallback if name generation fails
            if not name or name.strip() == "":
                name = f"User_{random.randint(1000, 9999)}"
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
    for question in new_questions:
        nickname = question['nickname']
        question_text = question['question']
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
