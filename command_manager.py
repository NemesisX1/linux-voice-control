import json
import os.path
import threading
from thefuzz import process

commands = dict()
choices = []


def init():
    global commands, choices
    commands = get_commands_from_file()
    choices = list(commands.keys())
    show_commands()


def get_commands_from_file():
    return json.load(open(os.path.join(os.getcwd(), "lvc-commands.json")))


def launch_if_any(text):
    probability = process.extractOne(text, choices)
    print("probability:", probability)
    if probability and is_text_prediction_applicable(text, probability[0]):
        command = commands[probability[0]]
        threading.Thread(target=lambda: os.system(command)).start()


def is_text_prediction_applicable(text, predicted_text):
    return text.startswith(predicted_text)


def show_commands():
    print(">>> Available Commands")
    for launcher in commands:
        print(launcher, ":", commands[launcher])
    print()
