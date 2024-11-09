import os
import json
import time
import logging
from urllib import request, error
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from discord_webhook import DiscordWebhook
import dotenv

dotenv.load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ROLE_ID = os.getenv("ROLE_ID")
SERVER_ID = os.getenv("SERVER_ID")
DO_BACKUP = os.getenv("DO_BACKUP", "False").lower() in ("true", "1", "yes")
if not DO_BACKUP:
    ROLE_ID = "000000000000000000"
BACKUP_TIMER = float(os.getenv("BACKUP_TIMER", "2")) * 3600
CONFIG_TIMER_MULTIPLE_PLAYER = (
    float(os.getenv("CONFIG_TIMER_MULTIPLE_PLAYER", "30")) * 60
)
CONFIG_TIMER_SINGLE_PLAYER = float(os.getenv("CONFIG_TIMER_SINGLE_PLAYER", "20")) * 60
CONFIG_TIMER_NO_PLAYER = float(os.getenv("CONFIG_TIMER_NO_PLAYER", "5")) * 60
GAME = os.getenv("GAME", "scum")
BASE_URL = os.getenv("BASE_URL", "https://www.g-portal.com/en")
BACKUP_URL = os.getenv(
    "BACKUP_URL",
    f"https://www.g-portal.com/eur/server/{GAME}/{SERVER_ID}/system/backup",
)
QUERY_URL = os.getenv(
    "QUERY_URL", f"https://api.g-portal.com/gameserver/query/{SERVER_ID}"
)
SELENIUM_URL = os.getenv("SELENIUM_URL", "localhost")
SELENIUM_PORT = os.getenv("SELENIUM_PORT", "4444")

# Check for required environment variables
required_env_vars = ["USERNAME", "PASSWORD", "WEBHOOK_URL", "ROLE_ID", "SERVER_ID"]
missing_vars = [var for var in required_env_vars if not globals().get(var)]
if missing_vars:
    logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
    exit(1)


def send_discord_message(message: str):
    """
    Sends a message to Discord via webhook.

    Args:
        message (str): The message content to send.
    """
    try:
        webhook = DiscordWebhook(url=WEBHOOK_URL, content=message)
        response = webhook.execute()
        if response.status_code == 200:
            logger.info("Message sent to Discord")
        else:
            logger.error(f"Failed to send message to Discord: {response.status_code}")
    except Exception as e:
        logger.error(f"An error occurred while sending message to Discord: {e}")


def get_server_status() -> dict[str, int | str]:
    """
    Retrieves the current server status from the API.

    Returns:
        dict: The server status data, or None if an error occurred.
    """
    logger.info("Fetching server status")
    try:
        with request.urlopen(QUERY_URL, timeout=10) as response:
            data = response.read()
            return json.loads(data)
    except error.URLError as e:
        logger.error(f"An error occurred while fetching server status: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching server status: {e}")
    return None


def notify_discord_half_time(timestamp: float, player_count: int):
    """
    Sends a half-time notification to Discord.

    Args:
        timestamp (float): The timestamp when the backup will occur.
        player_count (int): The number of players currently online.
    """
    message = (
        f"Server will be backed up <t:{int(timestamp)}:R>, please log off.\n"
        f"There are currently {player_count} player(s) online."
    )
    send_discord_message(message)


def notify_discord(player_count: int) -> tuple[bool, float, float]:
    """
    Notifies Discord about the upcoming backup and calculates the timer.

    Args:
        player_count (int): The number of players currently online.

    Returns:
        tuple: (do_backup (bool), timer (float), timestamp (float))
    """
    timer = 0
    if player_count == 0 and DO_BACKUP:
        timer = CONFIG_TIMER_NO_PLAYER
        logger.info("No players online, starting backup")
    elif player_count > 0:
        if player_count == 1:
            timer = CONFIG_TIMER_SINGLE_PLAYER
        else:
            timer = CONFIG_TIMER_MULTIPLE_PLAYER
        logger.info("Players online, notifying Discord about pending backup")

    if player_count > 0 or DO_BACKUP:
        timestamp = time.time() + timer
        message = (
            f"<@&{ROLE_ID}>\n"
            f"Server will be backed up <t:{int(timestamp)}:R>, please log off.\n"
            f"There are currently {player_count} player(s) online."
        )
        send_discord_message(message)
    else:
        timestamp = time.time()

    return DO_BACKUP, timer, timestamp


