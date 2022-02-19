import re

from django.core.management.base import BaseCommand
from telegram.ext import Updater, Filters, CommandHandler, MessageHandler, \
    CallbackQueryHandler

from tbot.mybot import bot
from tbot.utils import start, add_task, go_task, details_task, show_list, \
    force_dnd, get_sched, set_tings, do_callback


class Command(BaseCommand):
    help = 'deltaplan telebot'

    def handle(self, *args, **options):
        updater = Updater(
            bot=bot,
            use_context=True,
        )

        updater.dispatcher.add_handler(CommandHandler('start', start))
        updater.dispatcher.add_handler(CommandHandler('add', add_task))
        updater.dispatcher.add_handler(CommandHandler('list', show_list))
        updater.dispatcher.add_handler(CommandHandler('dnd', force_dnd))
        updater.dispatcher.add_handler(CommandHandler('sched', get_sched))
        updater.dispatcher.add_handler(CommandHandler('sets', set_tings))
        updater.dispatcher.add_handler(MessageHandler(
            Filters.regex(re.compile(r'dnd', re.IGNORECASE)), force_dnd))
        updater.dispatcher.add_handler(MessageHandler(Filters.regex('^\d+$'), details_task))
        updater.dispatcher.add_handler(MessageHandler(Filters.text, go_task))
        updater.dispatcher.add_handler(CallbackQueryHandler(do_callback))

        updater.start_polling()
        updater.idle()
