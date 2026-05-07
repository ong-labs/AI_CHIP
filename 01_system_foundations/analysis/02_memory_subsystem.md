# 02_memory_subsystem.md: Architectural Latency & Access Patterns

이 문서는 [02_cache_hierarchy_bench.py](../lab/02_cache_hierarchy_bench.py)를 통해 하드웨어의 메모리 지연 시간을 실측하고, 데이터 접근 패턴이 시스템 성능에 미치는 영향을 분석합니다.

---

## 1. 메모리 계층 구조 (Memory Hierarchy)

현대 컴퓨터 아키텍처는 속도, 용량, 가격의 균형을 맞추기 위해 계층적 저장 구조를 가집니다.

### 레이턴시 계층 (Latency Hierarchy)
DRAM 접근은 L1 캐시 접근보다 **약 100배** 느리며, 이 격차를 줄이는 것이 성능 최적화의 핵심입니다.

| 단계 | 크기 | 접근 시간 (Latency) |
| :--- | :--- | :--- |
| **Register** | ~32 × 8B | **< 1 ns** |
| **L1 cache** | 32~64 KB | **~1 ns** |
| **L2 cache** | 256 KB ~ 1 MB | **~3-5 ns** |
| **L3 cache** | 8~64 MB | **~10-30 ns** |
| **DRAM** | ~수 GB | **~80-150 ns** |

---

## 2. 핵심 개념 (Core Concepts)

*   **캐시 라인 (Cache Line)**: 캐시는 데이터를 바이트 단위가 아닌 **64 byte** 단위로 가져오며, `float32` 데이터 16개가 한 라인을 이룹니다.
*   **지역성 (Locality)**:
    *   **공간 지역성 (Spatial Locality)**: 인접 데이터를 곧 쓸 가능성.
    *   **시간 지역성 (Temporal Locality)**: 최근 쓴 데이터를 곧 다시 쓸 가능성.
*   **C-contiguous (Row-major)**: NumPy의 기본 메모리 배치 방식으로, 한 행(Row)이 메모리에 연속적으로 저장됩니다.

---

## 3. 실험 1: Pointer Chasing (지연 시간 실측)

### 실험 의도
무작위 순열을 통한 데이터 의존성 참조(`i = perm[i]`)로 CPU의 Prefetcher를 무력화하고, 순수 메모리 접근 지연 시간을 측정하여 계층 경계에서의 계단식 증가를 확인합니다.

### 실습 결과 (Actual Output)
사용자 환경에서 측정된 데이터는 다음과 같습니다.

| Size | ns/access | 단계 분석 (추정) |
| :--- | :--- | :--- |
| 1 KB | 81.1 | **L1/L2 Cache** |
| 4 KB | 77.2 | |
| 16 KB | 101.3 | |
| 64 KB | 85.9 | |
| 256 KB | 77.3 | |
| 1 MB | 88.7 | |
| 4 MB | 130.5 | **L3 Cache 전이** |
| 16 MB | 171.4 | |
| 64 MB | 186.5 | **DRAM 진입** |
| 256 MB | 203.2 | |

> **분석**: 데이터 크기가 4MB를 넘어서면서 레이턴시가 급격히 증가하며, 256MB 지점에서는 L1 대비 약 2.5배 이상의 지연이 발생함을 확인할 수 있습니다.

---

## 4. 실험 2: Row vs Column 접근 패턴

### 실험 의도
동일한 연산량이라도 메모리 접근 방향(행 방향 vs 열 방향)에 따라 성능이 달라짐을 수치로 확인합니다.

*   **행 방향 합 (axis=1, contiguous)**: 메모리 연속 접근으로 캐시 효율이 높음.
*   **열 방향 합 (axis=0, strided)**: 메모리 건너뛰기 접근으로 캐시 미스 유발 가능성 있음.

### 결과 분석
*   **axis=1 (row-wise)**: 6.38 ms
*   **axis=0 (col-wise)**: 3.52 ms
*   **Ratio col/row**: **0.55x**

> **ℹ️ NOTE**: 본 플랫폼(Apple Silicon 등)에서는 `col-wise`가 더 빠르게 측정되었습니다. 이는 Apple Accelerate와 같은 라이브러리가 메모리를 한 번 훑으며 L1 캐시에 들어가는 소량의 버퍼에 누적하는 Streaming Reduction 최적화를 수행했기 때문입니다.

---

## 5. 결론: 성능 병목의 원인 분석

1.  **인터프리터 오버헤드**: Python 루프가 매 iteration마다 바이트코드를 해석하는 부담을 가집니다.
2.  **캐시 비친화적 구조**: Python의 `list`는 객체 포인터의 배열로, 데이터가 메모리 곳곳에 흩어져 있어 접근 시마다 Cache Miss가 발생합니다.
3.  **패턴의 중요성**: NumPy 배열 안에서도 접근 패턴만으로 수 배의 성능 차이가 발생하며, 이는 하드웨어 아키텍처 이해가 성능 최적화의 필수임을 증명합니다.

---

## 6. 흔한 막힘 포인트 (Troubleshooting)

| 증상 | 원인 | 해결책 |
| :--- | :--- | :--- |
| **MemoryError** | 256 MB 이상의 배열이 RAM에 부담을 줌 | 최대 크기를 64 MB로 축소 |
| **그래프 평탄화** | `np.sum()` 등의 SIMD 연산이 캐시 단계를 가림 | **Pointer chasing**으로 대체 |
| **col-wise가 더 빠름** | Apple Accelerate 등 플랫폼 최적화 개입 | 정상적인 아키텍처 의존성 이슈로 이해 |
| **비율이 1.0 근처** | 행렬이 작아 전체가 L3에 들어감 | $N=4096$ 이상 사용 권장 |

---

## 💡 참고 사항 (Notes)

1. **숙련도 검증**: 본 문서에서 다룬 지연 시간 및 접근 패턴에 대한 이해도는 [02_memory_latency.md](../mastery/02_memory_latency.md)에서 퀴즈 형식을 통해 확인할 수 있습니다.
2. **플랫폼 의존성**: 메모리 지연 시간의 절대값과 접근 패턴별 성능 비율은 CPU 아키텍처(Intel, AMD, Apple Silicon 등) 및 OS의 메모리 관리 방식에 따라 상이할 수 있습니다.[cite: 1]
3. **데이터 시각화**: 실험 결과에 대한 시각적 지표는 [02_working_set_result.png](../lab/02_working_set_result.png) 파일을 참조해 주세요.
4. **학습 목차**: 전체 프로젝트의 구성과 학습 순서는 최상위 [README.md](../README.md)에서 확인 가능합니다.