def notify_backup_complete(next_backup: float, success: bool = True) -> None:
    """
    Notifies Discord about the backup completion status.

    Args:
        next_backup (float): The time in seconds until the next backup.
        success (bool): Whether the backup was successful.
    """
    next_backup_time = int(time.time() + next_backup)
    message = (
        f"Backup completed successfully. **Next backup:** <t:{next_backup_time}:R>."
        if success
        else f"Backup failed. **Next backup:** <t:{next_backup_time}:R>."
    )
    send_discord_message(message)


def login(browser: webdriver.Remote) -> webdriver.Remote:
    """
    Logs into the G-Portal website using the provided browser.

    Args:
        browser (webdriver.Remote): The Selenium WebDriver instance.

    Returns:
        webdriver.Remote: The browser instance after login.

    Raises:
        Exception: If login fails.
    """
    try:
        browser.get(BASE_URL)

        # Add the necessary cookies to bypass the consent
        browser.add_cookie(
            {
                "name": "cookiefirst-consent",
                "value": json.dumps(
                    {
                        "necessary": True,
                        "performance": False,
                        "functional": True,
                        "advertising": False,
                        "timestamp": int(time.time()),
                        "type": "category",
                        "version": "10f415a9-8c26-4538-8cbf-5b14f58a1ae2",
                    }
                ),
                "domain": ".g-portal.com",
                "path": "/",
            }
        )
        browser.refresh()
        wait = WebDriverWait(browser, 10)

        # Click on the login button
        login_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Login']"))
        )
        login_button.click()

        # Enter username
        username_input = wait.until(
            EC.visibility_of_element_located((By.ID, "username"))
        )
        username_input.send_keys(USERNAME)

        # Enter password
        password_input = browser.find_element(By.ID, "password")
        password_input.send_keys(PASSWORD)

        # Submit login form
        login_submit = browser.find_element(By.NAME, "login")
        login_submit.click()

        logger.info("Login successful")
        browser.get(BACKUP_URL)
        return browser

    except Exception as e:
        logger.error(f"An error occurred during login: {e}")
        raise


def backup_server(
    browser: webdriver.Remote, fake: bool = False, click_time: float = 0.5
) -> None:
    """
    Initiates a server backup via the web interface.

    Args:
        browser (webdriver.Remote): The Selenium WebDriver instance.
        fake (bool): If True, simulates the backup without actually performing it.
    """
    logger.info("Starting backup process")
    wait = WebDriverWait(browser, 10, poll_frequency=0.1)

    try:
        if browser.current_url != BACKUP_URL:
            browser.get(BACKUP_URL)

        # Wait until the backup button is clickable
        backup_button = wait.until(EC.element_to_be_clickable((By.ID, "make_backup")))
        backup_button.click()

        # Wait until the confirmation dialog appears
        confirm_div = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "dialog__actions"))
        )
        confirm_buttons = confirm_div.find_elements(By.TAG_NAME, "button")
        if len(confirm_buttons) < 2:
            logger.error("Confirmation buttons not found")
            raise Exception("Confirmation buttons not found")

        confirm_button = confirm_buttons[1]  # Assuming the second button is 'Confirm'

        if not fake:
            confirm_button.click()
            logger.info("Backup initiated successfully")

        logger.info("Backup completed successfully")

    except Exception as e:
        logger.error(f"An error occurred during backup: {e}")
        notify_backup_complete(BACKUP_TIMER, success=False)
        raise


def test_selenium_server_available(max_attempts: int = 5, delay: int = 5) -> float:
    """
    Tests if the Selenium server is available.

    Args:
        max_attempts (int): Maximum number of attempts to connect.
        delay (int): Delay in seconds between attempts.

    Returns:
        float: The time taken to establish a connection.

    Raises:
        Exception: If unable to connect to the Selenium server after max_attempts.
    """
    attempts = 0
    while attempts < max_attempts:
        try:
            logger.info(
                f"Connecting to Selenium server at {SELENIUM_URL}:{SELENIUM_PORT}"
            )
            start_time = time.time()
            options = FirefoxOptions()
            options.set_capability("pageLoadStrategy", "normal")
            browser = webdriver.Remote(
                command_executor=f"http://{SELENIUM_URL}:{SELENIUM_PORT}/wd/hub",
                options=options,
            )
            browser.quit()
            end_time = time.time()
            total_time = end_time - start_time
            logger.info("Selenium server is available")
            return total_time
        except Exception as e:
            logger.error(f"Error connecting to Selenium server: {e}")
            attempts += 1
            if attempts >= max_attempts:
                logger.error(
                    "Max attempts reached. Unable to connect to Selenium server."
                )
                raise
            else:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)


