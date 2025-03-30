# HappySlap Stream Bot

This is a standalone TypeScript bot for HappySlap.tv that:
- Fetches available games
- Selects one at random
- Hosts the game via WebSocket
- Can send join info to Streamer.bot or other systems

## Setup

1. Clone the repo
2. Run:

```bash
npm install
cp .env.example .env
# Fill out your API_BASE_URL and token in .env
```

3. Start the bot:

```bash
npm start
```

## Structure

- `src/getGames.ts` — Fetches game list from API
- `src/socket.ts` — Emits createParty to HappySlap server
- `src/index.ts` — Main entry point
- `.env` — Contains your API credentials and config
