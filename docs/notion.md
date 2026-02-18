> ## Documentation Index
> Fetch the complete documentation index at: https://developers.notion.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Notion MCP

> Learn how to connect AI agents to your Notion workspace.

Connect your AI tools to Notion using the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction), an open standard that lets AI assistants interact with your Notion workspace.

## What is Notion MCP?

Notion MCP is our hosted server that gives AI tools secure access to your Notion workspace. It's designed to work seamlessly with popular AI assistants like Claude Code, Cursor, VS Code, ChatGPT, and more.

<Frame caption="High-level diagram of the MCP data flow, where Notion hosts both the MCP Server and [Notion's API](/reference/intro), and your tools contain [MCP clients](/guides/mcp/common-mcp-clients) that connect to the remote MCP server to access our tools.">
  <img src="https://mintcdn.com/notion-demo/LHm9qfrJYJOPRxs6/images/docs/97125b4c4172e71d0a2293523ebf17424f7fec9fab5852d4b6c0eba2eaa0200d-image.png?fit=max&auto=format&n=LHm9qfrJYJOPRxs6&q=85&s=d562ef536d8a47c8d67111577be2521b" data-og-width="1346" width="1346" data-og-height="518" height="518" data-path="images/docs/97125b4c4172e71d0a2293523ebf17424f7fec9fab5852d4b6c0eba2eaa0200d-image.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/notion-demo/LHm9qfrJYJOPRxs6/images/docs/97125b4c4172e71d0a2293523ebf17424f7fec9fab5852d4b6c0eba2eaa0200d-image.png?w=280&fit=max&auto=format&n=LHm9qfrJYJOPRxs6&q=85&s=af68f7e54780815a317ea56640867e30 280w, https://mintcdn.com/notion-demo/LHm9qfrJYJOPRxs6/images/docs/97125b4c4172e71d0a2293523ebf17424f7fec9fab5852d4b6c0eba2eaa0200d-image.png?w=560&fit=max&auto=format&n=LHm9qfrJYJOPRxs6&q=85&s=fe7500dbf7f7ab9ec308277aaedc91b8 560w, https://mintcdn.com/notion-demo/LHm9qfrJYJOPRxs6/images/docs/97125b4c4172e71d0a2293523ebf17424f7fec9fab5852d4b6c0eba2eaa0200d-image.png?w=840&fit=max&auto=format&n=LHm9qfrJYJOPRxs6&q=85&s=273a0bdbc24b778126449895a05a5ec5 840w, https://mintcdn.com/notion-demo/LHm9qfrJYJOPRxs6/images/docs/97125b4c4172e71d0a2293523ebf17424f7fec9fab5852d4b6c0eba2eaa0200d-image.png?w=1100&fit=max&auto=format&n=LHm9qfrJYJOPRxs6&q=85&s=f82d7dd81aebfff8beebefaf1b840d7d 1100w, https://mintcdn.com/notion-demo/LHm9qfrJYJOPRxs6/images/docs/97125b4c4172e71d0a2293523ebf17424f7fec9fab5852d4b6c0eba2eaa0200d-image.png?w=1650&fit=max&auto=format&n=LHm9qfrJYJOPRxs6&q=85&s=08ef721aa44c0b8e7cc210f9338578b2 1650w, https://mintcdn.com/notion-demo/LHm9qfrJYJOPRxs6/images/docs/97125b4c4172e71d0a2293523ebf17424f7fec9fab5852d4b6c0eba2eaa0200d-image.png?w=2500&fit=max&auto=format&n=LHm9qfrJYJOPRxs6&q=85&s=0562ea153a312ee88b86f4d023e102d5 2500w" />
</Frame>

### Why use Notion MCP?

* **Easy setup** — Connect through simple OAuth, with one-click installation for supported AI tools
* **Full workspace access** — AI tools can read and write to your Notion pages just like you can
* **Optimized for AI** — Built specifically for AI agents with efficient data formatting

### What can you do with Notion MCP?

* **Create documentation** — Generate PRDs, tech specs, and architecture docs from your research and project data
* **Search and find answers** — Let AI search across all your Notion and connected workspace content
* **Manage tasks** — Generate code snippets from task descriptions and update project status automatically
* **Build reports** — Create release notes, project updates, and performance reports from multiple sources
* **Plan campaigns** — Generate comprehensive briefs and track progress across marketing channels