def send_misc_message(message: str) -> None:
    """
    Sends a miscellaneous message to Discord.

    Args:
        message (str): The message content to send.
    """
    send_discord_message(message)


def main() -> None:
    login_times = []
    backup_times = []
    total_prepare_time = 120  # Initial estimate of time required to prepare

    logger.debug("Starting backup script")
    logger.info("Environment variables:")
    for key in required_env_vars:
        value = os.getenv(key)
        logger.info(
            f"{key}: {'*' * len(value) if key in ['PASSWORD', 'WEBHOOK_URL'] else value}"
        )

    options = FirefoxOptions()
    options.set_capability("pageLoadStrategy", "normal")

    while True:
        try:
            # Get server status
            server_status = get_server_status()
            if server_status is None:
                logger.error(
                    "Unable to retrieve server status, will retry after delay."
                )
                time.sleep(60)  # Wait 1 minute before retrying
                continue

            # Test Selenium server availability
            selenium_start_time = test_selenium_server_available()

            player_count = server_status.get("currentPlayers", 0)
            logger.info(f"Players online: {player_count}")

            # Notify Discord and get timer
            backup, timer, timestamp = notify_discord(player_count=player_count)
            logger.info(f"Waiting for {timer} seconds before initiating backup")

            # Calculate prepare time based on averages
            avg_login_time = sum(login_times) / len(login_times) if login_times else 0
            avg_backup_time = (
                sum(backup_times) / len(backup_times) if backup_times else 0
            )
            if avg_backup_time == 0:
                avg_backup_time = 120
            if avg_login_time == 0:
                avg_login_time = 120

            total_prepare_time = avg_login_time + avg_backup_time + selenium_start_time

            # Ensure we don't sleep negative time
            sleep_time = max(timer - total_prepare_time, 0)
            logger.info(
                f"Sleeping for {sleep_time} seconds before preparing for backup"
            )
            time.sleep(sleep_time)

            # Re-fetch server status and notify half-time
            server_status = get_server_status()
            player_count = (
                server_status.get("currentPlayers", 0) if server_status else 0
            )
            notify_discord_half_time(timestamp, player_count)

            # Initialize browser and perform login
            browser = webdriver.Remote(
                command_executor=f"http://{SELENIUM_URL}:{SELENIUM_PORT}/wd/hub",
                options=options,
            )
            login_start = time.time()
            browser = login(browser)
            login_end = time.time()
            login_duration = login_end - login_start
            login_times.append(login_duration)
            logger.info(f"Login took {login_duration:.2f} seconds")

            # Wait until the scheduled backup time
            time_left = timestamp - time.time()
            if time_left > 0:
                logger.info(
                    f"Waiting {time_left:.2f} seconds until scheduled backup time"
                )
                time.sleep(time_left)

            # Perform backup
            backup_start = time.time()
            backup_server(browser, fake=not backup)
            backup_end = time.time()
            backup_duration = backup_end - backup_start
            backup_times.append(backup_duration)
            logger.info(f"Backup took {backup_duration:.2f} seconds")

            # Notify backup completion
            notify_backup_complete(BACKUP_TIMER, success=True)

            # Close browser
            browser.quit()

            # Wait until next backup cycle
            logger.info(f"Waiting for {BACKUP_TIMER} seconds before next backup cycle")
            time.sleep(BACKUP_TIMER)

        except Exception as e:
            logger.error(f"An error occurred during main loop: {e}")
            # notify_backup_complete(BACKUP_TIMER, success=False)
            # Ensure browser is closed
            if "browser" in locals():
                try:
                    browser.quit()
                except Exception:
                    pass
            # Wait before retrying
            time.sleep(60)
            continue


if __name__ == "__main__":
    main()
