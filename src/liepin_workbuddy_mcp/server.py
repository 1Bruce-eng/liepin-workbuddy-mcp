"""MCP server exposing the documented Liepin CLI to WorkBuddy."""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from .cli import LiepinCli, LiepinCliError

mcp = FastMCP("liepin-workbuddy")
cli = LiepinCli()


def _render_result(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
def liepin_search_jobs(
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
) -> str:
    """使用猎聘官方 CLI 搜索职位。薪资和筛选值按猎聘 CLI 支持格式原样传入；page 从 0 开始。

    返回官方 CLI 原始 JSON，不假设字段结构。调用前应确认目标城市、岗位和薪资条件已明确。
    """
    try:
        result = cli.search_jobs(
            job_name=job_name,
            address=address,
            salary_floor=salary_floor,
            salary_cap=salary_cap,
            salary_kind=salary_kind,
            company_name=company_name,
            work_experience=work_experience,
            edu_level=edu_level,
            comp_nature=comp_nature,
            page=page,
        )
        return _render_result(result.data)
    except (LiepinCliError, ValueError) as exc:
        return f"错误：{exc}"


@mcp.tool()
def liepin_get_resume() -> str:
    """读取当前猎聘账号简历。仅返回猎聘官方 CLI 的原始 JSON 数据，不会保存副本。"""
    try:
        return _render_result(cli.get_resume().data)
    except LiepinCliError as exc:
        return f"错误：{exc}"


@mcp.tool()
def liepin_update_job_expectation(
    record_id: int,
    jobtitle: str | None = None,
    dq: str | None = None,
    wantSalaryLow: int | None = None,
    wantSalaryHigh: int | None = None,
    wantSalaryMonths: int | None = None,
    workType: str | None = None,
    workweek: int | None = None,
    practiceMonths: int | None = None,
    confirmation: str = "",
) -> str:
    """更新猎聘的求职期望。写操作必须在用户查看更新字段后获得其明确确认。

    confirmation 必须精确为“确认更新猎聘求职期望”；record_id 必须来自简历查询结果。
    支持 jobtitle、dq、wantSalaryLow、wantSalaryHigh、wantSalaryMonths、workType、workweek 和 practiceMonths。
    """
    fields = {
        "jobtitle": jobtitle,
        "dq": dq,
        "wantSalaryLow": wantSalaryLow,
        "wantSalaryHigh": wantSalaryHigh,
        "wantSalaryMonths": wantSalaryMonths,
        "workType": workType,
        "workweek": workweek,
        "practiceMonths": practiceMonths,
    }
    fields = {name: value for name, value in fields.items() if value is not None}
    try:
        result = cli.update_job_want(record_id=record_id, fields=fields, confirmation=confirmation)
        return _render_result(result.data)
    except (LiepinCliError, ValueError) as exc:
        return f"错误：{exc}"


@mcp.tool()
def liepin_apply_job(job_id: int, job_kind: str, confirmation: str) -> str:
    """向猎聘投递指定职位。投递不可轻易撤回，必须先展示职位详情并取得用户明确确认。

    job_id 和 job_kind 必须来自本次猎聘职位搜索结果；job_kind 不得猜测。confirmation 必须精确为“确认投递该猎聘职位”。
    """
    if confirmation != "确认投递该猎聘职位":
        return "错误：投递已阻止。请先展示职位名称、公司、薪资、地点等可得详情，并获得用户明确确认；随后传 confirmation='确认投递该猎聘职位'。"
    try:
        result = cli.apply_job(job_id=job_id, job_kind=job_kind)
        return _render_result(result.data)
    except (LiepinCliError, ValueError) as exc:
        return f"错误：{exc}"


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
