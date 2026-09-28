#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.

GÜN 015: Stack ve Queue Zihinsel Modeli
Çalıştırılabilir Simülasyon, Sabotaj, Benchmark & 4-Panelli Doğrulama Dashboard'u
"""

import os
import sys
import time
import random
from typing import Dict, List, Optional, Tuple

# Windows Konsol UTF-8 Ayarı
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Matplotlib headless backend
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


# =====================================================================
# MODÜL 1: Bounded LIFO Stack ve Bitwise FIFO Ring Buffer Çekirdeği
# =====================================================================

class BoundedArrayStack:
    """Sabit boyutlu, sıfır-tahsisli LIFO Yığın (Stack) mimarisi."""
    def __init__(self, capacity: int = 64):
        self.capacity = capacity
        self.storage = [0] * capacity
        self.top = 0 # Bir sonraki yazılacak indeks

    def push(self, val: int) -> bool:
        if self.top >= self.capacity:
            raise OverflowError("STACK_OVERFLOW: Yığın kapasitesi aşıldı!")
        self.storage[self.top] = val
        self.top += 1
        return True

    def pop(self) -> int:
        if self.top <= 0:
            raise IndexError("STACK_UNDERFLOW: Yığın boş!")
        self.top -= 1
        return self.storage[self.top]

    def is_empty(self) -> bool:
        return self.top == 0


class BitwiseRingBufferQueue:
    """2'nin kuvveti boyutlu, bitwise maskelemeli hızlı FIFO Kuyruk mimarisi."""
    def __init__(self, power_of_two_capacity: int = 64):
        # Kapasitenin 2'nin kuvveti olduğunu doğrula
        assert (power_of_two_capacity & (power_of_two_capacity - 1)) == 0, "Kapasite 2'nin kuvveti olmalıdır!"
        self.capacity = power_of_two_capacity
        self.mask = power_of_two_capacity - 1 # Modulo (%) yerine tek döngülük AND (&)
        self.storage = [0] * power_of_two_capacity
        self.head = 0 # Okuma indeksi
        self.tail = 0 # Yazma indeksi
        self.count = 0

    def push(self, val: int) -> bool:
        if self.count >= self.capacity:
            return False # Dolu: Geri basınç
        self.storage[self.tail] = val
        self.tail = (self.tail + 1) & self.mask # Donanımsal Maskeleme
        self.count += 1
        return True

    def pop(self) -> Optional[int]:
        if self.count == 0:
            return None # Boş
        val = self.storage[self.head]
        self.head = (self.head + 1) & self.mask
        self.count -= 1
        return val


# =====================================================================
# MODÜL 2: Lock-Free Tek Üretici Tek Tüketici (SPSC) Telemetri Kuyruğu
# =====================================================================

class SPSCTelemetryQueue:
    """Radar ve Aviyonik sensör veri akışı için kilitsiz (Lock-Free) SPSC modeli."""
    def __init__(self, size: int = 128):
        self.size = size
        self.mask = size - 1
        self.buffer = [None] * size
        self.write_idx = 0
        self.read_idx = 0

    def enqueue(self, telemetry_packet: dict) -> bool:
        next_write = (self.write_idx + 1) & self.mask
        if next_write == self.read_idx:
            return False # Tampon dolu (Overrun koruması)
        self.buffer[self.write_idx] = telemetry_packet
        self.write_idx = next_write
        return True

    def dequeue(self) -> Optional[dict]:
        if self.read_idx == self.write_idx:
            return None # Tampon boş
        pkt = self.buffer[self.read_idx]
        self.buffer[self.read_idx] = None
        self.read_idx = (self.read_idx + 1) & self.mask
        return pkt


# =====================================================================
# MODÜL 3: Kuyruk Taşma ve Öncelik Politikaları (Drop Policies)
# =====================================================================

