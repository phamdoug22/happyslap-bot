# HappySlap Stream Bot

A Python bot for HappySlap.tv that:

- Automatically logs into HappySlap.tv
- Fetches available trivia games
- Selects and hosts random games
- Manages game sessions via WebSocket

## Setup

1. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
```

2. Activate the virtual environment:

   - Windows:

   ```bash
   .venv\Scripts\activate
   ```

   - Mac/Linux:

   ```bash
   source .venv/bin/activate
   ```

3. Install required packages:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your credentials:

```bash
EMAIL=your_email@example.com
PASSWORD=your_password
```

5. Start the bot:

```bash
python3 src/bot.py
```

## Project Structure

- `src/bot.py` - Main bot implementation with browser automation and WebSocket handling
- `src/config.py` - Configuration settings for login credentials
