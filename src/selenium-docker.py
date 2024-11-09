import os
import json
import re
import time
import logging
from urllib import request
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from discord_webhook import DiscordWebhook
import dotenv

dotenv.load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
USERNAME = os.environ.get("USERNAME")
PASSWORD = os.environ.get("PASSWORD")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
ROLE_ID = os.environ.get("ROLE_ID")
SERVER_ID = os.environ.get("SERVER_ID")
BACKUP_TIMER = int(os.environ.get("BACKUP_TIMER")) * 3600
CONFIG_TIMER_MULTIPLE_PLAYER = (
    float(os.environ.get("CONFIG_TIMER_MULTIPLE_PLAYER")) * 60
)
CONFIG_TIMER_SINGLE_PLAYER = float(os.environ.get("CONFIG_TIMER_SINGLE_PLAYER")) * 60
CONFIG_TIMER_NO_PLAYER = float(os.environ.get("CONFIG_TIMER_NO_PLAYER")) * 60
GAME = os.environ.get("GAME", "scum")
BASE_URL = os.environ.get("BASE_URL", "https://www.g-portal.com/en")
BACKUP_URL = os.environ.get(
    "BACKUP_URL",
    f"https://www.g-portal.com/eur/server/{GAME}/{SERVER_ID}/system/backup",
)
QUERY_URL = os.environ.get(
    "QUERY_URL", f"https://api.g-portal.com/gameserver/query/{SERVER_ID}"
)
SELENIUM_URL = os.environ.get("SELENIUM_URL", "localhost")
SELENIUM_PORT = os.environ.get("SELENIUM_PORT", "4444")
# Check required environment variables
required_env_vars = ["USERNAME", "PASSWORD", "WEBHOOK_URL", "ROLE_ID", "SERVER_ID"]
missing_vars = [var for var in required_env_vars if globals()[var] is None]
if missing_vars:
    logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
    exit(1)


# You can set DO_BACKUP via environment variable or default to False
DO_BACKUP = os.environ.get("DO_BACKUP", "False").lower() in ("true", "1", "yes")


def backup_server(browser: webdriver.Remote):
    """
    Automate the backup process using Selenium with Selenium Hub.
    """
    logger.info("Starting backup process")

    # Choose the browser to use (default to Firefox)
    wait = WebDriverWait(browser, 10)
    try:

        # Navigate to the backup page
        browser.get(BACKUP_URL)

        # Click the backup button
        backup_button = wait.until(EC.element_to_be_clickable((By.ID, "make_backup")))
        backup_button.click()

        # Wait for div containing the confirmation message class dialog__actions
        confirm_div = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "dialog__actions"))
        )

        # Click the confirm button /div/button[1]
        confirm_button = confirm_div.find_elements(By.TAG_NAME, "button")[1]
        confirm_button.click()
        logger.info("Backup initiated successfully")
        wait.until(
            EC.element_to_be_clickable(
                (By.CLASS_NAME, "notification notification--success")
            )
        )
        logger.info("Backup completed successfully")
    except Exception as e:
        logger.error(f"An error occurred during backup: {e}")
    finally:
        pass


def get_server_status():
    """
    Get the server status from the API.
    """
    try:
        with request.urlopen(QUERY_URL) as response:
            data = response.read()
            result = json.loads(data)
        return result
    except Exception as e:
        logger.error(f"An error occurred while fetching server status: {e}")
        return None


def notify_discord_half_time(timestamp: float, player_count: int):
    message = (
        f"Server will be backed up <t:{int(timestamp)}:R>, please log off.\n"
        f"There are currently {player_count} player(s) online."
    )
    webhook = DiscordWebhook(url=WEBHOOK_URL, content=message)
    try:
        response = webhook.execute()
        if response.status_code == 200:
            logger.info("Notification sent to Discord")
        else:
            logger.error(
                f"Failed to send notification to Discord: {response.status_code}"
            )
    except Exception as e:
        logger.error(f"An error occurred while sending Discord notification: {e}")


def notify_discord(player_count: int):
    """
    Send a notification to Discord about the pending backup.
    """
    if player_count == 0:
        if DO_BACKUP:
            timer = CONFIG_TIMER_NO_PLAYER
            logger.info("No players online, starting backup")
        else:
            logger.info("Backup disabled")
            timer = 0
    elif player_count > 0:
        logger.info("Players online, notifying Discord about pending backup")
        if player_count == 1:
            timer = CONFIG_TIMER_SINGLE_PLAYER
        else:
            timer = CONFIG_TIMER_MULTIPLE_PLAYER

    if player_count > 0 or DO_BACKUP:
        timestamp = float(time.time() + timer)
        message = (
            f"<@&{ROLE_ID}>\n"
            f"Server will be backed up <t:{int(timestamp)}:R>, please log off.\n"
            f"There are currently {player_count} player(s) online."
        )
        webhook = DiscordWebhook(url=WEBHOOK_URL, content=message)
        try:
            response = webhook.execute()
            if response.status_code == 200:
                logger.info("Notification sent to Discord")
            else:
                logger.error(
                    f"Failed to send notification to Discord: {response.status_code}"
                )
        except Exception as e:
            logger.error(f"An error occurred while sending Discord notification: {e}")

    return DO_BACKUP, timer, timestamp


