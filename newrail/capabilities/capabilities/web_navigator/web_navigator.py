import asyncio
import json
from typing import Dict, List, Optional, Union
import time
import random
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from playwright.async_api import async_playwright, ElementHandle

from newrail.agent.utils.mockeds.mocked_capability import MockedCapability
from newrail.capabilities.capability import Capability
from newrail.capabilities.utils.decorators import (
    action_decorator,
    action_with_summary,
    context_decorator,
)
from newrail.config.config import Config


import difflib


def get_different_sentences(str1, str2):
    # Split the strings into sentences
    sentences1 = str1.split(".")
    sentences2 = str2.split(".")

    # Create a Differ object
    differ = difflib.Differ()

    # Compute the difference between the two lists of sentences
    diff = list(differ.compare(sentences1, sentences2))

    # Filter the list to include only sentences that are in str1 but not str2, or vice versa
    different_sentences = [
        d[2:] for d in diff if d.startswith("- ") or d.startswith("+ ")
    ]

    return different_sentences


class WebNavigator(Capability):
    """
    Web scrape the web, performing actions such as: search relevant links on google, navigating to urls, click buttons or fill forms.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_text = ""
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self.start_browser())
        self.last_buttons: Dict[str, ElementHandle] = {}
        self.last_forms: List[
            Dict[str, Union[Dict[str, ElementHandle], ElementHandle]]
        ] = []

    async def start_browser(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=Config().headless_web_browser
        )
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        await self.page.set_viewport_size({"width": 1280, "height": 800})
        await self.page.goto("https://www.google.com/")

    @context_decorator
    def get_current_url(self) -> str:
        """Get the current URL of the page."""

        return f"Current web page: {self.page.url}"

    @action_decorator
    def google_search(self, query: str) -> str | list[str]:
        """Perform a Google search and retrieve the URL links as search results. !!Warning!! This function only returns the URL links not the info contained there, please use navigate_to_url next to navigate to the desired URL and retrieve the information you need.
        Args:
            query (str): The search query.
        """

        try:
            num_results = 8  # TODO: Make this configurable without exposing to agent.
            # Get the Google API key and Custom Search Engine ID from the config file
            api_key = Config().google_api_key
            custom_search_engine_id = Config().custom_search_engine_id

            # Initialize the Custom Search API service
            service = build("customsearch", "v1", developerKey=api_key)

            # Send the search query and retrieve the results
            result = (
                service.cse()
                .list(q=query, cx=custom_search_engine_id, num=int(num_results))
                .execute()
            )

            # Extract the search result items from the response
            search_results = result.get("items", [])

            # Create a list of only the URLs from the search results
            search_results_links = [item["link"] for item in search_results]

        except HttpError as e:
            # Handle errors in the API call
            error_details = json.loads(e.content.decode())

            # Check if the error is related to an invalid or missing API key
            if error_details.get("error", {}).get(
                "code"
            ) == 403 and "invalid API key" in error_details.get("error", {}).get(
                "message", ""
            ):
                return "Error: The provided Google API key is invalid or missing."
            else:
                return f"Error: {e}"
        # Return the list of search result URLs
        return self._safe_google_results(search_results_links)

    def _safe_google_results(self, results: str | list) -> str:
        """
            Return the results of a google search in a safe format.
        Args:
            results (str | list): The search results.
        """

        if isinstance(results, list):
            safe_message = json.dumps(results)
        else:
            safe_message = results.encode("utf-8", "ignore").decode("utf-8")
        result = f"These are the relevant links obtained from the google search: {safe_message}"
        if safe_message:
            result += "\nNow you can use the navigate_to_url action to navigate to any of these links to retrieve the information you need."
        return result

    @action_with_summary(has_question=True)
    def navigate_to_url(self, url: str, question: Optional[str] = None) -> str:
        """Navigates to the specified URL and retrieves the pertinent information from the webpage associated with the question.

        Args:
            url (str): The url to navigate to.
            question (Optional[str]): The question to look up on the target webpage, often used for web scraping or obtaining parsed information.
        """

        self.set_question(question=question)
        return self.loop.run_until_complete(self._navigate_to_url(url=url))

    async def _navigate_to_url(self, url):
        """Navigates to the specified URL and retrieves the content of the page.

        Args:
            url (str): The url to navigate to.
        """

        result = await self.page.goto(url, wait_until="load")
        if not result:
            return f"Failed to navigate to {url}"

        return f"Successfully navigated to {url}, content:\n{await self._get_text()}"

    async def _get_text(self):
        """Get the text of current page.

        Args:
            No arguments.
        """

        return await self.page.inner_text("body")

    @action_decorator
    def get_buttons(self):
        """Get all clickable buttons on the page.

        Args:
            No arguments.
        """

        buttons = self.loop.run_until_complete(self._get_buttons())
        if not buttons:
            buttons = "No buttons found"
        return buttons

    @action_decorator
    def get_forms(self):
        """Get all input forms on the page.

        Args:
            No arguments.
        """

        input_forms = self.loop.run_until_complete(self._get_forms())
        if not input_forms:
            input_forms = "No input forms found"
        return input_forms

    async def _get_buttons(self):
        """Get all clickable buttons on the page."""

        self.last_buttons = {}
        clickable_elements = await self.page.query_selector_all(
            'a, button, div[role="button"], span[role="button"]'
        )
        for element in clickable_elements:
            try:
                text_content = await element.text_content()
                if await element.is_visible() and text_content:
                    cleaned_text = text_content.strip().replace("\n", " ")
                    if cleaned_text:
                        self.last_buttons[cleaned_text] = element
            except Exception:
                continue
        return list(self.last_buttons.keys())

    async def _get_forms(self):
        """Get all input forms on the page."""

        form_elements = await self.page.query_selector_all("form")
        input_selectors = ["input", "textarea", "select"]

        forms = []
        self.last_forms = []
        for form in form_elements:
            form_dict = {}
            submit_button = None
            for selector in input_selectors:
                input_elements = await form.query_selector_all(selector)
                for element in input_elements:
                    try:
                        name = await element.get_attribute(
                            "name"
                        ) or await element.get_attribute("id")
                        placeholder = await element.get_attribute(
                            "placeholder"
                        ) or await element.get_attribute("aria-label")
                        label = name or placeholder
                        input_type = await element.get_attribute("type")
                        if input_type == "submit":
                            submit_button = element
                        elif label:
                            cleaned_label = label.strip().replace("\n", " ")
                            if cleaned_label and await element.is_visible():
                                form_dict[cleaned_label] = element
                    except Exception:
                        continue
            if form_dict:
                self.last_forms.append(
                    {"fields": form_dict, "submit_button": submit_button}
                )
                forms.append(form_dict.keys())

        # Handle inputs outside form elements
        for selector in input_selectors:
            input_elements = await self.page.query_selector_all(selector)
            for element in input_elements:
                try:
                    name = await element.get_attribute(
                        "name"
                    ) or await element.get_attribute("id")
                    placeholder = await element.get_attribute(
                        "placeholder"
                    ) or await element.get_attribute("aria-label")
                    label = name or placeholder
                    if label:
                        cleaned_label = label.strip().replace("\n", " ")
                        if cleaned_label and await element.is_visible():
                            self.last_forms.append(
                                {
                                    "fields": {cleaned_label: element},
                                    "submit_button": None,
                                }
                            )
                            forms.append({cleaned_label: element})
                except Exception:
                    continue

        return "\n - ".join(f"{i}: {list(form)}" for i, form in enumerate(forms))

    @action_decorator
    def fill_form(self, index, form_data):
        """Fill a form with the given data using the index and the required form data obtained from calling get_forms. Remember to call get_forms before calling this action.

        Args:
            index (int): The index of the form to fill.
            form_data (Dict[str, str]): A dictionary of field names and their values.
        """

        return self.loop.run_until_complete(self._fill_form(index, form_data))

    async def _fill_form(self, index, form_data):
        """Fill a form with the given data using the index and the required form data obtained from the content of the page.

        Args:
            index (int): The index of the form to fill.
            form_data (Dict[str, str]): A dictionary of field names and their values.
        """

        form = self.last_forms[index]
        for field, value in form_data.items():
            if field in form["fields"]:
                for character in value:
                    await form["fields"][field].type(character)
                    await asyncio.sleep(random.uniform(0.1, 0.3))
            else:
                return (
                    f"Form submission failed: Field {field} not found in form {index}"
                )
        current_url = self.page.url

        previous_text = await self._get_text()
        submit_button = form.get("submit_button")
        if submit_button:
            async with self.page.expect_navigation(wait_until="load", timeout=2000):
                await submit_button.click()
            new_url = self.page.url
            new_text = await self._get_text()
            if new_url != current_url:
                return f"Form submitted. The page has navigated to {new_url} with content:\n{new_text}"
            else:
                return f"Difference between new text and old text: {get_different_sentences(new_text, previous_text)}."
        else:
            return "Form has been filled the button to submit it can be called now, call get_buttons to see the available buttons."

    @action_decorator
    def click_button(self, button_str):
        """Click the button identified by button_str, obtained from calling get_buttons. Remember to call get_forms before calling this action.
        Args:
            button_str (str): The text of the button to click.
        """

        return self.loop.run_until_complete(self._click_button(button_str))

    async def _click_button(self, button_str):
        """Click the button identified by button_str, obtained from calling get_buttons
        Args:
            button_str (str): The text of the button to click.
        """

        button_element = self.last_buttons.get(button_str)
        if not button_element:
            return f"Failed to click button {button_str}, button not found!"
        current_url = self.page.url
        async with self.page.expect_navigation(
            wait_until="domcontentloaded", timeout=2000
        ) and self.page.expect_navigation(wait_until="load", timeout=2000):
            await button_element.click()
        await self.page.reload()
        new_url = self.page.url
        result = f"Successfully clicked button '{button_str}'"
        if current_url == new_url:
            return result
        return (
            result
            + f" after clicking the button, the url changed to: '{new_url}'. New page content:\n{await self._get_text()}"
        )

    def close(self):
        self.loop.run_until_complete(self.browser.close())
        self.loop.run_until_complete(self.playwright.stop())


def main():
    web_navigator = WebNavigator(
        **MockedCapability.initialize(plugin_name="test_plugin")
    )
    print("Google search result for: 'test'", web_navigator.google_search("test"))
    print(
        web_navigator.navigate_to_url(
            url="https://github.com/Significant-Gravitas/Auto-GPT",
            question="What is this?",
        )
    )
    sign_up_button = "Sign up"
    print("Clicking button sign up result", web_navigator.click_button(sign_up_button))
    sign_in_button = "Sign in →"
    print("Clicking button sign in result", web_navigator.click_button(sign_in_button))
    print(
        "input form:",
        web_navigator.fill_form(
            0, {"login": "test@example.com", "password": "password"}
        ),
    )
    time.sleep(10)


if __name__ == "__main__":
    main()
