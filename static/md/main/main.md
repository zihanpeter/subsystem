# News

## Site refresh (2026)
The whole site now shares one design system: a common header and footer, light / dark theme everywhere (including game pages), and clearer layouts for Reciter, Forum, and Yule.

## Reciter: spaced repetition
Reciting is no longer a one-shot “drill each word twice” session. Progress is saved per account and per wordlist. Each day you get a fixed queue of due words; **Know** / **Don't know** (and spelling correct / wrong) update long-term review dates. See **Systems Intro → Reciter** below for details.

## Branding
Subsystem now uses a consistent site icon in the header and in the browser tab.

--------
# Basic info & rules
Welcome to [subsystem.top](https://subsystem.top)!
## About the account
To access your account, click on the rightmost item in the menu bar at the top of the page

In the meantime, you can change your password or edit your profile here

Please use the [Markdown](https://help.luogu.com.cn/rules/academic/handbook/markdown), 
[KaTeX](https://katex.org/docs/supported.html) To edit your profile

You can switch theme colors from the moon / sun button in the top bar (works on every page). Logged-in users also keep the choice on their profile.

## Admin team
To maintain order in the community, we set up a team of custodians

Administrator rights:

- Post top discussions or top other people's discussions

- Publish an official vocabulary or make someone else's vocabulary official

- Delete/modify any non-compliant glossary/discussion

- Delete any comments that are not compliant

- Modify some users' non-standard personal profiles

-----
# Systems Intro

## Forum
You can delete or modify the articles you have created. At the same time, you can also delete your post under discussion

You can apply to the administrator to top your article

The title of an article cannot be longer than 64 characters, and all multi-line input fields can be resized by pulling on the bottom right corner

Please use the 
[Markdown](https://help.luogu.com.cn/rules/academic/handbook/markdown), 
[KaTeX](https://katex.org/docs/supported.html) To edit your article

## Reciter
Reciter is the vocabulary trainer: create wordlists, then review them with spaced repetition. Log in before you start — progress is stored for your account.

### 1. Browse and open a list
Open **Reciter** in the top menu. You can filter by difficulty or search by list name. Official lists and user lists are shown separately.

Open a list to see its words, today's progress chips, and the study buttons.

### 2. Create or edit a wordlist
Click **Create a new wordlist**. Enter a name (up to $64$ characters), choose difficulty, paste the words, then submit.

You can later **Modify** or **Delete** lists you own (admins can manage others when needed).

#### Without example sentences
For $n$ words, enter $2n$ lines: English, Chinese, English, Chinese, …

```
hello
你好
banana
香蕉
```

#### With example sentences / explanations
Choose **Include example sentence/explanation**. For $n$ words, enter $3n$ lines: English, Chinese, example, …

If a word has no example, put a placeholder on that line (for example `(CASE)`), or recognition may break.

```
hello
你好
Hello everyone!
banana
香蕉
(CASE)
```

#### Format tips
- Do not put characters such as `.` inside English headwords; that can cause server errors.
- Difficulty grades are set by list authors; ask [PeterLu](https://subsystem.top/profile?username=PeterLu) if you need the official scale.

### 3. How reviewing works
On a list page, start with **Learn meaning** (English → Chinese) or **Learn spelling** (Chinese → type English). Both modes share the same progress for each word.

#### Today's queue
The first time you open a list on a calendar day, Reciter builds a **today queue** from words whose next review date is today or earlier. That queue stays fixed for the rest of the day.

Status chips mean:

| Chip | Meaning |
|-|-|
| Today $a$ / $b$ | Words answered correctly at least once today / size of today's queue |
| Retry | Marked wrong today; must be answered correctly once more |
| Left | Still waiting in today's queue |
| Mastered | Words at a high familiarity level / total words in the list |

Extra actions on the list page:

- **Restart whole list today** — put every word into today's queue again
- **Review wrong words** — rebuild today's queue from words you have gotten wrong before

#### Spaced repetition
Each word has a level and a next-review date.

- **Know** (or a correct spelling) raises the level and delays the next review (about $0$, $1$, $2$, $4$, $7$, $14$, $30$, then $60$ days).
- **Don't know** (or a wrong spelling) resets the level, keeps the word due today, and adds it to **Retry** until you get it right once.

When **Left** reaches $0$ and **Retry** is empty, the session shows **Today finished**. Come back on later days for words that become due again.

#### Learn meaning controls
Reveal the answer before you rate yourself.

| Action | Keys |
|-|-|
| Show meaning | `S` or ↓ |
| Know | `A` or ← |
| Don't know | `D` or → |

#### Learn spelling controls
Type the English word and press **Enter** (or **Submit**). After a mistake, the correct word is shown; press **Enter** again to continue (the box is not re-checked).

## Yule
A project before Christmas.
### Background
Yule is established to create a wonderful online JavaScript gaming platform.

Now, all the games on Yule are provided by [ycy](https://subsystem.top/profile?username=ycy), a passionate developer. He is also the main programmer of the FRC team 5449 & FTC team 12527. You can go to his Github personal page by the link of the copyright statement under any Yule page of Subsystem.

### Contents
After you enter the Yule page, you can see a list of all the games, as well as the `Hot` value. `Hot` value presents how many times the game has been played.

What's more, you can click any game to enter the game introduction page, and you can see the detailed introduction of the game.