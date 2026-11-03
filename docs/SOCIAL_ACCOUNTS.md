# The social accounts and developer access

What exists on Instagram and TikTok, what each account and developer profile can do, and what was left out on purpose.
Last checked 03.11.2026; the TikTok developer profile's status was last seen on 01.11.2026. How the posts themselves
are made is in `docs/SOCIAL.md`, and how to replace the Instagram token is in `docs/runbooks/ROTATE_SECRETS.md`.

No secret values belong here: this repository is public.

## At a glance

| | Instagram | TikTok |
|---|---|---|
| Account | `thelazychef.ai`, professional and public | "The Lazy Chef \| Recipe Maps" |
| Developer access | Meta app "The Lazy Chef stats", in development mode | Business API developer profile, submitted; no app |
| Business account | Business portfolio "The Lazy Chef", not verified | TikTok for Business login with email; the TikTok account is not linked to it |
| Numbers | Fetched every morning | Typed in by hand |
| Posting | Approved posts go out through the API, without music | By hand from the phone |
| Company or org number needed | No | Yes, for the Accounts API |

## Instagram

### The account

`thelazychef.ai` is a professional account and public. It is linked to Pål's Facebook account in Meta's Accounts Center,
and he signs in to Meta's developer pages with that Facebook account. The API works the same for the Creator and
Business types, so which of the two it is makes no difference here. The account's id is in `deploy.yaml`
(`INSTAGRAM_USER_ID`).

### The Meta app

| | |
|---|---|
| App | "The Lazy Chef stats" at developers.facebook.com, shown as Unpublished, which is development mode |
| Use case | Manage messaging & content on Instagram. An ads use case was also ticked by accident when the app was made and may still be there; nothing uses it |
| Business portfolio | "The Lazy Chef", linked to the app with full access. Its only purpose is that Unified login requires one |
| App role | `thelazychef.ai` is an Instagram Tester, invitation accepted on instagram.com |
| Login configuration | Unified login: system-user access token, expiry never, the Instagram account as its asset |
| App Review, Advanced Access, business verification, live mode | None of them. They apply to apps that serve other people's accounts |

### What is switched on

The code uses three of the token's permissions:

| Permission | Used for |
|---|---|
| `instagram_basic` | Reading the account's posts, their captions and links |
| `instagram_manage_insights` | Views, reach, likes, comments, saves, shares and profile visits per post (`services/social_stats.py`) |
| `instagram_content_publish` | Publishing the approved posts in the Instagram queue (`services/social_publish.py`) |

**The token holds more than that.** Meta's `GET /me/permissions` on 03.11.2026 also lists `ads_management`, `ads_read`,
`instagram_manage_comments`, `instagram_manage_messages` and `public_profile` as granted. These were to be removed from
the configuration when it was set up on 01.11.2026, but the token still has them. No code uses them. To narrow it, remove them from the configuration and generate a new token
(`docs/runbooks/ROTATE_SECRETS.md`). To check a token, use `GET /me/permissions`: `debug_token` refuses this kind of token
with error 100.

The calls go to `graph.facebook.com/v26.0`. All the numbers came back for carousels on an account with one follower, even
though Meta says accounts under 100 followers may not get all of them.

### Where the token is

- Secret Manager in `thelazychefai-prod`: `INSTAGRAM_ACCESS_TOKEN`, which is what production reads.
- The MacBook's keychain: `thelazychef-instagram`.

It does not expire, so nothing renews it. Anyone holding it can publish to the account and, with the permissions above, read its messages.

### Traps when setting this up again

- Unified login needs a business portfolio. The older advice to skip it no longer holds. The portfolio is free and needs
  no verification. The alternative, Facebook login, needs a Facebook Page linked to the account.
- Meta's template for the configuration leaves out `instagram_manage_insights`. Without it there are no views, saves or
  shares, so add it to the configuration by hand.
- Make the account an Instagram Tester before pressing Add account, or that step stops with an error.
- A token made before the configuration changed stops working. Generate it again after any change.
- The prompt in `security add-generic-password -w` cuts what is pasted at 128 characters, and the token is longer. Copy
  the token, then pass it with `-w "$(pbpaste)"`.

### What the API cannot do

It cannot add music to a carousel. To post one with music, post it by hand (`docs/SOCIAL.md`, "The Instagram queue").

## TikTok

### The account

"The Lazy Chef | Recipe Maps" is signed in on the phone. Posts go up by hand from
`/admin/funnel/tiktok`, and the numbers are typed in on **Copy in numbers**. None of that needs a developer profile or an
organisation number.

**It is not linked to TikTok for Business, on purpose.** The dialog that offers the link was cancelled on 01.11.2026, for
two reasons. It asks for far more than a stats fetch needs, among them reading and managing messages, changing the
account type, and publishing ads and videos. And whether the link changes which sounds the account can use has not been
checked. Check the sound library first if this is ever taken up.

### The business login and developer profile

| | |
|---|---|
| Login | A TikTok for Business account at business-api.tiktok.com, made with `hello@thelazychef.app` and a password |
| Developer profile | Submitted 01.11.2026 and under review when last seen. Status: <https://business-api.tiktok.com/portal/developer/profile> |
| App | None. TikTok refuses to create one until the profile is approved |
| Email | TikTok rejects Gmail here, so `hello@thelazychef.app` forwards to `thelazychefai@gmail.com` (Namecheap's email forwarding on the domain) |

The profile as submitted has three things that do not match what it describes, which may lead to a rejection: the account
type says Technology Company (it should be Direct Advertiser), the description still has the placeholder `@BRUKERNAVN`,
and all four regions are selected. Correct them if the profile can be edited, or when submitting it again.

### What each TikTok API would give

| API | Would give | Status |
|---|---|---|
| Accounts API (business-api.tiktok.com) | Views, likes, comments, shares, saves and profile views per post | **Not applied for.** The form needs company verification: a registration document or a verified Business Center, and the full legal company name. Also a screen recording of how the data is used. We have no company |
| Display API in a sandbox (developers.tiktok.com) | Views, likes, comments and shares; no saves or profile views | **Not started.** Needs no review or company, with up to 10 test users on accounts you own. Whether a sandbox returns real numbers, and includes photo posts, is unconfirmed; a test of about 30 minutes would settle it. Outside a sandbox, TikTok's review refuses apps for private use |
| Content Posting API | Publishing | **Closed to us, company or not.** Without an audit, posts are private and the account must be private. The audit refuses tools that upload to your own accounts |

Reading TikTok by a script or in the browser is out as well: see `docs/SOCIAL.md`, "The TikTok posts page".

### Decisions and what would change them

- **No company for this.** A sole proprietorship would meet TikTok's form and costs nothing to register, but it is a legal
  and tax step. It saves about 1.5 to 3 hours a week of typing numbers at five posts a day, and less at today's two.
- **The sandbox waits** until typing the numbers becomes a real burden.

## Where each login and secret lives

| What | Where |
|---|---|
| Meta developer pages and the business portfolio | Pål's Facebook account |
| Instagram, TikTok and TikTok for Business | Pål's own logins; the project holds none of them |
| Instagram's token | Secret Manager and the MacBook's keychain, as above |
| `hello@thelazychef.app` | A forwarder at Namecheap, the domain's registrar; nothing to sign in to at that address |
| TikTok app id and secret | None exist yet |
