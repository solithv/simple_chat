import argparse
import os

from dotenv import load_dotenv

load_dotenv()
parser = argparse.ArgumentParser()

parser.add_argument(
    "-p", "--port", default=os.getenv("PORT", 5000), type=int, help="server port"
)
parser.add_argument("-d", "--debug", action="store_true")

args = parser.parse_args()
