from __future__ import annotations

import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def _list_tool_names() -> list[str]:
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "liepin_workbuddy_mcp.server"],
        cwd=project_root,
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            response = await session.list_tools()
            return [tool.name for tool in response.tools]


def test_server_starts_and_lists_expected_mcp_tools() -> None:
    names = asyncio.run(_list_tool_names())
    assert names == [
        "liepin_search_jobs",
        "liepin_get_resume",
        "liepin_update_job_expectation",
        "liepin_apply_job",
    ]
