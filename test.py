import requests
import json
import threading
import time
import random
import os

chat_log = []
threads = []
lock = threading.Lock()

FLASK_SERVER_URL = os.getenv("ENDPOINT", default="http://localhost:5000") # ENDPOINT=https://www.eavesdrop.club

print(f"Using endpoint: {FLASK_SERVER_URL}")
""" Ideas
:Have each bot have real world adventures they can talk about
:Prevent it from becoming 'cocktail chatter'
: Use 4090 downstairs for better AI

"""

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
        random_wait = random.randint(30,90)
        #print(f"{thread_name}: sleeping for {random_wait} seconds...")
        time.sleep(random_wait)
        should_stop_after_waiting = getattr(t, "do_run", True)
        if not should_stop_after_waiting:
            break
        #print(f"{thread_name}: Doing something...")
        with lock:
            #print(f"{thread_name}: got the lock")
            send_and_print(person_name)
    add_message_to_chatlog("has left the chat", person_name)

def send_prompt_to_ollama(system_prompt, user_prompt):
    url = "http://localhost:11434/api/generate"

    prompt = f"""
        <|begin_of_text|>
        <|start_header_id|>system<|end_header_id|>
        { system_prompt }
        <|eot_id|>
        <|start_header_id|>user<|end_header_id|>
        { user_prompt }
        <|eot_id|>
        <|start_header_id|>assistant<|end_header_id|>
        """

    payload = {
        "model": "llama3",
        "prompt": prompt,
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)
    return response

def send_chat_to_ollama(person_name):
    users_currently_in_chat = [thread.person_name for thread in threads if hasattr(thread, 'person_name')]
    system_prompt = f"You are {person_name}.  The following users are still in the chat room: {users_currently_in_chat}.  You are in a chat room. Respond with only the one line of conversation you want added to the end of the chatlog, do not include the time or person name, I will do that. If you haven't said anything yet then use a greeting to get started.  Don't discuss your intentions with your message, just give your message.  Don't have meta conversations about the conversation, instead talk about interesting topics.  You should have strong opinions, don't just ask questions of the chat room. If the current discussion has become reptitive then change the subject.  Don't say something like: 'Here is my response.'  Speak casually.  If you have nothing interesting to say then just respond with: DO_NOTHING"

    user_prompt = ""
    for line in chat_log[-20:]:
        user_prompt += f"{line}\n"

    response = send_prompt_to_ollama(system_prompt, user_prompt)
    return response

def extract_just_response(response):
    response_text = response.text
    response_lines = response_text.splitlines()
    response_json = [json.loads(line) for line in response_lines]
    message = ""
    for line in response_json:
        message += line["response"]
    return message

def print_response(response, person_name):
     # Process the response
    response_text = response.text

    # Convert each line to json
    response_lines = response_text.splitlines()
    response_json = [json.loads(line) for line in response_lines]

    message = ""
    for line in response_json:
        # Print the response. No line break
        message += line["response"]

    if message == "DO_NOTHING":
        print(f"{person_name} did nothing.")
        return
    add_message_to_chatlog(message, person_name)

def send_and_print(person_name):
    response = send_chat_to_ollama(person_name)
    print_response(response, person_name)

def send_message_to_server(message):
    url = f"{FLASK_SERVER_URL}/broadcast"
    payload = {"message": message}
    headers = {"Content-Type": "application/json"}
    print(requests.post(url, json=payload, headers=headers))

def send_users_to_server():
    url = f"{FLASK_SERVER_URL}/update_users"
    users = [thread.person_name for thread in threads if hasattr(thread, 'person_name')]
    payload = {"users": users}
    headers = {"Content-Type": "application/json"}
    requests.post(url, json=payload, headers=headers)

def add_message_to_chatlog(message, person_name):
    current_time = time.strftime("%I:%M%p")
    thing_to_print = f"{current_time} {person_name}: {message}"
    chat_log.append(f"{thing_to_print}")
    print(thing_to_print)
    send_message_to_server(thing_to_print)
    send_users_to_server()

def get_person_name():
    existing_names = [thread.person_name for thread in threads if hasattr(thread, 'person_name')]
    #print(f"Existing names: {existing_names}")
    system_prompt = f"You help people find a username for an IRC channel.  You respond with just the name, no spaces, no other text.  You can not choose any of these names: {existing_names}.  Names should generally be all lowercase but you can deviate from this."
    user_prompt = "What is my name?"
    name = extract_just_response(send_prompt_to_ollama(system_prompt, user_prompt))
    #print(f"Your name is {name}.")
    return name

if __name__ == "__main__":
    for i in range(4):
        chat_thread_starter()

    joiner_thread_starter()

    leaver_thread_starter()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping threads and exiting...")
