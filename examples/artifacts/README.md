# Sample Artifacts

이 디렉토리는 core artifact schema 6종에 대한 최소 예시를 담는다.

## 포함 파일
- `brief.sample.json`
- `plan.sample.json`
- `decision-log.sample.json`
- `run-state.sample.json`
- `review-report-spec.sample.json`
- `review-report-quality.sample.json`
- `eval-record.sample.json`

## 의도
- schema가 실제로 어떤 모양을 기대하는지 보여준다
- docs와 policy 설명이 너무 추상적으로 뜨는 걸 막는다
- future validator가 sample fixtures를 이용해 regression check 하게 만든다

## 주의
이 파일들은 예시 fixture다.
실행 로그나 진짜 작업 이력으로 쓰는 게 아니라, contract를 설명하기 위한 샘플이다.
