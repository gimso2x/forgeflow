# Local CLI / Python 패키지 사용법

ForgeFlow를 plugin 없이 Python 패키지로 설치해서 CLI로 사용할 수 있습니다.

## 설치

```bash
# GitHub에서 직접 설치
python3 -m pip install "forgeflow-runtime @ git+https://github.com/gimso2x/forgeflow.git"

# 또는 clone 후 editable install
git clone https://github.com/gimso2x/forgeflow.git
cd forgeflow
python3 -m pip install -e .
```

제공되는 console script:

- `forgeflow` — 기본 runtime orchestrator entrypoint
- `forgeflow-runtime` — 이름 충돌을 피하고 싶을 때 쓰는 같은 entrypoint

둘 다 `python3 scripts/run_orchestrator.py`와 같은 surface를 실행합니다.

설치 확인:

```bash
forgeflow --help
forgeflow-runtime --help
```

## 기본 명령어

### 작업 초기화

```bash
forgeflow init --task-id my-task-001 --objective "README 퀵스타트 개선" --risk low
```

출력 위치는 기본 `.forgeflow/tasks/<task-id>/`. `--task-dir /path/to/task`로 변경 가능.

기존 `brief.json`이 있으면 덮어쓰지 않고 실패합니다.

### 상태 확인

```bash
forgeflow status --task-dir .forgeflow/tasks/my-task-001
```

### 프로파일 분석

```bash
python3 scripts/forgeflow_profile.py summary .forgeflow/tasks/<task-id>
```

`pipeline-profile.json`을 요약하고 병목을 보여줍니다. 두 task profile을 비교할 수도 있습니다.

### 시각화

```bash
python3 scripts/forgeflow_visual.py plan .forgeflow/tasks/<task-id>/plan.json --format mermaid
```

`brief.json`, `plan.json`, `review-report.json`을 Mermaid 또는 Markdown으로 렌더링합니다.

## 다른 에이전트와 함께 사용

ForgeFlow CLI는 특정 AI 에이전트에 종속되지 않습니다. artifact 구조와 workflow 규약을 제공하므로, 어떤 에이전트든 `.forgeflow/tasks/` 구조를 따라 작업할 수 있습니다.

Generic adapter가 이 용도로 제공됩니다. 자세한 건 [adapter model](../adapter-model.md)을 참고하세요.

## 관련 문서

- [전체 설치 가이드](../../INSTALL.md)
- [스크립트 참조](../../scripts/README.md)
- [Artifact model](../artifact-model.md)
- [Windows 사용법](windows.md)
