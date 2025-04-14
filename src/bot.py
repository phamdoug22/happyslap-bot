from playwright.sync_api import sync_playwright
import time
import random
from pathlib import Path
import re
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

class HappySlapBot:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.email = os.getenv('EMAIL')
        self.password = os.getenv('PASSWORD')
        self.last_login_time = None
        self.LOGIN_INTERVAL = timedelta(hours=8)
        
        if not self.email or not self.password:
            raise ValueError("EMAIL and PASSWORD must be set in .env file")

    def start(self):
        playwright = sync_playwright().start()
        
        self.browser = playwright.chromium.launch(
            channel='chrome',
            headless=False,
            args=['--disable-web-security']
        )

        self.login()
        
        while True:
            try:
                if self.should_refresh_login():
                    print("Session refresh needed - logging in again...")
                    self.login()
                
                self.select_and_host_trivia_game()
                self.announce_game()
                time.sleep(60)
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(5)

    def should_refresh_login(self):
        if not self.last_login_time:
            return True
        return datetime.now() - self.last_login_time >= self.LOGIN_INTERVAL

    def login(self):
        print("Resetting context and logging in...")

        # Clean up previous context/page
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()

        self.context = self.browser.new_context()  # <- Fresh browser context
        self.page = self.context.new_page()

        self.page.goto("https://happyslap.tv/login")
        self.page.wait_for_selector("input[placeholder='Username or Email']")
        
        print(f"Using email: {self.email}")
        self.page.fill("input[placeholder='Username or Email']", self.email)
        self.page.fill("input[placeholder='Password']", self.password)
        self.page.click("button:has-text('Login')")

        try:
            self.page.wait_for_url("https://happyslap.tv/host", timeout=5000)
            print("Login successful!")
            self.last_login_time = datetime.now()
        except Exception as e:
            print("Login failed!")
            raise e

    def inject_countdown_overlay(self):
        self.page.evaluate("""() => {
            if (!document.getElementById('countdown-overlay')) {
                const overlay = document.createElement('div');
                overlay.id = 'countdown-overlay';
                overlay.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: rgba(0, 0, 0, 0.8);
                    color: white;
                    padding: 15px;
                    border-radius: 10px;
                    font-size: 24px;
                    z-index: 9999;
                `;
                document.body.appendChild(overlay);
            }
        }""")

    def update_countdown(self, text):
        self.page.evaluate(f"""text => {{
            document.getElementById('countdown-overlay').innerText = text;
        }}""", text)

    def select_and_host_trivia_game(self):
        print("Finding a trivia game...")
        self.page.goto("https://happyslap.tv/host/discover")
        self.page.wait_for_load_state('networkidle')

        search_input = self.page.wait_for_selector('input[class*="font-roboto"][class*="rounded-lg"]')
        print("Found search input, filling with 'Trivia'...")
        search_input.fill("Trivia")

        print("Searching for Trivia games...")
        self.page.wait_for_timeout(1500)

        self.page.wait_for_selector('[class*="grid-cols-3"]')
        game_cards = self.page.query_selector_all('[class*="grid-cols-3"] > div')
        if not game_cards:
            raise Exception("No trivia games found")

        random.choice(game_cards).click()

        host_button = self.page.wait_for_selector('button:has-text("Host Game")')
        host_button.click()

        self.page.wait_for_url(re.compile(r"https://happyslap.tv/trivia/host/[A-Z0-9]{5}/.*"))
        self.page.wait_for_load_state('networkidle')
        time.sleep(2)

        url_parts = self.page.url.split('/')
        join_code_index = url_parts.index('host') + 1
        if join_code_index < len(url_parts):
            self.current_join_code = url_parts[join_code_index]
            print(f"Join Code: {self.current_join_code}")
        else:
            join_code_element = self.page.query_selector('h1.text-hs-green.font-londrina')
            if join_code_element:
                self.current_join_code = join_code_element.inner_text()
                print(f"Join Code: {self.current_join_code}")

        self.inject_countdown_overlay()

        initial_player_count = len(self.page.query_selector_all('[class*="grid-cols-4"] > div'))
        if initial_player_count > 0:
            print("Waiting for player list to reset...")
            while len(self.page.query_selector_all('[class*="grid-cols-4"] > div')) > 0:
                time.sleep(0.5)

        lobby_start_time = time.time()
        player_joined = False
        game_started = False
        print("Lobby ready - waiting for players...")

        while True:
            restart_button = self.page.query_selector('text="Restart Game"')
            if restart_button:
                print("Game ended - showing scores...")
                for i in range(20, 0, -1):
                    self.update_countdown(f'Finding new game in: {i}s')
                    time.sleep(1)
                return self.select_and_host_trivia_game()

            if game_started:
                time.sleep(1)
                continue

            player_count = len(self.page.query_selector_all('[class*="grid-cols-4"] > div'))
            if time.time() - lobby_start_time > 600 and player_count == 0:
                print("Lobby timeout - no players for 10 minutes")
                for i in range(10, 0, -1):
                    self.update_countdown(f'Empty lobby - Finding new game in: {i}s')
                    time.sleep(1)
                return self.select_and_host_trivia_game()

            if player_count > 0 and not player_joined:
                print(f"First player joined! Starting countdown...")
                player_joined = True

                for i in range(50, 0, -1):
                    self.update_countdown(f'Starting in: {i}s')
                    time.sleep(1)

                play_button = self.page.query_selector('[class*="generic-button"][class*="bg-hs-green"]')
                if play_button:
                    self.update_countdown('Game in progress...')
                    play_button.click()
                    game_started = True

            time.sleep(1)

    def announce_game(self):
        if hasattr(self, 'current_join_code'):
            print(f"""
New game started!
Join code: {self.current_join_code}
HappySlap.tv - The best place for party games!
            """)

if __name__ == "__main__":
    bot = HappySlapBot()
    bot.start()
