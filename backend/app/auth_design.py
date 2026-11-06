"""Shared, script-free realm account presentation."""
from starlette.responses import HTMLResponse

from pathlib import Path

STYLE = Path(__file__).with_name('auth_premium.css').read_text(encoding='utf-8')


def realm_page(content, status=200):
    return HTMLResponse('''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Aitizen Realm · Your story begins</title><style>'''+STYLE+'''</style></head><body>
<header><strong><span class="brand-mark">◇</span>AITIZEN REALM</strong><span>THE CIVILIZATION SIMULATION</span></header>
<main><section class="story"><div class="realm-art" role="img" aria-label="An illustrated riverside village at sunset, with forests, mountains and citizens"></div><span class="scene-label">A WINDOW INTO THE REALM</span>
<i class="mote" style="--x:22%;--y:35%;--delay:0s"></i><i class="mote" style="--x:70%;--y:28%;--delay:-4s"></i><i class="mote" style="--x:55%;--y:52%;--delay:-8s"></i><i class="mote" style="--x:85%;--y:64%;--delay:-2s"></i>
<span class="eyebrow">Many lives. One shared world.</span><h1>Every life.<br><em>A new possibility.</em></h1><p>A home to build. A world to discover.<br>Your citizen’s next chapter begins here.</p><div class="caption"><span>01 / EXPLORE</span><span>02 / CONNECT</span><span>03 / BELONG</span></div></section>
<section class="card" aria-label="Account access">'''+content+'''</section></main><footer>AITIZEN REALM / EVERY LIFE LEAVES A STORY</footer></body></html>''', status_code=status, headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; form-action 'self'; frame-ancestors 'none'"})


PLAYER_FORM = '''<span class="eyebrow">ENTER THE REALM</span><h1>Your story continues.</h1><p>Sign in and find your place in a living world.</p><a class="google" href="/account/google"><svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#4285F4" d="M21.6 12.2c0-.7-.1-1.4-.2-2.2H12v4.2h5.4a4.7 4.7 0 0 1-2 3v2.5h3.2c1.9-1.8 3-4.3 3-7.5Z"/><path fill="#34A853" d="M12 22c2.7 0 5-.9 6.6-2.3L15.4 17c-.9.6-2 1-3.4 1-2.6 0-4.8-1.8-5.6-4.1H3.1v2.6A10 10 0 0 0 12 22Z"/><path fill="#FBBC05" d="M6.4 14a6 6 0 0 1 0-4V7.4H3.1a10 10 0 0 0 0 9.2Z"/><path fill="#EA4335" d="M12 6c1.5 0 2.8.5 3.8 1.5l2.8-2.8A9.5 9.5 0 0 0 12 2a10 10 0 0 0-8.9 5.4L6.4 10C7.2 7.8 9.4 6 12 6Z"/></svg>Continue with Google</a><div class="divider">OR SIGN IN WITH EMAIL</div>
<form method="post" action="/account/password"><input type="hidden" name="action" value="login"><label>Email address<input name="email" type="email" autocomplete="email" placeholder="you@example.com" required></label><label>Password<input name="password" type="password" autocomplete="current-password" required></label><button>Enter the realm &nbsp; →</button></form>
<details><summary>New here? Create your account</summary><form method="post" action="/account/password"><input type="hidden" name="action" value="signup"><label>Citizen name<input name="name" maxlength="80" autocomplete="nickname" required></label><label>Email address<input name="email" type="email" autocomplete="email" required></label><label>Create password<input name="password" type="password" autocomplete="new-password" minlength="8" required></label><button>Create account →</button></form><small>Confirm your email before signing in.</small></details><a class="admin-link" href="/admin/login">Realm administrator access</a>'''

ADMIN_FORM = '''<span class="eyebrow">Realm stewardship</span><h1>Welcome back, keeper.</h1><p>Sign in to manage the shared world.</p><form method="post" action="/login"><label>Owner access key<input name="key" type="password" required autocomplete="current-password"></label><button>Enter administration →</button></form><a class="admin-link" href="/account">← Return to player sign-in</a>'''
