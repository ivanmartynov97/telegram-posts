#!/usr/bin/env python3
"""
Разовое заполнение очереди на ~2 дня вперёд (12 слотов), без Groq —
тексты написаны напрямую. Ищет картинки в Wikipedia/Commons по теме.
"""
import json, os, base64, urllib.request, urllib.parse, ssl, time
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE, "config.json")) as f:
    cfg = json.load(f)
GH_TOKEN = cfg["github_token"]
GH_REPO  = cfg.get("github_repo", "ivanmartynov97/telegram-posts")
RIGA_TZ  = timezone(timedelta(hours=3))

def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def fetch_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "HistoryBot/1.0"})
    with urllib.request.urlopen(req, timeout=12, context=ssl_ctx()) as r:
        return json.loads(r.read())

def wiki_image(query, lang="en"):
    """Ищет картинку через Wikipedia pageimages (en по умолчанию — точнее для зарубежных тем)."""
    try:
        s = fetch_json(f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": 1
        }))
        hits = s.get("query", {}).get("search", [])
        if not hits:
            return None
        title = hits[0]["title"]
        p = fetch_json(f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "titles": title, "prop": "pageimages", "pithumbsize": 800, "format": "json"
        }))
        for page in p.get("query", {}).get("pages", {}).values():
            src = page.get("thumbnail", {}).get("source")
            if src:
                return src
    except Exception as e:
        print(f"   ⚠️ wiki_image({query}): {e}")
    return None

def gh_create(path, obj, msg):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    payload = {
        "message": msg,
        "content": base64.b64encode(json.dumps(obj, ensure_ascii=False, indent=2).encode()).decode()
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="PUT",
        headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx()) as r:
        return json.loads(r.read())

# ── Слоты (следующие ~2 дня, пропускаем 20.06 16:00 и 18:00 — уже заняты) ──
SLOTS = [
    (2026, 6, 20, 22),
    (2026, 6, 21, 7), (2026, 6, 21, 11), (2026, 6, 21, 13), (2026, 6, 21, 16), (2026, 6, 21, 18), (2026, 6, 21, 22),
    (2026, 6, 22, 7), (2026, 6, 22, 11), (2026, 6, 22, 13), (2026, 6, 22, 16), (2026, 6, 22, 18),
]