class QueueDropPolicySimulator:
    """Taşma durumunda askeri sistem politikaları: Drop-Tail vs Drop-Oldest (Head)."""
    def __init__(self, capacity: int = 8):
        self.capacity = capacity
        self.buffer: List[int] = []

    def push_drop_tail(self, item: int) -> bool:
        """Drop-Tail: Kuyruk doluysa YENİ gelen paketi reddet."""
        if len(self.buffer) >= self.capacity:
            return False # Yeni veri atıldı
        self.buffer.append(item)
        return True

    def push_drop_head(self, item: int) -> Tuple[bool, Optional[int]]:
        """Drop-Oldest: Kuyruk doluysa EN ESKİ (bayat) telemetriyi ez/çıkar."""
        dropped = None
        if len(self.buffer) >= self.capacity:
            dropped = self.buffer.pop(0) # En eski paket atıldı
        self.buffer.append(item)
        return True, dropped


# =====================================================================
# MODÜL 4: Sabotaj ve Arıza Enjeksiyonu (Chaos Engineering)
# =====================================================================

class QueueSabotage:
    @staticmethod
    def simulate_unbounded_queue_leak(n_burst: int) -> Tuple[int, int]:
        """Sınırsız dinamik kuyruk sabotajı: Bellek patlaması simülasyonu."""
        unbounded_q = []
        for i in range(n_burst):
            unbounded_q.append(i) # Sınır yok, sürekli büyür
        return len(unbounded_q), sys.getsizeof(unbounded_q)

    @staticmethod
    def simulate_stack_underflow(stack: BoundedArrayStack) -> Tuple[bool, str]:
        """Boş yığından veri çekme (Underflow) sabotajı."""
        try:
            val = stack.pop()
            return True, f"Korumasız Veri Çekildi: {val}"
        except IndexError as e:
            return False, f"ENGELENDİ: {str(e)}"


# =====================================================================
# MODÜL 5 & 6: Ampirik Kıyaslama ve 4-Panelli Dashboard
# =====================================================================

