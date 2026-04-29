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

## 권장 실행 순서
make target이 repo-managed `.venv`를 사용하므로 fresh clone에서는 아래 순서로 실행한다.

make setup
make check-env
make validate

Windows PowerShell에서는 아래 wrapper를 사용할 수 있다.

```powershell
.\scripts\setup.ps1
.\scripts\validate.ps1
```

## Codex plugin marketplace

Codex 앱에서 ForgeFlow를 local plugin entry로 노출하려면:

```bash
python3 scripts/install_codex_plugin.py
```

Windows PowerShell:

```powershell
.\scripts\install_codex_plugin.ps1
```

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
