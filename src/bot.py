from playwright.sync_api import sync_playwright
import time
import random
import requests
import socketio
from config import EMAIL, PASSWORD

class HappySlapBot:
    def __init__(self):
        self.browser = None
        self.page = None
        self.socket = None
        
    def start(self):
        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(headless=False)
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
        print("🔑 Attempting login...")
        self.page.goto("https://happyslap.tv/login")
        
        # Wait for login form to load
        self.page.wait_for_selector("input[placeholder='Username or Email']")
        
        # Fill login form
        print(f"📧 Using email: {EMAIL}")
        self.page.fill("input[placeholder='Username or Email']", EMAIL)
        self.page.fill("input[placeholder='Password']", PASSWORD)
        
        # Click login button
        self.page.click("button:has-text('Login')")
        
        try:
            self.page.wait_for_url("https://happyslap.tv/host", timeout=5000)
            print("✅ Login successful!")
            
            # Get access token after login
            self.access_token = self.page.evaluate("localStorage.getItem('accessToken')")
            
        except Exception as e:
            print("❌ Login failed!")
            raise e

    def fetch_trivia_games(self):
        """Fetch trivia games using the API directly"""
        try:
            print(f"🔍 Using access token: {self.access_token[:20]}...")
            
            response = requests.get(
                "https://api.happyslap.tv/api/game/public",  # Fixed URL
                params={
                    "game": "trivia",
                    "menu": "official",
                    "search": ""  # Added this from the network request
                },
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Accept": "application/json",
                    "Origin": "https://happyslap.tv",
                    "Referer": "https://happyslap.tv/host/discover"
                }
            )
            print(f"📡 API Status Code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ API Error: {response.text}")
                return []
                
            data = response.json()
            print(f"📦 Found {len(data['games'])} games")
            return data["games"]
            
        except Exception as e:
            print(f"❌ API Error: {str(e)}")
            if 'response' in locals():
                print(f"Response content: {response.text}")
            return []
        
    def connect_socket(self):
        """Connect to HappySlap socket server"""
        print("🔌 Connecting to socket...")
        self.socket = socketio.Client(logger=True, engineio_logger=True)
        
        @self.socket.event
        def connect():
            print("✅ Socket connected!")
            
        @self.socket.event
        def disconnect():
            print("❌ Socket disconnected!")
            
        @self.socket.event
        def connect_error(data):
            print(f"❌ Socket connection error: {data}")
        
        try:
            # Connect with auth token
            self.socket.connect(
                'https://api.happyslap.tv',
                headers={
                    'Authorization': f'Bearer {self.access_token}',
                    'Origin': 'https://happyslap.tv',
                    'Referer': 'https://happyslap.tv/'
                },
                transports=['polling', 'websocket'],
                wait=True
            )
        except Exception as e:
            print(f"❌ Socket connection failed: {str(e)}")
            raise e

    def create_party(self, game):
        """Create a party using socket connection"""
        try:
            print(f"🎲 Creating party for game type: {game['game']}")
            # Use callback to wait for response
            future = self.socket.call('createParty', {'gameType': game['game']})
            print(f"✅ Party created: {future}")
            return future
        except Exception as e:
            print(f"❌ Failed to create party: {str(e)}")
            raise e
        
    def select_and_host_trivia_game(self):
        """Find and host a random trivia game"""
        print("🎲 Finding a trivia game...")
        
        # Get trivia games from API
        games = self.fetch_trivia_games()
        if not games:
            raise Exception("No trivia games found")
            
        # Select random game
        game = random.choice(games)
        print(f"🎮 Selected: {game['title']}")
        
        # Connect socket if needed
        if not self.socket or not self.socket.connected:
            self.connect_socket()
            
        # Clear localStorage items
        self.page.evaluate("""() => {
            if (localStorage.getItem("base") !== null) {
                localStorage.removeItem("base");
            }
            if (localStorage.getItem("trivia") !== null) {
                localStorage.removeItem("trivia");
            }
        }""")
        
        # Create party via socket
        print("🎮 Creating party...")
        party_data = self.create_party(game)
        party_id = party_data['partyId']
        
        # Navigate directly to game URL
        game_url = f"https://happyslap.tv/{game['game']}/host/{party_id}/{game['id']}"
        print(f"🎯 Navigating to {game_url}")
        self.page.goto(game_url)
        
        # Store current game URL
        self.current_game_url = self.page.url
        print(f"🎮 Hosting game at: {self.current_game_url}")
        
        # Make sure we're fully loaded
        self.page.wait_for_load_state('networkidle')

    def announce_game(self):
        if hasattr(self, 'current_game_url'):
            print(f"""
📢 New game started!
🎮 Join us at: {self.current_game_url}
💫 HappySlap.tv - The best place for party games!
            """)

if __name__ == "__main__":
    bot = HappySlapBot()
    bot.start() 