def notify_backup_complete(next_backup: float, success: bool = True):
    """
    Send a notification to Discord about the backup completion.
    """
    next_backup_time = int(float(time.time()) + float(next_backup))
    if not success:
        message = f"<@&{ROLE_ID}>\nBackup failed. **Next backup:** <t:{int(next_backup_time)}:R>."
    elif success:
        message = f"<@&{ROLE_ID}>\nBackup completed successfully. **Next backup:** <t:{int(next_backup_time)}:R>.\n(Note: The backup timer may vary based on player count)"
    else:
        message = f"<@&{ROLE_ID}>\n Unknown error occurred. **Next backup:** <t:{int(next_backup_time)}:R>."
    webhook = DiscordWebhook(url=WEBHOOK_URL, content=message)
    try:
        response = webhook.execute()
        if response.status_code == 200:
            logger.info("Backup completion notification sent to Discord")
        else:
            logger.error(
                f"Failed to send backup completion notification to Discord: {response.status_code}"
            )
    except Exception as e:
        logger.error(
            f"An error occurred while sending backup completion notification: {e}"
        )


def login(browser: webdriver.Remote):
    # Open the base URL
    browser.get(BASE_URL)
    browser.add_cookie(
        {
            "name": "cookiefirst-consent",
            "value": json.dumps(
                {
                    "necessary": True,
                    "performance": False,
                    "functional": True,
                    "advertising": False,
                    "timestamp": time.time(),
                    "type": "category",
                    "version": "10f415a9-8c26-4538-8cbf-5b14f58a1ae2",
                }
            ),
        }
    )
    browser.refresh()
    wait = WebDriverWait(browser, 10)

    # Click the login button
    login_button = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Login']"))
    )
    login_button.click()

    # Enter username
    username_input = wait.until(EC.visibility_of_element_located((By.ID, "username")))
    username_input.send_keys(USERNAME)

    # Enter password
    password_input = browser.find_element(By.ID, "password")
    password_input.send_keys(PASSWORD)

    # Click the login button
    login_submit = browser.find_element(By.NAME, "login")
    login_submit.click()
    return browser


def main():
    # test_selenium_server_available()
    logger = logging.getLogger(__name__)
    logger.debug("Starting Selenium Docker script")
    # Print all environment variables

    logger.info("Environment variables:")
    for key, value in os.environ.items():
        if key in ["PASSWORD", "WEBHOOK_URL"]:
            value = "*" * len(value)
        logger.info(f"{key}: {value}")
    options = FirefoxOptions()
    options.set_capability("pageLoadStrategy", "eager")

    # browser.get(BASE_URL)
    while True:
        server_status = get_server_status()
        if server_status is None:
            logger.error("Unable to retrieve server status, aborting")
            return
        browser = None
        while browser is None:
            try:
                browser = webdriver.Remote(
                    command_executor=f"http://{SELENIUM_URL}:{SELENIUM_PORT}/wd/hub",
                    options=options,
                )
                sessionID = browser.session_id
            except Exception as e:
                logger.error(f"Error connecting to Selenium server: {e}")
                time.sleep(5)

        if not browser:
            logger.error("Unable to connect to Selenium server, aborting")
            return
        player_count = server_status.get("currentPlayers", 0)
        logger.info(f"Players online: {player_count}")
        backup, timer, timestamp = notify_discord(player_count=player_count)
        logger.info(f"Waiting for {timer} seconds before initiating backup")
        time.sleep(timer * 0.75)
        server_status = get_server_status()
        player_count = server_status.get("currentPlayers", 0)
        notify_discord_half_time(timestamp, player_count)
        browser = login(browser)
        time_left = timestamp - time.time()
        if time_left > 0:
            time.sleep(time_left)
        else:
            logger.info("Backup initiated")
        if backup:
            try:
                backup_server(browser)
                notify_backup_complete(BACKUP_TIMER, True)
            except Exception as e:
                logger.error(f"An error occurred during backup: {e}")
                notify_backup_complete(BACKUP_TIMER, False)

        logger.info(f"Waiting for {BACKUP_TIMER} seconds before checking again")
        browser.close()
        browser.quit()
        time.sleep(BACKUP_TIMER)


if __name__ == "__main__":
    main()
