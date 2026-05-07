# 00. Docs: Knowledge Base & Reference

이 폴더는 AI 반도체 설계 및 가속기 최적화 학습 과정에서 필요한 **이론적 배경, 핵심 용어 정리, 그리고 공통 레퍼런스** 문서를 관리합니다. 각 Unit의 실습(Lab)을 진행하기 전이나 후, 지식의 무결성을 점검하기 위한 자료로 활용됩니다.

---

## 📑 문서 카탈로그

현재 보관된 문서들은 다음과 같습니다. 모든 문서는 학습 로드맵의 특정 단계와 유기적으로 연결되어 있습니다.

### 1. 하드웨어 가속기 기초 (Essentials)
* **[00_npu_essentials_q20.md](./00_npu_essentials_q20.md)**: NPU 및 AI 하드웨어 설계의 핵심 개념 20가지를 엄선하여 정리한 퀵 레퍼런스입니다. 
    * **주요 내용**: SIMD, 캐시 계층 구조, Systolic Array, 정밀도(INT8/32), 성능 지표(Latency/Throughput).

---

## 🛠️ 향후 추가 예정 문서 (Roadmap)

학습 진도에 따라 다음과 같은 문서들이 본 폴더에 업데이트될 예정입니다.

* **Glossary**: AI 반도체 및 컴퓨터 아키텍처 전문 용어 사전
* **Tool-chain Guide**: 시뮬레이션 및 분석 도구(Profiler) 사용 매뉴얼
* **Reading List**: 논문 및 기술 블로그 아카이브

---

## 🏗️ Directory Structure

```text
00_docs/
├── README.md
└── 00_npu_essentials_q20.md