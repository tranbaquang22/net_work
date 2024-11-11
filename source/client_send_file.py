import socket

def send_file(filename, host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        with open(filename, 'rb') as file:
            data = file.read()
            s.sendall(data)
        print(f"{filename} đã được gửi đến {host}:{port}")

send_file("example.txt", "localhost", 8080)
