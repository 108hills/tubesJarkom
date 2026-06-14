import socket
import time
import sys
import datetime
import math
import os

# ─────────────────────────────────────────
#  KONFIGURASI
# ─────────────────────────────────────────
PROXY_HOST = "127.0.0.1"   
PROXY_PORT = 8080

SERVER_HOST = "127.0.0.1"  
UDP_PORT_SERVER = 9090
UDP_PORT_PROXY  = 9091

UDP_PACKET_COUNT = 10       
UDP_TIMEOUT = 1.0           
TCP_DEFAULT_PATH = "/HTML/index.html"  


# ─────────────────────────────────────────
#  HELPER: LOGGING (OTOMATIS SIMPAN)
# ─────────────────────────────────────────
def log(tag, message):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{now}] [{tag}] {message}"
    print(log_entry)
    
    # Buat folder 'logs' jika belum ada bray
    os.makedirs("logs", exist_ok=True)
    
    try:
        # Simpan di dalam folder logs/
        with open(os.path.join("logs", "log_client.txt"), "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    except Exception as e:
        print(f"Gagal menulis ke log file: {e}")

def save_output_to_file(text_block):
    # Buat folder 'logs' jika belum ada bray
    os.makedirs("logs", exist_ok=True)
    
    try:
        # Simpan di dalam folder logs/
        with open(os.path.join("logs", "hasil_client.txt"), "a", encoding="utf-8") as f:
            f.write(text_block + "\n")
    except Exception as e:
        print(f"Gagal menyimpan output ke file: {e}")


# ─────────────────────────────────────────
#  MODE TCP — HTTP CLIENT
# ─────────────────────────────────────────
def mode_tcp(path):
    log("TCP", f"Mengirim GET {path} ke proxy {PROXY_HOST}:{PROXY_PORT}")

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect((PROXY_HOST, PROXY_PORT))

        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {PROXY_HOST}:{PROXY_PORT}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        )
        t_send = time.time()
        s.sendall(request.encode("utf-8"))

        response = b""
        while True:
            try:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response += chunk
            except socket.timeout:
                break

        t_recv = time.time()
        s.close()

        rtt_ms = (t_recv - t_send) * 1000

        if not response:
            log("TCP", "Tidak ada response dari proxy.")
            return

        if b"\r\n\r\n" in response:
            header_part, body_part = response.split(b"\r\n\r\n", 1)
            header_text = header_part.decode("utf-8", errors="replace")
            status_line = header_text.split("\r\n")[0]
        else:
            header_text = ""
            status_line = "(tidak ada header)"
            body_part = response

        # Format output tabel agar dicetak di CMD sekaligus di-save ke file
        output_tcp = f"""
{"═" * 60}
  STATUS  : {status_line}
  RTT     : {rtt_ms:.2f} ms
  UKURAN  : {len(response)} bytes (header + body)
{"═" * 60}
── HEADER ──
{header_text}
── BODY (500 karakter pertama) ──
{body_part[:500].decode("utf-8", errors="replace")}
{"─" * 60}
"""
        print(output_tcp)
        save_output_to_file(output_tcp)

    except ConnectionRefusedError:
        log("TCP", f"Koneksi ditolak — pastikan proxy berjalan di {PROXY_HOST}:{PROXY_PORT}")
    except socket.timeout:
        log("TCP", "Timeout — proxy tidak merespons dalam 10 detik")
    except Exception as e:
        log("TCP", f"Error: {e}")


# ─────────────────────────────────────────
#  MODE UDP — QoS PINGER
# ─────────────────────────────────────────
def mode_udp(target_host=None, count=None, target_port=None):
    host  = target_host or SERVER_HOST
    n     = count or UDP_PACKET_COUNT

    port = target_port or UDP_PORT_SERVER

    log("UDP", f"Memulai QoS ping ke {host}:{port} — {n} paket")
    print()

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(UDP_TIMEOUT)

    rtt_list      = []  
    lost          = 0
    total_payload = 0
    t_start       = time.time()

    for seq in range(1, n + 1):
        timestamp = time.time()
        payload   = f"Ping {seq} {timestamp}".encode("utf-8")
        total_payload += len(payload)

        try:
            s.sendto(payload, (host, port))
            t_send = time.time()

            data, _ = s.recvfrom(1024)
            t_recv  = time.time()

            rtt_ms = (t_recv - t_send) * 1000
            rtt_list.append(rtt_ms)

            echo_ok = (data == payload)
            status  = "OK" if echo_ok else "ECHO MISMATCH"
            
            loop_log = f"  Paket {seq:>3}: RTT = {rtt_ms:7.3f} ms  [{status}]"
            print(loop_log)
            save_output_to_file(loop_log) # Simpan baris RTT per paket

        except socket.timeout:
            lost += 1
            loop_log = f"  Paket {seq:>3}: Request timed out"
            print(loop_log)
            save_output_to_file(loop_log)

        time.sleep(0.1)

    t_end    = time.time()
    duration = t_end - t_start
    s.close()

    received   = len(rtt_list)
    loss_pct   = (lost / n) * 100
    throughput = (total_payload * 8) / duration / 1000  

    if received > 0:
        rtt_min = min(rtt_list)
        rtt_avg = sum(rtt_list) / received
        rtt_max = max(rtt_list)

        if received > 1:
            diffs   = [abs(rtt_list[i] - rtt_list[i-1]) for i in range(1, received)]
            mean_d  = sum(diffs) / len(diffs)
            variance = sum((d - mean_d) ** 2 for d in diffs) / len(diffs)
            jitter  = math.sqrt(variance)
        else:
            jitter = 0.0
    else:
        rtt_min = rtt_avg = rtt_max = jitter = 0.0

    # Format output tabel statistik
    output_udp = f"""
{"═" * 60}
  QoS STATISTIK — {host}:{port}
{"═" * 60}
  Paket dikirim   : {n}
  Paket diterima  : {received}
  Packet Loss     : {loss_pct:.1f}%
  RTT min         : {rtt_min:.3f} ms
  RTT avg         : {rtt_avg:.3f} ms
  RTT max         : {rtt_max:.3f} ms
  Jitter          : {jitter:.3f} ms
  Throughput      : {throughput:.3f} kbps
{"═" * 60}
"""
    print(output_udp)
    save_output_to_file(output_udp)


# ─────────────────────────────────────────
#  HELPER: USAGE
# ─────────────────────────────────────────
def print_usage():
    print("""
Cara penggunaan:
  Mode TCP (HTTP):
    python client.py -mode tcp
  Mode UDP (QoS):
    python client.py -mode udp
""")


if __name__ == "__main__":
    args = sys.argv[1:]

    def get_arg(flag, default=None):
        if flag in args:
            idx = args.index(flag)
            if idx + 1 < len(args):
                return args[idx + 1]
        return default

    mode = get_arg("-mode", "").lower()
    path = get_arg("-path", TCP_DEFAULT_PATH)
    host = get_arg("-host", None)
    count_str = get_arg("-count", None)

    try:
        count = int(count_str) if count_str and count_str.isdigit() else None
    except ValueError:
        count = None

    target = get_arg("-target", "server")  # default ke server

    if mode == "tcp":
        mode_tcp(path)
    elif mode == "udp":
        if target == "proxy":
            mode_udp(target_host=PROXY_HOST, count=count, target_port=UDP_PORT_PROXY)
        else:
            mode_udp(target_host=SERVER_HOST, count=count, target_port=UDP_PORT_SERVER)
    else:
        print_usage()