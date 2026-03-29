# Pulse - X Growth Agent for OpenClaw

Pulse is an AI agent that handles your X (Twitter) content strategy end-to-end.
Competitor research. Account analysis. Post ideas. Threads. Performance tracking. Feedback loop.
It now also ships with a small local tracker script for automatic post snapshots via the X API.

Built with [OpenClaw](https://openclaw.ai). Self-installs in under 5 minutes.

---

## What Pulse Does

| System | What It Does |
|--------|-------------|
| 🔍 Competitor Scan | Finds outlier posts (3x+ avg engagement) across competitor accounts via X API |
| 📊 Account Analysis | Analyzes your own posts to find patterns in what performs and what doesn't |
| 💡 Idea Generation | Interviews you first, then generates research-backed ideas grounded in real experience |
| 📝 Post/Thread Writing | Full drafts in your voice with optimization package (hook variants, hashtags, timing, media) |
| 📈 Performance Logging | Tracks how each post does after publishing |
| 🔄 Feedback Loop | Logs every approval and rejection with reasons - Pulse never repeats a rejected angle |
| 🧠 Learning Loop | Reads all memory files before every session - gets smarter the longer you use it |

---

## Requirements

- [OpenClaw](https://openclaw.ai) installed
- Any supported AI model (Claude, GPT-4o, Gemini - all work)
- An X (Twitter) account (any size, any niche)
- X API access (Bearer Token) - see API Setup below

---

## API Setup

Pulse uses the X API v2 to research competitors. Here's how to get access:

1. Go to [developer.x.com](https://developer.x.com) and sign up for a developer account
2. Create a new project and app in the Developer Portal
3. Subscribe to the **Pay-Per-Use** plan (recommended):
   - ~$0.01 per tweet read, ~$0.01 per user lookup
   - No monthly commitment, no minimum spend
   - A full competitor scan of 5 accounts costs roughly $5
4. Go to **Keys and tokens** → generate a **Bearer Token**
5. Store that token in the `X_API_BEARER_TOKEN` environment variable used by OpenClaw

**Pricing note:** The Free tier is too limited for competitor scanning (1 request/24h). The Basic plan ($200/month flat) only makes sense above ~20K operations/month. For most creators, Pay-Per-Use is the best option.

---

## Installation - 2 Ways

### Option A: Send the repo link to OpenClaw (easiest)

Just tell your OpenClaw agent:

```
Install this skill: https://github.com/ricca91/x-agent
```

OpenClaw will clone the repo, install the skill, and Pulse will run onboarding automatically.

### Option B: Manual install

```bash
# Clone into your OpenClaw skills directory
git clone https://github.com/ricca91/x-agent.git ~/clawd/skills/x-agent
```

Then tell your OpenClaw:
```
Install Pulse
```

Pulse will detect the new skill and walk you through 11 onboarding questions.

---

## Onboarding

First time you run Pulse, it'll ask you 11 questions:

1. Your name and X handle
2. Profile URL
3. Your niche (one sentence)
4. Your target audience
5. Your follower goal + deadline
6. Current follower count
7. How you naturally write (voice description)
8. 3-5 competitor accounts to monitor
9. What to avoid (flops, off-brand formats)
10. Your top 2-3 posts (optional - for voice calibration)
11. Your X API Bearer Token

Takes about 5 minutes. Pulse writes your answers to `config.md` automatically. You never do this again.

---

## How to Use Pulse

After setup, just talk naturally:

```
Pulse, scan my competitors for what's working this week
```
```
Pulse, I want to write a post - interview me and let's find an idea
```
```
Pulse, write a thread about [idea]
```
```
Pulse, my last post got 1,200 likes - log the performance
```
```
Pulse, show me the feedback loop - what patterns have you noticed?
```

---

## How the Learning Loop Works

Pulse keeps a `memory/` folder with:
- `approved-ideas.md` - every idea you said yes to
- `rejected-ideas.md` - every idea you rejected + why
- `performance-log.md` - every post's stats after publishing
- `competitor-scans.md` - history of niche research
- `voice-examples.md` - your writing patterns and phrases

Before every session, Pulse reads all of these. It never repeats a rejected angle. It weights suggestions toward what's actually performed on your account. The longer you use it, the better the ideas.

---

## File Structure

```
x-agent/
├── README.md              ← You're reading this
├── SKILL.md               ← Pulse's full instructions (all 7 systems)
├── config.md              ← Auto-created during onboarding (gitignored)
├── example-config.md      ← Real example for reference
└── memory/
    ├── approved-ideas.md  ← Auto-populated (gitignored)
    ├── rejected-ideas.md  ← Auto-populated (gitignored)
    ├── performance-log.md ← Auto-populated (gitignored)
    ├── competitor-scans.md← Auto-populated (gitignored)
    ├── account-analysis.md← Auto-populated (gitignored)
    └── voice-examples.md  ← Auto-populated (gitignored)
```

Note: `config.md` and all `memory/` files are gitignored. The bearer token should stay in `X_API_BEARER_TOKEN`, not in a committed file. Your personal data and token stay on your machine.

---

## Customizing Pulse

- To change your account details: edit `config.md`
- To change how Pulse behaves: edit `SKILL.md` (plain English, no code)
- To reset and start fresh: delete `config.md` and all `memory/` files, then run "Install Pulse" again

---

## Local performance tracking

A small Python script now ships with the skill:

```bash
cd ~/.openclaw/skills/x-agent
export X_API_BEARER_TOKEN='your-token-here'
python3 scripts/track_x_performance.py --username RiccSartori --limit 10
```

What it does:
- fetches the account profile and recent posts from the X API
- saves raw and normalized JSON snapshots under `memory/x-metrics/`
- writes a readable markdown report in the same folder
- appends a short automatic snapshot entry to `memory/performance-log.md`

Use this for a quick local MVP snapshot. No auto-posting, no dashboards.

To automate daily snapshots (Mac/Linux), add this to your crontab (`crontab -e`):

```bash
# Daily snapshot at 9:00 AM
0 9 * * * cd ~/.openclaw/skills/x-agent && X_API_BEARER_TOKEN='your-token-here' python3 scripts/track_x_performance.py >> /tmp/pulse-snapshot.log 2>&1
```

Once the snapshot runs, Pulse will read `memory/performance-log.md` automatically during Account Analysis (System 2) and Performance Logging (System 5) - no manual data entry needed.

## FAQ

**Does this work for any niche?**
Yes. Onboarding calibrates Pulse to your niche, voice, and competitors.

**Do I need to be technical?**
No. If you can install OpenClaw, get an X API token, and answer 11 questions, you're set.

**Does Pulse post automatically?**
No. Pulse handles strategy and drafts. Publishing stays with you.

**Is my data private?**
Yes. `config.md` (including your API token) and all `memory/` files are gitignored and stay on your machine.

**What model works best?**
Claude Sonnet or GPT-4o. Both work well for this.

**How much does the X API cost?**
With Pay-Per-Use: ~$0.01 per operation. A typical competitor scan costs ~$5. Monthly cost depends on usage but most creators spend $10-30/month.

---

## License

MIT - free to use, modify, and share.
