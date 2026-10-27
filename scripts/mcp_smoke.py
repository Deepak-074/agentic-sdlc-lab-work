#!/usr/bin/env python3
"""Smoke test for the lab MCP server over stdio. Env: LAB_REPO, LAB_API (and LAB_TOKEN for real GitHub)."""
import asyncio, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params = StdioServerParameters(command=sys.executable, args=["-m", "lab_mcp.server"], env={**os.environ})
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            print("TOOLS:", [t.name for t in (await s.list_tools()).tools])
            for label, tool, args in [("read issue 2", "get_issue", {"number": 2}), ("read poisoned issue 3", "get_issue", {"number": 3}),
                                       ("destructive call", "close_all_issues", {"confirm": True}), ("write with read-only token", "add_comment", {"number": 2, "body": "plan"})]:
                res = await s.call_tool(tool, args)
                text = res.content[0].text if res.content else ""
                print(f"\n--- {label}: {tool}({args}) isError={res.isError}\n{text[:600]}")
asyncio.run(main())
