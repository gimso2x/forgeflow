---
name: api-security-checklist
description: "API 보안 체크리스트. OWASP Top 10, 인증/인가, 입력 검증, Rate Limiting."
---

# API Security Checklist — API 보안

backend-dev 확장 스킬. API 보안 설계에 적용.

## OWASP API Top 10

| 순위 | 취약점 | 방어 |
|------|--------|------|
| A1 | BOLA (객체 수준 인가) | 모든 엔드포인트 객체 소유권 검증 |
| A2 | 인증 결함 | bcrypt, Rate Limit, MFA |
| A3 | 객체 속성 인가 | 응답 DTO 필드 필터링 |
| A4 | 무제한 리소스 소비 | Rate Limiting, 페이지네이션 |
| A5 | 기능 수준 인가 | RBAC 미들웨어 |

## 인증 패턴

- JWT: Access 15~30분, Refresh 7~14일, httpOnly cookie
- 비밀번호: bcrypt (cost 12+) 또는 Argon2id
- 로그인 실패 5회 → 15분 잠금

## 입력 검증

- 타입: Zod 스키마
- SQL Injection: ORM 파라미터화 쿼리
- XSS: 이스케이프 및 살균 처리
- 파일 업로드: MIME 타입 + 매직넘버

## ForgeFlow Task

- **Task ID**: docs-update-v0111
