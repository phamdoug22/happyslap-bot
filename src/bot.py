from playwright.sync_api import sync_playwright
import time
import random
from pathlib import Path
import re
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

class HappySlapBot:
    def __init__(self):
        self.browser = None
        self.page = None
        self.email = os.getenv('EMAIL')
        self.password = os.getenv('PASSWORD')
        
        if not self.email or not self.password:
            raise ValueError("EMAIL and PASSWORD must be set in .env file")
        
    def start(self):
        playwright = sync_playwright().start()
        
        # Launch Chrome with minimal settings
        self.browser = playwright.chromium.launch(
            channel='chrome',  # Use Chrome instead of Chromium
            headless=False,
            args=[
                '--disable-web-security'  # Just this one flag to help with WebSocket
            ]
        )
        
        self.page = self.browser.new_page()
        
        # Login first
        self.login()
        
        while True:
            try:
                self.select_and_host_trivia_game()
                self.announce_game()
                time.sleep(60)
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(5)

    def login(self):
        """Login to HappySlap"""
        print("Attempting login...")
        self.page.goto("https://happyslap.tv/login")
        
        # Wait for login form to load
        self.page.wait_for_selector("input[placeholder='Username or Email']")
        
        # Fill login form
        print(f"Using email: {self.email}")
        self.page.fill("input[placeholder='Username or Email']", self.email)
        self.page.fill("input[placeholder='Password']", self.password)
        
        # Click login button
        self.page.click("button:has-text('Login')")
        
        try:
            self.page.wait_for_url("https://happyslap.tv/host", timeout=5000)
            print("Login successful!")
        except Exception as e:
            print("Login failed!")
            raise e

    def inject_countdown_overlay(self):
        """Helper to inject the countdown overlay"""
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
        """Helper to update countdown text"""
        self.page.evaluate(f"""text => {{
            document.getElementById('countdown-overlay').innerText = text;
        }}""", text)

    def select_and_host_trivia_game(self):
        """Find and host a random trivia game using the UI"""
        print("Finding a trivia game...")
        
        # Navigate to discover page
        self.page.goto("https://happyslap.tv/host/discover")
        self.page.wait_for_load_state('networkidle')
        
        # Find and fill the search bar
        search_input = self.page.wait_for_selector('input[class*="font-roboto"][class*="rounded-lg"]')
        print("Found search input, filling with 'Trivia'...")
        search_input.fill("Trivia")
        print("Searching for Trivia games...")
        
        self.page.wait_for_timeout(1500)  # Wait for debounce
        
        # Wait for and select game card
        self.page.wait_for_selector('[class*="grid-cols-3"]')
        game_cards = self.page.query_selector_all('[class*="grid-cols-3"] > div')
        if not game_cards:
            raise Exception("No trivia games found")
            
        random.choice(game_cards).click()
        
        # Wait for and click Host Game
        host_button = self.page.wait_for_selector('button:has-text("Host Game")')
        host_button.click()
        
        # Wait for lobby and get join code
        self.page.wait_for_url(re.compile(r"https://happyslap.tv/trivia/host/[A-Z0-9]{5}/.*"))
        
        # Wait for lobby to fully load and player list to reset
        self.page.wait_for_load_state('networkidle')
        time.sleep(2)  # Extra wait to ensure player list is fresh
        
        # Get join code from URL first
        url_parts = self.page.url.split('/')
        join_code_index = url_parts.index('host') + 1
        if join_code_index < len(url_parts):
            self.current_join_code = url_parts[join_code_index]
            print(f"Join Code: {self.current_join_code}")
        else:
            # Fallback to looking for code in the page
            join_code_element = self.page.query_selector('h1.text-hs-green.font-londrina')
            if join_code_element:
                self.current_join_code = join_code_element.inner_text()
                print(f"Join Code: {self.current_join_code}")
        
        # Inject overlay if needed
        self.inject_countdown_overlay()
        
        # Make sure player list is empty before starting lobby loop
        initial_player_count = len(self.page.query_selector_all('[class*="grid-cols-4"] > div'))
        if initial_player_count > 0:
            print("Waiting for player list to reset...")
            while len(self.page.query_selector_all('[class*="grid-cols-4"] > div')) > 0:
                time.sleep(0.5)
        
        # Reset lobby state
        lobby_start_time = time.time()
        player_joined = False
        print("Lobby ready - waiting for players...")
        
        while True:
            # Check for game end
            restart_button = self.page.query_selector('text="Restart Game"')
            if restart_button:
                print("Game ended - showing scores...")
                # Countdown before finding new game
                for i in range(20, 0, -1):
                    self.update_countdown(f'Finding new game in: {i}s')
                    time.sleep(1)
                return self.select_and_host_trivia_game()  # Start fresh game
            
            # Check empty lobby timeout
            player_count = len(self.page.query_selector_all('[class*="grid-cols-4"] > div'))
            if time.time() - lobby_start_time > 600 and player_count == 0:  # 10 minutes empty
                print("Lobby timeout - no players for 10 minutes")
                # Countdown before finding new game
                for i in range(10, 0, -1):
                    self.update_countdown(f'Empty lobby - Finding new game in: {i}s')
                    time.sleep(1)
                return self.select_and_host_trivia_game()  # Start fresh game
            
            # Handle player joining
            if player_count > 0 and not player_joined:
                print(f"First player joined! Starting countdown...")
                player_joined = True
                
                # Countdown to game start
                for i in range(50, 0, -1):
                    self.update_countdown(f'Starting in: {i}s')
                    time.sleep(1)
                
                # Start the game
                play_button = self.page.query_selector('[class*="generic-button"][class*="bg-hs-green"]')
                if play_button:
                    self.update_countdown('Game in progress...')
                    play_button.click()
            
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