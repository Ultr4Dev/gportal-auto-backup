# Automated Game Server Backup with Notifications
> This tool is mainly used  by me to backup a scum server.
## Overview

This project is a Python-based application designed to automate backups of game servers hosted on G-Portal. The tool uses Selenium for web automation to initiate backups and integrates with Discord for notifications about backup statuses.

## Features

- Automates backup processes using Selenium WebDriver.
- Notifies users on Discord when backups are about to start, are in progress, and are completed.
- Configurable timers based on player count to ensure minimal disruption.
- Supports multiple browsers (Firefox, Chrome, Edge) through Selenium.
- Containerized using Docker for easy deployment.

## Prerequisites

- Docker and Docker Compose
- Environment file (.env) with the required credentials and configurations.

I suggest creating a separate account on Gportal and give it guest access

## Environment Variables

Create a `.env` file and set the following:

```ini
# G-Portal Credentials
USERNAME="your_username" # Your Gportal
PASSWORD="your_password" # Your password

# Server Configuration (G-Portal)
GAME="GAME" # Set to the game example: scum
SERVER_ID="your_server_id" # found in the url when in the server overview
BASE_URL="https://www.g-portal.com/en"
BACKUP_URL="https://www.g-portal.com/eur/server/${GAME}/${SERVER_ID}/system/backup" 
QUERY_URL="https://api.g-portal.com/gameserver/query/${SERVER_ID}"

# Backup Control (Timer in hours)
BACKUP_TIMER=2
DO_BACKUP=True

# Discord Configuration
WEBHOOK_URL="your_webhook_url"
# Role ID to mention
ROLE_ID="your_role_id"

# Backup Timers (in minutes)
CONFIG_TIMER_MULTIPLE_PLAYER=30
CONFIG_TIMER_SINGLE_PLAYER=20
CONFIG_TIMER_NO_PLAYER=5

```

## Setup and Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Ultr4Dev/gportal-auto-backup.git
   cd gportal-auto-backup
   ```

2. Build and run the Docker container:
   ```bash
   docker-compose up --build
   ```

## Docker Configuration

### `docker-compose.yml`

The `docker-compose.yml` file sets up the `app` service to run the Python script and the `selenium-hub` service as the headless browser environment:

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: selenium_backup_app
    restart: always
    environment:
      - USERNAME=${USERNAME}
      - PASSWORD=${PASSWORD}
      - WEBHOOK_URL=${WEBHOOK_URL}
      - ROLE_ID=${ROLE_ID}
      - SERVER_ID=${SERVER_ID}
      - DO_BACKUP=${DO_BACKUP}
      - BACKUP_TIMER=${BACKUP_TIMER}
      - CONFIG_TIMER_MULTIPLE_PLAYER=${CONFIG_TIMER_MULTIPLE_PLAYER}
      - CONFIG_TIMER_SINGLE_PLAYER=${CONFIG_TIMER_SINGLE_PLAYER}
      - CONFIG_TIMER_NO_PLAYER=${CONFIG_TIMER_NO_PLAYER}
      - BROWSER=firefox
    volumes:
      - /dev/shm:/dev/shm
    network_mode: "bridge"
    depends_on:
      - selenium-hub
    command: ["python3", "selenium-docker.py"]

  selenium-hub:
    image: selenium/standalone-firefox:latest
    container_name: selenium_hub
    ports:
      - "4444:4444"
    shm_size: '2g'
```

## How It Works

1. The application periodically checks the server status using G-Portal's API.
2. It sends notifications to a Discord channel when the server will be backed up, based on current player counts.
3. If `DO_BACKUP` is set to `true`, the script triggers the backup process using Selenium.
4. Discord notifications are sent when backups are completed, with timestamps for the next scheduled backup.

## Logging

The application logs key events and errors for debugging and tracking purposes. These logs are outputted to the console.

## Customization

- **Browser**: Change the `BROWSER` environment variable to `chrome` or `edge` to use a different headless browser.
- **Timers**: Adjust backup intervals and player-based timers through the `.env` configuration.

## License

This project is open-source and licensed under the MIT License. Feel free to contribute, suggest improvements, or report issues.

---

Feel free to customize or expand on this README as needed for your specific repository.