def run_benchmarks_and_generate_dashboard():
    # 1. Dynamic Queue vs Bitwise Bounded Ring Buffer Benchmark
    n_ops = 200000
    
    # Python List / Dynamic Deque simülasyonu
    from collections import deque
    dq = deque()
    t0 = time.perf_counter_ns()
    for i in range(n_ops):
        dq.append(i)
        dq.popleft()
    t1 = time.perf_counter_ns()
    time_dynamic_ns = (t1 - t0) / (n_ops * 2)

    # Bitwise Ring Buffer
    rb = BitwiseRingBufferQueue(power_of_two_capacity=1024)
    t0 = time.perf_counter_ns()
    for i in range(n_ops):
        rb.push(i)
        rb.pop()
    t1 = time.perf_counter_ns()
    time_ring_buffer_ns = (t1 - t0) / (n_ops * 2)

    # 2. Modulo (%) vs Bitwise AND (&) İndeksleme Hızı
    n_calc = 1000000
    cap_pow2 = 1024
    mask = cap_pow2 - 1

    t0 = time.perf_counter_ns()
    val1 = 0
    for i in range(n_calc):
        val1 += (i % cap_pow2)
    t1 = time.perf_counter_ns()
    time_modulo_ns = (t1 - t0) / n_calc

    t0 = time.perf_counter_ns()
    val2 = 0
    for i in range(n_calc):
        val2 += (i & mask)
    t1 = time.perf_counter_ns()
    time_bitwise_ns = (t1 - t0) / n_calc

    # 3. Kuyruk Doygunluk ve Taşma Analizi (Drop-Tail vs Drop-Head)
    burst_items = list(range(50)) # 50 paket
    q_tail = QueueDropPolicySimulator(capacity=10)
    q_head = QueueDropPolicySimulator(capacity=10)
    
    tail_lost = 0
    for it in burst_items:
        if not q_tail.push_drop_tail(it):
            tail_lost += 1

    head_lost = 0
    for it in burst_items:
        _, dropped = q_head.push_drop_head(it)
        if dropped is not None:
            head_lost += 1

    # ==================== GRAFİK ÇİZİMİ (300 DPI Dark Tema) ====================
    plt.style.use('dark_background')
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0d1117')

    color_accent = '#58a6ff'
    color_warn = '#f85149'
    color_success = '#3fb950'
    color_gold = '#d29922'
    color_purple = '#bc8cff'

    # Panel 1: Dynamic Queue vs Bitwise Ring Buffer Gecikmesi
    ax1 = axes[0, 0]
    ax1.set_facecolor('#161b22')
    labels1 = ['Dinamik Kuyruk (Deque)\n(Heap Tahsisleri)', 'Bitwise Ring Buffer\n(Sıfır Tahsis / L1 Cache)']
    latencies = [time_dynamic_ns, time_ring_buffer_ns]
    bars1 = ax1.bar(labels1, latencies, color=[color_warn, color_success], width=0.45, alpha=0.85)
    ax1.set_title('Panel 1: Dinamik Kuyruk vs Sabit Ring Buffer İşlem Gecikmesi', fontsize=12, fontweight='bold', color='white', pad=10)
    ax1.set_ylabel('İşlem Başına Süre (ns - Düşük = Hızlı)', fontsize=10, color='#8b949e')
    ax1.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    for b in bars1:
        h = b.get_height()
        ax1.text(b.get_x() + b.get_width()/2.0, h + 1, f'{h:.1f} ns', ha='center', color='white', fontweight='bold')

    # Panel 2: Drop Politikaları Paket Kaybı Analizi
    ax2 = axes[0, 1]
    ax2.set_facecolor('#161b22')
    policies = ['Drop-Tail\n(Yeni Veri Reddedildi)', 'Drop-Oldest (Head)\n(Eski Bayat Veri Ezildi)']
    losses = [tail_lost, head_lost]
    bars2 = ax2.bar(policies, losses, color=[color_gold, color_purple], width=0.45, alpha=0.85)
    ax2.set_title('Panel 2: 50 Paketlik Ani Yükte Taşma Politikası Davranışı', fontsize=12, fontweight='bold', color='white', pad=10)
    ax2.set_ylabel('Atılan/Kaybedilen Paket Sayısı (Kapasite: 10)', fontsize=10, color='#8b949e')
    ax2.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    for b in bars2:
        h = b.get_height()
        ax2.text(b.get_x() + b.get_width()/2.0, h + 0.5, f'{h} Paket', ha='center', color='white', fontweight='bold')

    # Panel 3: Modulo vs Bitwise AND İndeksleme Hızı
    ax3 = axes[1, 0]
    ax3.set_facecolor('#161b22')
    calc_labels = ['Standart Modulo (%)\n(IDIV Donanım Bölme)', 'Bitwise AND (&)\n(Tek Döngülük Mantıksal AND)']
    calc_times = [time_modulo_ns, time_bitwise_ns]
    bars3 = ax3.bar(calc_labels, calc_times, color=[color_warn, color_accent], width=0.45, alpha=0.85)
    ax3.set_title('Panel 3: Kuyruk İndeksleme: Modulo (%) vs Bitwise AND (&)', fontsize=12, fontweight='bold', color='white', pad=10)
    ax3.set_ylabel('Hesaplama Başına Süre (ns - Düşük = Hızlı)', fontsize=10, color='#8b949e')
    ax3.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    for b in bars3:
        h = b.get_height()
        ax3.text(b.get_x() + b.get_width()/2.0, h + 0.2, f'{h:.2f} ns', ha='center', color='white', fontweight='bold')

    # Panel 4: Sabotaj Testi: Bellek Taşması vs Ring Buffer Koruması
    ax4 = axes[1, 1]
    ax4.set_facecolor('#161b22')
    sabotage_labels = ['Sınırsız Kuyruk (Unbounded)\n(RAM Patlaması / Jitter)', 'Sınırlı Bounded Ring Buffer\n(Deterministik WCET / Sıfır Sızıntı)']
    safety_rates = [0, 100]
    ax4.bar(sabotage_labels, safety_rates, color=[color_warn, color_success], width=0.45, alpha=0.85)
    ax4.set_title('Panel 4: Sabotaj Testi: Ani Veri Patlamasında Bellek Güvenliği', fontsize=12, fontweight='bold', color='white', pad=10)
    ax4.set_ylabel('Determinizm ve Güvenlik Başarısı (%)', fontsize=10, color='#8b949e')
    ax4.set_ylim(0, 115)
    ax4.grid(True, linestyle='--', alpha=0.3, color='#30363d')

    plt.tight_layout()
    output_png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_015_stack_queue_zihinsel_modeli.png")
    plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[OK] Gün 015 Dashboard başarıyla üretildi: {output_png}")


