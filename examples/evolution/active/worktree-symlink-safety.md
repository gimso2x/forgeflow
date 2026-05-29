# worktree-symlink-safety
<!-- .forgeflow 전체 디렉터리를 symlink하면 file watcher ELOOP crash 발생; 비순환 서브디렉터리만 개별 symlink -->
Trigger: medium/high/epic route에서 worktree isolation 생성 시
Stage: clarify
Mode: advisory
Apply: worktree의 .forgeflow symlink는 .forgeflow/ 전체가 아닌 tasks, telemetry, evolution, defaults.md 등 비순환 항목만 개별 symlink로 생성. .forgeflow/worktrees/는 절대 symlink에 포함하지 않음.
Skip: small route (worktree 미사용)
