# Scripts

## 목적
P0에서 필요한 최소 자동화를 둔다.

## 포함 스크립트
- `validate_context_paths.py` : README/AGENTS/CLAUDE/CODEX의 repo-local path 참조가 실제 파일을 가리키는지 검증
- `validate_structure.py` : 필수 디렉토리/파일 존재 검증
- `validate_policy.py` : workflow/stages/routes/schema 핵심 규칙 검증
- `generate_adapters.py` : canonical policy와 prompt를 target별 generated output으로 변환
- `validate_generated.py` : generated 산출물이 최소 규칙을 지키는지 검증
- `validate_sample_artifacts.py` : sample artifact fixture가 schema와 맞는지 검증
- `run_runtime_sample.py` : runtime sample을 disposable fixture copy에서 실행해서 tracked example이 더러워지지 않게 보호
- `setup.ps1` : Windows PowerShell에서 `.venv`를 만들고 dependency/environment check를 실행
- `validate.ps1` : Windows PowerShell에서 repo-managed `.venv\Scripts\python.exe`로 핵심 validation smoke 실행
- `run_orchestrator.ps1` : Windows PowerShell용 `run_orchestrator.py` wrapper
- `install_codex_plugin.py` : ForgeFlow를 home-local Codex plugin marketplace에 등록
- `install_codex_plugin.ps1` : Windows PowerShell용 Codex plugin marketplace 설치 wrapper
- `bootstrap_codex_plugin.py` : checkout 없이 raw GitHub URL에서 실행하는 Codex plugin 설치 bootstrap
- `codex_plugin_doctor.py` : Codex CLI, local marketplace, plugin root, project preset/CODEX 상태를 읽기 전용으로 진단
- `forgeflow_profile.py` : `pipeline-profile.json` 성능 artifact를 요약/병목 분석/비교
- `forgeflow_visual.py` : brief/plan/review artifact를 Mermaid 또는 Markdown 다이어그램으로 렌더링
- `visual-companion.cjs` : 로컬 브라우저 Mermaid companion 서버(WebSocket + POST `/diagram`, 기본 포트 8765)

## 권장 실행 순서
make target이 repo-managed `.venv`를 사용하므로 fresh clone에서는 아래 순서로 실행한다.

make setup
make check-env
make validate

Windows PowerShell에서는 아래 wrapper를 사용할 수 있다.

```powershell
.\scripts\setup.ps1
.\scripts\validate.ps1
.\scripts\run_orchestrator.ps1 init --task-id my-task-001 --objective "Update README quickstart" --risk low
```

## Codex plugin marketplace

Codex 앱에서 ForgeFlow를 local plugin entry로 노출하려면:

```bash
curl -fsSL https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py | python3 - -- --force
```

이미 checkout 안에 있다면:

```bash
python3 scripts/install_codex_plugin.py
```

Windows PowerShell:

```powershell
.\scripts\install_codex_plugin.ps1
```

Checkout 없이 PowerShell에서 bootstrap할 때는 `irm ... | python -`을 사용할 수 있다. `python` 대신 Windows launcher만 있는 환경에서는 checkout 안의 `install_codex_plugin.ps1` wrapper를 사용한다.

## Runtime sample
make target이 repo-managed `.venv`를 사용하므로 fresh clone에서는 아래 순서로 실행한다.

```bash
make setup
make check-env
make runtime-sample
```

- `runtime-sample`은 `scripts/run_runtime_sample.py --fixture-dir examples/runtime-fixtures/small-doc-task --route small`을 repo-managed Python으로 실행한다.
- `--fixture-dir`는 task fixture 디렉터리를 가리켜야 하며, 파일 경로면 명시적 `ERROR:`로 실패한다.
- disposable copy에서 실행하므로 tracked fixture가 dirty 상태로 남지 않는다.
- 임시 workspace는 실행 종료와 함께 지워지므로, 출력에는 disposable workspace 경로를 싣지 않는다.

## Performance profile

`run_route()`가 쓴 `pipeline-profile.json`은 아래 helper로 확인한다.

```bash
python3 scripts/forgeflow_profile.py summary .forgeflow/tasks/<task-id>
python3 scripts/forgeflow_profile.py bottlenecks .forgeflow/tasks/<task-id> --top 3
python3 scripts/forgeflow_profile.py compare .forgeflow/tasks/<baseline> .forgeflow/tasks/<candidate>
```

각 명령은 `--json`을 지원한다. 인자는 task directory 또는 `pipeline-profile.json` 파일 경로 둘 다 가능하다.

## Visual companion

설계/리뷰 artifact를 빠르게 시각화하려면 Python helper로 Mermaid 또는 Markdown을 생성한다.

```bash
python3 scripts/forgeflow_visual.py clarify .forgeflow/tasks/<task-id>/brief.json --format markdown
python3 scripts/forgeflow_visual.py plan .forgeflow/tasks/<task-id>/plan.json --format mermaid
python3 scripts/forgeflow_visual.py review .forgeflow/tasks/<task-id>/review-report.json --format markdown
```

브라우저에서 실시간으로 보려면 dependency-free Node 서버를 띄운 뒤 Mermaid source를 전송한다.

```bash
node scripts/visual-companion.cjs
python3 scripts/forgeflow_visual.py plan .forgeflow/tasks/<task-id>/plan.json \
  | curl -fsS -X POST --data-binary @- http://127.0.0.1:8765/diagram
```

브라우저는 `http://127.0.0.1:8765`를 열면 된다. 포트는 `FORGEFLOW_VISUAL_PORT=9876 node scripts/visual-companion.cjs`처럼 바꿀 수 있다.
