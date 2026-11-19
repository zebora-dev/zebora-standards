# Add the Zebora skills to your Claude

Skills are instructions and tools that teach Claude how we do things at Zebora: how to make an
on-brand image, how to restyle a deck, how to write in a brand's voice, and so on. Once they're
added, you just ask Claude in plain English ("make me a LinkedIn post about our Web Summit talk")
and it uses the right skill by itself.

All our skills come as one package called **zebora**. You add it once, and updates arrive on
their own.

This guide covers the Claude desktop app and claude.ai (most people) and Claude Code (developers).
You don't need a terminal or any coding knowledge for the first two.

## Before you start

You need:

1. **A Claude account**, ideally in Zebora's Claude organisation (ask Grant to invite you), signed
   in to the Claude desktop app or claude.ai. A personal Pro or Max account works for Options 2
   and 3.
2. **Code execution switched on.** Skills run small programs to make files. In Claude, open
   **Settings**, then **Capabilities**, and make sure **Code execution and file creation** and
   **Skills** are both on. On the Team plan these may already be on and greyed out; that's fine.

## Option 1: it's already there (ask first)

If your organisation admin has switched the zebora package on for everyone, you don't need to do
anything. To check:

1. Open Claude and click **Customize** (or **Settings**), then **Plugins** (it may say
   **Plugins & skills**).
2. Look for **zebora** in the list.
   - If it says **Installed**, you're done. Go to "Using the skills" below.
   - If it says **Install**, click it. You're done.
3. If it isn't there, use Option 2, or ask Grant to switch it on for the organisation (see "For
   the admin" at the end).

## Option 2: add it yourself

You need a GitHub account that has been given access to the `zebora-dev/zebora-standards`
repository. Ask Grant to add you if you haven't got one; it only takes a minute to set up.

1. In Claude, click **Customize**, then **Plugins**.
2. Click **Add**, then **Add marketplace**.
3. Type `zebora-dev/zebora-standards` and confirm.
4. If Claude asks you to connect GitHub, follow the prompts, sign in to GitHub and allow the
   **Claude** GitHub app to see the `zebora-standards` repository.
5. A marketplace called **zebora** appears. Open it, find the **zebora** plugin and click
   **Install**.

That's it. Start a new chat so Claude picks the skills up.

## Option 3: upload a single skill (only if the options above don't work)

1. Ask Grant for the zip file of the skill you want (for example `zebora-brand-assets.zip`).
2. In Claude, click **Customize**, then **Skills**, then the **+** button, then **Upload a skill**.
3. Choose the zip file.

Uploaded skills do not update themselves. When a skill changes, you'll need a new zip and to
upload it again. That's why Options 1 and 2 are better.

## Using the skills

Just ask. For example:

- "Make a LinkedIn post image that says *Own your narrative in AI*, with *narrative* in green."
- "I need a banner for our October newsletter."
- "Restyle this Google Slides deck into the Zebora brand." (needs the Google Drive connector)
- "Check this LinkedIn post is in the RateMyPrompts voice."

Claude will tell you when it's using a skill. If it doesn't pick one up, name it: "use the Zebora
brand assets skill". You can also type `/` in the message box to see the skills you have.

The skills most useful outside the tech team:

| Skill | What it's for |
|---|---|
| **zebora-brand-assets** | On-brand images: LinkedIn posts and covers, link previews, blog headers, slide images, report covers, email banners |
| **zebora-deck-refresh** | Restyling a Google Slides deck into the Zebora brand without changing the words |
| **ratemyprompts-voice** | Writing or checking RateMyPrompts copy in its tone of voice |

The others (scoring, onboarding, batch release) are for the data team. They need access to our
systems and won't do anything useful without it, so you can ignore them.

## Getting updates

- **Option 1 or 2:** updates arrive automatically. Start a new chat to get the latest version.
  If something seems out of date, go to **Customize**, then **Plugins**, open **zebora** and look
  for an **Update** button.
- **Option 3:** ask Grant for the new zip and upload it again (use **Upload new version** on the
  skill if it's offered, so you don't end up with two copies).

## If something goes wrong

| What you see | What to do |
|---|---|
| Claude says it can't run code or create files | Switch on **Code execution and file creation** in Settings, then Capabilities. |
| The marketplace won't add, or says "not found" | Your GitHub account hasn't got access to `zebora-dev/zebora-standards` yet, or the Claude GitHub app isn't allowed to see it. Ask Grant. |
| A skill appears twice | You've added it two ways (for example an uploaded zip and the plugin). Delete the uploaded one under **Customize**, then **Skills**. |
| The image or file doesn't appear | Ask Claude to "attach the file". In longer chats, start a new one. |

Anything else: send Grant a screenshot.

---

## For developers: Claude Code

In Claude Code (terminal or the desktop app's Code tab), run:

```text
/plugin marketplace add zebora-dev/zebora-standards
/plugin install zebora@zebora
```

The repository is private, so Claude Code uses your machine's git access. If the first command
fails, run `gh auth login` and `gh auth setup-git` in a terminal, then try again.

Skills are then available as `/zebora:<skill-name>` (for example `/zebora:zebora-brand-assets`),
and Claude still picks them up from plain requests.

Updates: run `/plugin marketplace update zebora`, or open `/plugin`, go to **Marketplaces**,
select **zebora** and switch on auto-update.

Some skills need extra setup the first time (for example `zebora-deck-refresh` needs `npm install`
and `pip3 install -r requirements.txt` in its folder). Each skill's `SKILL.md` says what it needs.

**If you used the old symlink set-up** (`~/.claude/skills/<name>` pointing at a checkout of this
repo), remove those symlinks after installing the plugin, or every skill will appear twice:

```sh
find ~/.claude/skills -maxdepth 1 -type l -lname '*zebora-standards*' -print -delete
```

Repositories that load skills through a `.standards` submodule (for example `brand-score-pipeline`)
keep working as they are; those skills are pinned to the submodule's version.

## For the admin: switch it on for everyone

Needs an Owner on the Team or Enterprise plan. Do this once and nobody else has to follow Option 2.

1. In claude.ai, open **Organization settings**, then **Plugins & skills**.
2. Check the **Policy** settings allow **Skills** and **Code execution and file creation**.
3. Click **Add**, then **Sync from GitHub**, and choose `zebora-dev/zebora-standards`. Install the
   Claude GitHub app on the `zebora-dev` organisation when asked, limited to this repository.
4. Leave **Sync automatically** on, so every merge to `main` reaches everyone.
5. Set the **zebora** plugin's default access to **Installed by default**.

To make zip files for Option 3, from a checkout of this repository run:

```sh
scripts/package-skills.sh            # writes dist/<skill>.zip for every skill
```

Before you give anyone a zip or switch on the sync, remember that some skills describe internal
systems and the brand guidelines, which are private. Keep them inside Zebora's Claude organisation.
