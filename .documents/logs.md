----------------------------------------
Exception occurred during processing of request from ('192.168.137.1', 51313)
Traceback (most recent call last):
  File "/usr/lib/python3.11/socketserver.py", line 317, in _handle_request_noblock
    self.process_request(request, client_address)
  File "/usr/lib/python3.11/socketserver.py", line 348, in process_request
    self.finish_request(request, client_address)
  File "/usr/lib/python3.11/socketserver.py", line 361, in finish_request
    self.RequestHandlerClass(request, client_address, self)
  File "/usr/lib/python3.11/socketserver.py", line 755, in __init__
    self.handle()
  File "/usr/lib/python3.11/http/server.py", line 432, in handle
    self.handle_one_request()
  File "/usr/lib/python3.11/http/server.py", line 420, in handle_one_request
    method()
  File "/app/bridge.py", line 98, in do_GET
    self._serve_latest()
  File "/app/bridge.py", line 146, in _serve_latest
    self.wfile.write(frame)
  File "/usr/lib/python3.11/socketserver.py", line 834, in write
    self._sock.sendall(b)
BrokenPipeError: [Errno 32] Broken pipe
----------------------------------------
----------------------------------------
Exception occurred during processing of request from ('192.168.137.1', 61391)
Traceback (most recent call last):
  File "/usr/lib/python3.11/socketserver.py", line 317, in _handle_request_noblock
    self.process_request(request, client_address)
  File "/usr/lib/python3.11/socketserver.py", line 348, in process_request
    self.finish_request(request, client_address)
  File "/usr/lib/python3.11/socketserver.py", line 361, in finish_request
    self.RequestHandlerClass(request, client_address, self)
  File "/usr/lib/python3.11/socketserver.py", line 755, in __init__
    self.handle()
  File "/usr/lib/python3.11/http/server.py", line 432, in handle
    self.handle_one_request()
  File "/usr/lib/python3.11/http/server.py", line 420, in handle_one_request
    method()
  File "/app/bridge.py", line 98, in do_GET
    self._serve_latest()
  File "/app/bridge.py", line 146, in _serve_latest
    self.wfile.write(frame)
  File "/usr/lib/python3.11/socketserver.py", line 834, in write
    self._sock.sendall(b)
BrokenPipeError: [Errno 32] Broken pipe
----------------------------------------
----------------------------------------
Exception occurred during processing of request from ('192.168.137.1', 61397)
Traceback (most recent call last):
  File "/usr/lib/python3.11/socketserver.py", line 317, in _handle_request_noblock
    self.process_request(request, client_address)
  File "/usr/lib/python3.11/socketserver.py", line 348, in process_request
    self.finish_request(request, client_address)
  File "/usr/lib/python3.11/socketserver.py", line 361, in finish_request
    self.RequestHandlerClass(request, client_address, self)
  File "/usr/lib/python3.11/socketserver.py", line 755, in __init__
    self.handle()
  File "/usr/lib/python3.11/http/server.py", line 432, in handle
    self.handle_one_request()
  File "/usr/lib/python3.11/http/server.py", line 420, in handle_one_request
    method()
  File "/app/bridge.py", line 98, in do_GET
    self._serve_latest()
  File "/app/bridge.py", line 146, in _serve_latest
    self.wfile.write(frame)
  File "/usr/lib/python3.11/socketserver.py", line 834, in write
    self._sock.sendall(b)
BrokenPipeError: [Errno 32] Broken pipe
----------------------------------------
📡 [BRIDGE] Client connecté : ('192.168.137.1', 51317)
📴 [BRIDGE] Client déconnecté : ('192.168.137.1', 51317)
admin@PI:~/test/PI2P_2026 $ 