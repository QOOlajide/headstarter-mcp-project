*   [](/)
*   [AI features for apps](/ai/)
*   Slack MCP Server

On this page

# Slack MCP Server

Model Context Protocol (MCP) is an open standard designed to give AI agents a consistent, secure way to discover and use external data, tools, and services. MCP standardizes how applications provide context to LLMs.

With the Slack MCP server, your integrated apps can search channels, send messages, and perform other Slack actions through MCP clients. Workspace admins can approve and manage all MCP client integrations, keeping your Slack data safe. This guide discusses the overall MCP architecture, offerings from Slack, and how to develop with the Slack MCP server.

## MCP overview[​](#overview "Direct link to MCP overview")

There are three components to MCP: the host, client, and server.

*   The **MCP host** is the user-facing application where you interact with the AI. The hosts's job is managing the overall user experience, taking requests, and coordinating the flow of communication.
*   The **MCP client** is the component that handles the actual communication on the host side. You can think of this as a specialized bridge or adapter built into the host application. The host's job is to take the AI's internal request (i.e. "I need to read a file to answer this question") and translate it into a standard MCP request, maintaining a one-to-one connection with an MCP server.
*   The **MCP server** is the gateway to a specific external tool or data source that the AI needs access to. It is a separate program that acts as a secure wrapper around a system like a database, file system, or an external API, like Slack. It's job is to tell the client what it can do ("I can `read_file`, `query_database`, etc."), translate and execute the standardized MCP request from the client, and enforce security by ensuring the AI only accesses what it's allowed to.

There are a few distinctions to make between MCP and APIs.

Feature

APIs

MCP

Optimization

Software-to-software communication; deterministic integrations

AI model-to-data communication and agentic interactions

Implementation

Client (developer) must read documentation and write code to invoke specific endpoints and process the output

Client (agent) can ask the server, "What tools can you offer?" at runtime. The server responds with machine-readable tool descriptions that match the token provided. The same input might result in different output across runs.

Output

Machine readable (JSON) and entity IDs

Human readable (markdown) with hydrated names for entities

### Slack MCP server features[​](#slack-mcp "Direct link to Slack MCP server features")

The Slack MCP server provides tools for searching through Slack, retrieving and sending messages, managing canvases, and managing users. Each of these tools provides useful functionality for interacting with Slack; combine them for comprehensive integrations that grasp your team's context and history.

#### Searching throughout Slack[​](#searching "Direct link to Searching throughout Slack")

The MCP server can search for a variety of information found throughout a Slack workspace:

*   Messages and files — filter by date, user, and content type. Retrieve metadata and content.
*   Users in a workspace — filter by name (with partial name matching), email, and user ID. Retrieve user details and statuses.
*   Private and public channels — filter by channel name and description. Retrieve channel metadata.

#### Retrieving and sending messages[​](#retrieving-sending-messages "Direct link to Retrieving and sending messages")

The MCP server can retrieve and send messages throughout a Slack workspace:

*   Send messages — send messages to any type of conversation in Slack.
*   Draft messages — draft, format, and preview messages directly within AI clients.
*   Read channels — grab the complete message history of channels.
*   Read threads — grab complete message thread conversations.

#### Managing canvases[​](#managing-canvases "Direct link to Managing canvases")

The MCP server can interact and modify Slack canvases:

*   Create/update a canvas — create and share rich, formatted documents.
*   Read a canvas — export canvases as markdown files.

#### Managing users[​](#managing-users "Direct link to Managing users")

The MCP server can also fetch user info. It can access complete user profile info, including custom profile fields and statuses.

#### Example use cases[​](#use-cases "Direct link to Example use cases")

There are many possibilities with the Slack MCP server. Here are just a few ideas:

*   Create an AI assistant in Slack that can search through your team's Slack history to answer questions, find past decisions, and provide context for current projects.
*   Bring content from outside Slack into Slack via messages and canvases for discussion with coworkers.
*   Bring content from Slack to AI agents, providing them full context of projects that exist across multiple products.

* * *

## Transport protocol and endpoint[​](#transport-protocol "Direct link to Transport protocol and endpoint")

