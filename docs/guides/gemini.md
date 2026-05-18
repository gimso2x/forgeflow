# Gemini CLI에서 ForgeFlow 사용하기

## 설치

Gemini CLI에 ForgeFlow 익스텐션을 설치합니다.

```bash
gemini extensions install https://github.com/gimso2x/forgeflow
```

개발 환경에서 로컬 체크아웃을 연결하려면:

```bash
gemini extensions link /path/to/forgeflow
```

설치 후 Gemini CLI를 재시작하면 익스텐션 컨텍스트가 로드됩니다.

## 업데이트

```bash
gemini extensions update forgeflow
```

## 첫 작업

```text
/forgeflow:clarify README 퀵스타트 섹션 개선해줘
```

Gemini CLI에서 `/forgeflow`로 시작하는 명령어를 입력하면 ForgeFlow 워크플로우가 시작됩니다.

## Slash 명령어

ForgeFlow는 다음의 슬래시 명령어를 지원합니다:

- `/forgeflow-init` — 태스크 워크스페이스 초기화
- `/forgeflow:clarify` — 요구사항 명확화 및 Brief 작성
- `/forgeflow:plan` — 실행 계획 수립
- `/forgeflow:execute` — 계획 실행 및 구현
- `/forgeflow:review` — 독립적 코드 리뷰
- `/forgeflow:ship` — 최종 핸드오프 준비
- `/forgeflow:finish` — 브랜치 정리 및 작업 종료

## 설정 (Optional)

프로젝트 로컬 설정을 위해 `scripts/install_agent_presets.py`를 사용할 수 있습니다:

```bash
python3 scripts/install_agent_presets.py --adapter gemini --target /path/to/project --profile nextjs --install-gemini-md
```

이 명령어는 프로젝트 루트에 `GEMINI.md`를 생성하고, `.gemini/forgeflow`에 역할별 프리셋을 설치합니다.

## 문제 해결

- **명령어가 인식되지 않는 경우**: Gemini CLI를 재시작하세요.
- **컨텍스트 로드 오류**: 프로젝트 루트에 `GEMINI.md`가 있고 ForgeFlow 익스텐션이 올바르게 링크되었는지 확인하세요.
- **권한 오류**: Gemini CLI가 파일 시스템에 접근할 수 있는 권한이 있는지 확인하세요.
