# The video inbox

Cooking videos seen on the phone are saved to `/admin/inbox`, to pick from later. Saving a video makes no recipe, but it
costs money: the video is read in the background, about 3 cents for a TikTok (an estimate). The page says so before saving,
and with many links the cost of them all is shown before anything is saved. Admin only.

## Pasting a link

Copy the link in TikTok or Instagram, open **Paste a link** in the inbox (`/admin/inbox/add`) and tap **Paste and save**. The
browser may show a small **Paste** bubble first: that is the phone asking, and it is one more tap. Or paste the link in the
field and save. Only a link is sent; anything else on the clipboard stays on the phone.

## Many links at once

On the same page, paste a list or any text with links in it, or choose a file such as TikTok's data download. Links are read
out of whatever the text is, so nothing depends on the file's format, which has not been checked against a real download.
**Check the links** says how many are new, how many are known (in the inbox, discarded, made, or there twice) and how many
are no video, with about what reading them costs. Nothing is saved before **Save**. At most 1000 new videos at a time: a whole
download also lists every video watched, so then choose only the file with the favourites.

Each is looked up in the queue, one every 30 seconds (`tasks.INBOX_SPACING`), so recipes are not held up and TikTok sees few
requests. 100 videos take about 50 minutes. One that fails stays usable and says why, and the rest go on. Every video stays in the list: Pål chooses the links,
so nothing is sorted away by its caption, and one sent by mistake is discarded by hand.

## The iPhone shortcut

The shortcut only copies the link and opens the page, and **Paste and save** does the rest. It does not put the link in the
address: tried on 04.11.2026 with TikTok and Chrome, that address got a space after `url=` and the link was lost, and the
cause was not found. This way has not been tried on a real iPhone yet.

Make it once, in the Shortcuts app (Snarveier) on the iPhone. Names in Norwegian in brackets:

1. Tap **+** and name the shortcut **Save to Lazy Chef**.
2. Tap **i** at the bottom, turn on **Show in Share Sheet** (Vis i delingsark), and tap **Done**.
3. At the top, set **Receive** (Motta) to **URLs** and **Text**.
4. Add **Copy to Clipboard** (Kopier til Utklipp). It takes **Shortcut Input** (Snarvei-inndata).
5. Add **URL**, and write the address: `googlechromes://thelazychef.app/admin/inbox/add` for Chrome, or
   `https://thelazychef.app/admin/inbox/add` for Safari.
6. Add **Open URLs** (Åpne URL-er).

Log in once in that browser with the admin account (`thelazychefai@gmail.com`). To save a video: **Share** in TikTok or
Instagram, **Save to Lazy Chef** (it may be under **More**), then **Paste and save**.

## Making recipes

Tick videos in the inbox and go on: **Many recipes at once** gets their links, and shows how many and what they cost
before anything is made. From there a video is made like any other link: it follows the video's ingredients and amounts,
without a chef's rules, and goes through the same structuring, validator, pantry job and images. The pantry job can swap an ingredient the pantry lacks, or ask Pål about it (`/admin/pantry-questions`); the video's own words stay in the recipe's source text. An amount the video does
not give is estimated (salt, pepper and garnish become "to taste"), and the admin chip on the recipe lists what was
estimated. The recipes are drafts until approved. A row stays in the inbox, marked as made.

## How it works

- `/admin/inbox/add?url=…` still works, though the shortcut no longer uses it. It writes nothing on the GET: the page sends itself as a POST, which another site's form cannot do (`utils/cross_site.py`).
  Only links to the video hosts in `services/recipe_v2/sources.py` are saved, so a link from someone else can at worst
  add a video to the inbox.
- A video is known by its `video_key`: the same video shared twice, or linked another way, is one row. A short link
  (`vm.tiktok.com/…`) has only itself to go by. Sharing a discarded video again takes it back.
- A video already made into a recipe is marked, by comparing the keys with the recipes' `source_input`.
- Each saved video is looked up in the queue (`/internal/tasks/video-inbox/<id>`, `inbox.look_up`): caption, uploader and
  length with `yt-dlp`; then the video is downloaded and Gemini writes down what it shows (`video_text`, under **What the
  video shows** in the list); then one small Claude call (`VIDEO_INBOX_MODEL`) for the dish's name, the approved recipes it
  looks most like, and suggested cuisine, main protein and meal types. About 3 cents for a TikTok of 40 seconds, an estimate
  (`docs/SERVICES_AND_COSTS.md`). The suggestions do not go into the recipe. A video whose details cannot be read keeps its
  link and says why, and costs no model call.
- Making the recipe uses `video_text` (`inbox.written_down`), so the video is paid for once, and the same text gives the same
  amounts each time. A video not read in the inbox (longer than 3 minutes, or the read failed) is read when the recipe is
  made, as any other link. A video that shows no recipe says so in the list; it can still be chosen. An empty answer from
  Gemini is not the same thing: it is tried once more, and the row says that reading gave no answer. Each read logs `Video
  read` with the model, why it stopped, what blocked it, the file's size, and how the answer began. **Look up** on a row
  reads it again.
