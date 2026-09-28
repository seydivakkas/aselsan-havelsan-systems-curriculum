# 21_OGRENME_SIRASI
**Kaynak:** 365_Gun_ASELSAN_HAVELSAN_Tum_Kutuphaneler_Mekanizmalar_Guncel.xlsx
**Satır sayısı:** 53
**Sütun sayısı:** 11

| Sıra | Gün Aralığı | Faz | Önce Öğren | Sonra Öğren | Bu Aşamadaki Kütüphane/Araçlar | Mekanizma Zinciri | Mini Çıkış | Ana Proje Bağı | Zorunluluk | Gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1–5 | F0 Bilgisayar | bit/byte, binary/hex | CPU/register/instruction | Python repr/bin/hex; Linux hexdump/xxd | bit→byte→binary representation→integer | Bir binary frame'i hex olarak açıkla. | P1/P9 | Zorunlu | F0 |
| 2 | 6–10 | F0 Bilgisayar | CPU/RAM/cache | program/process | lscpu, free, ps | source→machine code→CPU↔cache↔RAM | CPU/memory diagramı. | Tümü | Zorunlu | F0 |
| 3 | 11–15 | F0 Programlama | algorithm/state/control flow | function/data structures | Python/C++ minimal syntax | input→state→branch/loop→output | Sensor average mini program. | Tümü | Zorunlu | F0 |
| 4 | 16–20 | F0 Tooling | terminal/debug | Git/compiler | bash, git, gcc/g++ | edit→compile→run→debug→commit | İlk repo + bugfix commit. | Tümü | Zorunlu | F0 |
| 5 | 21–30 | F1 C++ | types, functions, scope | pointers/references | STL basic, GDB | type→memory→lifetime | RAII öncesi memory lab. | P1/P9 | Zorunlu | CPP-GATE-1 |
| 6 | 31–40 | F1 C++ | RAII/class/ownership | move/value categories | unique_ptr, span, string_view | resource→owner→lifetime→move/view | Leak-free parser skeleton. | P1/P9 | Zorunlu | CPP-GATE-1 |
| 7 | 41–50 | F1 C++ | templates/STL | type traits/concepts | STL algorithms, concepts | generic algorithm→type contract | Serializable concept lab. | P1/P10 | Zorunlu | CPP-GATE-1 |
| 8 | 51–60 | F1 C++ | constexpr/ranges | exceptions/noexcept | C++20 stdlib | compile-time→pipeline→error path | Compile-time CRC table + range pipeline. | P1/P9 | Zorunlu | CPP-GATE-1 |
| 9 | 61–75 | F1 C++ | object model/STL invalidation | CRTP, tests, sanitizers | GoogleTest, ASan/UBSan, CMake | object layout→API→test→sanitizer | Typed telemetry parser v1. | P1 | Zorunlu | CPP-GATE-1 |
| 10 | 76–85 | F2 Linux | filesystem/permissions | process/file descriptor | pwd/ls/find/stat/chmod/ps | file→fd→process→kernel | Linux process/file lab. | P1/P12 | Zorunlu | F2 |
| 11 | 86–95 | F2 Linux | fork/exec/signal | ELF/shared libs | strace, ldd, nm, readelf | process→syscall→loader→library | Shared lib + strace. | P1/P11 | Zorunlu | CPP-GATE-2 |
| 12 | 96–105 | F2 Linux | mmap/shared memory | systemd/perf | mmap, systemctl, journalctl, perf | process→IPC→daemon→profiling | Telemetry daemon. | P1 | Zorunlu | F2 |
| 13 | 106–115 | F3 Concurrency | thread/jthread/mutex | condition_variable/semaphore | STL concurrency, TSan | threads→shared state→sync | Bounded producer-consumer. | P1/P10 | Zorunlu | CPP-GATE-2 |
| 14 | 116–125 | F3 Concurrency | atomics/memory order | SPSC/ring buffer/cache | atomic, perf | happens-before→lock-free→cache | Mutex vs SPSC benchmark. | P1/P10 | Zorunlu | CPP-GATE-2 |
| 15 | 126–130 | F3 IPC | pipe/socket/shared memory | backpressure | POSIX shm/mmap | producer→bounded IPC→consumer | Shared VehicleState. | P1 | Zorunlu | F3 |
| 16 | 131–140 | F4 Networking | IP/port/socket | TCP/UDP | ip, ss, ping, nc, socket APIs | IP→transport→socket endpoint | TCP/UDP echo + pcap. | P1/P12 | Zorunlu | F4 |
| 17 | 141–150 | F4 Protocol | endianness/framing | sequence/CRC/versioning | struct, Protobuf, FlatBuffers | bytes→frame→validation→typed message | Versioned binary protocol. | P1/P9 | Zorunlu | F4 |
| 18 | 151–160 | F4 Network Quality | async I/O | loss/jitter/reorder/fuzz | Boost.Asio, epoll, netem, Wireshark, libFuzzer | I/O→fault→metric→hardening | Async resilient telemetry. | P1 | Zorunlu | CPP-GATE-2 |
| 19 | 161–170 | F5 Embedded | Cortex-M/memory map/GPIO | timer/interrupt | CMSIS, STM32 HAL, Renode | register→peripheral→interrupt | Virtual timer/GPIO. | P9/P11 | Zorunlu | F5 |
| 20 | 171–180 | F5 Bus/Memory | UART/SPI/I2C/CAN | DMA/JTAG | Zephyr/STM32 HAL, SocketCAN, OpenOCD | bus→buffer→DMA→debug | 4-bus sensor lab. | P9 | Zorunlu | CPP-GATE-3 |
| 21 | 181–190 | F5 RTOS | task/scheduler/priority | queue/semaphore/mutex/watchdog | Zephyr, FreeRTOS | event→ISR→queue→task→deadline | RTOS sensor pipeline. | P9/P11 | Zorunlu | F5 |
| 22 | 191–195 | F5 Embedded Network | lwIP/Zephyr sockets | fault/recovery | lwIP, Renode | sensor→RTOS→IP→UDP | Avionics gateway MVP. | P9 | Zorunlu | F5 |
| 23 | 196–205 | F6 DDS | participant/topic/IDL | writer/reader/discovery | Fast DDS/Cyclone DDS | type→topic→endpoint→discovery | Typed DDS telemetry. | P2/P10 | Zorunlu | F6 |
| 24 | 206–215 | F6 DDS/ROS2 | QoS reliability/history/deadline | ROS2 node/topic/service/action | Fast DDS, rclcpp/rclpy | DDS QoS→ROS graph | QoS fault matrix. | P2/P10 | Zorunlu | F6 |
| 25 | 216–225 | F6 Robotics | executor/lifecycle/TF2 | Gazebo/rosbag/Nav2 | ROS2 Jazzy, Gazebo Harmonic, RViz2 | node→frames→sim sensors→navigation | UGV skeleton. | P2 | Zorunlu | F6 |
| 26 | 226–232 | F7 PX4 | UAV axes/autopilot | PX4 SITL/uORB | PX4, Gazebo, QGroundControl | sim plant↔autopilot internal state | x500 SITL flight. | P1/P4/P8 | Zorunlu | F7 |
| 27 | 233–239 | F7 MAVLink | heartbeat/telemetry | command/ACK/mission | MAVSDK, pymavlink, raw MAVLink | link→state→command transaction | C++ VehicleState gateway. | P1/P8 | Zorunlu | F7 |
| 28 | 240–245 | F7 Verification | uXRCE-DDS/failsafe | failure injection/ULog | PX4 faults, pyulog, ROS2 | fault→failsafe→log→verification | AMTVS v0.1. | P1 | Zorunlu | CPP-GATE-3 |
| 29 | 246–252 | F8 CV | pixels/color/OpenCV | geometry/calibration | NumPy, OpenCV | frame→geometry→corrected image | Camera calibration lab. | P3/P5/P7 | Zorunlu | F8 |
| 30 | 253–260 | F8 Video | codec/timestamp | GStreamer/RTP/RTSP | GStreamer, FFmpeg | camera→encode→network→decode→frame | RTP video pipeline. | P3/P5 | Zorunlu | F8 |
| 31 | 261–267 | F8 DL | PyTorch/data/model | detection/tracking | PyTorch, torchvision, ByteTrack | frame→detector→association→track | Tracking baseline. | P3 | Zorunlu | F8 |
| 32 | 268–272 | F8 VLM | embeddings/CLIP | segmentation | transformers, OpenCLIP, SAM | text/image→embedding→target→mask | VLM target selection. | P3 | Yüksek | F8 |
| 33 | 273–275 | F8 Deployment | ONNX | ORT/TensorRT | ONNX, ORT, TensorRT | model→graph→engine→benchmark | FP32/FP16 benchmark. | P3/P7 | Zorunlu | CPP-GATE-4 |
| 34 | 276–282 | F9 Control | dynamics/feedback | PID/state-space/LQR | NumPy/SciPy/Eigen | state→error→controller→plant | PID/LQR baseline. | P4 | Zorunlu | F9 |
| 35 | 283–288 | F9 Estimation | noise/covariance | Kalman/EKF | FilterPy/Eigen/GTSAM | measurements→innovation→state estimate | GPS/IMU fusion. | P4/P7 | Zorunlu | F9 |
| 36 | 289–295 | F9 RL | MDP/reward/policy | PPO/domain randomization/eval | PyTorch, Gymnasium, JAX optional | state→policy→action→reward | RL vs classical controller. | P4 | Yüksek | F9 |
| 37 | 296–301 | F10 DSP | sampling/IQ | FFT/window/filter | NumPy, SciPy, FFTW | samples→frequency representation | Spectrum/filter lab. | P7 | Zorunlu | F10 |
| 38 | 302–307 | F10 Radar | FMCW/range FFT | Doppler/range-Doppler | SciPy/FFTW | chirp→beat→range→velocity | Range-Doppler map. | P7 | Zorunlu | F10 |
| 39 | 308–311 | F10 Detection | CFAR/clutter | Pd/Pfa | NumPy/SciPy | noise estimate→threshold→detection | CFAR SNR sweep. | P7 | Zorunlu | F10 |
| 40 | 312–315 | F10 Tracking/Fusion | Kalman/gating/association | radar+EO fusion | Stone Soup/GTSAM/OpenCV | detections→tracks→fusion | Fused tracking MVP. | P7 | Zorunlu | CPP-GATE-4 |
| 41 | 316–321 | F11 Verification | requirements/acceptance | unit/integration/system | GTest, pytest, CTest | requirement→test→result | Traceability baseline. | P1/P5/P11 | Zorunlu | F11 |
| 42 | 322–327 | F11 Failure | fault/error/failure | netem/sensor/process faults | netem, pytest, PX4 faults | fault→detection→recovery→evidence | Fault campaign. | P1/P11 | Zorunlu | F11 |
| 43 | 328–335 | F11 SIL/HIL | SIL/virtual ECU | HIL/readiness | Renode, QEMU, Robot Framework | sim firmware→fault→verification | Virtual ECU verification. | P11 | Zorunlu | F11 |
| 44 | 336–339 | F12 5G | UE/gNB/core roles | AMF/SMF/UPF/AUSF/UDM/NRF | Open5GS, UERANSIM | UE→RAN→core NF graph | 5G architecture diagram. | P12 | Zorunlu | F12 |
| 45 | 340–343 | F12 5G Protocols | NAS/NGAP/SCTP | PFCP/GTP-U/SBI | Wireshark/tshark | registration→session→user plane | Annotated 5G pcap. | P12 | Zorunlu | F12 |
| 46 | 344–346 | F12 5G Lab | Open5GS core | UERANSIM attach/PDU | Docker/systemd, Open5GS, UERANSIM | config→register→session→traffic | UE ping/iperf. | P12 | Zorunlu | F12 |
| 47 | 347–350 | F12 Distributed | timeouts/retry/idempotency/backpressure | observability/chaos | gRPC, Redis, Prometheus, Grafana, netem | failure→policy→metric→recovery | 5G resilience dashboard. | P12/P10 | Zorunlu | F12 |
| 48 | 351–354 | F13 AI Engineering | FastAPI/Pydantic | Postgres/Redis | FastAPI, Pydantic, psycopg, Redis | schema→API→state/cache | Verification API. | P5/P6 | Yüksek | F13 |
| 49 | 355–358 | F13 RAG | embedding/retrieval | Qdrant/pgvector | transformers, Qdrant, PostgreSQL | documents→chunks→vectors→retrieval | Requirement retrieval baseline. | P6 | Yüksek | F13 |
| 50 | 359–361 | F13 Code Intelligence | AST/parser | Tree-sitter/Clang | Tree-sitter, libclang | source→syntax tree→symbol relation | C++ symbol→test mapping. | P6 | Yüksek | F13 |
| 51 | 362–363 | F13 AI Evaluation | golden set/precision/recall | structured output/hallucination tests | pytest, sklearn, Pydantic | prediction→evidence→metric | Eval regression suite. | P6/P8 | Zorunlu | F13 |
| 52 | 364–365 | F13 Release | CI/CD/observability | architecture/benchmark/release | GitHub Actions, Docker, Prometheus | build→test→benchmark→release | 6 pinned repo audit. | Tümü | Zorunlu | CPP-GATE-5 |
