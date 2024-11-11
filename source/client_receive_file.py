import socket

def receive_file(filename, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", port))
        s.listen(1)
        print(f"Đang chờ kết nối trên cổng {port}...")
        conn, addr = s.accept()
        with conn:
            print(f"Kết nối từ {addr}")
            with open(filename, 'wb') as file:
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    file.write(data)
            print(f"Tệp {filename} đã được nhận")

receive_file("received_example.txt", 8080)
