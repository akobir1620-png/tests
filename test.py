import os
import time
import threading
import random
import telebot
from docx import Document
from http.server import HTTPServer, BaseHTTPRequestHandler

BOT_TOKEN = "8663784103:AAH7I-cKLI30nE3J8NpojSllqOPXH6mCceM"
bot = telebot.TeleBot(BOT_TOKEN)

stop_flags = {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot ishlayapti!")
    def log_message(self, *args):
        pass


def parse_docx_tables(filename):
    tests = []
    doc = Document(filename)

    for table in doc.tables:
        rows = [row.cells[0].text.strip() for row in table.rows]

        if len(rows) < 5:
            continue

        question = rows[0]
        options = rows[1:5]

        if not question or not any(options):
            continue

        tests.append({
            'q': question,
            'options': options,
            'correct': 0
        })

    return tests


def shuffle_options(item):
    options = item['options'].copy()
    correct_answer = options[item['correct']]

    random.shuffle(options)

    new_correct = options.index(correct_answer)

    return {
        'q': item['q'],
        'options': options,
        'correct': new_correct
    }


def send_tests(message, tests):
    chat_id = message.chat.id
    stop_flags[chat_id] = False
    count = 0
    errors = 0

    for i, item in enumerate(tests):

        if stop_flags.get(chat_id):
            bot.send_message(
                chat_id,
                f"⛔ Testlar to'xtatildi!\n"
                f"✅ Yuborildi: {count} ta\n"
                f"📋 Qoldi: {len(tests) - count} ta"
            )
            stop_flags[chat_id] = False
            return

        try:
            shuffled = shuffle_options(item)

            bot.send_poll(
                chat_id=chat_id,
                question=shuffled['q'],
                options=shuffled['options'],
                type='quiz',
                correct_option_id=shuffled['correct'],
                is_anonymous=False,
                open_period=30,
                explanation=f"✅ To'g'ri javob - {shuffled['correct'] + 1}-variant!"
            )
            count += 1

            if count % 50 == 0:
                bot.send_message(
                    chat_id,
                    f"📊 Progress: {count}/{len(tests)} ta yuborildi..."
                )

            for _ in range(31):
                if stop_flags.get(chat_id):
                    break
                time.sleep(1)

        except telebot.apihelper.ApiTelegramException as e:
            errors += 1
            print(f"⚠️ Test #{i} xato: {e}")
            if 'Too Many Requests' in str(e):
                time.sleep(10)
            elif 'QUESTION_TOO_LONG' in str(e):
                print(f"   Savol juda uzun: {item['q'][:50]}...")
            continue
        except Exception as e:
            errors += 1
            print(f"⚠️ Kutilmagan xato #{i}: {e}")
            time.sleep(2)

    msg = f"🎉 Muvaffaqiyatli yuborildi: {count} ta test"
    if errors > 0:
        msg += f"\n⚠️ Xatoliklar: {errors} ta"
    bot.send_message(chat_id, msg)
    stop_flags[chat_id] = False


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Salom!\n\n"
        "📌 Buyruqlar:\n"
        "/test — Testlarni boshlash\n"
        "/stop — Testlarni to'xtatish"
    )


@bot.message_handler(commands=['test'])
def test_command(message):
    chat_id = message.chat.id

    if stop_flags.get(chat_id) is False:
        bot.send_message(
            chat_id,
            "⚠️ Testlar allaqachon yuborilmoqda!\n"
            "To'xtatish uchun /stop yuboring."
        )
        return

    docx_files = [f for f in os.listdir('.') if f.endswith('.docx')]

    if not docx_files:
        bot.send_message(
            chat_id,
            "❌ .docx fayl topilmadi!"
        )
        return

    all_tests = []
    for f in docx_files:
        tests = parse_docx_tables(f)
        all_tests.extend(tests)

    if not all_tests:
        bot.send_message(
            chat_id,
            "❌ Faylda testlar topilmadi!"
        )
        return

    bot.send_message(
        chat_id,
        f"📚 Jami {len(all_tests)} ta test topildi. Yuborilmoqda...\n"
        f"⏱ Har bir savolga 30 sekund vaqt beriladi.\n"
        f"⛔ To'xtatish uchun /stop yuboring."
    )

    t = threading.Thread(target=send_tests, args=(message, all_tests))
    t.daemon = True
    t.start()


@bot.message_handler(commands=['stop'])
def stop_command(message):
    chat_id = message.chat.id

    if stop_flags.get(chat_id) is False:
        stop_flags[chat_id] = True
        bot.send_message(
            chat_id,
            "⏳ To'xtatilmoqda... Joriy savol tugagach to'xtaydi."
        )
    else:
        bot.send_message(
            chat_id,
            "ℹ️ Hozir aktiv test yo'q."
        )


if __name__ == '__main__':
    threading.Thread(
        target=lambda: HTTPServer(('0.0.0.0', 8080), Handler).serve_forever(),
        daemon=True
    ).start()

    docx_files = [f for f in os.listdir('.') if f.endswith('.docx')]
    print(f"🤖 Bot ishga tushdi!")
    print(f"📂 Topilgan .docx fayllar: {len(docx_files)} ta")
    for f in docx_files:
        tests = parse_docx_tables(f)
        print(f"   • {f}: {len(tests)} ta test")

    if not docx_files:
        print("⚠️  DIQQAT: .docx fayllar topilmadi!")
        print("   Bot bilan bir papkaga .docx fayl qo'ying.")

    try:
        bot.delete_webhook()
    except Exception:
        pass

    bot.infinity_polling(skip_pending=True)
