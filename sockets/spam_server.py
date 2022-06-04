import socket

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
	s.bind((HOST, PORT))
	s.listen(5)
	while True:
		conn, addr = s.accept()
		with conn:
			print(f"Connected by {addr}")
			while True:
				try:
					data = conn.recv(1024**2)
					if not data:
						break
					print(len(data))
				except:
					break
				# print(f'{addr} - {len(data)} bytes')
				# conn.sendall(data)
			print('Disconnected')