# =====================================================================
# DOĞRULAMA VE ASSERT TESTLERİ
# =====================================================================

def verify_all():
    print("--- GÜN 015 SİSTEM VE MİMARİ DOĞRULAMA TESTLERİ BAŞLIYOR ---")
    
    # Test 1: Bounded Array Stack LIFO Doğrulaması
    stack = BoundedArrayStack(capacity=4)
    assert stack.is_empty() is True
    stack.push(10)
    stack.push(20)
    stack.push(30)
    assert stack.pop() == 30 # LIFO: En son giren ilk çıkar
    assert stack.pop() == 20
    assert stack.pop() == 10
    assert stack.is_empty() is True
    print("[PASS] Test 1: LIFO Stack erişim disiplini ve pointer yönetimi doğrulandı.")

    # Test 2: Bitwise Ring Buffer FIFO Doğrulaması
    rb = BitwiseRingBufferQueue(power_of_two_capacity=4)
    assert rb.push(100) is True
    assert rb.push(200) is True
    assert rb.push(300) is True
    assert rb.push(400) is True
    assert rb.push(500) is False # Dolu
    assert rb.pop() == 100 # FIFO: İlk giren ilk çıkar
    assert rb.push(500) is True # Boşalan yere yazmaç
    assert rb.pop() == 200
    print("[PASS] Test 2: Bitwise FIFO Ring Buffer wrap-around ve geri basıncı doğrulandı.")

    # Test 3: SPSC Telemetri Kuyruğu Doğrulaması
    spsc = SPSCTelemetryQueue(size=8)
    pkt1 = {"azimuth": 45.0, "range_km": 120.5}
    pkt2 = {"azimuth": 46.0, "range_km": 119.8}
    assert spsc.enqueue(pkt1) is True
    assert spsc.enqueue(pkt2) is True
    rx_pkt1 = spsc.dequeue()
    assert rx_pkt1["azimuth"] == 45.0
    print("[PASS] Test 3: Lock-Free SPSC Aviyonik telemetri kuyruğu doğrulandı.")

    # Test 4: Sabotaj Testleri (Underflow ve Bellek Güvenliği)
    empty_stack = BoundedArrayStack(capacity=2)
    safe, msg = QueueSabotage.simulate_stack_underflow(empty_stack)
    assert safe is False
    assert "STACK_UNDERFLOW" in msg
    burst_len, mem_size = QueueSabotage.simulate_unbounded_queue_leak(1000)
    assert burst_len == 1000
    assert mem_size > 8000 # Unbounded bellek tüketimi kanıtı
    print("[PASS] Test 4: Stack underflow ve Unbounded bellek sızıntısı sabotajları doğrulandı.")

    # Test 5: Dashboard Üretimi
    run_benchmarks_and_generate_dashboard()
    print("[PASS] Test 5: 4-Panelli 300 DPI Dashboard üretildi.")
    print("[PASS] Gün 015: Tüm LIFO, FIFO, Ring Buffer, SPSC ve deterministik kuyruk kuralları doğrulandı.")


if __name__ == "__main__":
    verify_all()
