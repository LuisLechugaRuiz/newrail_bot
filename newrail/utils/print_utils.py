from colorama import Style
import random
import time

import newrail.capabilities.utils.speak as speak


def print_to_console(
    title,
    title_color,
    content,
    speak_text=False,
    min_typing_speed=0.05,
    max_typing_speed=0.01,
):
    if speak_text:
        speak.say_text(f"{title}. {content}")
    print(title_color + title + " " + Style.RESET_ALL, end="")
    if content:
        if isinstance(content, list):
            content = "\n".join(content)
        lines = content.split("\n")
        for line in lines:
            words = line.split()
            for i, word in enumerate(words):
                print(word, end="", flush=True)
                if i < len(words) - 1:
                    print(" ", end="", flush=True)
                typing_speed = random.uniform(min_typing_speed, max_typing_speed)
                time.sleep(typing_speed)
                # type faster after each word
                min_typing_speed = min_typing_speed * 0.95
                max_typing_speed = max_typing_speed * 0.95
            print()  # New line after each line


def indent(text, spaces=4):
    indentation = " " * spaces
    return "\n".join(indentation + line for line in text.split("\n"))
