import os
import math
import asyncio
from dataclasses import dataclass

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = os.getenv("BOT_TOKEN")

@dataclass
class MatchState:
    minute: int = 0
    home: int = 0
    away: int = 0
    lam90: float = 2.6
    tempo: float = 1.0

STATE = {}

def clamp(x, a, b):
    return max(a, min(b, x))

def poisson_p_ge_k(mu, k):
    if k <= 0:
        return 1.0
    s = 0.0
    for i in range(k):
        s += math.exp(-mu) * (mu ** i) / math.factorial(i)
    return clamp(1 - s, 0, 1)

def fair(p):
    return "∞" if p <= 0 else f"{1/p:.2f}"

def mu_rem(st):
    return st.lam90 * ((90 - st.minute) / 90) * st.tempo

def p_window(st, start):
    m = max(st.minute, start)
    mu = st.lam90 * ((90 - m) / 90) * st.tempo
    return clamp(1 - math.exp(-mu), 0, 1)

def render(st):
    mu = mu_rem(st)
    t = st.home + st.away
    p05 = poisson_p_ge_k(mu, 1)
    p15 = poisson_p_ge_k(mu, max(0, 2 - t))
    p25 = poisson_p_ge_k(mu, max(0, 3 - t))
    p75 = p_window(st, 75)

    return (
        f"⏱ {st.minute}' | {st.home}-{st.away}\n"
        f"μ: {mu:.2f}\n\n"
        f"Over 0.5: {p05*100:.1f}% | {fair(p05)}\n"
        f"Over 1.5: {p15*100:.1f}% | {fair(p15)}\n"
        f"Over 2.5: {p25*100:.1f}% | {fair(p25)}\n\n"
        f"Goal 75-FT: {p75*100:.1f}% | {fair(p75)}"
    )

def kb():
    k = InlineKeyboardBuilder()
    k.button(text="Tempo +", callback_data="tp+")
    k.button(text="Tempo -", callback_data="tp-")
    k.button(text="+1’", callback_data="m+")
    k.adjust(2, 1)
    return k.as_markup()

async def main():
    if not TOKEN:
        raise RuntimeError("Missing BOT_TOKEN")

    bot = Bot(TOKEN)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start(m: Message):
        await m.answer("Γράψε: /match 62 1-0 2.60")

    @dp.message(F.text.startswith("/match"))
    async def match(m: Message):
        try:
            p = m.text.split()
            st = MatchState(
                minute=int(p[1]),
                home=int(p[2].split("-")[0]),
                away=int(p[2].split("-")[1]),
                lam90=float(p[3]),
            )
            STATE[m.chat.id] = st
            await m.answer(render(st), reply_markup=kb())
        except:
            await m.answer("❌ Σωστό: /match 62 1-0 2.60")

    @dp.callback_query()
    async def cb(q: CallbackQuery):
        st = STATE.get(q.message.chat.id)
        if not st:
            await q.answer("Γράψε πρώτα /match", show_alert=True)
            return

        if q.data == "tp+":
            st.tempo += 0.05
        elif q.data == "tp-":
            st.tempo -= 0.05
        elif q.data == "m+":
            st.minute += 1

        await q.message.edit_text(render(st), reply_markup=kb())
        await q.answer()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
