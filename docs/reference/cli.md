# CLI Reference

## 설치

```bash
python3 -m pip install "forgeflow-runtime @ git+https://github.com/gimso2x/forgeflow.git"
```

console script: `forgeflow`, `forgeflow-runtime` (동일 entrypoint)

## 명령어

### init

작업 디렉터리와 초기 artifact를 생성합니다.

```bash
forgeflow init --task-id <id> --objective "<목표>" --risk low|medium|high|critical
```

옵션:
- `--task-dir <path>` — 출력 디렉터리 지정 (기본: `.forgeflow/tasks/<task-id>/`)
- `--risk low|medium|high|critical` — 리스크 등급. route로는 각각 `small|medium|high|epic`에 매핑됩니다.

기존 `brief.json`이 있으면 실패합니다.

### status

작업 상태를 확인합니다.

```bash
forgeflow status --task-dir .forgeflow/tasks/<task-id>
```

### exec-stage

단일 stage를 실행합니다.

```bash
forgeflow exec-stage <stage> --task-dir .forgeflow/tasks/<task-id>
```

### execute

전체 파이프라인을 실행합니다.

```bash
forgeflow execute --task-dir .forgeflow/tasks/<task-id>
```

옵션:
- `--adapter claude|codex|generic` — 어댑터 선택
- `--real` — 실제 CLI 실행 모드

## 보조 스크립트

| 스크립트 | 용도 |
|---|---|
| `scripts/forgeflow_profile.py` | pipeline-profile.json 요약/비교 |
| `scripts/forgeflow_visual.py` | artifact를 Mermaid/Markdown으로 렌더 |
| `scripts/codex_plugin_doctor.py` | Codex plugin 설치 상태 진단 |
| `scripts/smoke_codex_plugin.py` | Codex plugin smoke test |
| `scripts/validate_structure.py` | 필수 디렉토리/파일 검증 |
| `scripts/validate_policy.py` | workflow/stages/route 정책 검증 |
| `scripts/release.py` — 버전 갱신 + 릴리즈 |  |
| `scripts/check_versions.py` | 6개 버전 소스 일치 검증 |

## 종료 코드

- `0` — 성공
- `1` — 일반 오류
- `2` — artifact 검증 실패
- `3` — gate 평가 실패

---

자세한 스크립트 설명은 [scripts/README.md](../../scripts/README.md)을 참고하세요.
