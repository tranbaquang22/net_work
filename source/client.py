import socket
import threading
import tkinter as tk
from tkinter import scrolledtext
from tkinter import ttk
import os
import json
import datetime

# Tracker Server address
tracker_host = "127.0.0.1"
tracker_port = 9999

# Client port (unique for each client)
client_port = 8887

# Directory for storing client pieces
client_storage = f"{tracker_host}_{client_port}"
if not os.path.exists(client_storage):
    os.makedirs(client_storage)

class ClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Client {client_port}")

        # Log (read-only) for client activity
        self.log_text = scrolledtext.ScrolledText(root, width=60, height=15)
        self.log_text.grid(row=0, column=0, columnspan=3, padx=10, pady=10)
        self.log_text.config(state=tk.DISABLED)

        # Entry for piece name to upload or download
        self.file_entry = ttk.Entry(root, width=20)
        self.file_entry.grid(row=1, column=1, padx=10, pady=5)

        # List of all available pieces (left)
        self.available_pieces_list = tk.Listbox(root, width=30, height=10)
        self.available_pieces_list.grid(row=2, column=0, padx=10, pady=5)

        # List of downloaded/uploaded pieces (right)
        self.downloaded_pieces_list = tk.Listbox(root, width=30, height=10)
        self.downloaded_pieces_list.grid(row=2, column=2, padx=10, pady=5)

        # Buttons for Upload, Download, and Refresh
        ttk.Button(root, text="Upload", command=self.upload_file).grid(row=3, column=0, padx=10, pady=5)
        ttk.Button(root, text="Download", command=self.download_file).grid(row=3, column=2, padx=10, pady=5)
        ttk.Button(root, text="Refresh", command=self.refresh_file_list).grid(row=3, column=1, padx=10, pady=5)

        try:
            self.tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tracker_socket.connect((tracker_host, tracker_port))
            self.tracker_socket.send(str(client_port).encode('utf-8'))  # Send client port to the server
            self.log_message("Connected to Tracker Server.")
        except Exception as e:
            self.log_message(f"Error connecting to Tracker Server: {e}")

        self.listen_for_downloads()

    def log_message(self, message):
        """Append log messages in read-only mode."""
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{current_time}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def upload_file(self):
        """Send upload request to Tracker Server and create a real file if it doesn't exist."""
        piece_name = self.file_entry.get()
        if not piece_name:
            self.log_message("Please enter a piece name to upload.")
            return
        if piece_name in self.get_downloaded_pieces():
            self.log_message(f"Piece {piece_name} already exists on the client.")
            return
        try:
            # Create a real file for the piece if it doesn't exist
            piece_path = os.path.join(client_storage, piece_name)
            if not os.path.exists(piece_path):
                with open(piece_path, "w") as real_file:
                    real_file.write("This is the real data for piece " + piece_name)

            # Notify the tracker server
            self.tracker_socket.send(f"up {piece_name} {client_port}".encode('utf-8'))
            response = self.tracker_socket.recv(1024).decode('utf-8')
            self.log_message(response)
            self.downloaded_pieces_list.insert(tk.END, piece_name)  # Show uploaded piece on the right
        except Exception as e:
            self.log_message(f"Error uploading piece: {e}")

    def download_file(self):
        """Send download request to Tracker Server."""
        piece_name = self.file_entry.get()
        if not piece_name:
            self.log_message("Please enter a piece name to download.")
            return
        if piece_name in self.get_downloaded_pieces():
            self.log_message(f"Piece {piece_name} is already downloaded.")
            return
        try:
            self.tracker_socket.send(f"down {piece_name}".encode('utf-8'))
            response = self.tracker_socket.recv(1024).decode('utf-8')

            if not response.strip():
                self.log_message("No response from server.")
                return

            try:
                clients = json.loads(response)
                if not clients:
                    self.log_message("No clients have this piece.")
                    return
            except json.JSONDecodeError:
                self.log_message("Invalid response from server.")
                return

            for client in clients:
                threading.Thread(target=self.download_piece_from_client, args=(piece_name, client)).start()
        except Exception as e:
            self.log_message(f"Error sending download request: {e}")

    def download_piece_from_client(self, piece_name, client):
        """Download a piece from another client."""
        try:
            download_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            download_socket.connect((client["ip"], client["port"]))
            download_socket.send(f"{piece_name} {client_port}".encode('utf-8'))  # Send piece name and client port

            with open(os.path.join(client_storage, piece_name), "wb") as file:
                data = download_socket.recv(1024)
                while data:
                    file.write(data)
                    data = download_socket.recv(1024)
            download_socket.close()

            self.downloaded_pieces_list.insert(tk.END, piece_name)  # Add downloaded piece to the right list
            self.log_message(f"Downloaded piece {piece_name} from {client['ip']}:{client['port']}")
        except Exception as e:
            self.log_message(f"Error downloading piece {piece_name} from {client['ip']}:{client['port']} - {str(e)}")

    def refresh_file_list(self):
        """Request the list of all pieces from the server."""
        try:
            self.tracker_socket.send("refresh".encode('utf-8'))
            response = self.tracker_socket.recv(1024).decode('utf-8')
            try:
                all_pieces = json.loads(response)
                self.available_pieces_list.delete(0, tk.END)
                for piece in all_pieces:
                    self.available_pieces_list.insert(tk.END, f"ID: {piece['id']}, Piece: {piece['piece_index']}, Clients: {piece['clients']}")
            except json.JSONDecodeError:
                self.log_message("Failed to refresh piece list.")
        except Exception as e:
            self.log_message(f"Error refreshing piece list: {e}")

    def get_downloaded_pieces(self):
        return [self.downloaded_pieces_list.get(i) for i in range(self.downloaded_pieces_list.size())]

    def listen_for_downloads(self):
        """Listen for requests to download pieces from other clients."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(("0.0.0.0", client_port))
        server_socket.listen(50)
        threading.Thread(target=self.accept_connections, args=(server_socket,)).start()

    def accept_connections(self, server_socket):
        """Accept and handle download requests from other clients."""
        while True:
            client_socket, client_address = server_socket.accept()
            threading.Thread(target=self.send_piece, args=(client_socket, client_address)).start()

    def send_piece(self, client_socket, client_address):
        """Send a requested piece to another client and log if downloaded."""
        request_data = client_socket.recv(1024).decode('utf-8')
        piece_name, requester_port = request_data.split()
        piece_path = os.path.join(client_storage, piece_name)

        if os.path.exists(piece_path):
            with open(piece_path, "rb") as file:
                data = file.read(1024)
                while data:
                    client_socket.send(data)
                    data = file.read(1024)
            self.log_message(f"Client {client_address[0]}:{requester_port} downloaded piece {piece_name} from you")
        else:
            self.log_message(f"Piece {piece_name} does not exist in your storage.")
        client_socket.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = ClientApp(root)
    root.mainloop()
