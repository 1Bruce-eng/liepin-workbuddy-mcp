from __future__ import annotations

import json
import subprocess
from typing import Any

import pytest

from liepin_workbuddy_mcp import cli as cli_module
from liepin_workbuddy_mcp.cli import LiepinCli, LiepinCliError


class StubLiepinCli(LiepinCli):
    def __init__(self) -> None:
        super().__init__(executable="liepin-cli")
        self.command: list[str] | None = None

    def _resolve_executable(self) -> str:
        return "/opt/bin/liepin-cli"


def stub_subprocess(
    monkeypatch: pytest.MonkeyPatch,
    *,
    stdout: str = "{}",
    stderr: str = "",
    returncode: int = 0,
) -> list[list[str]]:
    commands: list[list[str]] = []

    def run(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, returncode, stdout, stderr)

    monkeypatch.setattr(cli_module.subprocess, "run", run)
    return commands


def test_search_maps_supported_options_and_json_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    commands = stub_subprocess(monkeypatch, stdout='{"jobs": []}')
    data = StubLiepinCli().search_jobs(
        job_name="产品经理",
        address="深圳",
        salary_floor="25",
        salary_cap="35",
        page=2,
    )
    assert data.data == {"jobs": []}
    assert commands[0] == [
        "/opt/bin/liepin-cli",
        "job",
        "search",
        "--page",
        "2",
        "--job-name",
        "产品经理",
        "--address",
        "深圳",
        "--salary-floor",
        "25",
        "--salary-cap",
        "35",
        "--output",
        "json",
    ]


def test_search_rejects_negative_page_without_invoking_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    commands = stub_subprocess(monkeypatch)
    with pytest.raises(ValueError, match="page"):
        StubLiepinCli().search_jobs(page=-1)
    assert commands == []


def test_apply_rejects_unknown_job_kind_without_invoking_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    commands = stub_subprocess(monkeypatch)
    with pytest.raises(ValueError, match="job_kind"):
        StubLiepinCli().apply_job(job_id=123, job_kind="2 or guessed")
    assert commands == []


def test_apply_uses_job_id_and_job_kind_from_search(monkeypatch: pytest.MonkeyPatch) -> None:
    commands = stub_subprocess(monkeypatch, stdout='{"ok": true}')
    result = StubLiepinCli().apply_job(job_id=123, job_kind="2")
    assert result.data == {"ok": True}
    assert commands[0] == [
        "/opt/bin/liepin-cli",
        "job",
        "apply",
        "--job-id",
        "123",
        "--job-kind",
        "2",
        "--output",
        "json",
    ]


def test_resume_expectation_update_requires_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    commands = stub_subprocess(monkeypatch, stdout='{"ok": true}')
    cli = StubLiepinCli()
    with pytest.raises(ValueError, match="confirmation"):
        cli.update_job_want(
            record_id=1,
            fields={"jobtitle": "产品经理"},
            confirmation="",
        )
    assert commands == []
    cli.update_job_want(
        record_id=7,
        fields={"jobtitle": "产品经理", "dq": "深圳"},
        confirmation="确认更新猎聘求职期望",
    )
    assert commands[0] == [
        "/opt/bin/liepin-cli",
        "resume",
        "update-job-want",
        "--id",
        "7",
        "--jobtitle",
        "产品经理",
        "--dq",
        "深圳",
        "--output",
        "json",
    ]


def test_cli_errors_are_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIEPIN_USER_TOKEN", "private-secret")
    assert "private-secret" not in LiepinCli._safe_error("failed private-secret")
    assert "[已隐藏凭证]" in LiepinCli._safe_error("failed private-secret")


def test_cli_rejects_non_json_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_subprocess(monkeypatch, stdout="not-json")
    with pytest.raises(LiepinCliError, match="有效 JSON"):
        StubLiepinCli().search_jobs()
