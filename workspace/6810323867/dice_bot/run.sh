#!/bin/bash

# Install dependencies
pip3 install python-telegram-bot flask requests

# Create database directory
mkdir -p /root/workspace/6810323867/dice_bot

# Run bot
cd /root/workspace/6810323867/dice_bot
python3 main.py
