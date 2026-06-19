# TUBES Jaringan Komputer

Sistem sederhana untuk tugas jaringan komputer yang terdiri dari:

- `webserver.py`: HTTP file server (TCP) dan QoS echo server (UDP).
- `proxy.py`: HTTP proxy dengan caching untuk mempercepat permintaan ke web server.
- `client.py`: Klien yang mendukung mode TCP untuk HTTP melalui proxy dan mode UDP untuk pengukuran QoS.
- `cache/`: Direktori cache untuk menyimpan response HTTP yang berhasil diambil oleh proxy.
- `HTML/`: Konten web statis yang dilayani oleh `webserver.py`.

## Anggota Kelompok

- 103012400371 : A MUH IMRAN RAMADHAN A
- 103012400230 : AHMAD KADHIM
- 103012400386 : HAMAD DAFALA

## Persyaratan

- Python 3.x
- Tidak menggunakan framework eksternal; semua kode berbasis pustaka standar Python berdasarkan deskripsi tugas yang diberikan

## Struktur Projek

- `client.py`: Client manual tanpa framework.
- `proxy.py`: Proxy caching HTTP.
- `webserver.py`: Web server statis + UDP echo.
- `cache/`: File cache proxy.
- `HTML/`: Halaman web dan aset statis.

## Cara Menjalankan

1. Jalankan web server terlebih dahulu:

   ```powershell
   py webserver.py
   ```

   - HTTP server akan berjalan pada `0.0.0.0:8000`.
   - UDP QoS echo server akan berjalan pada `0.0.0.0:9090`.

2. Jalankan proxy:

   ```powershell
   py proxy.py
   ```

   - Proxy mendengarkan pada `0.0.0.0:8080` (TCP HTTP).
   - Proxy UDP QoS listener berjalan pada `0.0.0.0:9091`.
   - Proxy akan meneruskan permintaan ke web server.

3. Jalankan client untuk mode TCP (HTTP):

   ```powershell
   py client.py -mode tcp -path /index.html
   ```

   Contoh lain:

   ```powershell
   py client.py -mode tcp -path /osi.html
   ```

4. Jalankan client untuk mode UDP (QoS):

   ```powershell
   py client.py -mode udp
   ```

   Default target adalah web server (`9090`). Untuk menargetkan proxy (`9091`):

   ```powershell
   py client.py -mode udp -target proxy
   ```

   Jika ingin menargetkan host spesifik atau jumlah paket berbeda:

   ```powershell
   py client.py -mode udp -host 127.0.0.1 -count 20
   py client.py -mode udp -host 127.0.0.1 -count 20 -target proxy
   ```

5. Jalankan client mode **Both** (TCP + UDP bersamaan):

   ```powershell
   py client.py -mode both
   ```

   Mode ini menjalankan TCP dan UDP secara **paralel** menggunakan thread terpisah.

## Multithreading

Client mendukung opsi `-thread N` untuk menjalankan **N thread paralel** dari mode yang dipilih.

| Flag | Deskripsi |
|---|---|
| `-thread N` | Jumlah thread yang dijalankan secara paralel (default: 1) |
| `-mode both` | Menjalankan TCP dan UDP bersamaan dalam thread terpisah |

### Contoh Penggunaan

```powershell
# 5 thread TCP paralel
py client.py -mode tcp -thread 5

# 3 thread UDP paralel
py client.py -mode udp -thread 3

# Both mode: 1 thread TCP + 1 thread UDP
py client.py -mode both

# Both mode: 4 thread TCP + 4 thread UDP (total 8 thread)
py client.py -mode both -thread 4

# UDP multithreading ke proxy
py client.py -mode udp -thread 3 -target proxy
```

> **Catatan:** Jika `-thread` tidak diberikan atau bernilai 1, client berjalan single-threaded seperti biasa (tidak ada perubahan perilaku).

## Konfigurasi

Nilai default dapat diubah langsung di file Python:

- `client.py`: `PROXY_HOST`, `PROXY_PORT`, `SERVER_HOST`, `UDP_PORT_SERVER`, `UDP_PORT_PROXY`, `UDP_PACKET_COUNT`.
- `proxy.py`: `PROXY_HOST`, `PROXY_PORT`, `SERVER_HOST`, `SERVER_PORT`, `CACHE_DIR`.
- `webserver.py`: `TCP_HOST`, `TCP_PORT`, `UDP_HOST`, `UDP_PORT`.

## Fungsi Utama

- `webserver.py`: Melayani file HTML/CSS/JS statis melalui HTTP dan memantulkan paket UDP untuk QoS.
- `proxy.py`: Menyimpan cache response HTTP 200 OK. Jika cache kosong, proxy meneruskan request ke web server.
- `client.py`: Mengirim request HTTP ke proxy dan mengukur latency, loss, jitter, throughput untuk UDP. Mendukung multithreading untuk pengujian beban.

## Catatan

- Pastikan `webserver.py` dan `proxy.py` berjalan sebelum menggunakan `client.py`.
- Cache proxy disimpan di `cache/`.
- Struktur path HTTP default di `client.py` adalah `/HTML/index.html`.
- Untuk pengujian **multi-device** (3 laptop, satu Wi-Fi): ubah `SERVER_HOST` di `proxy.py` dan `PROXY_HOST`/`SERVER_HOST` di `client.py` sesuai IP LAN masing-masing laptop. `webserver.py` tidak perlu diubah.