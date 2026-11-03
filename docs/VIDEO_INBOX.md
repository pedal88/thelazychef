# The video inbox

Cooking videos seen on the phone are saved to `/admin/inbox`, to pick from later. Saving a video makes nothing and costs
nothing. Admin only.

## The iPhone shortcut

Make it once, in the Shortcuts app on the iPhone:

1. Tap **+** to make a new shortcut and name it **Save to Lazy Chef**.
2. Tap the **i** at the bottom, turn on **Show in Share Sheet**, and tap **Done**.
3. At the top, set **Receive** to **URLs** and **Text**. If it has no input: **Continue**.
4. Add the action **URL Encode**, on **Shortcut Input**, with **Encode**.
5. Add the action **URL**, and write `https://thelazychef.app/admin/inbox/add?url=`, then choose the variable
   **URL Encoded Text** right after the `=`.
6. Add the action **Open URLs**.

Log in to thelazychef.app once in Safari on the phone. To save a video: **Share** in TikTok or Instagram, then
**Save to Lazy Chef** (it may be under **More**). Safari opens, and the inbox says **Saved**.

## How it works

- `/admin/inbox/add?url=…` writes nothing on the GET. The page sends itself as a POST with a token from the session.
  Only links to the video hosts in `services/recipe_v2/sources.py` are saved, so a link from someone else can at worst
  add a video to the inbox.
- A video is known by its `video_key`: the same video shared twice, or linked another way, is one row. A short link
  (`vm.tiktok.com/…`) has only itself to go by. Sharing a discarded video again takes it back.
- A video already made into a recipe is marked, by comparing the keys with the recipes' `source_input`.
