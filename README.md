# 🧠 MCP Server MVP — Headstarter Project

This project is an early implementation of an **MCP (Model Context Protocol) server** — a backend system designed to interpret structured user prompts and automate workflows across tools like Google Calendar, Slack, and Notion.

> ✅ This is my **MVP** version built using FastAPI, focused on demonstrating end-to-end automation and integration logic with mocked calendar data and real Slack API interaction.

---

## 🚀 What It Does (Current MVP Features)

- Accepts structured meeting requests via a `/schedule-meeting` endpoint
- Parses and validates input using **Pydantic**
- Simulates calendar availability checks (mocked free/busy data)
- Returns a meeting slot and generates a Google Meet placeholder link
- Sends a **real Slack message** to a configured channel with meeting details
- Handles real-world API errors (e.g., invalid Slack token, missing permissions)

---

## ❌ What It Doesn’t Do (Yet)

- Does not integrate a language model (like GPT or Claude)
- Does not fetch actual free/busy data from **Google Calendar**
- Does not retrieve notes or content from **Notion**
- Does not convert notes into flashcards or use the Quizlet API
- No natural language input — only structured, JSON-based requests

---

## 🧭 Why I Built It This Way

This MVP was designed under a time constraint to focus on:
- Laying the foundation of an MCP server
- Handling real HTTP requests
- Respecting authorization (via `.env` and Slack tokens)
- Demonstrating a working, cloud-deployed backend

I opted for FastAPI because of its speed and simplicity, and because it allowed me to focus on backend logic and integrations first.

---

## 💡 What I Learned

- Real-world API integration requires secure auth and token management
- Even a small backend system has many moving parts (routing, validation, async calls)
- Debugging real Slack errors like `invalid_auth` and `not_in_channel` gave me firsthand experience with permission contexts
- **Next.js might be a better long-term framework** for this project since it allows combining frontend + backend logic, edge functions, and seamless API routes — all within one stack

---

## 🛠️ What's Next

I plan to:
- Rebuild this project using **Next.js** as the core framework
- Connect to real data sources: Google Calendar, Notion
- Add an AI model layer to interpret user prompts (natural language → action)
- Extend support for workflows like turning Notion notes into flashcards
- Improve error handling, logging, and testing

---

## 📦 How to Use It

This app is deployed at:  
👉 [`https://headstarter-mcp-project.onrender.com/docs`](https://headstarter-mcp-project.onrender.com/docs)

You can:
- Use the Swagger UI to send `POST /schedule-meeting` requests
- Provide attendees, a time window, and duration in minutes
