---
name: fullstack-webapp
description: "풀스택 웹앱 오케스트레이터. 요구사항→설계→프론트엔드→백엔드→테스트→배포를 에이전트 팀이 협업하여 개발."
---

# Fullstack Web App — 풀스택 웹앱 개발 파이프라인

웹앱(Django)의 요구사항→설계→프론트엔드→백엔드→테스트→배포를 에이전트 팀이 협업하여 개발한다.

## 실행 모드: full

## 워크플로우

### Phase 1: 설계 (architect)
architect가 요구사항 분석 → 아키텍처 설계 → API 명세 → DB 스키마 작성

### Phase 2: 병렬 개발
- **frontend-dev**: architect의 설계 기반 프론트엔드 구현
- **backend-dev**: architect의 설계 기반 백엔드 구현
- **devops-engineer**: 인프라/배포 설정 (high/epic route 시)

### Phase 3: 검증 (qa-engineer)
qa-engineer가 전체 코드 리뷰 + 테스트 → 🔴 필수 수정 시 재작업 (최대 2회)

## 팀원 간 소통

- architect 완료 → frontend/backend/devops/qa에게 설계 전달
- frontend ↔ backend: API 연동 이슈 실시간 소통
- qa → 개발자: 🔴 필수 수정 요청 → 재검증

## ForgeFlow Task

- **Task ID**: docs-update-v0111
- **Route**: small
