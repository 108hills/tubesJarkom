import socket
import time
import sys
import datetime
import math
import os
import threading

# ─────────────────────────────────────────
#  KONFIGURASI
# ─────────────────────────────────────────
PROXY_HOST = "127.0.0.1"   # Alamat proxy (localhost)
PROXY_PORT = 8080

SERVER_HOST = "127.0.0.1"  # Alamat web server (localhost)
UDP_PORT_SERVER = 9090
UDP_PORT_PROXY  = 9091

UDP_PACKET_COUNT = 10       
UDP_TIMEOUT = 1.0           
TCP_DEFAULT_PATH = "/index.html"  


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
#  MULTITHREADING RUNNER
# ─────────────────────────────────────────
def run_threaded(target_func, args_list, thread_count, label):
    """
    Jalankan target_func sebanyak thread_count kali secara paralel.
    args_list = list of tuples, satu per thread.
    """
    log("THREAD", f"Memulai {thread_count} thread untuk mode {label}")
    threads = []
    for i in range(thread_count):
        args = args_list[i] if i < len(args_list) else args_list[0]
        t = threading.Thread(target=target_func, args=args, name=f"{label}-{i+1}")
        threads.append(t)

    t_start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    t_end = time.time()

    elapsed = (t_end - t_start) * 1000
    log("THREAD", f"Semua {thread_count} thread {label} selesai dalam {elapsed:.2f} ms")


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
  Mode Both (TCP + UDP bersamaan):
    python client.py -mode both

  Multithreading (jalankan N thread paralel):
    python client.py -mode tcp -thread 5
    python client.py -mode udp -thread 3
    python client.py -mode both -thread 4

  Lihat list Flags pada README.md untuk informasi lebih lanjut
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
    thread_str = get_arg("-thread", None)

    try:
        count = int(count_str) if count_str and count_str.isdigit() else None
    except ValueError:
        count = None

    try:
        thread_count = int(thread_str) if thread_str and thread_str.isdigit() else 1
    except ValueError:
        thread_count = 1

    target = get_arg("-target", "server")  # default ke server

    # Tentukan parameter UDP berdasarkan target
    udp_host = PROXY_HOST if target == "proxy" else SERVER_HOST
    udp_port = UDP_PORT_PROXY if target == "proxy" else UDP_PORT_SERVER

    if mode == "tcp":
        if thread_count > 1:
            args_list = [(path,)] * thread_count
            run_threaded(mode_tcp, args_list, thread_count, "TCP")
        else:
            mode_tcp(path)

    elif mode == "udp":
        if thread_count > 1:
            args_list = [(udp_host, count, udp_port)] * thread_count
            run_threaded(mode_udp, args_list, thread_count, "UDP")
        else:
            mode_udp(target_host=udp_host, count=count, target_port=udp_port)

    elif mode == "both":
        log("MAIN", "Mode BOTH — menjalankan TCP dan UDP secara bersamaan")
        threads = []

        # Buat thread TCP
        for i in range(thread_count):
            t = threading.Thread(target=mode_tcp, args=(path,), name=f"TCP-{i+1}")
            threads.append(t)

        # Buat thread UDP
        for i in range(thread_count):
            t = threading.Thread(
                target=mode_udp,
                args=(udp_host, count, udp_port),
                name=f"UDP-{i+1}"
            )
            threads.append(t)

        t_start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        t_end = time.time()

        elapsed = (t_end - t_start) * 1000
        log("MAIN", f"Mode BOTH selesai — {thread_count} TCP + {thread_count} UDP thread dalam {elapsed:.2f} ms")

    else:
        print_usage()