Slack supports JSON-RPC 2.0 over Streamable HTTP. All requests should be sent to:

```
https://mcp.slack.com/mcp
```

We do not support SSE-based connections or Dynamic Client Registration at this time.

* * *

## App Identity[​](#app-identity "Direct link to App Identity")

MCP clients must be backed by a registered Slack app with a fixed app ID and hardcode that app ID. This allows Slack to:

*   Let admins manage and approve your app/MCP client app using standard Slack app approval process.
*   Associate requests with your app for logging, rate limits, and access control.
*   Provide better support and visibility into usage.

If you're already using a Slack app for your integration, you can reuse it for MCP access.

Only directory-published apps or internal apps may use use MCP.

* * *

## Security concerns[​](#security "Direct link to Security concerns")

When using the Slack MCP server, please be mindful about connecting to or utilizing other MCP servers at the same time. Different servers may have their own security, stability, and usage characteristics, so think carefully before mixing them together. Use judgment when evaluating what to connect and share across environments. Using these clients means giving them access to your Slack data so you can use it as context while interacting with those apps.

Audit MCP activity with the associated [audit logs](/reference/audit-logs-api/methods-actions-reference/#mcp-server).

Only apps published in the Slack Marketplace and internal apps can use MCP at this time; unlisted apps are prohibited from using MCP.

* * *

## Authentication and Token Handling[​](#authentication "Direct link to Authentication and Token Handling")

Slack supports confidential OAuth for MCP clients. You'll need to use your app's `client_id` and `client_secret` for Slack OAuth.

If your MCP client supports OAuth 2.0 Authorization Server Metadata (RFC 8414) per MCP spec, you can rely on that. Users go through OAuth consent and authorize the app. You can initiate this OAuth request from your UX following standard MCP metadata discovery files:

*   `https://mcp.slack.com/.well-known/oauth-protected-resource`
*   `https://mcp.slack.com/.well-known/oauth-authorization-server`

PKCE support is coming soon

If you wish to use desktop clients, [contact](https://slack.com/help/requests/new) Slack support to get PKCE turned on.

### OAuth URL and endpoints[​](#oauth-endpoints "Direct link to OAuth URL and endpoints")

*   Authorization endpoint for Slack user tokens: `https://slack.com/oauth/v2_user/authorize`
*   Token endpoint for Slack user tokens: `https://slack.com/api/oauth.v2.user.access` (method docs [here](/reference/methods/oauth.v2.user.access))
*   If you also want to generate bot tokens (for in-Slack experience), follow instructions [here](/authentication/).

### OAuth scopes needed on user token for different tools[​](#oauth-scopes "Direct link to OAuth scopes needed on user token for different tools")

*   Search messages/channels: [`search:read.public`](/reference/scopes/search.read.public), [`search:read.private`](/reference/scopes/search.read.private), [`search:read.mpim`](/reference/scopes/search.read.mpim), [`search:read.im`](/reference/scopes/search.read.im)
*   Search files: [`search:read.files`](/reference/scopes/search.read.files)
*   Search users: [`search:read.users`](/reference/scopes/search.read.users)
*   Send message: [`chat:write`](/reference/scopes/chat.write)
*   Read a channel/thread: [`channels:history`](/reference/scopes/channels.history), [`groups:history`](/reference/scopes/groups.history), [`mpim:history`](/reference/scopes/mpim.history), [`im:history`](/reference/scopes/im.history)
*   Canvas create/update: [`canvases:read`](/reference/scopes/canvases.read), [`canvases:write`](/reference/scopes/canvases.write)
*   User profile/email: [`users:read`](/reference/scopes/users.read), [`users:read.email`](/reference/scopes/users.read.email)

* * *

## Developing with the Slack MCP server[​](#how-to-use "Direct link to Developing with the Slack MCP server")

MCP clients integrate with Slack by sending standard JSON-RPC 2.0 requests as defined by the MCP specification. Since Slack hosts and manages the MCP Server, handling the tool logic on your behalf, implementing the connection is simple.

The following instructions use the Bolt for JavaScript [Slack MCP Server Template app](https://github.com/slack-samples/bolt-js-slack-mcp-server) to show how to connect a Slack app to the Slack MCP server. While creating a new app is not necessary to start using the MCP server, we show creating a new app for the sake of example here.

Free sandbox

Join the Slack [Developer Program](https://api.slack.com/developer-program) for access to a free sandbox where you can build and experiment with apps outside of a production environment.

### Create an app[​](#new-app "Direct link to Create an app")

The first step to using the Slack MCP server in your Slack app is to create an app in the [app settings](https://api.slack.com/apps?new_app=1), then select **From a manifest**. Select a workspace where your app can live, then replace the JSON manifest with that of the [`manifest.json`](https://github.com/slack-samples/bolt-js-slack-mcp-server/blob/main/manifest.json) file from the sample app, also shown here:

`manifest.json`

```
{  "display_information": {      "name": "Slack MCP Sample"  },  "features": {      "app_home": {          "home_tab_enabled": false,          "messages_tab_enabled": true,          "messages_tab_read_only_enabled": false      },      "bot_user": {          "display_name": "Slack MCP Sample",          "always_online": true      },      "assistant_view": {          "assistant_description": "Sample that demonstrates the use of Slack's MCP server",          "suggested_prompts": []      }  },  "oauth_config": {      "redirect_urls": [          "https://example.ngrok-free.app/slack/oauth_redirect"      ],      "scopes": {          "user": [              "chat:write",              "canvases:write"          ],          "bot": [              "assistant:write",              "channels:history",              "chat:write",              "groups:history",              "im:history",              "mpim:history"          ]      }  },  "settings": {      "event_subscriptions": {          "request_url": "https://example.ngrok-free.app/slack/events",          "bot_events": [              "assistant_thread_context_changed",              "assistant_thread_started",              "message.im"          ]      },      "interactivity": {          "is_enabled": true,          "request_url": "https://example.ngrok-free.app/slack/events"      },      "org_deploy_enabled": true,      "socket_mode_enabled": false,      "token_rotation_enabled": false  }}
```

Enable the app for MCP by navigating to the **Agents & AI Apps** sidebar section and toggle **On** the **Model Context Protocol** feature.

![MCP setting](/assets/images/mcp_feature-bfe8c78372d2b7d24e1ff8d1721625dd.png)

### Add scopes[​](#add-scopes "Direct link to Add scopes")

After following the prompts to create the app, you land on the **Basic Information** page of the app settings. Select **OAuth & Permissions** from the left sidebar and scroll down to the **Scopes** section. Which scopes your app requires depends on what actions you'd like it to take. You can see on this page which scopes the template has added.

The scopes listed below are the scopes related to MCP server tools. Add them to the user token.

MCP tool

User scope needed

Search messages/channels

[`search:read.public`](/reference/scopes/search.read.public), [`search:read.private`](/reference/scopes/search.read.private), [`search:read.mpim`](/reference/scopes/search.read.mpim), [`search:read.im`](/reference/scopes/search.read.im)

Search files

[`search:read.files`](/reference/scopes/search.read.files)

Search users

[`search:read.users`](/reference/scopes/search.read.users)

Send a message

[`chat:write`](/reference/scopes/chat.write)

Read a channel/thread

[`channels:history`](/reference/scopes/channels.history), [`groups:history`](/reference/scopes/groups.history), [`mpim:history`](/reference/scopes/mpim.history), [`im:history`](/reference/scopes/im.history)

Create/update a canvas

[`canvases:read`](/reference/scopes/canvases.read), [`canvases:write`](/reference/scopes/canvases.write)

Read user profile/email

[`users:read`](/reference/scopes/users.read), [`users:read.email`](/reference/scopes/users.read.email)

### Add a redirect URL[​](#add-redirect-url "Direct link to Add a redirect URL")

After adding the scopes, scroll back up on the page to **Redirect URLs**. Add a redirect URL and save it.

Tip

If you do not have a redirect URL available for testing, we recommend using [ngrok](https://ngrok.com/docs/what-is-ngrok#getting-started-expose).

Using ngrok, the format of the URL might look something like this:

```
https:///b21a03fd701b.ngrok-free.app/slack/oauth_redirect
```

Enabling the app for OAuth is needed in order to utilize user tokens in the app, and therefore allow the app to take action on the user's behalf.

### Install and run[​](#install "Direct link to Install and run")

Once your URL is saved, click to **Install** the app and follow the prompts.

Next, clone the sample app repo with the following command in your terminal:

```
# Clone this project onto your machinegit clone https://github.com/slack-samples/bolt-js-slack-mcp-server.git
```

Then, navigate to the directory and open it in VSCode.

```
cd bolt-js-slack-mcp-servercode .
```

Rename the `.env.sample` file to `.env` and copy and paste your environment variable values there. Go back to the app settings and navigate to the **Basic Information** page for these values. For the `SLACK_INSTALL_URL`, use the same base redirect link you used earlier, with `install` appended. Following the prior example, it would look like this:

```
https://b21a03fd701b.ngrok-free.app/slack/install
```

The install link is needed for each user to install the app so that the MCP server can query Slack on behalf of the invoking user.

The OpenAI key must be obtained by creating an OpenAI account and [creating a new key](https://platform.openai.com/api-keys). Once these keys are saved, go back to your terminal and install, then start the app:

```
# Install dependenciesnpm install# Run Bolt servernpm start
```

### Update event subscriptions[​](#event-subscriptions "Direct link to Update event subscriptions")

With your app running, there is one more update to make in the app settings. Navigate to **Event Subscriptions** and update the URL to the base of the redirect URL, with `/events` appended, so that it looks something like:

```
https://b21a03fd701b.ngrok-free.app/slack/events
```

Slack will verify the URL, then you should be good to test the app!

Make sure you install the app using the install link, then create a new chat with the app to test its functionality. Upon creation of the new chat, the user is prompted with two static options that demonstrate either sending a message to #general, or creating a new canvas – both as and on behalf of the user! You can see the code behind this in the app's [`user-message.js`](https://github.com/slack-samples/bolt-js-slack-mcp-server/blob/main/listeners/assistant/user-message.js) file.

### The MCP call[​](#mcp-call "Direct link to The MCP call")

The MCP server is used as a tool that is provided alongside an API call to an LLM. Each LLM has a different way of formatting requests including an MCP server, so verify with their documentation for how to format it in your code. Here are a couple of examples.

In the sample app we created above, for example, the call to OpenAI using the Slack MCP server as a tool looks like this:

```
    const llmResponse = await openai.responses.create({        model: 'gpt-4o-mini',        input: `System: ${DEFAULT_SYSTEM_CONTENT}\n\n${parsedThreadHistory}\nUser: ${message.text}`,        tools: [            {                type: 'mcp',                server_label: 'slack',                server_url: 'https://mcp.slack.com/mcp',                headers: {                    Authorization: `Bearer ${context.userToken}`,                },                require_approval: 'never',            },        ],        stream: true,    });
```

For a call to Anthropic, it may look like this:

```
    const response = await client.beta.messages.create({        model: "claude-sonnet-4-20250514",        max_tokens: 1000,        system: DEFAULT_SYSTEM_CONTENT,        messages: [            ...parsedThreadHistory,            { role: "user", content: message.text }        ],        mcp_servers: [            {                type: 'url',                url: `https://mcp.slack.com/mcp`,                 name: 'slack',            }        ],        // The Anthropic SDK's structure for beta features might vary.     });
```

Check out the full code for the MCP sample app [here](https://github.com/slack-samples/bolt-js-slack-mcp-server).

* * *

## Available clients[​](#partner-clients "Direct link to Available clients")

Another method of using the Slack MCP server (if building a Slack app is not your jam) is accessing it via a partner application. The Slack MCP server is available in these select partner-built clients, no coding needed:

*   [Claude.ai](https://claude.ai)
*   [Claude Code](https://code.claude.com)
*   [Perplexity](https://perplexity.ai)
*   [Cursor](https://cursor.com)

## Related content[​](#related "Direct link to Related content")

✨ Check out our documentation on Developing apps with AI features [here](/ai/developing-ai-apps).

✨ To search Slack data without connecting it to an AI, see documentation for the Real Time Search API [here](/apis/web-api/real-time-search-api). The Real Time Search (RTS) API offers access to Slack data via API call.