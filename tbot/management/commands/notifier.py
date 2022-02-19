from datetime import datetime, date, time
from time import sleep

from django.core.management.base import BaseCommand
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from based.models import Task, Schedule, User
from tbot.mybot import bot, logger


def get_kb(exc):
    button = InlineKeyboardButton
    keyboard = [
        button(text="✔", callback_data=f"done_{exc}"),
        button(text="💤", callback_data=f"snooze_{exc}")]
    reply_markup = InlineKeyboardMarkup([keyboard])
    return reply_markup


def is_quite(u: User) -> bool:
    if u.userstate == 7:
        logger.debug(f"User [{u.nick}] at quite hour")
        return True

    t_start = (int(u.sleepstart[:-3]) * 60 + int(u.sleepstart[3:])) * 60
    t_end = (int(u.sleepend[:-3]) * 60 + int(u.sleepend[3:])) * 60
    if t_end < t_start:
        t_end += 24 * 60 * 60

    start_of_day = datetime.combine(date.today(), time()).timestamp()
    timenow = datetime.now().timestamp() + u.timezone * 60 * 60

    if start_of_day + t_start < timenow < start_of_day + t_end:
        logger.debug(f"User [{u.nick}] at night time 💤")
        return True
    else:
        logger.debug(f"User [{u.nick}] at LOUD TIME")
        return False


def get_postpone(notitime):
    ttime = time(int(notitime[:-3]), int(notitime[3:]))
    pptime = datetime.combine(date.today(), ttime).timestamp()
    if pptime < datetime.now().timestamp():
        pptime += 60 * 60 * 24
    return pptime


def try_delete(userid, messid):
    try:
        if messid:
            bot.delete_message(userid, messid)
    except Exception as err:
        logger.warning(f"ERR DELETE {err} ... retrying ...")
        try_delete(userid, messid)


def try_send(userid, text, taskid):
    try:
        mess_id = bot.send_message(userid, text,
                                   reply_markup=get_kb(taskid)).message_id
        return mess_id
    except Exception as err:
        logger.warning(f"ERR SENDING {err} ... retrying ...")


def go_sched():
    """
        Все висящие шедулки кикаются (каждые две минуты сообщение переотправляется),
        А если время ночное, то переносятся на время срабатывания следующего дня.
        Если подошло время шедулки, значит тихий час окончен.
    """
    timenow = int(datetime.now().timestamp())
    scheds = Schedule.objects.filter(notitime__lte=timenow).all()
    if scheds:
        for sch in scheds:
            u = sch.userid
            tsk = sch.taskid
            if u.userstate == 7:
                u.userstate = 0
                u.save()
                logger.debug(f"User [{u.nick}] OFF quite time")

            if is_quite(u):
                ntime = tsk.notitime
                pptime = get_postpone(ntime)
                sch.notitime = pptime
                tsk.notinext = pptime
                sch.save()
                tsk.save()
                bot.edit_message_text(f"Отложено до {ntime}", sch.userid.userid, sch.mess_id)
                logger.debug(f"Task <{tsk.taskname}> postponed till morning ...")
            else:
                text = f"{tsk.taskname} {tsk.counts * int(sch.multiply)} {tsk.measure}"
                sch.notitime = timenow + 60 * 2
                sch.save()
                logger.debug(f"Task <{tsk.taskname}> k-k-k-kicking")
                try_delete(u.userid, sch.mess_id)
                sch.mess_id = try_send(u.userid, text, tsk.id)
                sch.save()


def go_task():
    """
        Если наступило время повторного срабатывания задачи, то создаётся шедулка.
        Если шедулка уже существует, наращивается множитель.
        Время повторного срабатывания задачи увеличивается на заданный период.
    """
    timenow = int(datetime.now().timestamp())
    tasks = Task.objects.filter(status=1).filter(notinext__lte=timenow).all()
    if tasks:
        for t in tasks:
            sch = Schedule.objects.filter(taskid=t).first()
            if sch:
                sch.multiply += 1
                sch.notitime = t.notinext
                sch.save()
                logger.debug(f"Task <{t.taskname}> overdosed! (multiplyier incremented) ")
            else:
                if not is_quite(t.userid):
                    sch = Schedule(userid=t.userid, taskid=t, notitime=timenow, multiply=1)
                    sch.save()
                    logger.debug(f"Schedule for task  <{t.taskname}> created ")

            t.notinext = timenow + t.repper
            t.save()


class Command(BaseCommand):
    help = 'deltaplan notifier'

    def handle(self, *args, **options):
        while True:
            try:
                go_sched()
                go_task()
                sleep(3)
            except Exception as err:
                print('WTF ERR', err)
