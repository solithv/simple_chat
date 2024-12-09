import argparse
import os

from dotenv import load_dotenv

load_dotenv()
parser = argparse.ArgumentParser()

parser.add_argument("--host", action="store_true", help="host server")
parser.add_argument(
    "-p", "--port", default=os.getenv("PORT"), type=int, help="server port"
)
parser.add_argument("-d", "--debug", action="store_true", help="flask debug mode")

args = parser.parse_args()
