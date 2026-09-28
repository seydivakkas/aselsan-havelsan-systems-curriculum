# Graph Report - c:\Users\seydieryilmaz\Downloads\Olay_Proje\mufreddat_docs  (2026-09-20)

## Corpus Check
- 22 files · ~265,610 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 165 nodes · 191 edges · 20 communities (11 shown, 9 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 14 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- C++ Kütüphane Ekosistemi
- Müfredat Fazları ve Yol Haritası
- C++ Mastery Spine Omurgası
- Radar / DSP / Sinyal İşleme
- Embedded / RTOS / Gömülü Sistemler
- 5G / Dağıtık Sistemler
- Performans ve Sayısal Hesaplama
- Python Kütüphaneleri
- Robotik / ROS2 / PX4
- Linux Komut Referansı
- Systems C++ (S2)
- Build Araçları (C++/CMake)
- Kalman Filtreler
- DDS/ROS2 Middleware
- Linux/POSIX Temelleri
- S1 Core Language
- S2 Systems C++
- 5G AMF
- 5G SMF
- 5G UPF

## God Nodes (most connected - your core abstractions)
1. `365 Günlük ASELSAN/HAVELSAN Müfredatı` - 23 edges
2. `C++ Kütüphane Kataloğu` - 18 edges
3. `Python Kütüphane Kataloğu` - 13 edges
4. `Radar/DSP/Haberleşme Kataloğu` - 13 edges
5. `ROS2/PX4/CV Stack` - 13 edges
6. `S2 Systems C++` - 12 edges
7. `S4 Performance/Numerical` - 12 edges
8. `S3 Embedded/Robotics C++` - 11 edges
9. `5G / Distributed Systems` - 11 edges
10. `Embedded / RTOS Stack` - 11 edges

## Surprising Connections (you probably didn't know these)
- `rclpy (ROS2)` --semantically_similar_to--> `ROS2 Framework`  [INFERRED] [semantically similar]
  14_PYTHON_KUTUPHANELERI.md → 20_ROS2_PX4_CV_STACK.md
- `pymavlink` --semantically_similar_to--> `MAVLink Protokolü`  [INFERRED] [semantically similar]
  14_PYTHON_KUTUPHANELERI.md → 20_ROS2_PX4_CV_STACK.md
- `OpenCV C++` --semantically_similar_to--> `OpenCV Pipeline`  [INFERRED] [semantically similar]
  15_CPP_KUTUPHANELERI.md → 20_ROS2_PX4_CV_STACK.md
- `TensorRT C++` --semantically_similar_to--> `TensorRT Inference`  [INFERRED] [semantically similar]
  15_CPP_KUTUPHANELERI.md → 20_ROS2_PX4_CV_STACK.md
- `rclcpp (ROS2)` --semantically_similar_to--> `ROS2 Framework`  [INFERRED] [semantically similar]
  15_CPP_KUTUPHANELERI.md → 20_ROS2_PX4_CV_STACK.md

## Hyperedges (group relationships)
- **Core Systems Stack** — mufreddat_docs_04_teknoloji_neden_var_c_plus_plus_20, mufreddat_docs_04_teknoloji_neden_var_cmake, mufreddat_docs_04_teknoloji_neden_var_linux_posix [INFERRED 0.75]
- **5G Core Elements** — mufreddat_docs_18_5g_distributed_sistem_amf, mufreddat_docs_18_5g_distributed_sistem_smf, mufreddat_docs_18_5g_distributed_sistem_upf [EXTRACTED 1.00]
- **Embedded→Robotics Pipeline** — phase_f5, phase_f6, phase_f7, embedded_rtos, ros2_px4_cv [INFERRED 0.85]
- **CV/AI Perception Pipeline** — phase_f8, pylib_pytorch, cpplib_tensorrt_cpp, ros2_opencv_pipeline, ros2_tensorrt_inference [INFERRED 0.85]
- **Savunma Sanayi Yazılım Stack'i** — phase_f10, phase_f11, phase_f12, radar_dsp, fiveg_distributed, embedded_rtos [INFERRED 0.85]

## Communities (20 total, 9 thin omitted)

### Community 0 - "C++ Kütüphane Ekosistemi"
Cohesion: 0.08
Nodes (30): C++ Kütüphane Kataloğu, Boost.Asio, Catch2/GTest, CMake, Eigen, FastDDS, GStreamer, Intel TBB (+22 more)

### Community 1 - "Müfredat Fazları ve Yol Haritası"
Cohesion: 0.15
Nodes (19): 365 Günlük ASELSAN/HAVELSAN Müfredatı, F0 — Bilgisayar ve Yazılım Temelleri, F1 — C++20, F10 — Radar / DSP / Communications, F11 — Verification / SIL / HIL, F12 — 5G / Distributed Systems, F13 — AI Engineering / Architecture / Portfolio, F2 — Linux / POSIX (+11 more)

### Community 2 - "C++ Mastery Spine Omurgası"
Cohesion: 0.12
Nodes (17): C++ Mastery Spine (50 Ünite), S1 Core Language, Concepts, Constexpr, Exception Safety, Move Semantics, Ranges, Templates (+9 more)

### Community 3 - "Radar / DSP / Sinyal İşleme"
Cohesion: 0.14
Nodes (14): FFTW, Beamforming, CFAR Algılama, DFT/FFT, Radar/DSP/Haberleşme Kataloğu, EKF/UKF, FIR/IIR Filtre, FMCW Radar (+6 more)

### Community 4 - "Embedded / RTOS / Gömülü Sistemler"
Cohesion: 0.17
Nodes (12): FreeRTOS API, ARM Cortex-M, CAN/CAN-FD, FreeRTOS, JTAG/SWD Debug, lwIP, QEMU ARM Simulation, Embedded / RTOS Stack (+4 more)

### Community 5 - "5G / Dağıtık Sistemler"
Cohesion: 0.18
Nodes (11): AMF, CAP Theorem, Consensus (Raft/Paxos), 5G / Distributed Systems, gNB, GTP-U Tunneling, Open5GS, Service Mesh (+3 more)

### Community 6 - "Performans ve Sayısal Hesaplama"
Cohesion: 0.20
Nodes (11): F8 — Computer Vision / TensorRT, F9 — Control / Reinforcement Learning, S4 Performance/Numerical, Aos Soa, Assembly Reading, Branch Prediction, Lto Pgo, Numerical Robustness (+3 more)

### Community 7 - "Python Kütüphaneleri"
Cohesion: 0.18
Nodes (11): FastAPI, Matplotlib, NumPy, ONNX, OpenCV Python, Pandas, Pytest, Scikit-learn (+3 more)

### Community 8 - "Robotik / ROS2 / PX4"
Cohesion: 0.22
Nodes (10): F6 — DDS / ROS2 / Gazebo, F7 — PX4 / MAVLink, S3 Embedded/Robotics C++, Coroutines, Cross Compilation, Dds Adapter, Deterministic Alloc, Freestanding (+2 more)

### Community 9 - "Linux Komut Referansı"
Cohesion: 0.22
Nodes (9): Build Tools (gcc, make, cmake), Container (Docker), Debug/Perf (gdb, valgrind, perf), Filesystem (ls, find, chmod, tar), Git Version Control, Linux Komut Referansı, Network Tools (tcpdump, iperf3, ss), Process Management (ps, top, kill) (+1 more)

### Community 10 - "Systems C++ (S2)"
Cohesion: 0.22
Nodes (9): S2 Systems C++, Abi Linker, Atomics, Binary Parsing, Cache Locality, Cmake Packaging, Epoll Asio, Fuzz Testing (+1 more)

## Knowledge Gaps
- **120 isolated node(s):** `C++20`, `CMake`, `Linux/POSIX`, `S1 Core Language`, `S2 Systems C++` (+115 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `365 Günlük ASELSAN/HAVELSAN Müfredatı` connect `Müfredat Fazları ve Yol Haritası` to `Robotik / ROS2 / PX4`, `C++ Mastery Spine Omurgası`, `Performans ve Sayısal Hesaplama`?**
  _High betweenness centrality (0.400) - this node is a cross-community bridge._
- **Why does `ROS2/PX4/CV Stack` connect `C++ Kütüphane Ekosistemi` to `Robotik / ROS2 / PX4`, `Performans ve Sayısal Hesaplama`?**
  _High betweenness centrality (0.202) - this node is a cross-community bridge._
- **Why does `C++ Kütüphane Kataloğu` connect `C++ Kütüphane Ekosistemi` to `Müfredat Fazları ve Yol Haritası`, `Radar / DSP / Sinyal İşleme`, `Embedded / RTOS / Gömülü Sistemler`?**
  _High betweenness centrality (0.190) - this node is a cross-community bridge._
- **What connects `C++20`, `CMake`, `Linux/POSIX` to the rest of the system?**
  _120 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `C++ Kütüphane Ekosistemi` be split into smaller, more focused modules?**
  _Cohesion score 0.07586206896551724 - nodes in this community are weakly interconnected._
- **Should `C++ Mastery Spine Omurgası` be split into smaller, more focused modules?**
  _Cohesion score 0.11764705882352941 - nodes in this community are weakly interconnected._
- **Should `Radar / DSP / Sinyal İşleme` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._