POSTS = [
    {
        "text": "⚔️ Самая короткая война в истории длилась 38 минут.\n\n27 августа 1896 года Великобритания объявила войну Занзибару из-за смены султана без согласия Лондона. Британский флот открыл огонь в 9:02, дворец сдался в 9:40. Потери — около 500 человек со стороны Занзибара, у британцев — один раненый матрос.",
        "image_query": "Anglo-Zanzibar War", "lang": "en",
    },
    {
        "text": "🦃 Армия Австралии официально проиграла войну птицам.\n\nВ 1932 году фермеры запросили помощь военных против 20 000 страусов эму, уничтожавших урожай. Солдатам выдали пулемёты Lewis — и эму победили: птицы рассеивались стаями, пулемёты заклинивало, а сами эму оказались на удивление живучи. Военные отступили.",
        "image_query": "Emu War", "lang": "en",
    },
    {
        "text": "💥 30 июня 1908 года над Сибирью взорвалось что-то, что повалило 80 миллионов деревьев на территории 2150 км² — а кратера так и не нашли.\n\nТунгусский метеорит (вероятно, ледяная комета, взорвавшаяся в воздухе) высвободил энергию в 1000 раз больше Хиросимы. Если бы он влетел на 4-5 часов позже, взрыв пришёлся бы на Санкт-Петербург.",
        "image_query": "Tunguska event", "lang": "en",
    },
    {
        "text": "🎬📡 Хеди Ламарр — голливудская звезда 1940-х, которая в свободное время изобрела технологию, ставшую основой Wi-Fi и Bluetooth (частотное скакание сигнала для торпед).",
        "image_query": "Hedy Lamarr", "lang": "en", "is_photo": True,
    },
    {
        "text": "💃 Летом 1518 года в Страсбурге женщина по имени Troffea вышла на улицу и начала танцевать — без музыки, без остановки, несколько дней подряд. К ней присоединились десятки горожан.\n\nВ течение месяца «танцевали» около 400 человек, некоторые — до смерти от истощения. Городской совет, решив что танец — это болезнь, наняла музыкантов чтобы «вылечить» танцоров музыкой — что лишь усилило эпидемию.",
        "image_query": "Dancing plague of 1518", "lang": "en",
    },
    {
        "text": "🐕🚀 19 августа 1960 года собаки Белка и Стрелка стали первыми живыми существами, которые облетели Землю на орбите и вернулись живыми.\n\nСтрелка позже родила щенков — одного из них, Пушинку, советское правительство подарило дочери президента Кеннеди.",
        "image_query": "Belka and Strelka", "lang": "en",
    },
    {
        "text": "☢️ Цутому Ямагути пережил атомную бомбардировку Хиросимы 6 августа 1945 года — получил ожоги, но выжил и на следующий день вернулся домой в Нагасаки.\n\n9 августа над Нагасаки взорвалась вторая бомба. Он выжил и во второй раз — единственный человек, официально признанный Японией пострадавшим от обеих бомбардировок.",
        "image_query": "Tsutomu Yamaguchi", "lang": "en",
    },
    {
        "text": "⚙️ В 1901 году греческие водолазы нашли на дне моря бронзовый механизм возрастом более 2000 лет — с шестернями точнее, чем в европейских часах XIV века.\n\nАнтикитерский механизм предсказывал движение Солнца, Луны и затмения. Понадобилось сто лет рентгеновских снимков, чтобы понять, как он работает.",
        "image_query": "Antikythera mechanism", "lang": "en",
    },
    {
        "text": "🛰️ Спутник-1 — первый искусственный спутник Земли, запущенный СССР 4 октября 1957 года. Весил 83.6 кг, передавал простой сигнал «бип-бип», который можно было поймать обычным радиоприёмником — и слушал весь мир.",
        "image_query": "Sputnik 1", "lang": "en", "is_photo": True,
    },
    {
        "text": "🧱 Берлинская стена пала во многом из-за одной оговорки на пресс-конференции.\n\n9 ноября 1989 года чиновник Гюнтер Шабовски объявил о новых правилах выезда из ГДР, но на вопрос «когда это вступит в силу» ответил «немедленно, без задержек» — хотя имел в виду совсем другую дату. Через несколько часов толпы стояли у пропускных пунктов, и стену пришлось открыть.",
        "image_query": "Fall of the Berlin Wall", "lang": "en",
    },
    {
        "text": "🏛️ Клеопатра жила ближе по времени к запуску iPhone, чем к строительству Великой пирамиды Гизы.\n\nПирамида была построена около 2560 года до н.э., а Клеопатра родилась в 69 году до н.э. — между ними почти 2500 лет. От Клеопатры до нас — около 2090 лет.",
        "image_query": "Cleopatra", "lang": "en",
    },
    {
        "text": "🪣 В 1325 году города Болонья и Модена начали войну из-за украденного деревянного ведра.\n\nСолдаты Модены выкрали из колодца обычное дубовое ведро как акт издевательства. Болонья восприняла это как смертельное оскорбление и собрала армию в 32 000 человек. В битве при Цаппольно Модена, имея втрое меньше войск, разгромила болонцев — и ведро осталось в Модене, где висит в башне до сих пор.",
        "image_query": "War of the Bucket", "lang": "en",
    },
]

def main():
    assert len(SLOTS) == len(POSTS), f"{len(SLOTS)} слотов, {len(POSTS)} постов — должно совпадать"
    created = 0
    for (y, m, d, h), post in zip(SLOTS, POSTS):
        dt = datetime(y, m, d, h, 0, 0, tzinfo=RIGA_TZ)
        name = f"slot-{y}-{m:02d}-{d:02d}T{h:02d}.json"
        print(f"{name}: ищу фото «{post['image_query']}»...", end=" ", flush=True)
        img = wiki_image(post["image_query"], post.get("lang", "en"))
        print("✅" if img else "⚠️ нет фото")

        record = {
            "text": post["text"],
            **({"image_url": img} if img else {}),
            "scheduled_at": dt.isoformat(),
            "ai_generated": False,
            "manual_fill": True,
            "created_at": datetime.now(RIGA_TZ).isoformat(),
        }
        try:
            gh_create(f"queue/{name}", record, f"Fill 2 days: {name}")
            print(f"   ✅ создан queue/{name}")
            created += 1
        except Exception as e:
            print(f"   ❌ ошибка создания {name}: {e}")
        time.sleep(0.5)

    print(f"\nГотово: создано {created} из {len(SLOTS)} постов.")

if __name__ == "__main__":
    main()
