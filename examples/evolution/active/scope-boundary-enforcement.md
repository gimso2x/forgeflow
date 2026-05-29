# scope-boundary-enforcement
<!-- scope 파일 수가 route 임계값을 초과하면 자동 경고; review에서 boundary 위반 탐지 -->
Trigger: clarify 단계에서 scope_files 산정 시
Stage: clarify, review
Mode: advisory
Apply: scope_boundary를 brief.md에 명시적으로 기록하고 boundary_status(within/at_limit/exceeds)를 산정. exceeds 시 scope split 권장 advisory 발행. review에서 scope_boundary_violations 필드로 검증.
Skip: exact-output, label-only, dry-run 모드
