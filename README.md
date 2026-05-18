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
   - UDP QoS echo server akan berjalan pada `0.0.0.0:9000`.

2. Jalankan proxy:

   ```powershell
   py proxy.py
   ```

   - Proxy mendengarkan pada `0.0.0.0:8080`.
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

   Jika ingin menargetkan host spesifik atau jumlah paket berbeda:

   ```powershell
   py client.py -mode udp -host 127.0.0.1 -count 20
   ```

## Konfigurasi

Nilai default dapat diubah langsung di file Python:

- `client.py`: `PROXY_HOST`, `PROXY_PORT`, `SERVER_HOST`, `UDP_PORT`, `UDP_PACKET_COUNT`.
- `proxy.py`: `PROXY_HOST`, `PROXY_PORT`, `SERVER_HOST`, `SERVER_PORT`, `CACHE_DIR`.
- `webserver.py`: `TCP_HOST`, `TCP_PORT`, `UDP_HOST`, `UDP_PORT`.

## Fungsi Utama

- `webserver.py`: Melayani file HTML/CSS/JS statis melalui HTTP dan memantulkan paket UDP untuk QoS.
- `proxy.py`: Menyimpan cache response HTTP 200 OK. Jika cache kosong, proxy meneruskan request ke web server.
- `client.py`: Mengirim request HTTP ke proxy dan mengukur latency, loss, jitter, throughput untuk UDP.

## Catatan

- Pastikan `webserver.py` dan `proxy.py` berjalan sebelum menggunakan `client.py`.
- Cache proxy disimpan di `cache/`.
- Struktur path HTTP default di `client.py` adalah `/HTML/index.html`.
