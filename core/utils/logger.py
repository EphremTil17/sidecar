import logging
import sys, os
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Add custom SUCCESS level
SUCCESS_LEVEL_NUM = 25
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")

def success_ext(self, message, *args, **kws):
    if self.isEnabledFor(SUCCESS_LEVEL_NUM):
        self._log(SUCCESS_LEVEL_NUM, message, args, **kws)

logging.Logger.success = success_ext

class SidecarLogger:
    """
    Robust logging utility for SidecarAI.
    Ensures clear, color-coded output with dynamic level support.
    """
    def __init__(self, name="SidecarAI"):
        self.logger = logging.getLogger(name)
        self.update_level()
        
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            # Match the highly professional: TIME | LEVEL | MESSAGE
            formatter = logging.Formatter(
                f'{Fore.LIGHTBLACK_EX}%(asctime)s | {Style.RESET_ALL}%(levelname)-8s {Fore.LIGHTBLACK_EX}|{Style.RESET_ALL} %(message)s', 
                datefmt='%H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def update_level(self):
        """Re-evaluates the environment to set the logger level."""
        is_debug = os.getenv("SIDECAR_DEBUG", "false").lower() == "true"
        level = logging.DEBUG if is_debug else logging.INFO
        self.logger.setLevel(level)

    def info(self, msg):
        self.logger.info(f"{Fore.BLUE}{msg}{Style.RESET_ALL}")

    def warning(self, msg):
        self.logger.warning(f"{Fore.YELLOW}{msg}{Style.RESET_ALL}")

    def error(self, msg):
        self.logger.error(f"{Fore.RED}{Style.BRIGHT}{msg}{Style.RESET_ALL}")

    def success(self, msg):
        # Uses the custom SUCCESS level we injected
        self.logger.success(f"{Fore.GREEN}{msg}{Style.RESET_ALL}")

    def debug(self, msg):
        self.logger.debug(f"{Fore.LIGHTBLACK_EX}{msg}{Style.RESET_ALL}")

# Singleton instance
logger = SidecarLogger()
