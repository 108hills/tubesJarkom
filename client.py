import socket
import time
import sys
import datetime
import math

# ─────────────────────────────────────────
#  KONFIGURASI
# ─────────────────────────────────────────
PROXY_HOST = "127.0.0.1"   # Ganti IP jika proxy di mesin lain
PROXY_PORT = 8080

SERVER_HOST = "127.0.0.1"  # Untuk UDP QoS — arahkan ke web server
UDP_PORT = 9000

UDP_PACKET_COUNT = 10       # Jumlah paket UDP yang dikirim
UDP_TIMEOUT = 1.0           # Timeout per paket (detik)
TCP_DEFAULT_PATH = "/HTML/index.html"  # Path default untuk mode TCP


# ─────────────────────────────────────────
#  HELPER: LOGGING
# ─────────────────────────────────────────
def log(tag, message):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] [{tag}] {message}")


# ─────────────────────────────────────────
#  MODE TCP — HTTP CLIENT
# ─────────────────────────────────────────
def mode_tcp(path):
    """
    Kirim HTTP GET request ke proxy, tampilkan response di terminal.
    """
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

        # Pemisahan header and body
        if b"\r\n\r\n" in response:
            header_part, body_part = response.split(b"\r\n\r\n", 1)
            header_text = header_part.decode("utf-8", errors="replace")
            status_line = header_text.split("\r\n")[0]
        else:
            header_text = ""
            status_line = "(tidak ada header)"
            body_part = response

        print("\n" + "═" * 60)
        print(f"  STATUS  : {status_line}")
        print(f"  RTT     : {rtt_ms:.2f} ms")
        print(f"  UKURAN  : {len(response)} bytes (header + body)")
        print("═" * 60)
        print("\n── HEADER ──")
        print(header_text)
        print("── BODY (500 karakter pertama) ──")
        print(body_part[:500].decode("utf-8", errors="replace"))
        print("─" * 60 + "\n")

    except ConnectionRefusedError:
        log("TCP", f"Koneksi ditolak — pastikan proxy berjalan di {PROXY_HOST}:{PROXY_PORT}")
    except socket.timeout:
        log("TCP", "Timeout — proxy tidak merespons dalam 10 detik")
    except Exception as e:
        log("TCP", f"Error: {e}")


# ─────────────────────────────────────────
#  MODE UDP — QoS PINGER
# ─────────────────────────────────────────
def mode_udp(target_host=None, count=None):
    """
    Kirim UDP ping ke web server, ukur RTT, packet loss, jitter, throughput.
    Format payload: "Ping <seq> <timestamp>"
    """
    host  = target_host or SERVER_HOST
    n     = count or UDP_PACKET_COUNT

    log("UDP", f"Memulai QoS ping ke {host}:{UDP_PORT} — {n} paket")
    print()

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(UDP_TIMEOUT)

    rtt_list      = []  # ms
    lost          = 0
    total_payload = 0
    t_start       = time.time()

    for seq in range(1, n + 1):
        timestamp = time.time()
        payload   = f"Ping {seq} {timestamp}".encode("utf-8")
        total_payload += len(payload)

        try:
            s.sendto(payload, (host, UDP_PORT))
            t_send = time.time()

            data, _ = s.recvfrom(1024)
            t_recv  = time.time()

            rtt_ms = (t_recv - t_send) * 1000
            rtt_list.append(rtt_ms)

            # Verifikasi echo
            echo_ok = (data == payload)
            status  = "OK" if echo_ok else "ECHO MISMATCH"
            print(f"  Paket {seq:>3}: RTT = {rtt_ms:7.3f} ms  [{status}]")

        except socket.timeout:
            lost += 1
            print(f"  Paket {seq:>3}: Request timed out")

        # jeda antar paket
        time.sleep(0.1)

    t_end    = time.time()
    duration = t_end - t_start

    s.close()

    # ── Hitung statistik ──
    received   = len(rtt_list)
    loss_pct   = (lost / n) * 100
    throughput = (total_payload * 8) / duration / 1000  # kbps

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

    print("\n" + "═" * 60)
    print(f"  QoS STATISTIK — {host}:{UDP_PORT}")
    print("═" * 60)
    print(f"  Paket dikirim   : {n}")
    print(f"  Paket diterima  : {received}")
    print(f"  Packet Loss     : {loss_pct:.1f}%")
    print(f"  RTT min         : {rtt_min:.3f} ms")
    print(f"  RTT avg         : {rtt_avg:.3f} ms")
    print(f"  RTT max         : {rtt_max:.3f} ms")
    print(f"  Jitter          : {jitter:.3f} ms")
    print(f"  Throughput      : {throughput:.3f} kbps")
    print("═" * 60 + "\n")


# ─────────────────────────────────────────
#  HELPER: USAGE
# ─────────────────────────────────────────
def print_usage():
    print("""
Cara penggunaan:

  Mode TCP (HTTP):
    python client.py -mode tcp
    python client.py -mode tcp -path /HTML/index.html
    python client.py -mode tcp -path /HTML/osi.html

  Mode UDP (QoS):
    python client.py -mode udp
    python client.py -mode udp -host 192.168.1.10 -count 20

  Konfigurasi default:
    Proxy   : 127.0.0.1:8080
    Server  : 127.0.0.1:9000 (UDP)
    Path    : /HTML/index.html (TCP)
    Count   : 10 paket
""")


# ─────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────
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

    if mode == "tcp":
        mode_tcp(path)
    elif mode == "udp":
        mode_udp(target_host=host, count=count)
    else:
        print_usage()
