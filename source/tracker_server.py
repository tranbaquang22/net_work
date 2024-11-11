import socket
import threading
import tkinter as tk
from tkinter import scrolledtext
import json
import os
import datetime

# Server storage for client and file piece information
clients = {}
pieces = {}
torrent_file = "info.torrent"

# Function to save piece information to a .torrent file
def save_torrent_info():
    torrent_data = {
        "file_name": "example_file.txt",
        "piece_length": 512000,
        "pieces": [{"id": idx + 1, "piece_index": piece, "clients": pieces[piece]} for idx, piece in enumerate(pieces)]
    }
    with open(torrent_file, "w") as f:
        json.dump(torrent_data, f, indent=4)

# Function to log messages in real-time to the tracker GUI
def log_message(log_text, message):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_text.config(state=tk.NORMAL)
    log_text.insert(tk.END, f"[{current_time}] {message}\n")
    log_text.see(tk.END)
    log_text.config(state=tk.DISABLED)

# Function to handle requests from a client
def handle_client(client_socket, client_address, log_text):
    try:
        # Receive client's port to display correctly
        client_port = client_socket.recv(1024).decode('utf-8').strip()
        address_str = f"{client_address[0]}:{client_port}"
        
        log_message(log_text, f"Client {address_str} connected")

        while True:
            data = client_socket.recv(1024).decode('utf-8')
            if not data:
                break
            command_parts = data.split(" ")
            command = command_parts[0]

            if command == "up":
                piece_name = command_parts[1]

                if piece_name in pieces:
                    client_socket.send(f"Piece {piece_name} already exists.".encode('utf-8'))
                else:
                    pieces[piece_name] = [{"ip": client_address[0], "port": int(client_port)}]
                    client_socket.send(f"Piece {piece_name} information saved.".encode('utf-8'))
                    log_message(log_text, f"{address_str} uploaded piece {piece_name}")
                    save_torrent_info()

            elif command == "down":
                piece_name = command_parts[1]
                if piece_name in pieces:
                    client_socket.send(json.dumps(pieces[piece_name]).encode('utf-8'))
                    log_message(log_text, f"{address_str} requested piece {piece_name}")
                else:
                    client_socket.send("Piece does not exist.".encode('utf-8'))
                    log_message(log_text, f"{address_str} requested piece {piece_name}, but it does not exist")

            elif command == "refresh":
                client_socket.send(json.dumps([{"id": idx + 1, "piece_index": p, "clients": pieces[p]} for idx, p in enumerate(pieces)]).encode('utf-8'))

    except Exception as e:
        log_message(log_text, f"Error processing client {address_str}: {e}")
    finally:
        client_socket.close()

# Tracker Server GUI
def start_gui():
    root = tk.Tk()
    root.title("Tracker Server")

    log_text = scrolledtext.ScrolledText(root, width=60, height=20)
    log_text.grid(column=0, row=0, padx=10, pady=10)
    log_text.config(state=tk.DISABLED)

    # Main function to listen for client connections
    def main():
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(("0.0.0.0", 9999))
        server_socket.listen(100)
        log_message(log_text, "Tracker server is running...")

        while True:
            client_socket, client_address = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address, log_text))
            client_thread.start()

    server_thread = threading.Thread(target=main)
    server_thread.start()
    root.mainloop()

if __name__ == "__main__":
    start_gui()
