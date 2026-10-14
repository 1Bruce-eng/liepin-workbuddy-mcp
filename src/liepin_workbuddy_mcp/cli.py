"""Safe subprocess adapter for the documented Liepin CLI."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Sequence


@dataclass(frozen=True)
class CliResult:
    data: Any
    stderr: str


class LiepinCliError(RuntimeError):
    """A sanitized error raised when liepin-cli cannot complete a request."""


class LiepinCli:
    def __init__(self, executable: str | None = None, timeout: int = 25) -> None:
        self.executable = executable or os.environ.get("LIEPIN_CLI_PATH") or "liepin-cli"
        self.timeout = timeout

    def _resolve_executable(self) -> str:
        resolved = shutil.which(self.executable)
        if resolved:
            return resolved
        # WorkBuddy may run MCP servers with a reduced PATH. Prefer the CLI
        # installed into the same isolated Python environment as this server.
        sibling = os.path.join(os.path.dirname(sys.executable), self.executable)
        if os.path.isfile(sibling) and os.access(sibling, os.X_OK):
            return sibling
        raise LiepinCliError(
            "未找到猎聘官方 CLI（liepin-cli）。请按猎聘授权页链接的 CLI 仓库安装，"
            "并确保命令可从 PATH 调用；也可设置 LIEPIN_CLI_PATH 指向可执行文件。"
        )

    @staticmethod
    def _safe_error(output: str) -> str:
        """Remove possible token-like values before returning CLI diagnostics."""
        token = os.environ.get("LIEPIN_USER_TOKEN", "")
        text = output.strip()
        if token:
            text = text.replace(token, "[已隐藏凭证]")
        # Hide common token-shaped values without depending on CLI error wording.
        import re

        text = re.sub(r"(?i)(x-user-token|token)(\s*[:=]\s*)[^\s,;]+", r"\1\2[已隐藏凭证]", text)
        return text[:2000] or "猎聘 CLI 返回非零状态，但没有提供可读错误信息。"

    def run_json(self, args: Sequence[str], *, timeout: int | None = None) -> CliResult:
        command = [self._resolve_executable(), *args, "--output", "json"]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout or self.timeout,
                check=False,
                env=os.environ.copy(),
            )
        except subprocess.TimeoutExpired as exc:
            raise LiepinCliError(f"猎聘 CLI 调用超时（{exc.timeout} 秒）。请稍后重试。") from None
        except OSError as exc:
            raise LiepinCliError(f"无法启动猎聘 CLI：{exc.strerror or '执行失败'}") from None

        if completed.returncode != 0:
            diagnostic = self._safe_error(completed.stderr or completed.stdout)
            raise LiepinCliError(f"猎聘 CLI 执行失败（退出码 {completed.returncode}）：{diagnostic}")

        stdout = completed.stdout.strip()
        if not stdout:
            return CliResult(data=None, stderr=completed.stderr.strip())
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            # Never guess a schema from human-readable CLI output.
            raise LiepinCliError(
                "猎聘 CLI 本次没有返回有效 JSON。为避免误解析，未将输出当作职位或简历数据；"
                "请检查 CLI 版本与 `--output json` 支持情况。"
            ) from None
        return CliResult(data=data, stderr=completed.stderr.strip())

    def search_jobs(
        self,
        *,
        job_name: str | None = None,
        address: str | None = None,
        salary_floor: str | None = None,
        salary_cap: str | None = None,
        salary_kind: str | None = None,
        company_name: str | None = None,
        work_experience: str | None = None,
        edu_level: str | None = None,
        comp_nature: str | None = None,
        page: int = 0,
    ) -> CliResult:
        if page < 0:
            raise ValueError("page 必须是大于等于 0 的整数。")
        args: list[str] = ["job", "search", "--page", str(page)]
        options = {
            "--job-name": job_name,
            "--address": address,
            "--salary-floor": salary_floor,
            "--salary-cap": salary_cap,
            "--salary-kind": salary_kind,
            "--company-name": company_name,
            "--work-experience": work_experience,
            "--edu-level": edu_level,
            "--comp-nature": comp_nature,
        }
        for option, value in options.items():
            if value is not None:
                cleaned = value.strip()
                if cleaned:
                    args.extend([option, cleaned])
        return self.run_json(args)

    def get_resume(self) -> CliResult:
        return self.run_json(["resume", "get"])

    def apply_job(self, *, job_id: int, job_kind: str) -> CliResult:
        if job_id <= 0:
            raise ValueError("job_id 必须是正整数。")
        if job_kind not in {"1", "2"}:
            raise ValueError("job_kind 必须原样取自猎聘职位搜索结果，且 CLI 当前仅支持 '1' 或 '2'。")
        return self.run_json(["job", "apply", "--job-id", str(job_id), "--job-kind", job_kind])

    def update_job_want(
        self, *, record_id: int, fields: dict[str, Any], confirmation: str
    ) -> CliResult:
        if confirmation != "确认更新猎聘求职期望":
            raise ValueError("更新简历前必须提供 confirmation='确认更新猎聘求职期望'。")
        if record_id <= 0:
            raise ValueError("record_id 必须是 resume get 返回的求职期望记录 ID。")
        allowed = {
            "jobtitle": "--jobtitle",
            "dq": "--dq",
            "wantSalaryLow": "--want-salary-low",
            "wantSalaryHigh": "--want-salary-high",
            "wantSalaryMonths": "--want-salary-months",
            "workType": "--work-type",
            "workweek": "--workweek",
            "practiceMonths": "--practice-months",
        }
        unknown = sorted(set(fields) - set(allowed))
        if unknown:
            raise ValueError(f"不支持的求职期望字段：{', '.join(unknown)}")
        if not fields:
            raise ValueError("至少提供一个需要更新的求职期望字段。")

        args = ["resume", "update-job-want", "--id", str(record_id)]
        for field_name, value in fields.items():
            if value is None:
                continue
            option = allowed[field_name]
            if isinstance(value, (dict, list)):
                raise ValueError(f"字段 {field_name} 暂不支持复杂类型；请使用猎聘 CLI 已记录的简单参数格式。")
            args.extend([option, str(value)])
        return self.run_json(args)
