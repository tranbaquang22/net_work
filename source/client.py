# Client 
import socket
import threading

def client_action():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(("localhost", 8080))
    print("Connected to the tracker server")
    # Gửi thông tin hoặc yêu cầu đến máy chủ
    client_socket.close()

# Khởi chạy nhiều luồng để mô phỏng đa luồng
threads = []
for i in range(5):
    thread = threading.Thread(target=client_action)
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()
